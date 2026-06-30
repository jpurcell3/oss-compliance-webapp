#!/usr/bin/env python3
"""
Scan fusion-stage repository to analyze component counts and compliance details
"""

import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import get_config_manager
from remote_scanner import RemoteRepositoryScanner

def main():
    print("=" * 80)
    print("SCANNING FUSION-STAGE REPOSITORY FOR COMPONENT ANALYSIS")
    print("=" * 80)
    
    # Load configuration
    config_manager = get_config_manager()
    
    # Get eos2git instance configuration
    eos2git_instance = config_manager.get_github_instance('eos2git')
    if not eos2git_instance:
        print("ERROR: eos2git instance not found in configuration")
        return
    
    # Get default user (auto-decrypted token)
    user = eos2git_instance.get_default_user()
    if not user:
        print("ERROR: No users configured for eos2git instance")
        return
    
    print(f"GitHub Instance: {eos2git_instance.name}")
    print(f"API URL: {eos2git_instance.api_url}")
    print(f"Organization: {eos2git_instance.org}")
    print(f"User: {user.username}")
    print(f"Token (first 10 chars): {user.token[:10]}...")
    print()
    
    # Initialize scanner with instance configuration
    scanner_config = {
        'api_url': eos2git_instance.api_url,
        'token': user.token,
        'org': eos2git_instance.org
    }
    
    # Get Jenkins configuration
    jenkins_config = config_manager.get_jenkins_config()
    
    # Get Artifactory configuration  
    artifactory_config = config_manager.get_artifactory_config()
    
    # Get whitelist URLs
    whitelist_urls = config_manager.get_whitelist_urls()
    
    print(f"Artifactory Base: {artifactory_config.base_url}")
    print(f"Virtual Repos: {artifactory_config.virtual_repos}")
    print(f"Whitelist URLs: {whitelist_urls}")
    print()
    
    # Initialize scanner
    scanner = RemoteRepositoryScanner(
        github_instance_config=scanner_config,
        whitelist_urls=whitelist_urls,
        jenkins_config={
            'user': jenkins_config.user,
            'token': jenkins_config.token,
            'urls': jenkins_config.urls
        }
    )
    
    # Override artifactory config with values from config_manager
    scanner.artifactory_base = artifactory_config.base_url
    scanner.virtual_repos = artifactory_config.virtual_repos
    
    # Scan the fusion-stage repository
    repo_name = 'fusion-stage'
    print(f"Starting comprehensive scan for: {repo_name}")
    print("=" * 80)
    
    try:
        report = scanner.scan_remote_repository(repo_name)
        
        print("\n" + "=" * 80)
        print("SCAN RESULTS SUMMARY")
        print("=" * 80)
        
        # Print basic summary
        if 'summary' in report:
            summary = report['summary']
            print(f"Repository: {summary.get('repository_name', 'N/A')}")
            print(f"Scan Timestamp: {summary.get('scan_timestamp', 'N/A')}")
            
            if 'component_analysis' in summary:
                comp_analysis = summary['component_analysis']
                print(f"\nComponent Analysis:")
                print(f"  Total Components: {comp_analysis.get('total_components', 0)}")
                print(f"  Compliant Components: {comp_analysis.get('compliant_components', 0)}")
                print(f"  Non-Compliant Components: {comp_analysis.get('non_compliant_components', 0)}")
                print(f"  Compliance Percentage: {comp_analysis.get('component_compliance_percentage', 0)}%")
            
            if 'basic_compliance' in summary:
                basic = summary['basic_compliance']
                print(f"\nBasic Compliance:")
                print(f"  Total Items: {basic.get('total_items', 0)}")
                print(f"  Compliant Items: {basic.get('compliant_items', 0)}")
                print(f"  Non-Compliant Items: {basic.get('non_compliant_items', 0)}")
                print(f"  Compliance Percentage: {basic.get('compliance_percentage', 0)}%")
        
        # Print findings details
        print(f"\n" + "=" * 80)
        print("DETAILED FINDINGS")
        print("=" * 80)
        
        findings = report.get('findings', [])
        print(f"Total Findings: {len(findings)}")
        
        # Group findings by type
        findings_by_type = {}
        for finding in findings:
            ftype = finding.get('type', 'unknown')
            if ftype not in findings_by_type:
                findings_by_type[ftype] = []
            findings_by_type[ftype].append(finding)
        
        print(f"\nFindings by Type:")
        for ftype, type_findings in findings_by_type.items():
            print(f"  {ftype}: {len(type_findings)}")
        
        # Print detailed findings
        print(f"\nDetailed Findings:")
        for i, finding in enumerate(findings, 1):
            print(f"\n{i}. {finding.get('type', 'unknown')}")
            print(f"   File: {finding.get('file', 'N/A')}")
            print(f"   Issue: {finding.get('issue', 'N/A')}")
            print(f"   Severity: {finding.get('severity', 'N/A')}")
            print(f"   Compliant: {finding.get('compliant', False)}")
            if 'recommended_action' in finding:
                print(f"   Recommended Action: {finding['recommended_action']}")
        
        # Print scan metadata
        print(f"\n" + "=" * 80)
        print("SCAN METADATA")
        print("=" * 80)
        
        metadata = report.get('scan_metadata', {})
        for key, value in metadata.items():
            print(f"{key}: {value}")
        
        # Save full report to JSON file for detailed analysis
        output_file = Path('fusion_stage_scan_report.json')
        import json
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nFull report saved to: {output_file}")
        
    except Exception as e:
        print(f"ERROR during scan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()