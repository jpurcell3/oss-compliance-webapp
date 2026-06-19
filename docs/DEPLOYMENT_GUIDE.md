# Deployment Guide
## OSS Compliance Web Application

**Version:** 1.2  
**Last Updated:** 2026-06-12  
**Application Version:** 1.0

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Deployment](#local-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Production Deployment](#production-deployment)
6. [Database Migration](#database-migration)
7. [Configuration](#configuration)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 20GB SSD
- **OS**: Linux (Ubuntu 20.04+), Windows 10+, macOS 10.15+
- **Python**: 3.9 or higher
- **Network**: Internet connectivity for external API access

#### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 50GB+ SSD
- **OS**: Linux (Ubuntu 22.04 LTS recommended)
- **Python**: 3.10 or higher
- **Network**: 1+ Gbps with low latency

### Software Dependencies

#### Required Software
- **Python 3.9+**: Application runtime
- **Git**: Version control (for remote scanning)
- **SQLite 3**: Database (default) or PostgreSQL 14+
- **Docker 20+**: Containerization (optional)
- **Docker Compose 2+**: Multi-container management (optional)

#### External Services
- **Artifactory**: Artifact repository (existing instance)
- **GitHub Enterprise**: Repository hosting (for remote scanning)
- **Jenkins**: CI/CD server (for PR validation)
- **Reverse Proxy**: Nginx/Apache (for production)

### Network Requirements

#### Required Ports
- **5001**: Application HTTP port (configurable)
- **443**: HTTPS (production)
- **80**: HTTP redirect (production)

#### External Access
- **GitHub API**: api.github.com or enterprise instance
- **Jenkins API**: Jenkins server URL
- **Artifactory**: Artifactory server URL

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd oss-compliance-webapp
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
mkdir -p config
cp config/app_config.example.yaml config/app_config.yaml
nano config/app_config.yaml  # Edit with your configuration
```

### 5. Generate Encryption Key

Generate and set the encryption key for credential security:

```bash
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

**Important**: Store this key securely. If lost, encrypted credentials cannot be decrypted. Add to your shell profile or set as environment variable before running the application.

### 6. Initialize Database

```bash
python init_db.py
```

### 7. Run Database Migrations

```bash
python migrate_add_pr_submissions.py
```

---

## Local Deployment

### 1. Start Application

```bash
python app.py
```

The application will be available at `http://localhost:5001`

### 2. Verify Installation

```bash
curl http://localhost:5001/
```

### Configuration for Local Deployment

Create `config/app_config.yaml`:

```yaml
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
```

Set environment variable for encryption key:
```bash
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

---

## Docker Deployment

### Dockerfile

The application includes a Dockerfile for containerization (v1.0 with configurable debug logging):

```dockerfile
FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc git && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org Flask==2.3.3 Flask-SQLAlchemy==3.0.5 PyYAML==6.0.1 requests==2.31.0 urllib3==2.0.3 werkzeug==2.3.7 cryptography==41.0.7 gunicorn==21.2.0

COPY . .

RUN mkdir -p reports uploads cache logs instance && groupadd -r appuser && useradd -r -g appuser appuser && chown -R appuser:appuser /app

USER appuser

EXPOSE 5001

ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--reload", "--workers", "2", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
```

**Key Changes:**
- Removed `python-dotenv` dependency (no longer needed)
- All configuration now in `config/app_config.yaml`
- Tokens encrypted and stored in YAML

### Build Docker Image

```bash
docker build -t oss-compliance-webapp:latest .
```

### Run Container

```bash
# Generate encryption key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Run container
docker run -d \
  --name oss-compliance \
  -p 5001:5001 \
  -e ENCRYPTION_KEY=$ENCRYPTION_KEY \
  -e DEBUG_LOGGING=true \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/reports:/app/reports \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/instance:/app/instance \
  oss-compliance-webapp:latest
```

### Docker Compose Deployment

Create `docker-compose.yml`:

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
      - PYTHONUNBUFFERED=1
      - SSL_VERIFY=false
      - ENCRYPTION_KEY=${ENCRYPTION_KEY:-your-secret-encryption-key-here}
      - DEBUG_LOGGING=${DEBUG_LOGGING:-true}
    volumes:
      - ./config/app_config.yaml:/app/config/app_config.yaml:ro
      - ./reports:/app/reports
      - ./uploads:/app/uploads
      - ./cache:/app/cache
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

**Configuration:**
- All configuration in `config/app_config.yaml`
- Tokens encrypted and stored in YAML
- Add tokens via web UI at http://localhost:5001/config

#### Deploy with Docker Compose

```bash
docker-compose up -d
```

#### View Logs

```bash
docker-compose logs -f app
```

#### Stop Services

```bash
docker-compose down
```

---

## Production Deployment

### Production Architecture

```
Internet → Load Balancer → Nginx → Gunicorn → Flask App → PostgreSQL
                                    ↓
                              Static Files
```

### 1. Server Preparation

#### Ubuntu/Debian Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib git

# Create application user
sudo useradd -r -s /bin/false osscompliance
sudo mkdir -p /opt/oss-compliance
sudo chown osscompliance:osscompliance /opt/oss-compliance
```

### 2. Application Setup

```bash
# Switch to application user
sudo -u osscompliance -i

# Navigate to application directory
cd /opt/oss-compliance

# Clone repository
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Setup environment
mkdir -p config
cp config/app_config.example.yaml config/app_config.yaml
nano config/app_config.yaml  # Configure for production
```

### 3. PostgreSQL Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE oss_compliance;
CREATE USER oss_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE oss_compliance TO oss_user;
\q
```

Set DATABASE_URL environment variable:

```bash
export DATABASE_URL=postgresql://oss_user:secure_password@localhost/oss_compliance
```

### 4. Initialize Database

```bash
python init_db.py
python migrate_add_pr_submissions.py
```

### 5. Gunicorn Configuration

Create `/etc/systemd/system/oss-compliance.service`:

```ini
[Unit]
Description=OSS Compliance Web Application
After=network.target postgresql.service

[Service]
User=osscompliance
Group=osscompliance
WorkingDirectory=/opt/oss-compliance
Environment="PATH=/opt/oss-compliance/venv/bin"
Environment="ENCRYPTION_KEY=your-encryption-key-here"
Environment="DATABASE_URL=postgresql://oss_user:secure_password@localhost/oss_compliance"
Environment="DEBUG_LOGGING=false"
ExecStart=/opt/oss-compliance/venv/bin/gunicorn \
    --workers 4 \
    --bind unix:oss-compliance.sock \
    --timeout 120 \
    --access-logfile /var/log/oss-compliance/access.log \
    --error-logfile /var/log/oss-compliance/error.log \
    app:app

Restart=always

[Install]
WantedBy=multi-user.target
```

### 6. Nginx Configuration

Create `/etc/nginx/sites-available/oss-compliance`:

```nginx
upstream oss_compliance {
    server unix:/opt/oss-compliance/oss-compliance.sock;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";

    # Application Proxy
    location / {
        proxy_pass http://oss_compliance;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Static Files
    location /static {
        alias /opt/oss-compliance/static;
        expires 30d;
    }

    # Reports Directory
    location /reports {
        alias /opt/oss-compliance/reports;
        internal;
    }
}
```

Enable site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/oss-compliance /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Start Services

```bash
# Start Gunicorn service
sudo systemctl start oss-compliance
sudo systemctl enable oss-compliance

# Check status
sudo systemctl status oss-compliance
```

### 8. SSL Certificate Setup

#### Using Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Database Migration

### Migration Scripts

The application includes migration scripts for database schema updates:

#### Current Migration (v0.5.0)

```bash
python migrate_add_pr_submissions.py
```

This creates the `pr_submissions` table for PR tracking with the following features:
- Foreign key relationship to reports table
- GitHub Enterprise compliance tracking
- Jenkins build status monitoring
- Multi-user support tracking
- Comprehensive error logging

#### Database Initialization

```bash
python init_db.py
```

Initializes the database with required tables:
- `reports` - Compliance scan results
- `pr_submissions` - PR tracking and status

**v0.5.0 Database Improvements:**
- Enhanced database path configuration for Docker compatibility
- Support for both SQLite (development) and PostgreSQL (production)
- Orphaned record cleanup for data integrity
- Improved database initialization with error handling

### Future Migrations

For production deployments, consider using a migration tool like **Alembic**:

#### Install Alembic

```bash
pip install alembic
```

#### Initialize Alembic

```bash
alembic init alembic
```

#### Configure Alembic

Edit `alembic.ini`:

```ini
sqlalchemy.url = postgresql://oss_user:password@localhost/oss_compliance
```

#### Create Migration

```bash
alembic revision --autogenerate -m "Add new feature"
```

#### Apply Migration

```bash
alembic upgrade head
```

---

## Configuration

### Production Environment Variables

```env
# Flask Configuration
SECRET_KEY=<generate-strong-secret-key>
FLASK_ENV=production

# Debug Logging Configuration (v1.0)
FLASK_DEBUG=False  # Set to True for troubleshooting, controlled via web interface

# Encryption Configuration (v0.5.0)
ENCRYPTION_KEY=<generate-fernet-encryption-key>

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/oss_compliance

# Artifactory Configuration
ARTIFACTORY_BASE=isgedge.artifactory.cec.lab.emc.com

# GitHub Configuration (v0.5.0 with multi-user support)
GITHUB_INSTANCES=eos2git,github
GITHUB_INSTANCE_eos2git_TOKEN=<encrypted-production-token>
GITHUB_INSTANCE_eos2git_API_URL=https://api.eos2git.cec.lab.emc.com
GITHUB_INSTANCE_eos2git_ORG=ISG-Edge
GITHUB_INSTANCE_eos2git_USERS={"default_user": {"token": "encrypted_token_1"}, "user2": {"token": "encrypted_token_2"}}

# Jenkins Configuration
JENKINS_USER=<jenkins-user>
JENKINS_API_TOKEN=<jenkins-token>
JENKINS_URLS=https://jenkins.example.com
JENKINS_PR_VALIDATION_JOB=oss-compliance-validation

# Security
SSL_VERIFY=true
MAX_CONTENT_LENGTH=16777216
```

### Generate Secret Key

```python
import secrets
print(secrets.token_hex(32))
```

### Generate Encryption Key (v0.5.0)

Generate Fernet encryption key for credential security:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

**Important Security Notes:**
- Store the encryption key securely (e.g., in a secret manager)
- Do not commit the encryption key to version control
- If the encryption key is lost, encrypted credentials cannot be decrypted
- Rotate encryption keys periodically (recommended: every 90 days)

---

## Monitoring and Maintenance

### Application Monitoring

#### Health Check Endpoint

Add to `app.py`:

```python
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
```

#### Monitoring Setup

```bash
# Create monitoring script
cat > /opt/scripts/monitor.sh << 'EOF'
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/health)
if [ $response -ne 200 ]; then
    echo "Application is down!" | mail -s "OSS Compliance Alert" admin@example.com
    systemctl restart oss-compliance
fi
EOF

chmod +x /opt/scripts/monitor.sh

# Add to crontab
*/5 * * * * /opt/scripts/monitor.sh
```

### Log Management

#### Configure Log Rotation

Create `/etc/logrotate.d/oss-compliance`:

```
/var/log/oss-compliance/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 osscompliance osscompliance
    sharedscripts
}
```

### Backup Strategy

#### Database Backup

```bash
#!/bin/bash
# Backup script
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U oss_user oss_compliance | gzip > $BACKUP_DIR/oss_compliance_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "oss_compliance_*.sql.gz" -mtime +30 -delete
```

#### Report Backup

```bash
#!/bin/bash
# Backup reports
rsync -avz /opt/oss-compliance/reports/ /backups/reports/
```

---

## Troubleshooting

### Common Issues

#### Application Won't Start

**Symptoms**: Service fails to start or crashes immediately

**Solutions**:
1. Check logs: `journalctl -u oss-compliance -n 50`
2. Verify configuration: `cat config/app_config.yaml`
3. Check ENCRYPTION_KEY is set: `echo $ENCRYPTION_KEY`
4. Check dependencies: `pip list`
5. Test Python import: `python -c "import app"`

#### Database Connection Errors

**Symptoms**: Application cannot connect to PostgreSQL

**Solutions**:
1. Verify PostgreSQL is running: `systemctl status postgresql`
2. Check DATABASE_URL environment variable: `echo $DATABASE_URL`
3. Test connection: `psql -U oss_user -d oss_compliance`
4. Check firewall rules

#### GitHub API Rate Limiting

**Symptoms**: Scans fail with 403 errors

**Solutions**:
1. Check rate limit status: Review GitHub token usage
2. Implement caching: Ensure repository caching is enabled
3. Use authentication: Verify GitHub token is configured
4. Add delay between requests: Implement rate limiting

#### High Memory Usage

**Symptoms**: Application consumes excessive memory

**Solutions**:
1. Monitor memory: `top` or `htop`
2. Adjust Gunicorn workers: Reduce worker count
3. Implement cleanup: Ensure temporary files are cleaned
4. Add memory limits: Docker or system limits

### Debug Mode

#### Configurable Debug Logging (v1.0)

Debug logging can now be controlled via the web interface:

1. **Web Interface Control**: Navigate to Configuration → Application Settings
2. **Toggle Debug Logging**: Use the checkbox to enable/disable debug logging
3. **Configuration File**: Debug logging setting is stored in `config/app_config.yaml`

#### Configuration File Control

Update `config/app_config.yaml`:

```yaml
app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
  debug_logging: true  # Set to false to disable debug logging
```

#### Environment Variable Control

Set DEBUG_LOGGING environment variable:

```bash
export DEBUG_LOGGING=true  # Set to false to disable debug logging
```

Or update `app_config.yaml`:

```yaml
app_settings:
  debug_logging: true
```

**Note**: The `debug_logging` setting in `app_config.yaml` controls application debug output and can be toggled via the web UI.

#### Verbose Logging

Update Gunicorn service:

```ini
ExecStart=/opt/oss-compliance/venv/bin/gunicorn \
    --log-level debug \
    --capture-output \
    app:app
```

---

## Rollback Procedures

### Application Rollback

#### 1. Stop Current Version

```bash
sudo systemctl stop oss-compliance
```

#### 2. Restore Previous Version

```bash
cd /opt/oss-compliance
git checkout <previous-commit>
pip install -r requirements.txt
```

#### 3. Restart Service

```bash
sudo systemctl start oss-compliance
```

### Database Rollback

#### 1. Stop Application

```bash
sudo systemctl stop oss-compliance
```

#### 2. Restore Database

```bash
psql -U oss_user oss_compliance < backup_file.sql
```

#### 3. Restart Application

```bash
sudo systemctl start oss-compliance
```

### Docker Rollback

#### 1. Stop Current Container

```bash
docker-compose down
```

#### 2. Pull Previous Image

```bash
docker pull oss-compliance-webapp:previous-version
```

#### 3. Update docker-compose.yml

```yaml
image: oss-compliance-webapp:previous-version
```

#### 4. Restart Services

```bash
docker-compose up -d
```

---

## Performance Tuning

### Gunicorn Tuning

#### Worker Count

```bash
# Formula: (2 x CPU cores) + 1
workers = 9  # For 4-core system
```

#### Worker Type

```bash
# For I/O bound operations
--worker-class gthread
--threads 4
```

### Database Tuning

#### PostgreSQL Configuration

Edit `/etc/postgresql/14/main/postgresql.conf`:

```ini
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 1310kB
min_wal_size = 1GB
max_wal_size = 4GB
```

---

## Security Hardening

### Application Security

#### 1. File Permissions

```bash
sudo chmod 750 /opt/oss-compliance
sudo chmod 640 /opt/oss-compliance/config/app_config.yaml
```

#### 2. Firewall Configuration

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

#### 3. Fail2Ban Setup

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Secret Management

#### 1. Environment Variables

Never commit `config/app_config.yaml` file to version control (it contains encrypted tokens).

Add to `.gitignore`:
```bash
echo "config/app_config.yaml" >> .gitignore
echo "config/app_config.*.yaml" >> .gitignore
```

#### 2. Secret Rotation

Establish schedule for rotating:
- GitHub tokens (every 90 days) - update via web UI
- Jenkins tokens (every 90 days) - update via web UI
- Database passwords (every 180 days) - update DATABASE_URL
- Flask secret keys (every 180 days) - update SECRET_KEY
- Encryption keys (every 90 days) - requires re-encrypting all tokens

---

## Disaster Recovery

### Backup Strategy

1. **Daily Database Backups**: Automated PostgreSQL backups
2. **Weekly Report Backups**: Backup all generated reports
3. **Configuration Backups**: Version control for configuration files
4. **Application Backups**: Docker images or git tags

### Recovery Procedures

1. **Restore from Backup**: Use backup scripts to restore data
2. **Verify Integrity**: Check database and file integrity
3. **Test Functionality**: Verify application functionality
4. **Monitor Performance**: Monitor system performance post-recovery

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-06-12 | Added v0.5.0 features: credential encryption, multi-user GitHub support, Docker database configuration, improved migration scripts |
| 1.0 | 2026-05-29 | Initial deployment guide |

---

**Document Status**: Complete  
**Last Updated**: 2026-06-12  
**Next Review**: 2026-09-12