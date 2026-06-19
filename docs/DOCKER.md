# Docker Deployment Guide for OSS Compliance Web Application

## Quick Start

### Using Docker Compose (Recommended for Local Development)

1. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - URL: http://localhost:5001

### Manual Docker Build

1. **Build the Docker image:**
   ```bash
   docker build -t oss-compliance-webapp:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -p 5001:5001 \
     --env-file .env \
     -v $(pwd)/reports:/app/reports \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/cache:/app/cache \
     --name oss-compliance-webapp \
     oss-compliance-webapp:latest
   ```

## GitHub Container Registry (ghcr.io)

### Automated Build and Push

The application includes a GitHub Actions workflow that automatically builds and pushes Docker images to GitHub Container Registry when you push to the main/master branch or create version tags.

### Manual Push to GitHub Container Registry

1. **Authenticate with GitHub Container Registry:**
   ```bash
   echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
   ```

   Or using GitHub CLI:
   ```bash
   gh auth login
   gh auth token
   ```

2. **Build and tag the image:**
   ```bash
   docker build -t ghcr.io/jpurcell3/oss-scanner:latest .
   docker tag ghcr.io/jpurcell3/oss-scanner:latest ghcr.io/jpurcell3/oss-scanner:v1.0.0
   ```

3. **Push to GitHub Container Registry:**
   ```bash
   docker push ghcr.io/jpurcell3/oss-scanner:latest
   docker push ghcr.io/jpurcell3/oss-scanner:v1.0.0
   ```

### Pull and Run from GitHub Container Registry

1. **Pull the image:**
   ```bash
   docker pull ghcr.io/jpurcell3/oss-scanner:latest
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -p 5001:5001 \
     --env-file .env \
     -v $(pwd)/reports:/app/reports \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/cache:/app/cache \
     --name oss-compliance-webapp \
     ghcr.io/jpurcell3/oss-scanner:latest
   ```

## Environment Variables

The container expects the same environment variables as the local application. Key variables:

- `GITHUB_INSTANCES` - Comma-separated list of GitHub instance IDs
- `GITHUB_INSTANCE_<id>_API_URL` - API URL for each GitHub instance
- `GITHUB_INSTANCE_<id>_TOKEN` - GitHub token for each instance
- `GITHUB_INSTANCE_<id>_ORG` - Organization name for each instance
- `JENKINS_USER` - Jenkins username
- `JENKINS_API_TOKEN` - Jenkins API token
- `JENKINS_URLS` - Comma-separated Jenkins server URLs
- `ARTIFACTORY_BASE` - Artifactory base URL
- `SSL_VERIFY` - SSL verification (true/false)

## Volume Mounts

- `/app/reports` - Scan reports output
- `/app/uploads` - File upload directory
- `/app/cache` - Repository cache
- `/app/.env` - Environment configuration (read-only)

## Health Check

The container includes a health check that monitors the application:
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Start period**: 40 seconds
- **Retries**: 3

Check health status:
```bash
docker inspect --format='{{.State.Health.Status}}' oss-compliance-webapp
```

## Troubleshooting

### View Logs
```bash
docker logs -f oss-compliance-webapp
```

### Enter Container Shell
```bash
docker exec -it oss-compliance-webapp /bin/bash
```

### Rebuild Without Cache
```bash
docker-compose build --no-cache
docker-compose up
```

### Clean Up
```bash
docker-compose down
docker system prune -a
```

## Production Deployment

For production deployment, consider:

1. **Use specific version tags** instead of `latest`
2. **Configure resource limits** in docker-compose.yml
3. **Use secrets management** for sensitive data
4. **Enable HTTPS** with reverse proxy (nginx/traefik)
5. **Set up log aggregation** (ELK, CloudWatch, etc.)
6. **Configure backup strategy** for reports and cache

## Security Considerations

- Container runs as non-root user `appuser`
- Minimal Python 3.11-slim base image
- No unnecessary packages installed
- Health checks enabled
- Read-only .env file mount
- Regular security updates recommended