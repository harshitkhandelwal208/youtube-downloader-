# Dockerfile
FROM python:3.11-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set working dir
WORKDIR /app

# Copy files
COPY app.py /app/

# Install deps
RUN pip install --no-cache-dir flask yt-dlp gunicorn

# Run with gunicorn on $PORT (Render sets PORT)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app", "--workers=2"]
