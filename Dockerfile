# Use python-slim as a base to keep image size reasonable
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    FLASK_APP=app.py

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /code

# Copy requirements and install
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy all application files
COPY . /code/

# Create instance, temp, and flask_session directories and ensure they are writable
RUN mkdir -p /code/instance /code/temp /code/flask_session && \
    chmod -R 777 /code/instance /code/temp /code/flask_session

# Expose the Flask port
EXPOSE 7860

# Run the Flask app
CMD ["python", "app.py"]
