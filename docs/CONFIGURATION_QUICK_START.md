# Configuration Quick Start Guide
## OSS Compliance Web Application

**Version:** 1.1  
**Last Updated:** 2026-06-12  
**Application Version:** 1.0

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Copy Configuration Template

```bash
cd oss-compliance-webapp
cp config/app_config.example.yaml config/app_config.yaml
```

### Step 2: Edit Configuration

```bash
nano config/app_config.yaml
```

Update these sections:

```yaml
github_instances:
  your_instance:
    name: "Your GitHub"
    api_url: "https://github.example.com/api/v3"
    org: "your-organization"
    users:
      - username: "default_user"
        token_env: "GITHUB_TOKEN"
        email: "you@example.com"
```

### Step 3: Create Environment File

```bash
cat > .env << 'EOF'
# Generate these keys first!
ENCRYPTION_KEY=your-encryption-key-here
SECRET_KEY=your-secret-key-here

# Flask debug mode (v1.0: can also be controlled via web interface)
FLASK_DEBUG=True

# GitHub token (referenced from config)
GITHUB_TOKEN=ghp_your_token_here

# Jenkins token
JENKINS_API_TOKEN=your_jenkins_token
EOF
```

### Step 4: Generate Keys

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Generate secret key
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```

Copy the output to your `.env` file.

### Step 5: Test Configuration

```bash
python test_config.py
```

Expected output:
```
✓ All ConfigManager tests passed!
✓ All EnvFileManager tests passed!
```

### Step 6: Run Application

**Local:**
```bash
python app.py
```

**Docker:**
```bash
docker-compose up -d
```

**Access:** http://localhost:5001

---

## 📁 File Structure

```
oss-compliance-webapp/
├── config/
│   ├── app_config.yaml          # Your configuration (edit this)
│   └── app_config.example.yaml  # Template (don't edit)
├── .env                          # Secrets (create this, never commit)
├── config_manager.py             # Configuration loader (don't edit)
├── env_file_manager.py           # .env helper (don't edit)
└── test_config.py                # Test script (run to validate)
```

---

## ⚙️ Configuration Sections

### Artifactory

```yaml
artifactory:
  base_url: "your-artifactory.example.com"
  virtual_repos:
    docker: "your-docker-virtual"
    go: "your-go-virtual"
    npm: "your-npm-virtual"
```

### GitHub Instances

```yaml
github_instances:
  instance_name:
    name: "Display Name"
    api_url: "https://github.example.com/api/v3"
    org: "your-organization"
    users:
      - username: "user1"
        token_env: "GITHUB_TOKEN_1"  # References .env
        email: "user1@example.com"
      - username: "user2"
        token_env: "GITHUB_TOKEN_2"
        email: "user2@example.com"
```

### Jenkins

```yaml
jenkins:
  user: "jenkins-service-account"
  token_env: "JENKINS_API_TOKEN"  # References .env
  urls:
    - "https://jenkins.example.com"
  pr_validation_job: "oss-compliance-validation"
```

### Whitelist URLs

```yaml
whitelist_urls:
  - "https://github.com"
  - "https://gitlab.com"
  - "https://bitbucket.org"
```

### App Settings

```yaml
app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
  debug_logging: true  # v1.0: Enable/disable debug logging, can be toggled via web interface
```

---

## 🔐 Secrets in .env

```env
# Required
ENCRYPTION_KEY=your-fernet-key-here
SECRET_KEY=your-flask-secret-here

# GitHub tokens (one per user in config)
GITHUB_TOKEN_1=ghp_token_for_user1
GITHUB_TOKEN_2=ghp_token_for_user2

# Jenkins
JENKINS_API_TOKEN=your_jenkins_token

# Optional
FLASK_ENV=production
FLASK_DEBUG=True  # v1.0: Flask debug mode (can also be controlled via web interface)
DATABASE_URL=sqlite:///instance/reports.db
```

---

## 🐛 Debug Logging Configuration (v1.0)

### Web Interface Control

The easiest way to control debug logging is through the web interface:

1. Navigate to **Configuration** page
2. Scroll to **Application Settings** section
3. Toggle **Debug Logging** checkbox
4. Click **Save Settings**

Changes take effect immediately without requiring an application restart.

### Configuration File Control

Debug logging can also be set in `config/app_config.yaml`:

```yaml
app_settings:
  debug_logging: true  # Set to false to disable
```

### Environment Variable Control

Flask debug mode can be controlled via environment variable:

```env
FLASK_DEBUG=True  # Enable Flask debug mode
```

**Note**: The `debug_logging` setting controls application debug output, while `FLASK_DEBUG` controls Flask's development mode. Both can be used independently.

### Best Practices

- **Development**: Keep `debug_logging: true` for troubleshooting
- **Production**: Set `debug_logging: false` and enable temporarily when needed
- **Security**: Debug output masks sensitive tokens (shows first 10 chars only)
- **Performance**: Disable debug logging in production for better performance

For detailed debug logging documentation, see [DEBUG_LOGGING_GUIDE.md](DEBUG_LOGGING_GUIDE.md).

---

## ✅ Validation Checklist

- [ ] `config/app_config.yaml` exists
- [ ] `.env` file exists with all required keys
- [ ] Encryption key generated
- [ ] Secret key generated
- [ ] GitHub tokens set in `.env`
- [ ] GitHub tokens referenced correctly in YAML (`token_env`)
- [ ] Debug logging configured in `app_settings.debug_logging`
- [ ] Test script passes: `python test_config.py`
- [ ] Application starts without errors

---

## 🐛 Common Issues

### "Configuration file not found"

```bash
cp config/app_config.example.yaml config/app_config.yaml
```

### "Environment variable not set"

Check `.env` file has the token:
```bash
grep GITHUB_TOKEN .env
```

Add if missing:
```bash
echo "GITHUB_TOKEN=ghp_your_token" >> .env
```

### "Invalid YAML syntax"

Validate YAML:
```bash
python -c "import yaml; yaml.safe_load(open('config/app_config.yaml'))"
```

### "Validation failed"

Run test script for details:
```bash
python test_config.py
```

---

## 📚 More Information

- **Full Guide**: [CONFIGURATION_SIMPLIFICATION.md](./CONFIGURATION_SIMPLIFICATION.md)
- **Docker Deployment**: [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)
- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

---

## 🆘 Need Help?

1. Run test script: `python test_config.py`
2. Check logs: `docker-compose logs` (if using Docker)
3. Validate YAML syntax
4. Ensure all tokens are in `.env`
5. Check file permissions

---

**Quick Start Complete!** 🎉

Your application is now configured and ready to use.
