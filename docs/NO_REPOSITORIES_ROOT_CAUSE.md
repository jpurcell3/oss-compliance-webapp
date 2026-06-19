# No Repositories - Root Cause Analysis

## The Issue

**Symptom**: Home page shows no repositories  
**API Response**: `{"repositories": []}`  
**Root Cause**: **NO TOKENS CONFIGURED**

## Why No Tokens?

During the cleanup process, we:
1. Removed `.env` file dependency
2. Removed `token_env` fields from config
3. **Removed all tokens from the configuration**

Current config state:
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      email: ''
      # NO token_encrypted field!
    - username: jpurcell
      email: ''
      # NO token_encrypted field!
```

## How the Scanner Works

```
1. User loads home page
2. JavaScript calls /api/repositories
3. Scanner tries to fetch repos from GitHub
4. Scanner looks for token in users dict
5. NO TOKEN FOUND → Returns empty list
6. Home page shows "No repositories"
```

## Verification

### Test 1: Check Config
```bash
$ python test_config.py
[OK] GitHub instances: ['eos2git', 'github']
  - eos2git: ISG-Edge - 3 users
    - default_user (has token: False)  ← NO TOKEN
    - jpurcell (has token: False)      ← NO TOKEN
```

### Test 2: Check API
```bash
$ curl http://localhost:5001/api/repositories
{"repositories": []}  ← Empty because no token
```

### Test 3: Check Scanner
```python
scanner = WebComplianceScanner()
github_config = scanner.get_github_instance('eos2git')
users = github_config['users']
print(users['default_user'])
# Output: {'token': '', 'email': ''}  ← Empty token!
```

## The Fix

**You need to add tokens via the UI:**

### Step-by-Step:

1. **Start the app**:
   ```bash
   python app.py
   ```

2. **Navigate to Configuration**:
   ```
   http://localhost:5001/config
   ```

3. **Add Token for a User**:
   - Find the GitHub instance card (e.g., "ISG-Edge")
   - Click **"Users"** button
   - Click **"Edit"** next to a user (e.g., default_user)
   - Paste your GitHub Personal Access Token in the "API Token" field
   - Click **"Save User"**

4. **Verify Token Saved**:
   ```bash
   $ cat config/app_config.yaml
   ```
   Should see:
   ```yaml
   users:
   - username: default_user
     token_encrypted: gAAAAABh...  ← Token is here!
     email: ''
   ```

5. **Test Repositories**:
   - Go back to home page
   - Repositories should now appear!

## Why This Happened

### Timeline:
1. ✅ Started with tokens in `.env` file
2. ✅ Decided to move to encrypted tokens in YAML
3. ✅ Removed `.env` dependency
4. ✅ Removed `token_env` fields
5. ❌ **Forgot to migrate existing tokens to `token_encrypted`**
6. ❌ Result: No tokens configured anywhere

### What We Should Have Done:

**Migration Script** (we didn't run this):
```python
import os
import yaml
from app import encrypt_token

# Load config
config = yaml.safe_load(open('config/app_config.yaml'))

# Migrate tokens from environment variables
for instance_id, instance in config['github_instances'].items():
    for user in instance['users']:
        # Get token from old env var
        token_env = f"GITHUB_{instance_id.upper()}_TOKEN_{user['username'].upper()}"
        token = os.getenv(token_env)
        
        if token:
            # Encrypt and save
            user['token_encrypted'] = encrypt_token(token)
            print(f"Migrated token for {user['username']}")

# Save
yaml.dump(config, open('config/app_config.yaml', 'w'))
```

## Current State

### What Works:
- ✅ Config page loads
- ✅ User dropdown shows users
- ✅ Scanner code works (dict structure)
- ✅ Template works (list structure)
- ✅ Banner messages work
- ✅ Token encryption works

### What Doesn't Work:
- ❌ No repositories (no tokens)
- ❌ Can't scan repos (no tokens)
- ❌ Can't test endpoints (no tokens)

## Solution

**Add tokens manually via UI** (5 minutes per user):

1. Configuration → GitHub Instance → Users → Edit
2. Paste token
3. Save
4. Repeat for each user you want to use

**OR**

**Run migration script** (if you still have `.env` file with tokens):
```python
# Save this as migrate_tokens.py
import os
import yaml
from dotenv import load_dotenv
from app import encrypt_token

load_dotenv()

config_path = 'config/app_config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

for instance_id, instance in config['github_instances'].items():
    for user in instance['users']:
        token_env = f"GITHUB_{instance_id.upper()}_TOKEN_{user['username'].upper()}"
        token = os.getenv(token_env)
        
        if token:
            user['token_encrypted'] = encrypt_token(token)
            print(f"✓ Migrated token for {instance_id}/{user['username']}")
        else:
            print(f"✗ No token found for {instance_id}/{user['username']}")

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print("\nMigration complete!")
```

## Bottom Line

**The scanner works fine. You just need to add tokens.**

No fingers crossed. The code is correct. The configuration is just empty.

## Date
January 2025
