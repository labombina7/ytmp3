FROM python:3.11-alpine

RUN apk add --no-cache ffmpeg curl

RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod +x /usr/local/bin/yt-dlp

WORKDIR /app

COPY app.py .
COPY requirements.txt .
COPY public ./public  
COPY sync_ytmusic.py .
COPY headers_auth.json ./headers_auth.json

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5558

CMD ["python", "app.py"]