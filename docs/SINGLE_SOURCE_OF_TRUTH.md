# Single Source of Truth - Eliminated Dual Configuration Tracking

## Overview
Completely eliminated the dual-tracking issue by removing the `token_env` field from all configuration structures. Now there is only ONE way to configure tokens: `token_encrypted` in `app_config.yaml`.

## The Problem
The application was tracking configuration in TWO places:
1. **`token_env`** in `app_config.yaml` → pointed to environment variables
2. **`token_encrypted`** in `app_config.yaml` → stored encrypted tokens directly

This created:
- Confusion about which to use
- Maintenance burden (updating both)
- Inconsistent behavior
- Harder debugging

## The Solution
**Removed `token_env` completely**. Now there is only:
- **`token_encrypted`** in `app_config.yaml` → single source of truth

## Changes Made

### 1. Updated Data Classes

#### GitHubUser
**Before**:
```python
@dataclass
class GitHubUser:
    username: str
    token_env: str = ""  # Legacy
    token_encrypted: str = ""  # New
    email: str = ""
    
    @property
    def token(self) -> str:
        # Try encrypted first
        if self.token_encrypted:
            return decrypt_token(self.token_encrypted)
        # Fall back to env var
        if self.token_env:
            return os.getenv(self.token_env, "")
        return ""
```

**After**:
```python
@dataclass
class GitHubUser:
    username: str
    token_encrypted: str = ""  # Only way to store tokens
    email: str = ""
    
    @property
    def token(self) -> str:
        if self.token_encrypted:
            return decrypt_token(self.token_encrypted)
        return ""
```

#### JenkinsConfig
**Before**:
```python
@dataclass
class JenkinsConfig:
    user: str
    token_env: str = ""  # Legacy
    token_encrypted: str = ""  # New
    urls: List[str] = field(default_factory=list)
```

**After**:
```python
@dataclass
class JenkinsConfig:
    user: str
    token_encrypted: str = ""  # Only way to store tokens
    urls: List[str] = field(default_factory=list)
```

#### ArtifactoryConfig
**Before**:
```python
@dataclass
class ArtifactoryConfig:
    base_url: str
    virtual_repos: Dict[str, str] = field(default_factory=dict)
    user: str = ""
    token_env: str = ""  # Legacy
    token_encrypted: str = ""  # New
```

**After**:
```python
@dataclass
class ArtifactoryConfig:
    base_url: str
    virtual_repos: Dict[str, str] = field(default_factory=dict)
    user: str = ""
    token_encrypted: str = ""  # Only way to store tokens
```

### 2. Updated Configuration Loading

**Before**:
```python
users = [
    GitHubUser(
        username=user.get('username', ''),
        token_env=user.get('token_env', ''),  # Load both
        token_encrypted=user.get('token_encrypted', ''),
        email=user.get('email', '')
    )
    for user in users_data
]
```

**After**:
```python
users = [
    GitHubUser(
        username=user.get('username', ''),
        token_encrypted=user.get('token_encrypted', ''),  # Only this
        email=user.get('email', '')
    )
    for user in users_data
]
```

### 3. Updated app_config.yaml

**Before**:
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_env: GITHUB_EOS2GIT_TOKEN_DEFAULT_USER  # Dual tracking
      token_encrypted: gAAAAABh...  # Dual tracking
      email: ''

jenkins:
  user: jpurcell
  token_env: JENKINS_API_TOKEN  # Dual tracking
  token_encrypted: gAAAAABh...  # Dual tracking
```

**After**:
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_encrypted: gAAAAABh...  # Single source
      email: ''

jenkins:
  user: jpurcell
  token_encrypted: gAAAAABh...  # Single source
```

## Configuration Structure

### Complete Example
```yaml
version: '1.0'

artifactory:
  base_url: isgedge.artifactory.cec.lab.emc.com
  user: myuser
  token_encrypted: gAAAAABh...  # Encrypted token
  virtual_repos:
    docker: isgedge-docker-virtual
    go: isgedge-go-virtual

github_instances:
  eos2git:
    name: ISG-Edge
    api_url: https://eos2git.cec.lab.emc.com/api/v3
    org: ISG-Edge
    users:
    - username: default_user
      token_encrypted: gAAAAABh...  # Encrypted token
      email: ''
    - username: jpurcell
      token_encrypted: gAAAAABh...  # Encrypted token
      email: jeff.purcell@dell.com

jenkins:
  user: jpurcell
  token_encrypted: gAAAAABh...  # Encrypted token
  urls:
  - https://osj-isg-03-prd.cec.delllabs.net

whitelist_urls:
- github.com/fusion-e
- eos2git.cec.lab.emc.com

app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
  debug_logging: true
```

