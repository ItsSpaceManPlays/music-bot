FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80 443 8080
EXPOSE 50000-65535/udp

CMD ["python", "main.py"]