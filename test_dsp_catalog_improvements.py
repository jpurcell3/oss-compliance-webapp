#!/usr/bin/env python3
"""
Test dsp-catalog-svc with improved Jenkins discovery and alternative evidence sources
"""
import requests
import json
import time

def test_improvements():
    """Test dsp-catalog-svc scan with improvements"""
    print("=" * 80)
    print("Testing dsp-catalog-svc with Improved Evidence Collection")
    print("=" * 80)
    
    time.sleep(3)
    
    url = "http://localhost:5001/scan/remote"
    data = {
        'repo_names': 'dsp-catalog-svc',
        'github_instance': 'eos2git',
        'use_enhanced': 'true'
    }
    
    print(f"\nTriggering scan...")
    response = requests.post(url, data=data, timeout=600)
    
    if response.status_code == 200:
        result = response.json()
        
        if result.get('success'):
            report = result.get('report', {})
            
            # Check runtime configurations
            runtime_configs = report.get('runtime_configurations', {})
            print(f"\n{'='*80}")
            print("RUNTIME CONFIGURATIONS FOUND")
            print(f"{'='*80}")
            
            total_configs = 0
            for pm, configs in runtime_configs.items():
                if configs:
                    print(f"\n{pm.upper()}: {len(configs)} configurations")
                    total_configs += len(configs)
                    for i, config in enumerate(configs[:3], 1):
                        print(f"  {i}. {config.get('config_value', 'N/A')}")
                        print(f"     Source: {config.get('source_type', 'N/A')} - {config.get('source_location', 'N/A')}")
            
            if total_configs == 0:
                print("\nNo runtime configurations found")
            
            # Check component analysis
            summary = report.get('summary', {})
            comp_analysis = summary.get('component_analysis', {})
            
            print(f"\n{'='*80}")
            print("COMPONENT ANALYSIS")
            print(f"{'='*80}")
            print(f"Total: {comp_analysis.get('total_components')}")
            print(f"Compliant: {comp_analysis.get('compliant_components')} ({comp_analysis.get('component_compliance_percentage')}%)")
            print(f"Unconfirmed: {comp_analysis.get('warning_components')}")
            print(f"Non-compliant: {comp_analysis.get('non_compliant_components')}")
            
            # Check findings with evidence
            findings = report.get('findings', [])
            findings_with_evidence = [f for f in findings if f.get('runtime_evidence')]
            
            print(f"\n{'='*80}")
            print("FINDINGS WITH RUNTIME EVIDENCE")
            print(f"{'='*80}")
            print(f"Total findings: {len(findings)}")
            print(f"Findings with runtime evidence: {len(findings_with_evidence)}")
            
            # Save report
            with open('dsp_catalog_svc_improved.json', 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nFull report saved to: dsp_catalog_svc_improved.json")
            
            # Compare with previous results
            print(f"\n{'='*80}")
            print("COMPARISON WITH PREVIOUS SCAN")
            print(f"{'='*80}")
            print(f"Previous: 0 runtime configurations, 3.28% compliant")
            print(f"Current:  {total_configs} runtime configurations, {comp_analysis.get('component_compliance_percentage')}% compliant")
            
            if total_configs > 0:
                print(f"\n✅ IMPROVEMENT: Found {total_configs} runtime configurations!")
            else:
                print(f"\n⚠️  Still no runtime configurations found")
                print(f"   Check if:")
                print(f"   1. Dockerfile/Makefile have GOPROXY or PIP_INDEX_URL")
                print(f"   2. GitHub Actions workflows exist")
                print(f"   3. Jenkins jobs exist (try manual mapping)")
            
        else:
            print(f"Scan failed: {result}")
    else:
        print(f"HTTP Error {response.status_code}: {response.text}")

if __name__ == '__main__':
    test_improvements()
