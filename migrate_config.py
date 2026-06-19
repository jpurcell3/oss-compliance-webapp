#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script to convert .env configuration to YAML + secrets
Extracts tokens from GITHUB_INSTANCE_*_USERS JSON and creates individual env vars
"""

import os
import sys
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load current .env
load_dotenv()

print("="*60)
print("Configuration Migration Script")
print("="*60)

# Extract GitHub instances
github_instances_str = os.getenv('GITHUB_INSTANCES', '')
github_instances_list = [x.strip() for x in github_instances_str.split(',') if x.strip()]

print(f"\nFound {len(github_instances_list)} GitHub instance(s): {github_instances_list}")

# Build YAML configuration
yaml_config = {
    'version': '1.0',
    'artifactory': {
        'base_url': os.getenv('ARTIFACTORY_BASE', 'isgedge.artifactory.cec.lab.emc.com'),
        'virtual_repos': {}
    },
    'github_instances': {},
    'jenkins': {
        'user': os.getenv('JENKINS_USER', ''),
        'token_env': 'JENKINS_API_TOKEN',
        'urls': [],
        'pr_validation_job': 'oss-compliance-validation'
    },
    'whitelist_urls': [],
    'app_settings': {
        'max_scan_threads': 4,
        'cache_ttl_hours': 1,
        'report_retention_days': 90
    }
}

# Extract virtual repos
for key, value in os.environ.items():
    if key.startswith('VIRTUAL_REPO_'):
        repo_type = key.replace('VIRTUAL_REPO_', '').lower()
        yaml_config['artifactory']['virtual_repos'][repo_type] = value

# Extract whitelist URLs
whitelist_str = os.getenv('WHITELIST_URLS', '')
if whitelist_str:
    yaml_config['whitelist_urls'] = [url.strip() for url in whitelist_str.split(',') if url.strip()]

# Extract Jenkins URLs
jenkins_urls_str = os.getenv('JENKINS_URLS', '')
if jenkins_urls_str:
    yaml_config['jenkins']['urls'] = [url.strip() for url in jenkins_urls_str.split(',') if url.strip()]

# Extract GitHub instances and create token environment variables
new_env_vars = {}
token_counter = {}

for instance_id in github_instances_list:
    instance_name = os.getenv(f'GITHUB_INSTANCE_{instance_id}_NAME', instance_id)
    instance_org = os.getenv(f'GITHUB_INSTANCE_{instance_id}_ORG', '')
    instance_api_url = os.getenv(f'GITHUB_INSTANCE_{instance_id}_API_URL', '')
    
    # Get users from JSON
    users_json = os.getenv(f'GITHUB_INSTANCE_{instance_id}_USERS', '{}')
    try:
        users_dict = json.loads(users_json)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse users JSON for {instance_id}")
        users_dict = {}
    
    # Create YAML instance entry
    yaml_instance = {
        'name': instance_name,
        'api_url': instance_api_url,
        'org': instance_org,
        'users': []
    }
    
    # Extract tokens and create environment variable names
    for username, user_data in users_dict.items():
        token = user_data.get('token', '')
        email = user_data.get('email', '')
        
        # Create unique token environment variable name
        token_env_name = f'GITHUB_{instance_id.upper()}_TOKEN_{username.upper()}'
        
        yaml_instance['users'].append({
            'username': username,
            'token_env': token_env_name,
            'email': email
        })
        
        # Store token for new .env file
        if token:
            new_env_vars[token_env_name] = token
    
    yaml_config['github_instances'][instance_id] = yaml_instance

# Display migration plan
print("\n" + "="*60)
print("Migration Plan")
print("="*60)

print("\n1. YAML Configuration (config/app_config.yaml):")
print(f"   - Artifactory: {yaml_config['artifactory']['base_url']}")
print(f"   - Virtual Repos: {len(yaml_config['artifactory']['virtual_repos'])}")
print(f"   - GitHub Instances: {len(yaml_config['github_instances'])}")
for instance_id, instance in yaml_config['github_instances'].items():
    print(f"     - {instance_id}: {instance['name']} ({len(instance['users'])} users)")
print(f"   - Jenkins URLs: {len(yaml_config['jenkins']['urls'])}")
print(f"   - Whitelist URLs: {len(yaml_config['whitelist_urls'])}")

print("\n2. New .env file (secrets only):")
print("   Required keys:")
print("   - ENCRYPTION_KEY (generate new)")
print("   - SECRET_KEY (generate new)")
print("   - JENKINS_API_TOKEN")
print(f"   GitHub tokens ({len(new_env_vars)} total):")
for token_name in sorted(new_env_vars.keys()):
    print(f"   - {token_name}")

# Ask for confirmation
print("\n" + "="*60)

# Check for --yes flag
if '--yes' in sys.argv or '-y' in sys.argv:
    response = 'yes'
    print("Auto-confirming migration (--yes flag)")
else:
    try:
        response = input("Proceed with migration? (yes/no): ").strip().lower()
    except EOFError:
        print("\nNo input provided. Use --yes flag to auto-confirm.")
        response = 'no'

if response != 'yes':
    print("Migration cancelled.")
    exit(0)

# Backup existing files
print("\n" + "="*60)
print("Creating backups...")
print("="*60)

if Path('.env').exists():
    backup_path = Path('.env.backup.pre-migration')
    Path('.env').rename(backup_path)
    print(f"✓ Backed up .env to {backup_path}")

if Path('config/app_config.yaml').exists():
    backup_path = Path('config/app_config.yaml.backup.pre-migration')
    Path('config/app_config.yaml').rename(backup_path)
    print(f"✓ Backed up config/app_config.yaml to {backup_path}")

# Write new YAML configuration
print("\n" + "="*60)
print("Writing new configuration files...")
print("="*60)

with open('config/app_config.yaml', 'w') as f:
    yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
print("✓ Created config/app_config.yaml")

# Generate new encryption and secret keys
encryption_key = Fernet.generate_key().decode()
import secrets
secret_key = secrets.token_hex(32)

# Write new .env file with only secrets
with open('.env', 'w') as f:
    f.write("# OSS Compliance Web Application - Secrets Only\n")
    f.write("# Configuration is in config/app_config.yaml\n\n")
    
    f.write("# Flask Configuration\n")
    f.write(f"SECRET_KEY={secret_key}\n")
    f.write("FLASK_ENV=production\n\n")
    
    f.write("# Encryption Key\n")
    f.write(f"ENCRYPTION_KEY={encryption_key}\n\n")
    
    f.write("# GitHub Tokens\n")
    for token_name, token_value in sorted(new_env_vars.items()):
        f.write(f"{token_name}={token_value}\n")
    
    f.write("\n# Jenkins Token\n")
    jenkins_token = os.getenv('JENKINS_API_TOKEN', '')
    f.write(f"JENKINS_API_TOKEN={jenkins_token}\n")

print("✓ Created new .env file (secrets only)")

# Summary
print("\n" + "="*60)
print("Migration Complete!")
print("="*60)

print("\nWhat was done:")
print("1. ✓ Backed up old .env and config/app_config.yaml")
print("2. ✓ Created new config/app_config.yaml with all configuration")
print("3. ✓ Created new .env with only secrets (tokens and keys)")
print("4. ✓ Generated new ENCRYPTION_KEY and SECRET_KEY")
print(f"5. ✓ Extracted {len(new_env_vars)} GitHub tokens to individual env vars")

print("\nNext steps:")
print("1. Review config/app_config.yaml")
print("2. Review .env (secrets only)")
print("3. Test configuration: python test_config.py")
print("4. Restart application: python app.py")

print("\nRollback (if needed):")
print("  mv .env.backup.pre-migration .env")
print("  mv config/app_config.yaml.backup.pre-migration config/app_config.yaml")

print("\n" + "="*60)
