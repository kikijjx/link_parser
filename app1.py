import argparse
import httpx
from urllib.parse import urljoin, urlparse
import pika
from bs4 import BeautifulSoup
import sys
from dotenv import load_dotenv
import os

load_dotenv()

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'urls')

def retrieve_internal_links(page_url):
    try:
        with httpx.Client() as client:
            response = client.get(page_url)
            response.raise_for_status()
            page_content = response.text
            soup = BeautifulSoup(page_content, 'html.parser')
            base_url = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"
            links = []

            # Логирование информации о текущей странице
            title_tag = soup.find('title')
            page_title = title_tag.text if title_tag else "No Title"
            print(f"Processing page: {page_title} ({page_url})")

            # Поиск всех ссылок (a, img, video, audio)
            for tag in soup.find_all(['a', 'img', 'video', 'audio']):
                resource = tag.get('href') or tag.get('src')
                if resource:
                    full_url = urljoin(base_url, resource)
                    if full_url.startswith(base_url):
                        link_text = tag.get_text(strip=True) or "No Text"
                        print(f"Found link: '{link_text}' -> {full_url}")
                        links.append(full_url)

            return links
    except httpx.RequestError as e:
        print(f"Error fetching {page_url}: {e}")
        return []

def send_links_to_queue(url):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
        )
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

        links = retrieve_internal_links(url)
        if links:
            for link in links:
                channel.basic_publish(
                    exchange='',
                    routing_key=RABBITMQ_QUEUE,
                    body=link,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                print(f"Link sent: {link}")
        else:
            print(f"No internal links found at {url}")

        connection.close()
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error connecting to RabbitMQ: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help="URL to parse and send links from")

    args = parser.parse_args()

    send_links_to_queue(args.url)