## Benefits

### 1. **Single Source of Truth**
- Only ONE place to store tokens
- No confusion about which field to use
- No dual maintenance

### 2. **Simpler Code**
- Removed fallback logic
- Cleaner token property
- Easier to understand

### 3. **Easier Maintenance**
- Update one field, not two
- No sync issues
- Less error-prone

### 4. **Better Security**
- All tokens encrypted
- No plain text in env vars
- Consistent encryption

### 5. **Clearer Intent**
- Code clearly shows tokens come from YAML
- No ambiguity about configuration source
- Better documentation

## Migration Path

### From token_env to token_encrypted

If you have existing configurations with `token_env`:

1. **Get the token value** from the environment variable
2. **Encrypt it** using the UI or:
   ```python
   from app import encrypt_token
   encrypted = encrypt_token("your_token_here")
   ```
3. **Add to YAML**:
   ```yaml
   users:
   - username: myuser
     token_encrypted: gAAAAABh...
     email: ''
   ```
4. **Remove** the `token_env` field
5. **Test** that authentication works

### Bulk Migration Script

```python
import yaml
from pathlib import Path
from app import encrypt_token
import os

# Load config
config_path = Path('config/app_config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Migrate GitHub users
for instance_id, instance in config.get('github_instances', {}).items():
    for user in instance.get('users', []):
        if 'token_env' in user and not user.get('token_encrypted'):
            token = os.getenv(user['token_env'])
            if token:
                user['token_encrypted'] = encrypt_token(token)
            del user['token_env']

# Migrate Jenkins
jenkins = config.get('jenkins', {})
if 'token_env' in jenkins and not jenkins.get('token_encrypted'):
    token = os.getenv(jenkins['token_env'])
    if token:
        jenkins['token_encrypted'] = encrypt_token(token)
    del jenkins['token_env']

# Migrate Artifactory
artifactory = config.get('artifactory', {})
if 'token_env' in artifactory and not artifactory.get('token_encrypted'):
    token = os.getenv(artifactory['token_env'])
    if token:
        artifactory['token_encrypted'] = encrypt_token(token)
    del artifactory['token_env']

# Save
with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print("Migration complete!")
```

## Testing

### Test Case 1: Load Configuration
```bash
$ python test_config.py
[OK] Config loaded successfully
[OK] GitHub instances: ['eos2git', 'github']
  - eos2git: ISG-Edge - 3 users
    - default_user (has token: False)
    - jpurcell (has token: False)
[OK] Jenkins: jpurcell - 1 URLs (has token: False)
[OK] Artifactory: isgedge.artifactory.cec.lab.emc.com (has token: False)
```

### Test Case 2: Add Token via UI
1. Open Manage Users modal
2. Edit user
3. Enter token
4. Save
5. **Expected**: Token encrypted and saved as `token_encrypted`
6. **Result**: ✅ Only `token_encrypted` field in YAML

### Test Case 3: Test Endpoint
1. Select user with token
2. Click "Test"
3. **Expected**: Token decrypted and used
4. **Result**: ✅ Authentication successful

## Files Modified

### Configuration
- `config_manager.py`
  - Removed `token_env` from all dataclasses
  - Simplified token properties
  - Updated loading methods

- `config/app_config.yaml`
  - Removed all `token_env` fields
  - Clean structure with only `token_encrypted`

### No Changes Needed
- `app.py` - Already using ConfigManager
- Frontend - Already using API endpoints
- API endpoints - Already using ConfigManager

## Backward Compatibility

**None**. This is a breaking change. If you have `token_env` fields in your config:
1. They will be ignored
2. Tokens won't work until you add `token_encrypted`
3. Use the migration script above

## Environment Variables Still Used

Only these system-level variables (NOT from config):
- `ENCRYPTION_KEY` - Required for token encryption/decryption
- `SECRET_KEY` - Flask secret (optional)
- `DATABASE_URL` - Database connection (optional)
- `SSL_VERIFY` - SSL verification (optional)

## Summary

**Before**: 2 ways to configure tokens (confusing)
```yaml
token_env: GITHUB_TOKEN  # Option 1
token_encrypted: gAAAAABh...  # Option 2
```

**After**: 1 way to configure tokens (clear)
```yaml
token_encrypted: gAAAAABh...  # Only option
```

**Result**: Single source of truth, simpler code, easier maintenance!

## Date
January 2025
