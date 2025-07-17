# We use the lightweight official Python base
FROM python:3.10-slim

# set the working directory inside of the container
WORKDIR /app

# install system level dependencies, only the necessary ones
# and clean up cached package lists
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libxrender1 libsm6 libxext6 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# copy Python packages
COPY requirements.txt .

# install Python packages
RUN pip install --no-cache-dir -r requirements.txt 

# copy all other files
COPY . .

# set environment variables for the app to run in headless mode
ENV HEADLESS=1 \
    MPLBACKEND=Agg \
    IMAGE_DIR=/app/shared-images \
    PYTHONUNBUFFERED=1

# automatically run the app and logs(unbuffered)
CMD [ "python", "-u", "main.py" ]
