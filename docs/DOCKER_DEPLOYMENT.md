# Docker Deployment Guide
## OSS Compliance Web Application

**Version:** 1.1  
**Last Updated:** 2026-06-12  
**Application Version:** 1.0

---

## Overview

This guide covers deploying the OSS Compliance Web Application using Docker and Docker Compose with the new YAML-based configuration system.

---

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- Git (for cloning repository)

---

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd oss-compliance-webapp
```

### 2. Create Configuration

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Create configuration file
cat > config/app_config.yaml << 'EOF'
version: '1.0'

artifactory:
  base_url: isgedge.artifactory.cec.lab.emc.com
  virtual_repos:
    docker: isgedge-docker-virtual
    go: isgedge-go-virtual
    helm: isgedge-helm-virtual
    maven: isgedge-maven-virtual
    npm: isgedge-npm-virtual
    pypi: isgedge-pypi-virtual
    rpm: isgedge-rpm-virtual

github_instances:
  eos2git:
    name: ISG-Edge
    api_url: https://eos2git.cec.lab.emc.com/api/v3
    org: ISG-Edge
    users:
    - username: default_user
      token_encrypted: ''  # Add encrypted token via web UI
      email: ''

jenkins:
  user: jenkins-user
  token_encrypted: ''  # Add encrypted token via web UI
  urls:
  - https://jenkins.example.com
  pr_validation_job: oss-compliance-validation

whitelist_urls:
  - github.com/fusion-e
  - eos2git.cec.lab.emc.com/ISG-Edge

app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
  debug_logging: true
EOF
```

### 3. Generate Encryption Key

```bash
# Generate encryption key and set as environment variable
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"
```

### 4. Build and Run

```bash
# Build image
docker-compose build

# Start container
docker-compose up -d

# View logs
docker-compose logs -f
```

### 5. Access Application

Open browser to: `http://localhost:5001`

---

## Configuration Architecture

### File Structure

```
oss-compliance-webapp/
├── config/
│   └── app_config.yaml          # Main configuration (contains encrypted tokens)
├── Dockerfile                    # Image definition
├── docker-compose.yml            # Container orchestration
└── .dockerignore                 # Files excluded from image
```

### Configuration Separation

**In Docker Image:**
- Application code
- Python dependencies
- Default configuration structure

**Mounted as Volumes:**
- `config/app_config.yaml` - Configuration with encrypted tokens
- `reports/` - Generated reports (persistent)
- `uploads/` - Uploaded files (persistent)
- `cache/` - Repository cache (persistent)
- `instance/` - Database files (persistent)

**Environment Variables:**
- `ENCRYPTION_KEY` - Required for token encryption/decryption
- `DEBUG_LOGGING` - Enable/disable debug logging
- `SECRET_KEY` - Flask secret key (optional, has default)
- `DATABASE_URL` - Database connection (optional, defaults to SQLite)

---

## Configuration Files

### `config/app_config.yaml`

```yaml
version: "1.0"

artifactory:
  base_url: "isgedge.artifactory.cec.lab.emc.com"
  virtual_repos:
    docker: "isgedge-docker-virtual"
    go: "isgedge-go-virtual"
    helm: "isgedge-helm-virtual"
    maven: "isgedge-maven-virtual"
    npm: "isgedge-npm-virtual"
    pypi: "isgedge-pypi-virtual"
    rpm: "isgedge-rpm-virtual"

github_instances:
  eos2git:
    name: "EOS2Git"
    api_url: "https://eos2git.cec.lab.emc.com/api/v3"
    org: "ISG-Edge"
    users:
      - username: "default_user"
        token_encrypted: "gAAAAABh..."  # Encrypted token (add via web UI)
        email: ""

jenkins:
  user: "jenkins-user"
  token_encrypted: "gAAAAABh..."  # Encrypted token (add via web UI)
  urls:
    - "https://jenkins.example.com"
  pr_validation_job: "oss-compliance-validation"

whitelist_urls:
  - "https://github.com"
  - "https://gitlab.com"

app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
  debug_logging: true
```

---

## Docker Compose Configuration

### `docker-compose.yml`

