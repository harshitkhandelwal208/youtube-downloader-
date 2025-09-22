FROM python:3.11-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything (including cookies.txt if present)
COPY . /app/

# Install deps
RUN pip install --no-cache-dir flask yt-dlp gunicorn

# Run app
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app", "--workers=2"]
