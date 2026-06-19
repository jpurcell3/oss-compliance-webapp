# Quick Start: Add Tokens to Configuration

## The Issue
After cleaning up the configuration to remove `.env` dependency and `token_env` fields, all tokens were removed from the configuration. You need to add them back via the UI.

## How to Add Tokens

### Step 1: Start the Application
```bash
cd "C:\Users\jpurcell\OneDrive - Dell Technologies\Documents\GitHub\projects\oss-compliance-webapp"
python app.py
```

### Step 2: Navigate to Configuration
1. Open browser to `http://localhost:5001`
2. Click on **Configuration** in the navigation menu
3. You'll see your GitHub instances listed

### Step 3: Add Token to a User

#### For GitHub Instances:
1. Find the GitHub instance card (e.g., "ISG-Edge" or "fusion-e")
2. Click the **"Users"** button
3. In the "Manage Users" modal, you'll see a list of users
4. Click **"Edit"** next to the user you want to add a token for
5. The form will populate with:
   - Username (read-only when editing)
   - Email
   - **API Token (optional)** ← Enter your GitHub token here
6. Paste your GitHub Personal Access Token
7. Click **"Save User"**
8. The token will be encrypted and saved to `config/app_config.yaml`

#### For Jenkins:
1. Find the Jenkins card
2. Click **"Edit"**
3. Enter your Jenkins API token
4. Click **"Save"**

#### For Artifactory:
1. Find the Artifactory card
2. Click **"Edit"**
3. Enter your Artifactory token
4. Click **"Save"**

### Step 4: Test the Connection
1. After adding a token, go back to the endpoint card
2. Select the user from the **"Test with user:"** dropdown
3. Click **"Test"**
4. You should see a success message if the token is valid

## Token Security

### How Tokens Are Stored
- Tokens are **encrypted** using Fernet encryption
- Stored as `token_encrypted` in `config/app_config.yaml`
- Example:
  ```yaml
  users:
  - username: jpurcell
    token_encrypted: gAAAAABh1234567890abcdef...
    email: jeff.purcell@dell.com
  ```

### Encryption Key
The encryption key is stored in the `ENCRYPTION_KEY` environment variable. Make sure this is set:

**Windows (PowerShell)**:
```powershell
$env:ENCRYPTION_KEY = "your-encryption-key-here"
```

**Linux/Mac**:
```bash
export ENCRYPTION_KEY="your-encryption-key-here"
```

**Docker**:
```yaml
environment:
  - ENCRYPTION_KEY=your-encryption-key-here
```

If `ENCRYPTION_KEY` is not set, the app will generate a new one on startup (but this means you won't be able to decrypt tokens after restart).

## Quick Token Setup for All Users

If you want to quickly add tokens for all your users:

### 1. Open Configuration Page
Navigate to `http://localhost:5001/config`

### 2. For Each GitHub Instance:
- Click **"Users"** button
- For each user:
  - Click **"Edit"**
  - Paste the token
  - Click **"Save User"**

### 3. Test Each Endpoint:
- Select user from dropdown
- Click **"Test"**
- Verify success

## Example: Adding Token for "default_user"

1. **Navigate**: Configuration → GitHub Instances → ISG-Edge
2. **Click**: "Users" button
3. **Find**: "default_user" in the list
4. **Click**: "Edit" button next to default_user
5. **Form appears**:
   ```
   Username: default_user (read-only)
   Email: [empty or existing]
   API Token: [paste your token here]
   ```
6. **Paste**: Your GitHub Personal Access Token (e.g., `ghp_abc123...`)
7. **Click**: "Save User"
8. **Success**: Token is now encrypted and saved

## Verifying Tokens Are Saved

### Check the Config File:
```bash
cat config/app_config.yaml
```

You should see:
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_encrypted: gAAAAABh...  # ← Token is here!
      email: ''
```

### Check via Test:
1. Select user from dropdown
2. Click "Test"
3. Should see: "✓ Connection successful"

## Troubleshooting

### "GitHub token required" Error
**Cause**: No token configured for the selected user

**Fix**: 
1. Click "Users" button
2. Edit the user
3. Add a token
4. Save

### "Decryption failed" Error
**Cause**: `ENCRYPTION_KEY` changed or not set

**Fix**:
1. Set `ENCRYPTION_KEY` environment variable
2. Re-add all tokens via UI

### Token Field is Empty When Editing
**This is normal!** For security, we never display existing tokens in the UI. The token field will always be empty when editing a user. If you leave it blank, the existing token is kept. If you enter a new token, it will replace the old one.

## Current Configuration State

After cleanup, your config looks like this:

```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      email: ''
      # NO token_encrypted yet - need to add via UI
    - username: jpurcell
      email: ''
      # NO token_encrypted yet - need to add via UI
```

**You need to add tokens via the UI for each user you want to test with.**

## Summary

1. ✅ Token input field exists in UI
2. ✅ Token is optional (can add later)
3. ✅ Token is encrypted when saved
4. ✅ Token is stored in `config/app_config.yaml`
5. ⚠️ **You need to add tokens via UI** - they were removed during cleanup

**Next Step**: Open the UI and add your tokens!

## Date
January 2025
