#!/usr/bin/env python3
"""
Quick script to scan fusion-stage repository with Jenkins checks
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from remote_scanner import RemoteRepositoryScanner

# Load environment variables
load_dotenv()

def main():
    print("Starting OSS Compliance Scan for fusion-stage with Jenkins checks...")
    print("=" * 60)
    
    # Use environment variables directly
    artifactory_base = os.getenv('ARTIFACTORY_BASE', 'isgedge.artifactory.cec.lab.emc.com')
    github_api_url = os.getenv('GITHUB_API_URL', 'https://eos2git.cec.lab.emc.com/api/v3')
    github_org = os.getenv('GITHUB_ORG', 'ISG-Edge')
    github_token = os.getenv('GITHUB_TOKEN')
    jenkins_user = os.getenv('JENKINS_USER')
    jenkins_token = os.getenv('JENKINS_API_TOKEN')
    jenkins_urls = [url.strip() for url in os.getenv('JENKINS_URLS', '').split(',') if url.strip()]
    whitelist_urls = [url.strip() for url in os.getenv('WHITELIST_URLS', '').split(',') if url.strip()]
    
    print(f"[OK] Configuration loaded from environment variables")
    print(f"  - Artifactory: {artifactory_base}")
    print(f"  - GitHub API: {github_api_url}")
    print(f"  - GitHub Org: {github_org}")
    print(f"  - Jenkins URLs: {len(jenkins_urls)}")
    print(f"  - Whitelist URLs: {len(whitelist_urls)}")
    
    # GitHub instance configuration
    github_instance_config = {
        'api_url': github_api_url,
        'token': github_token,
        'org': github_org
    }
    
    # Jenkins configuration
    jenkins_config_dict = {
        'user': jenkins_user,
        'token': jenkins_token,
        'urls': jenkins_urls
    }
    
    # Initialize scanner with Jenkins configuration
    print(f"\nInitializing RemoteRepositoryScanner with Jenkins checks...")
    scanner = RemoteRepositoryScanner(
        github_instance_config=github_instance_config,
        whitelist_urls=whitelist_urls,
        jenkins_config=jenkins_config_dict
    )
    
    # Scan fusion-stage repository
    repo_name = 'fusion-stage'
    print(f"\n{'='*60}")
    print(f"Scanning repository: {repo_name}")
    print(f"Organization: {scanner.github_org}")
    print(f"Jenkins checks: ENABLED ({len(scanner.jenkins_urls)} URLs configured)")
    print(f"{'='*60}\n")
    
    try:
        report = scanner.scan_remote_repository(repo_name)
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"fusion-stage_oss_{timestamp}.json"
        report_path = os.path.join('reports', report_filename)
        
        os.makedirs('reports', exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"[OK] Scan completed successfully!")
        print(f"{'='*60}")
        print(f"Report saved to: {report_path}")
        
        # Print summary
        if 'summary' in report:
            summary = report['summary']
            print(f"\nSummary:")
            print(f"  Total Items: {summary.get('total_items', 0)}")
            print(f"  Compliant: {summary.get('compliant_items', 0)}")
            print(f"  Non-Compliant: {summary.get('non_compliant_items', 0)}")
            print(f"  Compliance Rate: {summary.get('compliance_percentage', 0):.1f}%")
        
        # Print Jenkins information
        if 'scan_metadata' in report:
            metadata = report['scan_metadata']
            print(f"\nJenkins Integration:")
            print(f"  Jenkins Configs Found: {metadata.get('jenkins_configs_found', 0)}")
            print(f"  Repository Type: {metadata.get('repository_type', 'unknown')}")
        
        print(f"\n{'='*60}")
        
    except Exception as e:
        print(f"\n[ERROR] Error during scan: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
