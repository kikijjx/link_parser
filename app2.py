import argparse
import asyncio
import httpx
from urllib.parse import urljoin, urlparse
import aio_pika
from bs4 import BeautifulSoup
import sys
import signal
from dotenv import load_dotenv
import os

load_dotenv()

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'urls')

async def fetch_page_links(url):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            page_content = response.text
            soup = BeautifulSoup(page_content, 'html.parser')
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            links = []

            title_tag = soup.find('title')
            page_title = title_tag.text if title_tag else "No Title"
            print(f"Processing page: {page_title} ({url})")

            for tag in soup.find_all(['a', 'img', 'video', 'audio']):
                href = tag.get('href')
                src = tag.get('src')

                if href:
                    full_url = urljoin(base_url, href)
                    if full_url.startswith(base_url):
                        link_text = tag.get_text(strip=True) or "No Text"
                        print(f"Found link: '{link_text}' -> {full_url}")
                        links.append(full_url)

                if src:
                    full_url = urljoin(base_url, src)
                    if full_url.startswith(base_url):
                        link_text = tag.get_text(strip=True) or "No Text"
                        print(f"Found link: '{link_text}' -> {full_url}")
                        links.append(full_url)

            if not links:
                print(f"No internal links found on {url}")
            return links

    except httpx.RequestError as e:
        print(f"Error fetching URL {url}: {e}")
        return []

async def process_message(channel, body):
    url = body.decode()
    print(f"Processing URL: {url}")
    links = await fetch_page_links(url)

    if links:
        for link in links:
            await send_link_to_queue(channel, link)
            print(f"Link sent: {link}")
    else:
        print(f"No internal links found on {url}")

async def send_link_to_queue(channel, link):
    await channel.default_exchange.publish(
        aio_pika.Message(body=link.encode()),
        routing_key=RABBITMQ_QUEUE
    )

async def start_consumer():
    connection = await aio_pika.connect_robust(
        f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
    )
    channel = await connection.channel()
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                await process_message(channel, message.body)

def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    asyncio.run(start_consumer())
