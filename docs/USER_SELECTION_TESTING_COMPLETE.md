# User Selection for Endpoint Testing - Implementation Complete

## Overview
This update adds user selection functionality to GitHub endpoint testing, allowing administrators to test individual user tokens and verify connectivity on a per-user basis.

## Features Implemented

### 1. User Selection Dropdown
Each GitHub endpoint card now includes a dropdown to select which user's token to test:

```html
<div class="mt-2">
    <label class="block text-xs font-medium text-gray-600 mb-1">Test with user:</label>
    <select id="user-select-{{ instance_id }}" class="text-xs border-gray-300 rounded-md shadow-sm">
        <option value="default_user" selected>default_user (default)</option>
        <option value="jpurcell">jpurcell</option>
        <option value="jpurcell2">jpurcell2</option>
    </select>
</div>
```

**Features:**
- Automatically populated from configured users
- Default user pre-selected
- Shows "(default)" label for default_user
- Clean, compact design that fits within the endpoint card

### 2. Updated Test Function
The `testEndpoint()` JavaScript function now:
- Retrieves the selected username from the dropdown
- Sends username to the backend in the test request
- Displays which user was tested in the success/failure message

```javascript
// Get selected username for GitHub endpoints
let username = '';
if (type === 'github') {
    const userSelect = document.getElementById(`user-select-${id}`);
    if (userSelect) {
        username = userSelect.value;
    }
}

const requestBody = {type: type, instance_id: id};
if (username) {
    requestBody.username = username;
}
```

### 3. Enhanced Feedback
Test results now show which user was tested:

**Success Message:**
```
Connection successful!

Successfully authenticated as jpurcell

Tested with user: jpurcell
```

**Failure Message:**
```
Connection failed!

GitHub token is required for testing

Tested with user: jpurcell2
```

## Backend Integration

### Updated `/test-endpoint` Route
The backend now properly handles the `username` parameter:

```python
username = request.json.get('user', '') or request.json.get('username', '')

# For GitHub endpoints
if endpoint_type == 'github':
    instance = config_manager.get_github_instance(instance_id)
    if instance:
        # Try to find the specified user or use default
        user_obj = None
        if username:
            user_obj = instance.get_user(username)
        if not user_obj:
            user_obj = instance.get_default_user()
        
        if user_obj:
            token = user_obj.token
            username = user_obj.username
```

## User Experience Flow

### 1. View Endpoint Configuration
- Navigate to Configuration page
- Click "Endpoints" tab
- See all GitHub instances with user selection dropdowns

### 2. Select User to Test
- Choose a user from the dropdown (default_user is pre-selected)
- Each user shows their username
- Default user is clearly marked

### 3. Test Connection
- Click "Test" button
- System tests with the selected user's token
- Status badge updates (Connected/Failed)
- Alert shows detailed results including username

### 4. Test Different Users
- Select a different user from dropdown
- Click "Test" again
- Compare results across different users
- Identify which users have valid tokens

## Benefits

### 1. **Granular Testing**
- Test each user's token individually
- Identify which users have valid/invalid tokens
- Verify token permissions per user

### 2. **Troubleshooting**
- Quickly identify token issues
- Test default connectivity vs. user-specific connectivity
- Diagnose permission problems

### 3. **Token Management**
- See which users need tokens configured
- Verify tokens after adding/updating them
- Ensure all users have working credentials

### 4. **Security**
- Test without exposing actual token values
- Verify tokens work before using in production scans
- Audit which users have valid access

## Testing Scenarios

### Scenario 1: All Users Have Tokens
```
GitHub Instance: ISG-Edge (eos2git)
Users:
  - default_user: ✓ Connected
  - jpurcell: ✓ Connected
  - jpurcell2: ✓ Connected
```

### Scenario 2: Mixed Token Status
```
GitHub Instance: ISG-Edge (eos2git)
Users:
  - default_user: ✓ Connected (from env var)
  - jpurcell: ✓ Connected (from env var)
  - jpurcell2: ✗ Failed (no token configured)
```

### Scenario 3: Default User Only
```
GitHub Instance: fusion-e (github)
Users:
  - default_user: ✓ Connected
  - jpurcell: ✗ Failed (no token)
```

## Configuration Examples

### With Environment Variables (Legacy)
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_env: GITHUB_EOS2GIT_TOKEN_DEFAULT_USER
      email: ''
    - username: jpurcell
      token_env: GITHUB_EOS2GIT_TOKEN_JPURCELL
      email: ''
```

### With Encrypted Tokens (New)
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_encrypted: gAAAAABh1234...
      email: ''
    - username: jpurcell
      token_encrypted: gAAAAABh5678...
      email: jeff.purcell@dell.com
```

### Mixed (Backward Compatible)
```yaml
github_instances:
  eos2git:
    users:
    - username: default_user
      token_env: GITHUB_EOS2GIT_TOKEN_DEFAULT_USER  # Legacy
      email: ''
    - username: jpurcell
      token_encrypted: gAAAAABh5678...  # New
      email: jeff.purcell@dell.com
```

## Files Modified

### Frontend
- `templates/config_redesigned.html`
  - Added user selection dropdown to GitHub endpoint cards
  - Updated `testEndpoint()` function to send username
  - Enhanced success/failure messages with username

### Backend
- `app.py`
  - Updated `/test-endpoint` to use ConfigManager
  - Added username parameter handling
  - Improved token retrieval logic

### Configuration
- `config_manager.py`
  - Added `get_user()` method to GitHubInstance
  - Added `get_default_user()` method
  - Updated token property to support encrypted tokens

## Next Steps

### Immediate
1. ✅ Test with actual environment variables
2. ✅ Verify user selection works correctly
3. ✅ Confirm error messages are helpful

### Future Enhancements
1. Add token input fields to user management modal
2. Support token encryption/decryption in UI
3. Add "Test All Users" button to test all users at once
4. Show token status (valid/invalid/not set) in user list
5. Add token expiration warnings

## Known Limitations

1. **Token Display**: Tokens are never displayed in the UI (security feature)
2. **Encryption Key**: Must be set in environment variable `ENCRYPTION_KEY`
3. **No Token Rotation**: Changing tokens requires manual update in config
4. **Single Instance Testing**: Can only test one user at a time

## Security Considerations

1. **Tokens Never Exposed**: UI never displays actual token values
2. **Encrypted Storage**: Tokens stored encrypted in config file
3. **Secure Transmission**: Tokens sent over HTTPS in production
4. **Access Control**: Only admins can access configuration page

## Troubleshooting

### User Dropdown is Empty
- Check that users are configured in `app_config.yaml`
- Verify the GitHub instance has a `users` array
- Reload the configuration page

### Test Always Fails
- Verify the selected user has a token configured
- Check environment variables are set (for legacy mode)
- Verify `ENCRYPTION_KEY` is set (for encrypted tokens)
- Check token permissions in GitHub

### "GitHub token required" Error
- Selected user has no token configured
- Add token via environment variable or encrypted token field
- Select a different user with a valid token

## Date
January 2025
