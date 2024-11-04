FROM python:3.9-slim

RUN apt-get update && apt-get upgrade
    

RUN apt-get install -y ffmpeg mosquitto && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app

RUN mkdir -p source_test_videos clips

COPY server.py .
COPY test_videos.json .
COPY mosquitto.conf /etc/mosquitto/mosquitto.conf

EXPOSE 1883

CMD ["sh", "-c", "mosquitto -c /etc/mosquitto/mosquitto.conf & python server.py"]