```yaml
version: '3.8'

services:
  oss-compliance-webapp:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: oss-compliance-webapp
    image: oss-compliance-webapp:1.0
    ports:
      - "5001:5001"
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=production
      - FLASK_DEBUG=${FLASK_DEBUG:-True}
      - PYTHONUNBUFFERED=1
      - SSL_VERIFY=false
      - ENCRYPTION_KEY=${ENCRYPTION_KEY:-your-secret-encryption-key-here}
      - DEBUG_LOGGING=${DEBUG_LOGGING:-true}
    volumes:
      # Mount configuration file (contains encrypted tokens)
      - ./config/app_config.yaml:/app/config/app_config.yaml:ro
      # Mount reports directory for persistence
      - ./reports:/app/reports
      # Mount uploads directory
      - ./uploads:/app/uploads
      # Mount cache directory
      - ./cache:/app/cache
      # Mount database directory for persistence
      - ./instance:/app/instance
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5001/')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - oss-compliance-network

networks:
  oss-compliance-network:
    driver: bridge
```

---

## Multi-Environment Deployment

### Development Environment

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  oss-compliance-webapp:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=${FLASK_DEBUG:-True}
      - PYTHONUNBUFFERED=1
      - SSL_VERIFY=false
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - DEBUG_LOGGING=${DEBUG_LOGGING:-true}
    volumes:
      - ./config/app_config.dev.yaml:/app/config/app_config.yaml:ro
      - ./reports:/app/reports
      - ./uploads:/app/uploads
      - ./cache:/app/cache
      - ./instance:/app/instance
```

Run with:
```bash
docker-compose -f docker-compose.dev.yml up
```

**Note**: Debug logging can now be controlled via the web interface in the Application Settings section, eliminating the need for development-specific Docker configurations.

### Production Environment

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  oss-compliance-webapp:
    image: oss-compliance-webapp:1.0
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=${FLASK_DEBUG:-False}
      - PYTHONUNBUFFERED=1
      - SSL_VERIFY=false
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - DEBUG_LOGGING=${DEBUG_LOGGING:-false}
    volumes:
      - ./config/app_config.prod.yaml:/app/config/app_config.yaml:ro
      - ./reports:/app/reports
      - ./uploads:/app/uploads
      - ./cache:/app/cache
      - ./instance:/app/instance
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

Run with:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Building the Image

### Build Locally

```bash
# Build with default tag
docker-compose build

# Build with custom tag
docker build -t oss-compliance-webapp:0.5.0 .

# Build with specific platform
docker build --platform linux/amd64 -t oss-compliance-webapp:0.5.0 .
```

### Build for Multiple Platforms

```bash
# Enable buildx
docker buildx create --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t oss-compliance-webapp:0.5.0 \
  --push \
  .
```

### Push to Registry

```bash
# Tag for registry
docker tag oss-compliance-webapp:0.5.0 your-registry.com/oss-compliance-webapp:0.5.0

# Push to registry
docker push your-registry.com/oss-compliance-webapp:0.5.0
```

---

## Running the Container

### Start Container

```bash
# Start in foreground
docker-compose up

# Start in background
docker-compose up -d

# Start with rebuild
docker-compose up --build -d
```

### Stop Container

```bash
# Stop gracefully
docker-compose stop

# Stop and remove
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs

```bash
# Follow logs
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# View logs for specific time
docker-compose logs --since 30m
```

### Execute Commands

```bash
# Open shell in container
docker-compose exec oss-compliance-webapp bash

# Run Python script
docker-compose exec oss-compliance-webapp python test_config.py

# Check configuration
docker-compose exec oss-compliance-webapp python -c "from config_manager import get_config_manager; print(get_config_manager().get_config_summary())"
```

---

## Health Checks

### Container Health

```bash
# Check container health
docker-compose ps

# View health check logs
docker inspect --format='{{json .State.Health}}' oss-compliance-webapp | jq
```

### Application Health

```bash
# Test application endpoint
curl http://localhost:5001/

# Test with health check
curl http://localhost:5001/health
```

---

## Troubleshooting

### Configuration Not Found

**Error:**
```
FileNotFoundError: Configuration file not found: config/app_config.yaml
```

**Solution:**
```bash
# Ensure config file exists
ls -la config/app_config.yaml

# Check volume mount
docker-compose exec oss-compliance-webapp ls -la /app/config/

# Recreate container with volumes
docker-compose down
docker-compose up -d
```

### Environment Variables Not Set

**Error:**
```
Warning: Generated new encryption key: gAAAAABh...
```

**Solution:**
```bash
# Set ENCRYPTION_KEY environment variable
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Pass to docker-compose
docker-compose up

# Or add to docker-compose.yml
environment:
  - ENCRYPTION_KEY=your-encryption-key-here
```

