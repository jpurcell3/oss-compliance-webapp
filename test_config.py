#!/usr/bin/env python3
"""Test configuration loading"""

from config_manager import get_config_manager

try:
    cm = get_config_manager()
    print('[OK] Config loaded successfully')
    
    instances = cm.get_github_instances()
    print(f'\n[OK] GitHub instances: {list(instances.keys())}')
    for id, inst in instances.items():
        print(f'  - {id}: {inst.name} - {len(inst.users)} users')
        for user in inst.users:
            print(f'    - {user.username} (has token: {bool(user.token)})')
    
    jenkins = cm.get_jenkins_config()
    print(f'\n[OK] Jenkins: {jenkins.user} - {len(jenkins.urls)} URLs (has token: {bool(jenkins.token)})')
    
    artifactory = cm.get_artifactory_config()
    print(f'\n[OK] Artifactory: {artifactory.base_url} (has token: {bool(artifactory.token)})')
    
    print('\n[OK] All configuration loaded successfully!')
    
except Exception as e:
    print(f'\n[ERROR] Error loading configuration: {e}')
    import traceback
    traceback.print_exc()
