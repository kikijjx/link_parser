
## Запуск

1. Установить виртуальное окружение:
```bash
python -m venv venv
```
2. Запустить окружение:
```bash
venv/scripts/activate
```
3. Установить зависимости:
```bash
pip install -r requirements.txt
```
4. Запустить RabbitMQ
```bash
docker-compose up --build
```

6. Отредактировать файл .env (пример в файле .env.example):
```bash
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=urls
```
6. Запустить приложение:
```bash
python app1.py <LINK>
python app2.py
```

### Примеры:
```bash
python app1.py https://habr.com/ru/articles/865478/
```