### Permission Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/app/reports'
```

**Solution:**
```bash
# Fix permissions on host
chmod -R 755 reports uploads cache instance

# Or run as root (not recommended)
docker-compose exec -u root oss-compliance-webapp chown -R appuser:appuser /app
```

### Port Already in Use

**Error:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:5001: bind: address already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :5001

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "5002:5001"
```

### Container Keeps Restarting

```bash
# Check logs
docker-compose logs --tail=50

# Check health status
docker-compose ps

# Disable restart policy temporarily
docker-compose up --no-start
docker-compose start
```

---

## Security Best Practices

### 1. Secrets Management

**Never commit secrets to Git:**
```bash
# Add to .gitignore
echo "config/app_config.yaml" >> .gitignore
echo "config/app_config.*.yaml" >> .gitignore
echo "!config/app_config.example.yaml" >> .gitignore
```

**Use Docker secrets (Swarm mode):**
```yaml
services:
  oss-compliance-webapp:
    secrets:
      - encryption_key

secrets:
  encryption_key:
    external: true
```

**Set ENCRYPTION_KEY via environment variable:**
```bash
# Set before starting container
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
docker-compose up
```

### 2. Non-Root User

The Dockerfile already runs as non-root user `appuser`:
```dockerfile
USER appuser
```

### 3. Read-Only Volumes

Mount configuration as read-only:
```yaml
volumes:
  - ./config/app_config.yaml:/app/config/app_config.yaml:ro
```

### 4. Network Isolation

Use Docker networks for isolation:
```yaml
networks:
  oss-compliance-network:
    driver: bridge
    internal: true  # No external access
```

### 5. Resource Limits

Set resource limits:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

---

## Monitoring

### Container Metrics

```bash
# View resource usage
docker stats oss-compliance-webapp

# View container processes
docker-compose top
```

### Application Logs

```bash
# Follow application logs
docker-compose logs -f oss-compliance-webapp

# Export logs
docker-compose logs > app.log
```

### Health Monitoring

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' oss-compliance-webapp

# Get health check history
docker inspect --format='{{json .State.Health}}' oss-compliance-webapp | jq
```

---

## Backup and Restore

### Backup

```bash
# Backup volumes
docker run --rm \
  -v oss-compliance-webapp_reports:/data/reports \
  -v oss-compliance-webapp_instance:/data/instance \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/oss-compliance-backup-$(date +%Y%m%d).tar.gz /data

# Backup configuration
tar czf config-backup-$(date +%Y%m%d).tar.gz config/
```

### Restore

```bash
# Restore volumes
docker run --rm \
  -v oss-compliance-webapp_reports:/data/reports \
  -v oss-compliance-webapp_instance:/data/instance \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/oss-compliance-backup-20260612.tar.gz -C /

# Restore configuration
tar xzf config-backup-20260612.tar.gz
```

---

## Upgrading

### Upgrade Application

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose build

# Stop old container
docker-compose down

# Start new container
docker-compose up -d

# Verify
docker-compose logs -f
```

### Upgrade with Zero Downtime

```bash
# Build new image with new tag
docker build -t oss-compliance-webapp:1.0 .

# Update docker-compose.yml with new tag
sed -i 's/0.6.0/1.0/g' docker-compose.yml

# Start new container (old still running)
docker-compose up -d --no-deps --scale oss-compliance-webapp=2 oss-compliance-webapp

# Stop old container
docker-compose up -d --no-deps --scale oss-compliance-webapp=1 oss-compliance-webapp
```

---

## Performance Tuning

### Gunicorn Workers

Adjust workers in Dockerfile:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--threads", "4", "app:app"]
```

Formula: `workers = (2 x CPU cores) + 1`

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
    reservations:
      cpus: '2'
      memory: 2G
```

### Volume Performance

Use named volumes for better performance:
```yaml
volumes:
  reports:
  uploads:
  cache:
  instance:

services:
  oss-compliance-webapp:
    volumes:
      - reports:/app/reports
      - uploads:/app/uploads
      - cache:/app/cache
      - instance:/app/instance
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Registry
        uses: docker/login-action@v2
        with:
          registry: your-registry.com
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: your-registry.com/oss-compliance-webapp:latest
```

---

## Appendix

### Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Test Configuration in Container

```bash
docker-compose exec oss-compliance-webapp python test_config.py
```

---

**Document Status**: Complete  
**Last Updated**: 2026-06-12  
**Next Review**: 2026-09-12
