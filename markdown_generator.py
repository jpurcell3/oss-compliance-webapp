#!/usr/bin/env python3
"""
Markdown Summary Generator for Enhanced OSS Compliance Reports
Generates executive summary reports similar to command-line output
"""

from typing import Dict
from pathlib import Path


def generate_markdown_summary(report: Dict, output_path: str = None) -> str:
    """Generate a markdown summary report similar to command-line output"""
    md_lines = []
    
    # Header
    md_lines.append("# OSS Compliance Analysis - Enhanced Report")
    md_lines.append("")
    repo_name = report.get('summary', {}).get('repository_name', 'Unknown')
    md_lines.append(f"**Repository:** {repo_name}")
    md_lines.append(f"**Scan Date:** {report.get('summary', {}).get('scan_timestamp', 'N/A')}")
    md_lines.append("")
    
    # Executive Summary
    md_lines.append("## Executive Summary")
    md_lines.append("")
    
    comp_analysis = report.get('summary', {}).get('component_analysis', {})
    total_comp = comp_analysis.get('total_components', 0)
    compliant_comp = comp_analysis.get('compliant_components', 0)
    non_compliant_comp = comp_analysis.get('non_compliant_components', 0)
    compliance_pct = comp_analysis.get('component_compliance_percentage', 0)
    
    md_lines.append(f"- **Total Components:** {total_comp}")
    md_lines.append(f"- **Compliant:** {compliant_comp} ({compliance_pct}%)")
    md_lines.append(f"- **Non-Compliant:** {non_compliant_comp} ({100-compliance_pct:.1f}%)")
    md_lines.append("")
    
    # Ecosystem Breakdown
    md_lines.append("## Component Breakdown by Ecosystem")
    md_lines.append("")
    
    ecosystem_breakdown = report.get('ecosystem_breakdown', {})
    for ecosystem, data in sorted(ecosystem_breakdown.items()):
        total = data.get('total_components', 0)
        compliant = data.get('compliant', 0)
        non_compliant = data.get('non_compliant', 0)
        rate = data.get('compliance_rate', 0)
        
        md_lines.append(f"### {ecosystem.upper()} ({total} components)")
        md_lines.append("")
        
        # Endpoint type breakdown
        endpoint_types = data.get('endpoint_types', {})
        if endpoint_types:
            for etype, count in sorted(endpoint_types.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total * 100) if total > 0 else 0
                md_lines.append(f"- **{etype.replace('_', ' ').title()}:** {count} modules ({pct:.1f}%)")
        
        md_lines.append(f"- **Compliant:** {compliant} ({rate}%)")
        md_lines.append(f"- **Non-Compliant:** {non_compliant} ({100-rate:.1f}%)")
        md_lines.append("")
    
    # Critical Issues
    critical_issues = report.get('critical_issues', [])
    if critical_issues:
        md_lines.append("## ⚠️ Critical Configuration Issues")
        md_lines.append("")
        
        for idx, issue in enumerate(critical_issues, 1):
            md_lines.append(f"### {idx}. {issue.get('issue', 'Unknown Issue')}")
            md_lines.append("")
            md_lines.append(f"**Severity:** {issue.get('severity', 'UNKNOWN')}")
            md_lines.append("")
            md_lines.append(f"**Description:** {issue.get('description', 'N/A')}")
            md_lines.append("")
            
            if 'impact' in issue:
                md_lines.append(f"**Impact:** {issue['impact']}")
                md_lines.append("")
            
            if 'recommendation' in issue:
                md_lines.append(f"**Recommendation:** {issue['recommendation']}")
                md_lines.append("")
    
    # Recommendations
    recommendations = report.get('recommendations', [])
    if recommendations:
        md_lines.append("## Recommended Actions")
        md_lines.append("")
        
        for idx, rec in enumerate(recommendations, 1):
            priority = rec.get('priority', 'UNKNOWN')
            category = rec.get('category', 'General')
            
            md_lines.append(f"### {idx}. [{priority}] {category}")
            md_lines.append("")
            md_lines.append(f"**Issue:** {rec.get('issue', 'N/A')}")
            md_lines.append("")
            
            if rec.get('current_config'):
                md_lines.append(f"**Current Configuration:**")
                md_lines.append(f"```")
                md_lines.append(rec['current_config'])
                md_lines.append(f"```")
                md_lines.append("")
            
            if rec.get('desired_config'):
                md_lines.append(f"**Desired Configuration:**")
                md_lines.append(f"```")
                md_lines.append(rec['desired_config'])
                md_lines.append(f"```")
                md_lines.append("")
            
            md_lines.append(f"**Impact:** {rec.get('impact', 'N/A')}")
            md_lines.append("")
            md_lines.append(f"**Action:** {rec.get('action', 'N/A')}")
            md_lines.append("")
            
            implementation = rec.get('implementation', [])
            if implementation:
                md_lines.append("**Implementation Steps:**")
                md_lines.append("")
                for step_num, step in enumerate(implementation, 1):
                    md_lines.append(f"{step_num}. {step}")
                md_lines.append("")
            
            if rec.get('estimated_impact'):
                md_lines.append(f"**Estimated Impact:** {rec['estimated_impact']}")
                md_lines.append("")
        
        # Current Proxy Configurations
        current_proxy_configs = report.get('current_proxy_configurations', {})
        if current_proxy_configs:
            md_lines.append("## Current Proxy Configurations")
            md_lines.append("")
            
            for ecosystem, config in sorted(current_proxy_configs.items()):
                if any(config.values()):  # Only show if there's actual configuration
                    md_lines.append(f"### {ecosystem.upper()}")
                    md_lines.append("")
                    for key, value in config.items():
                        if value:
                            md_lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
                    md_lines.append("")
    
    # Proxy Analysis Summary
    proxy_analysis = report.get('proxy_analysis', {})
    if proxy_analysis:
        md_lines.append("## Proxy Configuration Analysis")
        md_lines.append("")
        
        total = proxy_analysis.get('total_components', 0)
        proxied = proxy_analysis.get('proxied_components', 0)
        direct_public = proxy_analysis.get('direct_public_components', 0)
        direct_private = proxy_analysis.get('direct_private_components', 0)
        
        md_lines.append(f"- **Total Components:** {total}")
        md_lines.append(f"- **Proxied through Artifactory:** {proxied} ({proxied/total*100 if total > 0 else 0:.1f}%)")
        md_lines.append(f"- **Direct Public:** {direct_public} ({direct_public/total*100 if total > 0 else 0:.1f}%)")
        md_lines.append(f"- **Direct Private:** {direct_private} ({direct_private/total*100 if total > 0 else 0:.1f}%)")
        md_lines.append("")
        
        if direct_public > 0:
            md_lines.append(f"⚠️ **{direct_public} components are accessing public repositories directly** instead of through Artifactory proxy.")
            md_lines.append("")
    
    # Generate markdown content
    markdown_content = "\n".join(md_lines)
    
    # Save to file if path provided
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Markdown summary saved to: {output_path}")
    
    return markdown_content


if __name__ == '__main__':
    import json
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python markdown_generator.py <report.json> [output.md]")
        sys.exit(1)
    
    report_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else report_file.replace('.json', '_summary.md')
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    markdown = generate_markdown_summary(report, output_file)
    print("\nMarkdown Summary:")
    print("=" * 80)
    print(markdown)
    print("=" * 80)
