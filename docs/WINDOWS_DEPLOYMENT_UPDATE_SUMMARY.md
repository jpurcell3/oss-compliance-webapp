# Windows Deployment Update Summary

## Overview
Updated Windows deployment configuration to reflect the migration from `.env` file to YAML-based configuration with encrypted tokens.

## Files Updated

### 1. docker-helper.bat

**Changes Made**:
- Removed `--env-file .env` from docker run command
- Added `-e ENCRYPTION_KEY=%ENCRYPTION_KEY%` environment variable
- Added `-e DEBUG_LOGGING=true` environment variable
- Added `-v %cd%/config:/app/config` volume mount for configuration
- Added `-v %cd%/instance:/app/instance` volume mount for database
- Updated help message to mention adding tokens via web UI

**Before**:
```batch
docker run -d -p 5001:5001 --env-file .env -v %cd%/reports:/app/reports -v %cd%/uploads:/app/uploads -v %cd%/cache:/app/cache --name %IMAGE_NAME% %IMAGE_NAME%:%VERSION%
```

**After**:
```batch
docker run -d -p 5001:5001 -e ENCRYPTION_KEY=%ENCRYPTION_KEY% -e DEBUG_LOGGING=true -v %cd%/config:/app/config -v %cd%/reports:/app/reports -v %cd%/uploads:/app/uploads -v %cd%/cache:/app/cache -v %cd%/instance:/app/instance --name %IMAGE_NAME% %IMAGE_NAME%:%VERSION%
```

### 2. docs/DEPLOYMENT_GUIDE.md

**Changes Made**:
- Updated Dockerfile example to remove `python-dotenv`
- Updated local deployment configuration to use YAML instead of .env
- Updated encryption key generation to use environment variable
- Updated Docker run command to remove .env and add ENCRYPTION_KEY
- Updated docker-compose.yml to remove .env mount and add ENCRYPTION_KEY
- Updated production deployment to use YAML configuration
- Updated PostgreSQL setup to use DATABASE_URL environment variable
- Updated systemd service file to remove EnvironmentFile=.env
- Updated systemd service to add ENCRYPTION_KEY and DATABASE_URL environment variables
- Updated troubleshooting section to reference config/app_config.yaml
- Updated security hardening to reference config/app_config.yaml
- Updated secret management to reference YAML configuration

## Key Changes Summary

### Before (Old Windows Deployment)
- `.env` file required for secrets
- `--env-file .env` in docker run command
- Configuration split between .env and YAML
- Multiple environment variable references

### After (New Windows Deployment)
- No `.env` file
- ENCRYPTION_KEY as environment variable
- Single source of truth (YAML only)
- Tokens encrypted in YAML
- Add tokens via web UI

## Windows Deployment Instructions

### Quick Start with docker-helper.bat

```batch
# 1. Set encryption key
set ENCRYPTION_KEY=your-encryption-key-here

# 2. Build image
docker-helper.bat build

# 3. Run container
docker-helper.bat run

# 4. Add tokens via web UI
# Navigate to http://localhost:5001/config
```

### Manual Docker Run on Windows

```batch
# Generate encryption key (PowerShell)
$ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Run container
docker run -d -p 5001:5001 -e ENCRYPTION_KEY=%ENCRYPTION_KEY% -e DEBUG_LOGGING=true -v %cd%/config:/app/config -v %cd%/reports:/app/reports -v %cd%/uploads:/app/uploads -v %cd%/cache:/app/cache -v %cd%/instance:/app/instance --name oss-compliance-webapp oss-compliance-webapp:latest
```

### Using docker-compose on Windows

```bash
# Set encryption key
set ENCRYPTION_KEY=your-encryption-key-here

# Build and run
docker-compose build
docker-compose up -d
```

## Configuration

### Create config/app_config.yaml

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

## Adding Tokens

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

### 3. Easier Windows Deployment
- Fewer environment variables to manage
- Configuration can be version controlled (encrypted)
- Simpler Docker setup
- Works with docker-helper.bat

### 4. Better UX
- All configuration through web UI
- No file editing required
- Immediate feedback

## Migration from Old Windows Setup

If you have existing Windows deployment with `.env` file:

1. **Backup current setup**:
```batch
docker stop oss-compliance-webapp
tar -czf backup-%date%.tar.gz .env config/ reports/
```

2. **Generate encryption key**:
```batch
set ENCRYPTION_KEY=your-encryption-key-here
```

3. **Update app_config.yaml**:
   - Remove `token_env` fields
   - Add `token_encrypted` fields with encrypted tokens
   - Use web UI to add tokens after deployment

4. **Update docker-helper.bat**:
   - Already updated in this change

5. **Rebuild and deploy**:
```batch
docker-helper.bat build
docker-helper.bat run
```

## Testing

### Test Container Startup
```batch
# Build and start
docker-helper.bat build
docker-helper.bat run

# Check logs
docker logs -f oss-compliance-webapp

# Test configuration
docker exec oss-compliance-webapp python test_config.py
```

### Test Token Management
1. Open http://localhost:5001/config
2. Add user with token via UI
3. Verify token encrypted in YAML
4. Test endpoint connectivity

## Files Modified

- `docker-helper.bat` - Removed .env, added ENCRYPTION_KEY
- `docs/DEPLOYMENT_GUIDE.md` - Updated all references

## Date
January 2025
