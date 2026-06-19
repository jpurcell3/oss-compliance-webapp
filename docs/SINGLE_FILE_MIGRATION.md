# Single-File Configuration Migration Guide

**Date:** 2026-06-12  
**Version:** OSS Compliance Web Application v0.5.0

---

## Overview

The OSS Compliance Web Application has been simplified to use **a single YAML configuration file** instead of maintaining two separate configuration files. This eliminates confusion and reduces the chance of configuration errors.

### Before (Two Files - Confusing!)

```
.env (40+ variables - configuration + secrets mixed together)
├── ARTIFACTORY_BASE=...
├── VIRTUAL_REPO_DOCKER=...
├── GITHUB_INSTANCES=...
├── GITHUB_INSTANCE_eos2git_USERS={"default_user": {"token": "..."}}
├── GITHUB_TOKEN=...
└── ... (many more)

config/app_config.yaml (duplicate configuration)
├── artifactory: ...
├── github_instances: ...
└── ... (duplicates .env)
```

**Problems:**
- ❌ Two files to maintain
- ❌ Configuration duplicated
- ❌ Secrets mixed with configuration
- ❌ Confusing which file to edit
- ❌ Easy to get out of sync

### After (Single File - Clear!)

```
config/app_config.yaml (ALL configuration)
├── artifactory: {base_url, virtual_repos}
├── github_instances: {name, api_url, org, users}
├── jenkins: {user, token_env, urls}
└── whitelist_urls: [...]

.env (ONLY secrets)
├── ENCRYPTION_KEY=...
├── SECRET_KEY=...
├── GITHUB_EOS2GIT_TOKEN_DEFAULT_USER=...
├── GITHUB_EOS2GIT_TOKEN_JPURCELL=...
└── JENKINS_API_TOKEN=...
```

**Benefits:**
- ✅ Single source of truth for configuration
- ✅ Secrets separated from configuration
- ✅ Clear what goes where
- ✅ Easy to maintain
- ✅ No duplication

---

## Migration Steps

### Step 1: Run Migration Script

```bash
cd oss-compliance-webapp
python migrate_config.py --yes
```

**What it does:**
1. Backs up your current `.env` to `.env.backup.pre-migration`
2. Backs up your current `config/app_config.yaml` to `config/app_config.yaml.backup.pre-migration`
3. Extracts all configuration from `.env` to `config/app_config.yaml`
4. Extracts all tokens from JSON format to individual environment variables
5. Creates new `.env` with ONLY secrets (tokens and keys)
6. Generates new `ENCRYPTION_KEY` and `SECRET_KEY`

### Step 2: Review New Files

**Check `config/app_config.yaml`:**
```bash
cat config/app_config.yaml
```

Should contain:
- Artifactory configuration
- GitHub instances (2: eos2git, github)
- Jenkins configuration
- Whitelist URLs
- App settings

**Check `.env`:**
```bash
cat .env
```

Should contain ONLY:
- `SECRET_KEY`
- `ENCRYPTION_KEY`
- `GITHUB_*_TOKEN_*` (individual tokens)
- `JENKINS_API_TOKEN`

### Step 3: Test Configuration

```bash
python test_config.py
```

Expected output:
```
✓ All ConfigManager tests passed!
✓ All EnvFileManager tests passed!
```

### Step 4: Test Application

```bash
python test_admin_config.py
```

Should show:
- 2 GitHub instances (eos2git, github)
- All users with tokens
- Artifactory configuration
- Whitelist URLs

### Step 5: Restart Application

```bash
# Local
python app.py

# Docker
docker-compose down
docker-compose up --build -d
```

---

## What Changed

### Configuration Loading

**Before:**
```python
# Hybrid loading - confusing!
if os.getenv('GITHUB_INSTANCES'):
    # Use environment variables
    instances = load_from_env()
else:
    # Use YAML
    instances = load_from_yaml()
```

**After:**
```python
# Simple - always use YAML!
config = get_config_manager()
instances = config.get_github_instances()
```

### Token Storage

**Before (JSON in .env):**
```env
GITHUB_INSTANCE_eos2git_USERS={"default_user": {"token": "ghp_..."}, "jpurcell": {"token": "ghp_..."}}
```

**After (Individual env vars):**
```env
GITHUB_EOS2GIT_TOKEN_DEFAULT_USER=ghp_...
GITHUB_EOS2GIT_TOKEN_JPURCELL=ghp_...
```

### YAML Configuration

**Before (incomplete):**
```yaml
github_instances:
  eos2git:
    users:
      - username: "default_user"
        token_env: "GITHUB_EOS2GIT_TOKEN_1"  # Didn't exist!
```

**After (complete):**
```yaml
github_instances:
  eos2git:
    name: "ISG-Edge"
    api_url: "https://eos2git.cec.lab.emc.com/api/v3"
    org: "ISG-Edge"
    users:
      - username: "default_user"
        token_env: "GITHUB_EOS2GIT_TOKEN_DEFAULT_USER"  # Exists in .env!
      - username: "jpurcell"
        token_env: "GITHUB_EOS2GIT_TOKEN_JPURCELL"  # Exists in .env!
```

---

## Rollback (If Needed)

If something goes wrong, you can rollback:

```bash
# Restore old files
mv .env.backup.pre-migration .env
mv config/app_config.yaml.backup.pre-migration config/app_config.yaml

# Restart application
python app.py
```

---

## New File Structure

### config/app_config.yaml (Configuration)

