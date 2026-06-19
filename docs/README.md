# OSS Compliance Verification Web Application v1.0

A Flask-based web application for scanning software repositories to verify compliance with approved Artifactory virtual repositories.

## Features

- **Multi-Language Support**: Scans Go, Python, Node.js, Java/Maven projects
- **Unified Configuration Interface**: Single-page configuration for all endpoints (GitHub, Jenkins, Artifactory)
- **Multi-Instance Support**: Multiple GitHub instances with multiple users per instance
- **Remote Repository Scanning**: Scan GitHub repositories directly without cloning
- **Enhanced Endpoint Analysis**: Detailed endpoint detection and proxy chain analysis
- **Runtime Configuration Enumeration**: Jenkins configuration discovery from repo files
- **Three-Tier Compliance Model**: INFO, WARNING, ERROR severity levels with false positive elimination
- **Token Hints**: Display partial tokens (first 4 + last 4 chars) for security
- **Save → Test Workflow**: Tokens immediately available after save for testing
- **YAML Configuration**: Simplified single-file configuration with automatic validation
- **Credential Encryption**: Secure token storage in .env file
- **Report Generation**: Detailed compliance reports in JSON and Markdown formats
- **Report History**: View and manage all previous scan reports with database tracking
- **Docker Support**: Production-ready Docker deployment

## Quick Start

### 1. Installation

```bash
# Clone or navigate to the application directory
cd oss-compliance-webapp

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp config/app_config.example.yaml config/app_config.yaml

# Edit configuration
nano config/app_config.yaml
```

### 2. Configuration

**For existing installations with .env file:**

```bash
# Run migration script to convert to single-file configuration
python migrate_config.py --yes
```

**For new installations:**

**Create `config/app_config.yaml`:**

```yaml
artifactory:
  base_url: "your-artifactory.example.com"
  virtual_repos:
    docker: "your-docker-virtual"
    go: "your-go-virtual"
    npm: "your-npm-virtual"

github_instances:
  your_instance:
    name: "Your GitHub"
    api_url: "https://github.example.com/api/v3"
    org: "your-organization"
    users:
      - username: "default_user"
        token_env: "GITHUB_YOUR_INSTANCE_TOKEN"
        email: "you@example.com"
```

**Create `.env` file with secrets only:**

```bash
# Generate keys
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Create .env with secrets only
cat > .env << 'EOF'
# OSS Compliance Web Application - Secrets Only
# Configuration is in config/app_config.yaml

SECRET_KEY=your-generated-secret
ENCRYPTION_KEY=your-generated-key
GITHUB_YOUR_INSTANCE_TOKEN=ghp_your_token_here
JENKINS_API_TOKEN=your_jenkins_token
EOF
```

### 3. Test Configuration

```bash
python test_config.py
```

### 4. Run the Application

**Local:**
```bash
python app.py
```

**Docker:**
```bash
docker-compose up -d
```

The application will be available at `http://localhost:5001`

## Usage

### Scanning a Repository

1. Open the web interface in your browser
2. Enter the absolute path to the repository you want to scan
3. Click "Start Scan"
4. Review the results and export reports as needed

### Viewing Reports

1. Click "Reports" in the navigation
2. View all previous scan results
3. Export reports in different formats:
   - **JSON**: Raw scan data
   - **Markdown**: Human-readable report
   - **Spec**: WindSurf automation specification

### Configuration

Configure endpoints through the **Unified Configuration Interface**:
- **Access**: Click "Configuration" in the navigation
- **GitHub Instances**: Add/edit GitHub instances with multiple users
- **Jenkins Servers**: Add Jenkins servers with credentials
- **Artifactory**: Configure Artifactory base URL and credentials
- **Virtual Repos**: Configure approved virtual repositories (JSON format)
- **Whitelist URLs**: Manage allowed dependency URLs

**Configuration File Structure:**
- `config/app_config.yaml` - All non-secret configuration
- `.env` - Secrets only (tokens, keys)

## Architecture

```
oss-compliance-webapp/
|-- app.py                 # Main Flask application
|-- compliance_scanner.py  # Core scanning logic
|-- requirements.txt       # Python dependencies
|-- .env.example          # Environment configuration template
|-- templates/            # HTML templates
|   |-- index.html        # Home page
|   |-- results.html      # Scan results
|   |-- reports.html      # Report list
|   |-- config.html       # Configuration page
|-- uploads/              # Uploaded files (auto-created)
|-- reports/              # Generated reports (auto-created)
|-- config/               # Configuration files (auto-created)
```

## Supported File Types

- **Go**: `go.mod` files
- **Python**: `requirements.txt` files
- **Node.js**: `package.json` files
- **Java/Maven**: `pom.xml` files
- **Jenkins**: `Jenkinsfile` files
- **Build**: `Makefile` files

## Compliance Checks

The scanner verifies:

1. **Direct External URLs**: Direct GitHub/PyPI/npmjs.org references
2. **Missing Proxy Configuration**: No GOPROXY, PIP_INDEX_URL, NPM_CONFIG_REGISTRY
3. **Repository Configuration**: Maven repositories not pointing to Artifactory
4. **Virtual Repository Usage**: Using approved virtual repositories

## Report Formats

### JSON Report
```json
{
  "scan_summary": {
    "total_findings": 5,
    "compliance_percentage": 16.67,
    "repository_name": "my-repo"
  },
  "findings": [...],
  "recommendations": [...]
}
```

