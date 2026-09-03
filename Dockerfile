FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application files
COPY . .

# Environment variables
ENV PORT=8080
ENV HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "server.py"]
