# Use a slim Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed, e.g., unzip)
RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements if you have them (recommended)
# If you don’t have requirements.txt, we’ll just install Flask
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Expose port 3000
EXPOSE 3000

# Run the Flask server
CMD ["python", "server.py"]
