# Configuration Simplification Guide
## OSS Compliance Web Application

**Version:** 1.0  
**Last Updated:** 2026-06-12  
**Application Version:** 0.5.0

---

## Overview

The OSS Compliance Web Application has been enhanced with a simplified, YAML-based configuration system that provides:

- **Centralized Configuration**: Single YAML file for all non-secret configuration
- **Validation**: Automatic validation of configuration on load
- **Type Safety**: Structured configuration with dataclasses
- **Backward Compatibility**: Falls back to environment variables if YAML not available
- **Security**: Secrets remain in environment variables, referenced from YAML

---

## Configuration Architecture

### Before (Environment Variables Only)

```
.env file
├── ARTIFACTORY_BASE=...
├── VIRTUAL_REPO_DOCKER=...
├── VIRTUAL_REPO_GO=...
├── GITHUB_INSTANCES=eos2git,github
├── GITHUB_INSTANCE_eos2git_API_URL=...
├── GITHUB_INSTANCE_eos2git_ORG=...
├── GITHUB_INSTANCE_eos2git_USERS={"default_user": {"token": "..."}}
├── JENKINS_USER=...
├── JENKINS_API_TOKEN=...
└── ... (40+ variables)
```

**Issues:**
- Hard to read and maintain
- No validation until runtime
- Easy to make syntax errors
- Difficult to organize
- No comments or documentation inline

### After (YAML + Environment Variables)

```
config/app_config.yaml (structured configuration)
├── artifactory:
│   ├── base_url
│   └── virtual_repos: {docker, go, npm, ...}
├── github_instances:
│   └── eos2git:
│       ├── name, api_url, org
│       └── users: [{username, token_env, email}]
├── jenkins: {user, token_env, urls}
└── whitelist_urls: [...]

.env file (secrets only)
├── ENCRYPTION_KEY=...
├── SECRET_KEY=...
├── GITHUB_EOS2GIT_TOKEN_1=...
└── JENKINS_API_TOKEN=...
```

**Benefits:**
- Easy to read and edit
- Supports comments
- Automatic validation
- Organized structure
- Secrets separated from configuration
- Version control friendly (YAML can be committed, secrets cannot)

---

## New Files

### 1. `config_manager.py`

Centralized configuration management with validation.

**Key Classes:**
- `ConfigManager`: Main configuration manager
- `GitHubInstance`: GitHub instance configuration
- `GitHubUser`: GitHub user configuration
- `ArtifactoryConfig`: Artifactory configuration
- `JenkinsConfig`: Jenkins configuration
- `AppSettings`: Application settings

**Key Methods:**
```python
from config_manager import get_config_manager

config = get_config_manager()
artifactory = config.get_artifactory_config()
github_instances = config.get_github_instances()
jenkins = config.get_jenkins_config()
whitelist = config.get_whitelist_urls()
```

### 2. `env_file_manager.py`

Safe manipulation of .env files.

**Key Methods:**
```python
from env_file_manager import EnvFileManager

env = EnvFileManager()
env_dict = env.read()
env.update({'KEY': 'value'})
env.remove(['OLD_KEY'])
issues = env.validate()
```

### 3. `config/app_config.yaml`

Main configuration file (structured YAML).

### 4. `config/app_config.example.yaml`

Template configuration file for new installations.

### 5. `test_config.py`

Test script to validate configuration.

---

## Configuration File Format

### `config/app_config.yaml`

```yaml
version: "1.0"

# Artifactory configuration
artifactory:
  base_url: "isgedge.artifactory.cec.lab.emc.com"
  virtual_repos:
    docker: "isgedge-docker-virtual"
    go: "isgedge-go-virtual"
    npm: "isgedge-npm-virtual"
    # ... more repos

# GitHub instances
github_instances:
  eos2git:
    name: "EOS2Git"
    api_url: "https://eos2git.cec.lab.emc.com/api/v3"
    org: "ISG-Edge"
    users:
      - username: "default_user"
        token_env: "GITHUB_EOS2GIT_TOKEN_1"  # References .env variable
        email: ""
      - username: "user2"
        token_env: "GITHUB_EOS2GIT_TOKEN_2"
        email: "user2@example.com"

# Jenkins configuration
jenkins:
  user: "jenkins-user"
  token_env: "JENKINS_API_TOKEN"  # References .env variable
  urls:
    - "https://jenkins.example.com"
  pr_validation_job: "oss-compliance-validation"

# Whitelist URLs
whitelist_urls:
  - "https://github.com"
  - "https://gitlab.com"

# Application settings
app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
```

