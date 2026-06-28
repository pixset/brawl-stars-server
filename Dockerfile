FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Game server port (TCP) + HTTP port
EXPOSE 9339
EXPOSE 8080

CMD ["python", "start.py"]
