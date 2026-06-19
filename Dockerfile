# OSS Compliance Web Application v1.0
# Unified configuration interface, remote repository scanning, enhanced endpoint analysis
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc git \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Install Playwright browsers in a shared location
RUN mkdir -p /ms-playwright && chmod 777 /ms-playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium

# Copy application code
COPY . .

# Create necessary directories and set permissions in single layer
# Note: config directory is included in COPY above
RUN mkdir -p reports uploads cache logs instance && groupadd -r appuser && useradd -r -g appuser appuser && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose Flask port
EXPOSE 5001

# Set environment variables
ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--reload", "--workers", "2", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "app:app"]