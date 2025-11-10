FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    mkvtoolnix \
    mediainfo \
    libmediainfo0v5 \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m botuser
USER botuser

COPY . .

EXPOSE 5000

CMD ["python", "-m", "bot"]