---

## Migration Guide

### Step 1: Create Configuration File

```bash
cd oss-compliance-webapp
cp config/app_config.example.yaml config/app_config.yaml
```

### Step 2: Customize Configuration

Edit `config/app_config.yaml` with your settings:

```yaml
artifactory:
  base_url: "your-artifactory.example.com"
  virtual_repos:
    docker: "your-docker-virtual"
    # ... customize repos

github_instances:
  your_instance:
    name: "Your GitHub"
    api_url: "https://github.example.com/api/v3"
    org: "your-org"
    users:
      - username: "default_user"
        token_env: "GITHUB_YOUR_INSTANCE_TOKEN"
        email: "user@example.com"
```

### Step 3: Set Environment Variables

Create or update `.env` with secrets:

```env
# Encryption key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-encryption-key

# Secret key (generate with: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your-secret-key

# GitHub tokens (referenced from YAML)
GITHUB_YOUR_INSTANCE_TOKEN=ghp_your_token_here

# Jenkins token (referenced from YAML)
JENKINS_API_TOKEN=your_jenkins_token
```

### Step 4: Test Configuration

```bash
python test_config.py
```

Expected output:
```
============================================================
OSS Compliance Configuration Test Suite
============================================================

Testing ConfigManager
============================================================
✓ Configuration loaded successfully
✓ Artifactory config valid
✓ GitHub instances valid
✓ Jenkins config valid
✓ Whitelist URLs valid
✓ All ConfigManager tests passed!

Testing EnvFileManager
============================================================
✓ .env file read successfully
✓ All EnvFileManager tests passed!

Test Summary
============================================================
ConfigManager: ✓ PASS
EnvFileManager: ✓ PASS
✓ All tests passed!
```

### Step 5: Start Application

```bash
python app.py
```

The application will:
1. Try to load `config/app_config.yaml`
2. If successful, use YAML configuration
3. If not found, fall back to environment variables (backward compatible)

---

## Validation

### Automatic Validation

The ConfigManager automatically validates:

- **Artifactory**: Base URL and virtual repos are required
- **GitHub Instances**: Name, API URL, org, and at least one user required
- **Jenkins**: User, token_env, and at least one URL required
- **Tokens**: Warns if environment variables are not set

### Manual Validation

Run the test script:

```bash
python test_config.py
```

Or validate programmatically:

```python
from config_manager import get_config_manager

try:
    config = get_config_manager()
    print("Configuration is valid!")
except ValueError as e:
    print(f"Configuration error: {e}")
```

---

## Backward Compatibility

The application maintains full backward compatibility:

1. **YAML Available**: Uses ConfigManager
2. **YAML Not Found**: Falls back to environment variables
3. **Hybrid**: Can use YAML for structure, env vars for secrets

### Legacy Environment Variable Support

All existing environment variables still work:

```env
GITHUB_INSTANCES=eos2git,github
GITHUB_INSTANCE_eos2git_API_URL=...
GITHUB_INSTANCE_eos2git_ORG=...
GITHUB_INSTANCE_eos2git_USERS={"default_user": {"token": "..."}}
```

---

## Best Practices

### 1. Separate Secrets from Configuration

**Do:**
```yaml
# config/app_config.yaml
github_instances:
  eos2git:
    users:
      - username: "user1"
        token_env: "GITHUB_TOKEN_1"  # Reference to env var
```

```env
# .env (not committed to git)
GITHUB_TOKEN_1=ghp_actual_token_here
```

**Don't:**
```yaml
# config/app_config.yaml - NEVER DO THIS
github_instances:
  eos2git:
    users:
      - username: "user1"
        token: "ghp_actual_token_here"  # ✗ Secret in YAML!
```

