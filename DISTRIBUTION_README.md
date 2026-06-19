# OSS Compliance Web Application - Distribution

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Git (for remote scanning)
- SQLite 3 (default) or PostgreSQL 14+ (optional)

### Installation

1. **Extract the archive**
   ```bash
   unzip oss-compliance-webapp-v1.0-*.zip
   cd oss-compliance-webapp
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Create configuration**
   ```bash
   mkdir -p config
   cp config/app_config.example.yaml config/app_config.yaml
   nano config/app_config.yaml  # Edit with your configuration
   ```

5. **Generate encryption key**
   ```bash
   export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   # On Windows PowerShell:
   # $env:ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

6. **Initialize database**
   ```bash
   python init_db.py
   ```

7. **Run the application**
   ```bash
   python app.py
   ```

8. **Access the application**
   Open your browser to: http://localhost:5001

### Docker Deployment

1. **Build and run with Docker**
   ```bash
   docker build -t oss-compliance-webapp:latest .
   docker run -d -p 5001:5001 -e ENCRYPTION_KEY=your-key -v $(pwd)/config:/app/config -v $(pwd)/reports:/app/reports -v $(pwd)/uploads:/app/uploads -v $(pwd)/cache:/app/cache -v $(pwd)/instance:/app/instance --name oss-compliance-webapp oss-compliance-webapp:latest
   ```

2. **Or use docker-compose**
   ```bash
   export ENCRYPTION_KEY=your-key
   docker-compose up -d
   ```

### Adding Tokens

Tokens are added via the web UI:

1. Navigate to http://localhost:5001/config
2. Click "Users" on a GitHub instance
3. Click "Edit" on a user
4. Paste your token
5. Click "Save User"
6. Token is encrypted and saved to YAML

### Documentation

Full documentation is available in the `docs/` directory:
- `DEPLOYMENT_GUIDE.md` - Complete deployment instructions
- `DOCKER_DEPLOYMENT.md` - Docker-specific deployment
- `CONFIGURATION_QUICK_START.md` - Configuration guide
- `API_REFERENCE.md` - API documentation

### Support

For issues or questions, please refer to the documentation or contact the support team.

## Version Information

- Application Version: 1.0
- Distribution Date: 2026-06-12
- Python Required: 3.9+

## Security Notes

- The `ENCRYPTION_KEY` environment variable is required for token encryption/decryption
- Never commit `config/app_config.yaml` to version control (contains encrypted tokens)
- Add `config/app_config.yaml` to `.gitignore`
- Rotate encryption keys and tokens regularly (every 90 days recommended)
