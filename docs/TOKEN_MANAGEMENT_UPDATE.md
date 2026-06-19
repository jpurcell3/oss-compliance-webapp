# Token Management Update - Encrypted Token Storage

## Overview
This update transitions the application from environment variable-based token storage to encrypted token storage directly in the `app_config.yaml` file. This provides better security, easier management, and the ability to test individual user tokens.

## Problem Statement
The original implementation had several issues:
1. **Endpoint testing failed** with "GitHub token required" errors
2. **User list was empty** in the Manage Users modal
3. **No way to test individual user tokens** - only generic connectivity
4. **Tokens stored in environment variables** - difficult to manage and not portable

## Solution

### 1. Updated Configuration Structure

#### Before (Environment Variable Based):
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_env: GITHUB_EOS2GIT_TOKEN_DEFAULT_USER  # Reference to env var
      email: ''
```

#### After (Encrypted Token Storage):
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_env: GITHUB_EOS2GIT_TOKEN_DEFAULT_USER  # Legacy support (optional)
      token_encrypted: gAAAAABh...  # New: encrypted token (optional)
      email: ''
```

### 2. Updated Data Classes

#### GitHubUser
- Added `token_encrypted` field for storing encrypted tokens
- Made `token_env` optional (legacy support)
- Updated `token` property to try encrypted token first, then fall back to environment variable

#### JenkinsConfig
- Added `token_encrypted` field
- Made `token_env` optional
- Updated `token` property with same fallback logic

#### ArtifactoryConfig
- Added `user`, `token_env`, and `token_encrypted` fields
- Added `token` property for consistent access

### 3. Updated API Endpoints

#### `/api/github-users/<instance_id>`
- Now uses `ConfigManager` instead of `WebComplianceScanner`
- Returns proper user list with `has_token` flag
- Converts `GitHubUser` objects to JSON-serializable dicts

#### `/api/github-user/<instance_id>/<username>`
- Updated to use `ConfigManager`
- Returns user details including token status

#### `/test-endpoint`
- Updated to use `ConfigManager` for all endpoint types
- Properly retrieves tokens from encrypted storage or environment variables
- Supports user selection for GitHub endpoints

### 4. Token Encryption/Decryption

The application uses Fernet (symmetric encryption) to secure tokens:

```python
def encrypt_token(token: str) -> str:
    """Encrypt a token using Fernet encryption."""
    key = get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(token.encode())
    return encrypted.decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token using Fernet encryption."""
    key = get_encryption_key()
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()
```

**Note**: The encryption key is stored in the `ENCRYPTION_KEY` environment variable. This should be generated once and kept secure.

## Benefits

### 1. **Improved Security**
- Tokens are encrypted at rest in the config file
- No plain text tokens in environment variables
- Centralized encryption key management

### 2. **Better Usability**
- Users can be managed through the UI
- Tokens can be added/updated without restarting the application
- User list now displays correctly in the Manage Users modal

### 3. **Enhanced Testing**
- Can test individual user tokens
- Default user for generic connectivity testing
- User selection dropdown for endpoint testing (coming in next phase)

### 4. **Backward Compatibility**
- Still supports `token_env` for legacy configurations
- Graceful fallback from encrypted to environment variable tokens
- No breaking changes to existing deployments

## Migration Path

### For New Deployments
1. Generate an encryption key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Set `ENCRYPTION_KEY` environment variable
3. Add users with `token_encrypted` field (use UI or encrypt manually)

### For Existing Deployments
1. Continue using `token_env` (no changes required)
2. Optionally migrate to encrypted tokens:
   - Generate encryption key
   - Use UI to add encrypted tokens
   - Remove `token_env` references once encrypted tokens are set

## Testing Results

### Configuration Loading
```
[OK] Config loaded successfully
[OK] GitHub instances: ['eos2git', 'github']
  - eos2git: ISG-Edge - 3 users
    - default_user (has token: True)
    - jpurcell (has token: True)
    - jpurcell2 (has token: False)
  - github: fusion-e - 2 users
    - default_user (has token: True)
    - jpurcell (has token: False)
[OK] Jenkins: jpurcell - 1 URLs (has token: True)
[OK] Artifactory: isgedge.artifactory.cec.lab.emc.com (has token: False)
```

### API Endpoint Test
```json
{
  "success": true,
  "users": [
    {
      "email": "",
      "has_token": true,
      "username": "default_user"
    },
    {
      "email": "",
      "has_token": true,
      "username": "jpurcell"
    },
    {
      "email": "",
      "has_token": false,
      "username": "jpurcell2"
    }
  ]
}
```

## Next Steps

### Phase 1: User Selection for Testing (In Progress)
- Add user selection dropdown to endpoint cards
- Update test endpoint to accept username parameter
- Show test results per user

### Phase 2: Token Management UI (Pending)
- Add token input fields to Add/Edit User modals
- Encrypt tokens before saving to config
- Show token status (set/not set) without revealing actual token

### Phase 3: Full Testing (Pending)
- Test all endpoints with user selection
- Verify encryption/decryption
- Test migration from env vars to encrypted tokens

## Files Modified

### Core Files
- `config_manager.py` - Updated data classes with token_encrypted support
- `app.py` - Updated `/test-endpoint` and user API endpoints to use ConfigManager

### Configuration
- `config/app_config.yaml` - Schema updated to support token_encrypted field

### Documentation
- `docs/TOKEN_MANAGEMENT_UPDATE.md` - This document

## Security Considerations

1. **Encryption Key**: Must be kept secure and backed up
2. **Config File**: Should have restricted file permissions (600 on Linux)
3. **Backups**: Encrypted tokens in backups are useless without the encryption key
4. **Key Rotation**: Not currently supported - would require re-encrypting all tokens

## Date
January 2025