### 2. Use Comments

```yaml
# Artifactory configuration
artifactory:
  base_url: "isgedge.artifactory.cec.lab.emc.com"
  virtual_repos:
    # Docker images
    docker: "isgedge-docker-virtual"
    # Go modules
    go: "isgedge-go-virtual"
```

### 3. Version Control

**Commit to Git:**
- `config/app_config.example.yaml` ✓
- `config/app_config.yaml` ✓ (if no secrets)

**Never Commit:**
- `.env` ✗
- `.env.backup` ✗
- Any file with actual tokens/secrets ✗

### 4. Environment-Specific Configuration

Create environment-specific files:

```bash
config/
├── app_config.yaml          # Development
├── app_config.prod.yaml     # Production
├── app_config.staging.yaml  # Staging
└── app_config.example.yaml  # Template
```

Load specific config:

```python
config = ConfigManager("config/app_config.prod.yaml")
```

---

## Troubleshooting

### Configuration File Not Found

**Error:**
```
FileNotFoundError: Configuration file not found: config/app_config.yaml
Please copy config/app_config.example.yaml to config/app_config.yaml and customize it.
```

**Solution:**
```bash
cp config/app_config.example.yaml config/app_config.yaml
# Edit config/app_config.yaml with your settings
```

### Token Environment Variable Not Set

**Warning:**
```
Warning: Environment variable 'GITHUB_EOS2GIT_TOKEN_1' not set for user 'default_user'
```

**Solution:**
Add to `.env`:
```env
GITHUB_EOS2GIT_TOKEN_1=your_token_here
```

### Invalid YAML Syntax

**Error:**
```
ValueError: Invalid YAML in configuration file: ...
```

**Solution:**
- Check YAML syntax (indentation, colons, hyphens)
- Use a YAML validator
- Compare with `app_config.example.yaml`

### Validation Failed

**Error:**
```
ValueError: Configuration validation failed: GitHub instance 'eos2git' missing organization
```

**Solution:**
- Check required fields in YAML
- Run `python test_config.py` for detailed validation
- Ensure all required sections are present

---

## API Reference

### ConfigManager

```python
from config_manager import ConfigManager, get_config_manager

# Get singleton instance
config = get_config_manager()

# Reload configuration
config.reload()

# Get configurations
artifactory = config.get_artifactory_config()
github_instances = config.get_github_instances()
github_instance = config.get_github_instance('eos2git')
jenkins = config.get_jenkins_config()
whitelist = config.get_whitelist_urls()
settings = config.get_app_settings()

# Get summary (no secrets)
summary = config.get_config_summary()

# Update configuration
config.update_config({'artifactory': {'base_url': 'new-url'}})
```

### EnvFileManager

```python
from env_file_manager import EnvFileManager

env = EnvFileManager('.env')

# Read all variables
env_dict = env.read()

# Get specific variable
value = env.get('KEY', default='default_value')

# Set variable
env.set('KEY', 'value')

# Update multiple variables
env.update({'KEY1': 'value1', 'KEY2': 'value2'})

# Remove variables
env.remove(['OLD_KEY1', 'OLD_KEY2'])

# Validate
issues = env.validate()

# Print summary
env.print_summary()
```

---

## Rollback Instructions

If you need to rollback to the previous configuration approach:

```bash
# Rollback to checkpoint
git checkout 5ebc7fe

# Or just remove the new files
rm config_manager.py
rm env_file_manager.py
rm -rf config/
rm test_config.py

# Restart application (will use environment variables only)
python app.py
```

---

## Future Enhancements

### Planned Features

1. **Configuration UI**: Web-based configuration editor
2. **Configuration Validation API**: REST API for validation
3. **Configuration Import/Export**: Backup and restore configurations
4. **Configuration Versioning**: Track configuration changes
5. **Environment Detection**: Auto-load config based on environment
6. **Configuration Encryption**: Encrypt entire YAML file
7. **Remote Configuration**: Load config from remote source

---

**Document Status**: Complete  
**Last Updated**: 2026-06-12  
**Next Review**: 2026-09-12
