FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY auto_clip ./auto_clip

RUN pip install --no-cache-dir . yt-dlp

EXPOSE 8080

CMD ["auto-clip-processor", "--host", "0.0.0.0", "--port", "8080", "--work-dir", "/data/artifacts"]
