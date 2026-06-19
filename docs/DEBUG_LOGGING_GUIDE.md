# Debug Logging Guide
## OSS Compliance Web Application

**Version:** 1.0  
**Last Updated:** 2026-06-12  
**Application Version:** 1.0

---

## Table of Contents
1. [Overview](#overview)
2. [Configuration Options](#configuration-options)
3. [Web Interface Control](#web-interface-control)
4. [Configuration File Control](#configuration-file-control)
5. [Environment Variable Control](#environment-variable-control)
6. [Debug Output Examples](#debug-output-examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

As of version 1.0, the OSS Compliance Web Application features configurable debug logging that can be controlled through multiple methods:

- **Web Interface**: Toggle debug logging via the Configuration page
- **Configuration File**: Set debug logging in `config/app_config.yaml`
- **Environment Variables**: Control via `FLASK_DEBUG` environment variable
- **Programmatic Control**: Use the `set_debug_logging()` function in code

This flexible approach allows for easy troubleshooting in production without requiring code changes or restarts.

### Key Features

- **Runtime Control**: Enable/disable debug logging without application restart
- **Granular Control**: Separate application debug logging from Flask debug mode
- **Security**: Debug logging defaults to enabled but can be disabled in production
- **Centralized Management**: Single source of truth for debug logging configuration

---

## Configuration Options

### Application vs. Flask Debug Mode

The application provides two separate debug controls:

#### Application Debug Logging (`debug_logging`)
- **Location**: `config/app_config.yaml` under `app_settings.debug_logging`
- **Scope**: Application-specific debug output (scan operations, API calls, etc.)
- **Control**: Web interface, configuration file, programmatic
- **Impact**: Controls `print(f"DEBUG: ...")` statements throughout the application

#### Flask Debug Mode (`FLASK_DEBUG`)
- **Location**: Environment variable or `.env` file
- **Scope**: Flask framework debug mode (auto-reload, error pages, etc.)
- **Control**: Environment variables, Docker compose configuration
- **Impact**: Controls Flask's development mode features

**Recommendation**: Use application debug logging for troubleshooting scan operations, and Flask debug mode only during development.

---

## Web Interface Control

### Accessing Debug Settings

1. Navigate to the Configuration page: `http://localhost:5001/config`
2. Scroll to the "Application Settings" section
3. Locate the "Debug Logging" toggle

### Enabling/Disabling Debug Logging

1. **To Enable**: Check the "Enable Debug Logging" checkbox
2. **To Disable**: Uncheck the "Enable Debug Logging" checkbox
3. **Apply Changes**: Click the "Save Settings" button

### Verification

After saving, you should see a confirmation message:
- "Debug logging enabled successfully" 
- "Debug logging disabled successfully"

The changes take effect immediately without requiring an application restart.

---

## Configuration File Control

### Location

The debug logging setting is stored in:
```
config/app_config.yaml
```

### Configuration Structure

```yaml
app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
  debug_logging: true  # Set to false to disable
```

### Updating the Configuration

1. Open `config/app_config.yaml` in a text editor
2. Locate the `app_settings` section
3. Set `debug_logging` to `true` or `false`
4. Save the file
5. The application will automatically reload the configuration

### Validation

The configuration is validated on load. Invalid values will default to `true`.

---

## Environment Variable Control

### FLASK_DEBUG Environment Variable

The `FLASK_DEBUG` environment variable controls Flask's debug mode:

```bash
# Enable Flask debug mode
export FLASK_DEBUG=True

# Disable Flask debug mode
export FLASK_DEBUG=False
```

### Docker Compose Configuration

In `docker-compose.yml`:

```yaml
environment:
  - FLASK_DEBUG=${FLASK_DEBUG:-True}  # Defaults to True if not set
```

### .env File Configuration

In `.env` file:

```env
# Flask debug mode (development vs production)
FLASK_DEBUG=True

# Application environment
FLASK_ENV=production
```

### Environment Variable Precedence

1. **Runtime Environment Variables**: Highest priority
2. **.env File**: Medium priority
3. **docker-compose.yml Defaults**: Lowest priority

---

## Debug Output Examples

### GitHub API Calls

When debug logging is enabled, you'll see output like:

```
DEBUG: GitHub config - API URL: https://api.github.com
DEBUG: GitHub config - Org: Fusion-e
DEBUG: GitHub config - Token present: Yes
DEBUG: GitHub config - Token (first 10 chars): ghp_xxxxxx...
```

### Repository Scanning

```
DEBUG: Scan GitHub config - API URL: https://api.github.com
DEBUG: Scan GitHub config - Org: Fusion-e
DEBUG: Scan GitHub config - Token present: Yes
DEBUG: Scan GitHub config - Token (first 10 chars): ghp_xxxxxx...
```

### Jenkins Operations

```
DEBUG: Checking Jenkins GOPROXY config with 2 URLs
DEBUG: Successfully connected to Jenkins at https://jenkins.example.com, found 15 jobs
DEBUG: Found GOPROXY in Jenkins job hzp-build-job
```

### SSL Configuration

```
DEBUG: SSL_VERIFY from env: 'false', ssl_verify set to: False
```

---

## Best Practices

### Production Environments

1. **Default to Disabled**: Set `debug_logging: false` in production configurations
2. **Enable Temporarily**: Enable debug logging only when troubleshooting specific issues
3. **Monitor Logs**: When enabled, monitor log volume to prevent disk space issues
4. **Security**: Ensure debug logs don't contain sensitive information

### Development Environments

1. **Keep Enabled**: Leave debug logging enabled during development
2. **Use Flask Debug Mode**: Combine with `FLASK_DEBUG=True` for full development experience
3. **Regular Review**: Periodically review debug output for optimization opportunities

### Troubleshooting Workflow

1. **Reproduce Issue**: Ensure the issue is reproducible
2. **Enable Debug Logging**: Turn on debug logging via web interface
3. **Perform Operation**: Execute the failing operation
4. **Review Output**: Analyze debug output for clues
5. **Disable Logging**: Turn off debug logging after troubleshooting
6. **Document Findings**: Record the issue and resolution

### Security Considerations

1. **Token Masking**: Debug output masks sensitive tokens (shows first 10 chars only)
2. **Access Control**: Restrict configuration page access to authorized users
3. **Log Retention**: Implement log rotation for debug output
4. **Audit Trail**: Log configuration changes for audit purposes

---

## Troubleshooting

### Debug Logging Not Working

**Symptoms**: Debug output not appearing despite being enabled

**Solutions**:
1. Check `config/app_config.yaml` for correct syntax
2. Verify the application has read access to the configuration file
3. Check for Python syntax errors in application code
4. Restart the application to reload configuration

### Configuration Changes Not Taking Effect

**Symptoms**: Changes to debug logging setting don't affect output

**Solutions**:
1. Clear application cache: `rm -rf cache/*`
2. Check for multiple configuration files
3. Verify YAML syntax is correct
4. Check application logs for configuration errors

### Excessive Debug Output

**Symptoms**: Too much debug output flooding logs

**Solutions**:
1. Disable debug logging when not needed
2. Implement log rotation in your logging system
3. Filter debug output in your log management system
4. Use selective debug logging for specific components

### Web Interface Not Responding

**Symptoms**: Configuration page changes don't save

**Solutions**:
1. Check file permissions on `config/app_config.yaml`
2. Verify the application has write access to configuration directory
3. Check browser console for JavaScript errors
4. Review application logs for server-side errors

---

## Programmatic Control

### Setting Debug Logging in Code

```python
# In app.py or other modules
from app import set_debug_logging

# Enable debug logging
set_debug_logging(True)

# Disable debug logging
set_debug_logging(False)
```

### Setting Debug Logging in Remote Scanner

```python
# In remote_scanner.py
from remote_scanner import set_debug_logging

# Enable debug logging
set_debug_logging(True)

# Disable debug logging
set_debug_logging(False)
```

### Checking Debug Logging Status

```python
# Check current debug logging status
if _debug_logging_enabled:
    print("Debug logging is enabled")
else:
    print("Debug logging is disabled")
```

---

## Migration from Previous Versions

### Version 0.5.x to 1.0

**Breaking Changes**: None

**New Features**:
- Added `debug_logging` configuration option
- Added web interface control for debug logging
- Removed hardcoded debug statements

**Migration Steps**:
1. Update `config/app_config.yaml` to include `debug_logging: true`
2. Update Docker configuration to use `FLASK_DEBUG=${FLASK_DEBUG:-True}`
3. Remove any hardcoded debug print statements from custom code
4. Test the new debug logging functionality

**Configuration Migration**:
```yaml
# Add to app_settings section
app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
  debug_logging: true  # New in v1.0
```

---

## Appendix

### Configuration File Schema

```yaml
version: '1.0'
artifactory:
  base_url: string
  virtual_repos:
    docker: string
    go: string
    # ... other repos
github_instances:
  instance_id:
    name: string
    api_url: string
    org: string
    users:
      - username: string
        token_env: string
        email: string
jenkins:
  user: string
  token_env: string
  urls:
    - string
  pr_validation_job: string
whitelist_urls:
  - string
app_settings:
  max_scan_threads: integer
  cache_ttl_hours: integer
  report_retention_days: integer
  debug_logging: boolean  # New in v1.0
```

### Environment Variable Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FLASK_DEBUG` | boolean | `True` | Flask framework debug mode |
| `FLASK_ENV` | string | `production` | Flask environment mode |
| `ENCRYPTION_KEY` | string | - | Fernet encryption key for credentials |
| `SSL_VERIFY` | boolean | `false` | SSL certificate verification |

### Related Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Full deployment instructions
- [Configuration Guide](CONFIGURATION_QUICK_START.md) - Configuration management
- [API Reference](API_REFERENCE.md) - Complete API documentation

---

**Document Status**: Complete  
**Last Updated**: 2026-06-12  
**Next Review**: 2026-09-12