### Markdown Report
Human-readable report with executive summary, detailed findings, and recommendations.

### WindSurf Spec
Automation specification for remediation:
```yaml
windsurf_automation_spec:
  version: "1.0"
  changes: [...]
```

## API Endpoints

### Repository Scanning
- `POST /scan` - Scan local repository
- `POST /scan/remote` - Scan remote repository (enhanced mode)
- `GET /api/repositories` - List available repositories (with search)
- `POST /api/repositories/refresh` - Force refresh repository cache
- `GET /api/teams` - Get team configurations
- `GET /api/team-repositories/<team_name>` - Get repositories for a team

### Configuration Management
- `GET /config` - Unified configuration page
- `POST /update-endpoint` - Add/update GitHub/Jenkins/Artifactory endpoints
- `POST /delete-endpoint` - Delete GitHub/Jenkins/Artifactory endpoints
- `POST /update-repos-whitelist` - Update virtual repos and whitelist URLs
- `POST /test-endpoint` - Test endpoint connection (GitHub/Jenkins/Artifactory)

### Reports
- `GET /reports` - List all reports with pagination and filtering
- `GET /report/<filename>` - View specific report
- `GET /export/<filename>?format=json|markdown|spec` - Export report
- `DELETE /report/<filename>` - Delete a report

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | dev-secret-key |
| `ENCRYPTION_KEY` | Fernet encryption key for tokens | auto-generated |
| `SSL_VERIFY` | Enable SSL certificate verification | false (for corporate proxies) |
| `ARTIFACTORY_BASE` | Artifactory base URL | isgedge.artifactory.cec.lab.emc.com |
| `VIRTUAL_REPO_*` | Virtual repository names | See .env.example |
| `MAX_CONTENT_LENGTH` | Max upload size | 16777216 |
| `UPLOAD_FOLDER` | Upload directory | uploads |
| `REPORTS_FOLDER` | Reports directory | reports |
| `GITHUB_*_TOKEN_*` | GitHub PAT tokens | Set in .env |
| `JENKINS_API_TOKEN` | Jenkins API token | Set in .env |
| `ARTIFACTORY_TOKEN` | Artifactory API token | Set in .env |

## Documentation

- **[Unified Configuration Guide](./CONFIGURATION_QUICK_START.md)** - Single-page configuration interface
- **[Single-File Migration Guide](./SINGLE_FILE_MIGRATION.md)** - Migrate from dual-file to single-file config
- **[Configuration Simplification](./CONFIGURATION_SIMPLIFICATION.md)** - Complete configuration guide
- **[Docker Deployment](./DOCKER_DEPLOYMENT.md)** - Docker deployment guide
- **[API Reference](./API_REFERENCE.md)** - API documentation
- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Production deployment
- **[Database Guide](./DATABASE_GUIDE.md)** - Database management
- **[SDD Overview](./SDD_OVERVIEW.md)** - Software design documentation
- **[Enhanced Scan Guide](./ENHANCED_SCAN_GUIDE.md)** - Enhanced endpoint analysis guide

## Security Considerations

- **Token Storage**: Tokens stored in `.env` file, never committed to git
- **Token Hints**: UI displays partial tokens (first 4 + last 4 chars) for security
- **SSL Verification**: Configurable via `SSL_VERIFY` environment variable (default: false for corporate proxies)
- **SAML SSO**: GitHub.com organizations with SAML require token authorization
- **Non-Root User**: Docker runs as non-root user
- **Read-Only Volumes**: Configuration mounted read-only
- **HTTPS**: Use HTTPS in production with reverse proxy

## Troubleshooting

### Configuration Issues

```bash
# Test configuration
python test_config.py

# Check for validation errors
python -c "from config_manager import get_config_manager; get_config_manager()"
```

### Common Issues

1. **Configuration file not found**: `cp config/app_config.example.yaml config/app_config.yaml`
2. **Token not set**: Check `.env` file has required tokens
3. **SSL Certificate Error**: Set `SSL_VERIFY=false` in `.env` (for corporate proxies)
4. **GitHub SAML SSO Error**: Authorize token at https://github.com/settings/tokens → Configure SSO
5. **fusion-e repos not loading**: Don't click Refresh button; use cached repos
6. **Permission denied**: Fix permissions with `chmod -R 755 reports uploads cache instance`
7. **Port in use**: Change port in `docker-compose.yml` or `app.py`
8. **New users not appearing in dropdown**: Config auto-reloads after save

### Logs

```bash
# Local
python app.py  # Shows logs in console

# Docker
docker-compose logs -f
```

## Development

### Running Tests
```bash
# Test configuration
python test_config.py

# Test application (when available)
pytest tests/
```

### Adding New Features
1. Update configuration in `config/app_config.yaml`
2. Update `config_manager.py` if new config sections needed
3. Update documentation
4. Run tests

## Production Deployment

### Docker Deployment (Recommended)

See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) for complete guide.

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```
CMD ["python", "app.py"]
```

### Environment Setup
- Set `FLASK_ENV=production`
- Configure proper logging
- Set up reverse proxy (nginx/Apache)
- Enable HTTPS

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Verify configuration settings
4. Test with a simple repository first

## License

Internal use only - Dell Technologies
