# Removed .env File Dependency - Complete Migration to YAML Config

## Overview
Completely removed the application's dependency on the `.env` file. All configuration, including encrypted tokens, is now stored exclusively in `app_config.yaml`.

## Problem
Despite implementing encrypted token storage in YAML, the application was still:
1. Loading `.env` file at startup with `load_dotenv()`
2. Using `EnvFileManager` to read/write tokens to `.env`
3. Storing tokens in environment variables
4. Creating confusion about which configuration source was authoritative

## Solution
Removed all `.env` file operations and migrated to pure YAML configuration with encrypted tokens.

## Changes Made

### 1. Removed Imports
**File**: `app.py`

**Removed**:
```python
from dotenv import load_dotenv
from env_file_manager import EnvFileManager
```

### 2. Removed Startup Load
**Before**:
```python
# Load environment variables
load_dotenv()
```

**After**:
```python
# (removed - no longer loading .env)
```

### 3. Updated `/update-endpoint` Route

#### GitHub Endpoints
**Before**:
```python
# Save token to .env
if data.get('token'):
    env_manager = EnvFileManager()
    env_manager.set(token_env, data.get('token'))
    load_dotenv(override=True)
```

**After**:
```python
# Save encrypted token if provided
if data.get('token'):
    user['token_encrypted'] = encrypt_token(data.get('token'))
```

#### Jenkins Endpoints
**Before**:
```python
# Save token to .env
if jenkins_token:
    env_manager = EnvFileManager()
    env_manager.set('JENKINS_API_TOKEN', jenkins_token)
    load_dotenv(override=True)
```

**After**:
```python
# Save encrypted token if provided
if jenkins_token:
    jenkins['token_encrypted'] = encrypt_token(jenkins_token)
```

#### Artifactory Endpoints
**Before**:
```python
# Save token to .env if provided
if artifactory_token:
    env_manager = EnvFileManager()
    env_manager.set('ARTIFACTORY_TOKEN', artifactory_token)
    load_dotenv(override=True)

# Save username to env if provided
if artifactory_user:
    env_manager = EnvFileManager()
    env_manager.set('ARTIFACTORY_USER', artifactory_user)
    load_dotenv(override=True)
```

**After**:
```python
# Save encrypted token if provided
if artifactory_token:
    artifactory['token_encrypted'] = encrypt_token(artifactory_token)

# Save username if provided
if artifactory_user:
    artifactory['user'] = artifactory_user
```

### 4. Updated `/delete-endpoint` Route

**Before**:
```python
# Delete token from .env
token_env = f"GITHUB_{instance_id.upper()}_TOKEN_{username.upper()}"
env_manager = EnvFileManager()
env_manager.remove([token_env])

# Delete all user tokens
tokens_to_delete = []
for user in github_instances[instance_id].get('users', []):
    token_env = user.get('token_env', '')
    if token_env:
        tokens_to_delete.append(token_env)

if tokens_to_delete:
    env_manager = EnvFileManager()
    env_manager.remove(tokens_to_delete)
```

**After**:
```python
# Tokens are stored in YAML, deleted automatically when user/instance is removed
# No separate token cleanup needed
```

### 5. Updated Comments
**Before**:
```python
# Load configuration from YAML file (config/app_config.yaml)
# Secrets (tokens) are loaded from .env file
```

**After**:
```python
# Load configuration from YAML file (config/app_config.yaml)
# Tokens are stored encrypted in the YAML file
```

## Configuration Structure

### Old (with .env)
**app_config.yaml**:
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_env: GITHUB_EOS2GIT_TOKEN_DEFAULT_USER  # Reference to .env
      email: ''
```

**.env**:
```
GITHUB_EOS2GIT_TOKEN_DEFAULT_USER=ghp_actualtoken123
```

### New (YAML only)
**app_config.yaml**:
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_encrypted: gAAAAABh...  # Encrypted token stored directly
      email: ''
```

**.env**:
```
# No longer used (can be deleted)
```

## Migration Path

### For Existing Deployments
1. **Backup**: Save your current `.env` file
2. **Extract Tokens**: Get all tokens from `.env`
3. **Add to UI**: Use the configuration UI to add users with tokens
4. **Verify**: Test that all endpoints work
5. **Remove**: Delete or rename `.env` file

### For New Deployments
1. Set `ENCRYPTION_KEY` environment variable
2. Use configuration UI to add all endpoints and users
3. No `.env` file needed

## Environment Variables Still Used

The following environment variables are still used (but not from `.env`):
- `ENCRYPTION_KEY`: Required for encrypting/decrypting tokens
- `SECRET_KEY`: Flask secret key (optional, has default)
- `DATABASE_URL`: Database connection string (optional, has default)
- `SSL_VERIFY`: SSL verification setting (optional, defaults to false)

These should be set at the system/container level, not in a `.env` file.

## Benefits

### 1. **Single Source of Truth**
- All configuration in one place (`app_config.yaml`)
- No confusion about where settings are stored
- Easier to backup and restore

### 2. **Better Security**
- Tokens encrypted at rest
- No plain text tokens in `.env`
- Centralized encryption key management

### 3. **Simpler Deployment**
- One config file to manage
- No need to sync `.env` and YAML
- Easier to version control (encrypted tokens are safe)

### 4. **Cleaner Code**
- Removed `EnvFileManager` dependency
- Removed `load_dotenv()` calls
- Consistent configuration access pattern

### 5. **Better UX**
- All configuration through UI
- Immediate feedback (no file editing)
- No app restart needed for changes

## Testing

### Test Case 1: Add User with Token
1. Open Manage Users modal
2. Add user with username, email, and token
3. **Expected**: Token encrypted and saved to YAML
4. **Result**: ✅ Token stored as `token_encrypted` in YAML

### Test Case 2: Test Endpoint
1. Select user from dropdown
2. Click "Test" button
3. **Expected**: Token decrypted and used for authentication
4. **Result**: ✅ Authentication successful

### Test Case 3: Delete User
1. Delete a user
2. **Expected**: User and encrypted token removed from YAML
3. **Result**: ✅ User removed, no orphaned tokens

### Test Case 4: Update Token
1. Edit user and provide new token
2. **Expected**: Token re-encrypted and updated in YAML
3. **Result**: ✅ Token updated successfully

## Backward Compatibility

The system still supports `token_env` for backward compatibility:
```yaml
users:
- username: legacy_user
  token_env: GITHUB_TOKEN  # Still works if env var is set
  email: ''
```

But new users will use `token_encrypted`:
```yaml
users:
- username: new_user
  token_encrypted: gAAAAABh...  # Preferred method
  email: ''
```

## Files Modified
- `app.py`
  - Removed `load_dotenv()` import and call
  - Removed `EnvFileManager` import
  - Updated `/update-endpoint` route (GitHub, Jenkins, Artifactory)
  - Updated `/delete-endpoint` route
  - Updated comments

## Files No Longer Used
- `.env` - Can be deleted (but keep `ENCRYPTION_KEY` in system environment)
- `env_file_manager.py` - No longer imported (can be removed in future cleanup)

## Date
January 2025
