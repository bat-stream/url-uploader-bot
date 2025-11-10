# -------------------------------
# Dockerfile for Python Telegram Bot
# -------------------------------
FROM python:3.11-slim

# Disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    mkvtoolnix \
    mediainfo \
    libmediainfo0v5 \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose port if Flask server runs (adjust if needed)
EXPOSE 5000

# Default command to start your bot
CMD ["python", "-m", "bot"]
