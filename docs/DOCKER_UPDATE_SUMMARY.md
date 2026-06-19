# Docker Image Update Summary

## Overview
Updated Docker configuration to reflect the migration from `.env` file to YAML-based configuration with encrypted tokens.

## Files Updated

### 1. Dockerfile

**Changes Made**:
- Removed `python-dotenv==1.0.0` from pip install (no longer needed)
- All other dependencies remain the same

**Before**:
```dockerfile
RUN pip install ... python-dotenv==1.0.0 ...
```

**After**:
```dockerfile
RUN pip install ... (no python-dotenv)
```

### 2. docker-compose.yml

**Changes Made**:
- Removed `.env` file mount
- Added `ENCRYPTION_KEY` environment variable
- Added `DEBUG_LOGGING` environment variable
- Updated comments to reflect YAML-based configuration

**Before**:
```yaml
volumes:
  - ./.env:/app/.env:ro
  - ./config/app_config.yaml:/app/config/app_config.yaml:ro
```

**After**:
```yaml
environment:
  - ENCRYPTION_KEY=${ENCRYPTION_KEY:-your-secret-encryption-key-here}
  - DEBUG_LOGGING=${DEBUG_LOGGING:-true}
volumes:
  - ./config/app_config.yaml:/app/config/app_config.yaml:ro
```

### 3. docs/DOCKER_DEPLOYMENT.md

**Changes Made**:
- Updated Quick Start to remove .env file creation
- Added encryption key generation step
- Updated configuration file structure section
- Removed `.env` secrets section
- Updated `config/app_config.yaml` example to use `token_encrypted` instead of `token_env`
- Updated docker-compose.yml example to remove .env mount
- Updated multi-environment deployment examples
- Updated troubleshooting section for ENCRYPTION_KEY
- Updated security best practices to remove .env references
- Updated backup section to remove .env backup

## Key Changes Summary

### Before (Old Docker Configuration)
- `.env` file mounted as volume for secrets
- Tokens stored in environment variables
- `python-dotenv` dependency required
- Configuration split between `.env` and YAML
- Multiple environment variable references

### After (New Docker Configuration)
- No `.env` file
- Tokens encrypted and stored in YAML
- No `python-dotenv` dependency
- Single source of truth (YAML only)
- Only ENCRYPTION_KEY as environment variable

## Environment Variables

### Required
- `ENCRYPTION_KEY` - Required for token encryption/decryption

### Optional
- `SECRET_KEY` - Flask secret key (has default)
- `DEBUG_LOGGING` - Enable debug logging (default: true)
- `DATABASE_URL` - Database connection (defaults to SQLite)
- `SSL_VERIFY` - SSL verification (default: false)

### No Longer Used
- All GitHub token environment variables
- All Jenkins token environment variables
- All Artifactory environment variables
- All instance-specific environment variables

## Deployment Instructions

### Quick Start
```bash
# 1. Clone repository
git clone <repo>
cd oss-compliance-webapp

# 2. Create config
mkdir -p config
cat > config/app_config.yaml << 'EOF'
# Add your configuration
EOF

# 3. Set encryption key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 4. Build and run
docker-compose build
docker-compose up -d
```

### Adding Tokens
Tokens are now added via the web UI:
1. Navigate to http://localhost:5001/config
2. Click "Users" on a GitHub instance
3. Click "Edit" on a user
4. Paste your token
5. Click "Save User"
6. Token is encrypted and saved to YAML

## Benefits

### 1. Simpler Configuration
- Single configuration file (YAML)
- No .env file management
- Clear separation of concerns

### 2. Better Security
- Tokens encrypted in YAML
- No plaintext in environment variables
- ENCRYPTION_KEY only system-level secret

### 3. Easier Deployment
- Fewer environment variables to manage
- Configuration can be version controlled (encrypted)
- Simpler Docker setup

### 4. Better UX
- All configuration through web UI
- No file editing required
- Immediate feedback

## Migration from Old Docker Setup

If you have existing Docker deployment with `.env` file:

1. **Backup current setup**:
```bash
docker-compose down
tar czf backup-$(date +%Y%m%d).tar.gz .env config/ reports/
```

2. **Generate encryption key**:
```bash
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

3. **Update app_config.yaml**:
   - Remove `token_env` fields
   - Add `token_encrypted` fields with encrypted tokens
   - Use web UI to add tokens after deployment

4. **Update docker-compose.yml**:
   - Remove `.env` mount
   - Add `ENCRYPTION_KEY` environment variable

5. **Rebuild and deploy**:
```bash
docker-compose build
docker-compose up -d
```

## Testing

### Test Container Startup
```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f

# Test configuration
docker-compose exec oss-compliance-webapp python test_config.py
```

### Test Token Management
1. Open http://localhost:5001/config
2. Add user with token via UI
3. Verify token encrypted in YAML
4. Test endpoint connectivity

## Files Modified

- `Dockerfile` - Removed python-dotenv
- `docker-compose.yml` - Removed .env mount, added ENCRYPTION_KEY
- `docs/DOCKER_DEPLOYMENT.md` - Updated all references

## Date
January 2025
