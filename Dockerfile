# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app

# Copy entrypoint OUTSIDE /app so the bind mount .:/app won't hide it
COPY docker/entrypoint.sh /entrypoint.sh
# Set permissions while still root
RUN chmod 0755 /entrypoint.sh

# Create non-root user (switch AFTER perms are set)
RUN useradd -m djangouser
USER djangouser

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