```yaml
version: '1.0'

artifactory:
  base_url: isgedge.artifactory.cec.lab.emc.com
  virtual_repos:
    docker: isgedge-docker-virtual
    go: isgedge-go-virtual
    # ... more repos

github_instances:
  eos2git:
    name: ISG-Edge
    api_url: https://eos2git.cec.lab.emc.com/api/v3
    org: ISG-Edge
    users:
      - username: default_user
        token_env: GITHUB_EOS2GIT_TOKEN_DEFAULT_USER
        email: ''
      - username: jpurcell
        token_env: GITHUB_EOS2GIT_TOKEN_JPURCELL
        email: ''
  
  github:
    name: fusion-e
    api_url: https://api.github.com/fusion-e
    org: Fusion-e
    users:
      - username: default_user
        token_env: GITHUB_GITHUB_TOKEN_DEFAULT_USER
        email: ''

jenkins:
  user: jpurcell
  token_env: JENKINS_API_TOKEN
  urls:
    - https://osj-isg-03-prd.cec.delllabs.net
  pr_validation_job: oss-compliance-validation

whitelist_urls:
  - github.com/fusion-e
  - eos2git.cec.lab.emc.com/ISG-Edge
  - eos2git.cec.lab.emc.com
  - github.com/cloudify-cosmo

app_settings:
  max_scan_threads: 4
  cache_ttl_hours: 1
  report_retention_days: 90
```

### .env (Secrets Only)

```env
# OSS Compliance Web Application - Secrets Only
# Configuration is in config/app_config.yaml

# Flask Configuration
SECRET_KEY=<your-secret-key>
FLASK_ENV=production

# Encryption Key
ENCRYPTION_KEY=<your-encryption-key>

# GitHub Tokens
GITHUB_EOS2GIT_TOKEN_DEFAULT_USER=<your-github-token>
GITHUB_EOS2GIT_TOKEN_JPURCELL=<your-github-token>
GITHUB_GITHUB_TOKEN_DEFAULT_USER=<your-github-token>

# Jenkins Token
JENKINS_API_TOKEN=<your-jenkins-token>
```

---

## Frequently Asked Questions

### Q: Why make this change?

**A:** Having two configuration files was confusing and error-prone. Users didn't know which file to edit, and configuration could get out of sync. Now there's one clear place for configuration (YAML) and one clear place for secrets (.env).

### Q: Do I have to migrate?

**A:** Yes, the application now requires `config/app_config.yaml`. The migration script makes it easy - just run `python migrate_config.py --yes`.

### Q: What if I have custom configuration?

**A:** The migration script preserves all your configuration. It extracts everything from `.env` and puts it in the YAML file.

### Q: Can I still use environment variables?

**A:** Secrets (tokens, keys) are still in environment variables (`.env`). But configuration structure is now in YAML only.

### Q: What about Docker?

**A:** Docker works the same way - mount both `config/app_config.yaml` and `.env` as volumes. See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md).

### Q: How do I add a new GitHub user?

**A:** 
1. Add user to `config/app_config.yaml`:
   ```yaml
   users:
     - username: "newuser"
       token_env: "GITHUB_EOS2GIT_TOKEN_NEWUSER"
       email: "newuser@example.com"
   ```
2. Add token to `.env`:
   ```env
   GITHUB_EOS2GIT_TOKEN_NEWUSER=ghp_new_token_here
   ```
3. Restart application

### Q: How do I add a new GitHub instance?

**A:**
1. Add instance to `config/app_config.yaml`:
   ```yaml
   github_instances:
     new_instance:
       name: "New Instance"
       api_url: "https://github.new.com/api/v3"
       org: "new-org"
       users:
         - username: "default_user"
           token_env: "GITHUB_NEW_TOKEN"
           email: ""
   ```
2. Add token to `.env`:
   ```env
   GITHUB_NEW_TOKEN=ghp_token_here
   ```
3. Restart application

---

## Benefits Summary

### Before (Dual Files)
- ❌ 40+ environment variables
- ❌ Configuration duplicated
- ❌ Secrets mixed with configuration
- ❌ JSON embedded in environment variables
- ❌ Confusing which file to edit
- ❌ Easy to get out of sync
- ❌ Hard to version control

### After (Single File)
- ✅ Clean YAML configuration
- ✅ Single source of truth
- ✅ Secrets separated
- ✅ Individual token environment variables
- ✅ Clear what goes where
- ✅ Easy to maintain
- ✅ Version control friendly

---

## Migration Checklist

- [ ] Run `python migrate_config.py --yes`
- [ ] Review `config/app_config.yaml`
- [ ] Review `.env` (secrets only)
- [ ] Run `python test_config.py`
- [ ] Run `python test_admin_config.py`
- [ ] Restart application
- [ ] Verify admin/config page shows all instances and users
- [ ] Test credential validation
- [ ] Keep backups until confirmed working

---

## Support

If you encounter issues:

1. **Check backups exist:**
   ```bash
   ls -la .env.backup.pre-migration
   ls -la config/app_config.yaml.backup.pre-migration
   ```

2. **Test configuration:**
   ```bash
   python test_config.py
   python test_admin_config.py
   ```

3. **Check logs:**
   ```bash
   python app.py  # Look for errors
   ```

4. **Rollback if needed:**
   ```bash
   mv .env.backup.pre-migration .env
   mv config/app_config.yaml.backup.pre-migration config/app_config.yaml
   ```

---

**Document Status**: Complete  
**Last Updated**: 2026-06-12  
**Migration Required**: Yes
