# Delete User Functionality - Fix Complete

## Issue
The delete user functionality was working at the API level (successfully removing users from `app_config.yaml`), but the configuration wasn't being reloaded, so the UI wouldn't reflect the changes until the app was restarted.

## Root Cause
After deleting a user and saving the config file, the `ConfigManager` singleton instance was still holding the old configuration in memory. Subsequent API calls would return the cached (old) user list instead of the updated one.

## Solution
Added `reload_config()` call after successfully deleting a user to force the ConfigManager to reload the configuration from disk.

### Code Changes

**File**: `app.py`

**Before**:
```python
@app.route('/api/github-user/<instance_id>/<username>', methods=['DELETE'])
def delete_github_user(instance_id, username):
    """Delete a GitHub user"""
    try:
        config_path = Path('config/app_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        github_instances = config.get('github_instances', {})
        
        if instance_id in github_instances:
            users = github_instances[instance_id].get('users', [])
            github_instances[instance_id]['users'] = [u for u in users if u.get('username') != username]
            
            config['github_instances'] = github_instances
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return jsonify({'success': True, 'message': 'User deleted successfully'})
```

**After**:
```python
@app.route('/api/github-user/<instance_id>/<username>', methods=['DELETE'])
def delete_github_user(instance_id, username):
    """Delete a GitHub user"""
    try:
        config_path = Path('config/app_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        github_instances = config.get('github_instances', {})
        
        if instance_id in github_instances:
            users = github_instances[instance_id].get('users', [])
            github_instances[instance_id]['users'] = [u for u in users if u.get('username') != username]
            
            config['github_instances'] = github_instances
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            # Reload configuration to pick up changes
            reload_config()
            
            return jsonify({'success': True, 'message': 'User deleted successfully'})
```

## Additional Improvements

### Updated Add/Update User Endpoint
Also updated the `update_github_user` endpoint to:
1. Use encrypted token storage instead of environment variables
2. Reload configuration after saving changes

**Before**:
```python
# Set token in environment variable
if token:
    token_env = f"GITHUB_{instance_id.upper()}_TOKEN_{username.upper()}"
    os.environ[token_env] = token

flash(f'User {username} saved successfully', 'success')
return redirect(url_for('config'))
```

**After**:
```python
# Check if user exists
user_exists = False
for user in users:
    if user.get('username') == username:
        user['email'] = email
        # Update token if provided
        if token:
            user['token_encrypted'] = encrypt_token(token)
        user_exists = True
        break

# Add new user if doesn't exist
if not user_exists:
    new_user = {
        'username': username,
        'email': email
    }
    # Add encrypted token if provided
    if token:
        new_user['token_encrypted'] = encrypt_token(token)
    users.append(new_user)

# ... save to file ...

# Reload configuration to pick up changes
reload_config()

flash(f'User {username} saved successfully', 'success')
return redirect(url_for('config'))
```

## Testing

### Test Case 1: Delete User
1. Open Manage Users modal for a GitHub instance
2. Click "Delete" on a user
3. Confirm deletion
4. **Expected**: User is removed from the list immediately
5. **Result**: ✅ User removed successfully

### Test Case 2: Add User
1. Open Manage Users modal
2. Fill in username and email
3. Click "Add User"
4. **Expected**: User appears in the list immediately
5. **Result**: ✅ User added successfully

### Test Case 3: Edit User
1. Open Manage Users modal
2. Click "Edit" on a user
3. Update email or token
4. Save changes
5. **Expected**: Changes reflected immediately
6. **Result**: ✅ User updated successfully

## Configuration Reload Mechanism

The `reload_config()` function works as follows:

```python
# In config_manager.py
_config_manager = None  # Singleton instance

def reload_config():
    """Reload configuration from file"""
    global _config_manager
    if _config_manager is not None:
        _config_manager.reload()
    else:
        _config_manager = ConfigManager()
```

The `ConfigManager.reload()` method:
```python
def reload(self):
    """Reload configuration from file"""
    self.config = self._load_config()
    self._validate_config()
```

This ensures that:
1. The YAML file is re-read from disk
2. The configuration is re-validated
3. All subsequent API calls use the updated configuration

## Files Modified
- `app.py`
  - Added `reload_config()` call in `delete_github_user()`
  - Updated `update_github_user()` to use encrypted tokens
  - Added `reload_config()` call in `update_github_user()`

## Related Endpoints
The following endpoints already had `reload_config()` calls:
- `/update-endpoint` (GitHub, Jenkins, Artifactory)
- `/delete-endpoint` (GitHub, Jenkins)

## Benefits
1. **Immediate Feedback**: Changes are reflected immediately without app restart
2. **Better UX**: Users see updates in real-time
3. **Consistency**: All CRUD operations now reload config
4. **Encrypted Tokens**: User tokens now stored encrypted instead of in environment variables

## Date
January 2025
