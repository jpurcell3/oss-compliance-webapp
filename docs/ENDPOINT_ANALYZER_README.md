# Enhanced Endpoint Analyzer

## Overview

The Enhanced Endpoint Analyzer extends the OSS Compliance Scanner with detailed enumeration and analysis of:

1. **All OSS components** in the repository (Go modules, Python packages, NPM packages, Maven dependencies, Docker images)
2. **Configured endpoints** for each component (where they're actually being fetched from)
3. **Proxy and translation mechanisms** (Artifactory proxies, URL rewriting, git config translations)
4. **Configuration locations** (Dockerfile, Makefile, Jenkinsfile, config files)
5. **Compliance mapping** between components and their endpoint configurations

## Key Features

### 1. Component Enumeration
- **Go modules**: Parses `go.mod` files to extract all dependencies with versions
- **Python packages**: Parses `requirements.txt` including direct GitHub URLs
- **NPM packages**: Parses `package.json` for all dependency types
- **Maven dependencies**: Parses `pom.xml` for groupId:artifactId pairs
- **Docker images**: Extracts FROM statements in Dockerfiles

### 2. Endpoint Discovery
Discovers endpoint configurations from multiple sources:
- **Dockerfile**: `GOPROXY`, `GOPRIVATE`, `PIP_INDEX_URL`, `NPM_CONFIG_REGISTRY`, git config URL rewriting
- **Makefile**: curl/wget commands with repository URLs
- **Jenkinsfile**: Environment variable configurations
- **Config files**: `.npmrc`, `.pypirc`, `pip.conf`
- **go.mod**: `replace` directives for module redirection

### 3. Endpoint Classification
Classifies each endpoint as:
- **DIRECT_PUBLIC**: Direct to public registry (github.com, npmjs.org, pypi.org)
- **DIRECT_PRIVATE**: Direct to internal/private registry (eos2git.cec.lab.emc.com)
- **PROXIED**: Through Artifactory or other proxy
- **TRANSLATED**: URL rewriting/translation configured (git config)
- **UNKNOWN**: Cannot determine type

### 4. Component-to-Endpoint Mapping
Maps each OSS component to:
- **Declared endpoint**: What's specified in the dependency file
- **Actual endpoint**: How it's actually resolved (considering proxy/translation)
- **Proxy chain**: Sequence of proxies/translations applied
- **Compliance status**: compliant, non_compliant, or warning
- **Recommendations**: Specific actions to achieve compliance

### 5. Critical Issue Detection
Automatically identifies critical issues:
- **GOPRIVATE misconfiguration**: github.com in GOPRIVATE bypasses proxy for public modules
- **Missing proxy configuration**: Dependencies without Artifactory proxy
- **High non-compliance rate**: >50% of components non-compliant
- **Direct public endpoints**: Components bypassing approved proxies

## Usage

### Standalone Execution

```bash
# Analyze a repository
python endpoint_analyzer.py /path/to/repo

# Comprehensive scan with enhanced reporting
python enhanced_scanner.py /path/to/repo output_report.json
```

### Integration with Web App

```python
from enhanced_scanner import EnhancedComplianceScanner

# Initialize scanner
scanner = EnhancedComplianceScanner(
    repo_root='/path/to/repo',
    artifactory_base='isgedge.artifactory.cec.lab.emc.com',
    virtual_repos={
        'go': 'isgedge-maven-virtual',
        'pypi': 'isgedge-pypi-virtual',
        'npm': 'isgedge-npm-virtual'
    }
)

# Run comprehensive scan
report = scanner.scan_comprehensive()

# Export report
scanner.export_report(report, 'compliance_report.json')

# Get summary text
summary = scanner.generate_summary_text(report)
print(summary)
```

## Report Structure

The comprehensive report includes:

```json
{
  "summary": {
    "repository_name": "repo-name",
    "scan_timestamp": "2026-05-20T11:46:00",
    "basic_compliance": { ... },
    "component_analysis": {
      "total_components": 172,
      "compliant_components": 6,
      "non_compliant_components": 166,
      "component_compliance_percentage": 3.49
    },
    "endpoint_summary": {
      "total_configurations": 8,
      "by_type": {
        "direct_public": 103,
        "direct_private": 6,
        "proxied": 0
      }
    }
  },
  "endpoint_configurations": [
    {
      "url": "github.com, eos2git.cec.lab.emc.com",
      "type": "direct_public",
      "location": "dockerfile",
      "file": "hzp-drift-svc/Dockerfile",
      "line": 18,
      "snippet": "ENV GOPRIVATE=\"github.com, eos2git.cec.lab.emc.com\"",
      "compliant": false,
      "notes": "GOPRIVATE bypasses proxy for github.com"
    }
  ],
  "component_mappings": [
    {
      "component": {
        "name": "github.com/google/uuid",
        "version": "v1.6.0",
        "ecosystem": "go",
        "source_file": "hzp-drift-svc/go.mod",
        "line_number": 19
      },
      "declared_endpoint": "github.com",
      "actual_endpoint": {
        "url": "github.com",
        "type": "direct_public",
        "location": "dockerfile",
        "compliant": false
      },
      "proxy_chain": [],
      "compliance_status": "non_compliant",
      "recommendations": [
        "Configure GOPROXY=https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/go/isgedge-maven-virtual,direct",
        "Remove 'github.com' from GOPRIVATE (only include eos2git.cec.lab.emc.com)"
      ]
    }
  ],
  "critical_issues": [
    {
      "severity": "CRITICAL",
      "issue": "GOPRIVATE includes github.com - bypassing proxy for public modules",
      "file": "hzp-drift-svc/Dockerfile",
      "line": 18,
      "recommendation": "Remove github.com from GOPRIVATE. Only include eos2git.cec.lab.emc.com",
      "impact": "All GitHub modules are bypassing Artifactory proxy"
    }
  ],
  "recommendations": [
    {
      "priority": "CRITICAL",
      "category": "Go Module Configuration",
      "issue": "GOPRIVATE includes github.com",
      "impact": "136 Go modules affected",
      "action": "Update Dockerfile GOPRIVATE configuration",
      "implementation": [
        "Remove 'github.com' from GOPRIVATE environment variable",
        "Keep only 'eos2git.cec.lab.emc.com' in GOPRIVATE",
        "Add GOPROXY=https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/go/isgedge-maven-virtual,direct"
      ]
    }
  ],
  "ecosystem_breakdown": {
    "go": {
      "total_components": 136,
      "compliant": 6,
      "non_compliant": 130,
      "compliance_rate": 4.41,
      "endpoint_types": {
        "direct_public": 103,
        "direct_private": 6
      }
    }
  },
  "proxy_analysis": {
    "total_components": 172,
    "proxied_components": 0,
    "direct_public_components": 166,
    "direct_private_components": 6,
    "proxy_effectiveness": 0.0,
    "proxy_configurations": [],
    "translation_rules": [
      {
        "rule": "Translates https://eos2git.cec.lab.emc.com -> https://GH_USER:GH_TOKEN@eos2git.cec.lab.emc.com",
        "file": "hzp-drift-svc/Dockerfile",
        "line": 17
      }
    ]
  }
}
```

## Key Insights from ISG-Edge Analysis

Based on the analysis of the ISG-Edge repository, we discovered:

### Critical Finding: GOPRIVATE Misconfiguration
```dockerfile
ENV GOPRIVATE="github.com, eos2git.cec.lab.emc.com"
```

**Problem**: Including `github.com` in GOPRIVATE tells Go to bypass the proxy for ALL github.com modules.

**Impact**: 
- 103+ public GitHub modules are fetched directly from github.com
- These modules SHOULD be proxied through Artifactory but are not
- Only the 6 `eos2git.cec.lab.emc.com` modules truly need to be in GOPRIVATE

**Solution**:
```dockerfile
ENV GOPRIVATE="eos2git.cec.lab.emc.com"
ENV GOPROXY="https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/go/isgedge-maven-virtual,direct"
```

This ensures:
- 6 internal modules → Direct from `eos2git.cec.lab.emc.com` (with auth)
- 166 public modules → Proxied through Artifactory (cached, compliant)

### Module Distribution in ISG-Edge

**hzp-drift-svc** (172 total dependencies):
- GOPRIVATE endpoints: 6 modules (3.5%)
- Public github.com: 103 modules (59.9%)
- Other public sources: 63 modules (36.6%)

**Current state**: ~96.5% of modules are public but bypassing the proxy due to misconfiguration.

## Integration with Existing Scanner

The `EnhancedComplianceScanner` combines:

1. **Basic compliance checks** (from `compliance_scanner.py`)
   - File-level configuration checks
   - Pattern matching for common issues
   - Basic recommendations

2. **Detailed endpoint analysis** (from `endpoint_analyzer.py`)
   - Component-level enumeration
   - Endpoint configuration discovery
   - Proxy/translation chain analysis
   - Per-component compliance mapping

3. **Comprehensive reporting**
   - Merged findings with deduplication
   - Enhanced recommendations with implementation steps
   - Critical issue identification
   - Ecosystem-specific breakdowns
   - Proxy effectiveness analysis

## Next Steps

To integrate with your web application:

1. **Update `app.py`** to use `EnhancedComplianceScanner` instead of `ComplianceScanner`
2. **Add new UI sections** to display:
   - Component-to-endpoint mappings
   - Endpoint configuration details
   - Proxy chain visualizations
   - Critical issues dashboard
3. **Add filtering/sorting** for component mappings by:
   - Ecosystem
   - Compliance status
   - Endpoint type
4. **Add export options** for:
   - Full JSON report
   - Summary text report
   - CSV export of component mappings

## Example Output

```
OSS COMPLIANCE SCAN REPORT
Repository: ISG-Edge
Scan Date: 2026-05-20T11:46:00

=== OVERALL COMPLIANCE ===
Total Components: 172
Compliant: 6 (3.49%)
Non-Compliant: 166
Warnings: 0

=== ENDPOINT ANALYSIS ===
Total Endpoint Configurations: 8
Proxied Components: 0
Direct Public: 166
Direct Private: 6
Proxy Effectiveness: 0.0%

=== CRITICAL ISSUES ===

[CRITICAL] GOPRIVATE Misconfiguration
  github.com in GOPRIVATE bypasses Artifactory for all public Go modules
  Recommendation: Remove github.com from GOPRIVATE immediately

[HIGH] High Non-Compliance Rate
  96.5% of components are non-compliant
  Recommendation: Immediate action required to configure package manager proxies

=== TOP RECOMMENDATIONS ===

1. [CRITICAL] Go Module Configuration
   Issue: GOPRIVATE includes github.com - bypassing proxy for public modules
   Action: Update Dockerfile GOPRIVATE configuration
   Implementation:
   - Remove "github.com" from GOPRIVATE environment variable
   - Keep only "eos2git.cec.lab.emc.com" in GOPRIVATE
   - Add GOPROXY=https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/go/isgedge-maven-virtual,direct
   - This will proxy public GitHub modules through Artifactory while keeping internal modules direct
```

## Benefits

1. **Accurate compliance measurement**: Per-component tracking instead of file-level
2. **Root cause identification**: Pinpoints exact configuration issues
3. **Actionable recommendations**: Specific steps to fix each issue
4. **Comprehensive visibility**: Full chain from component to endpoint
5. **Automated detection**: Identifies misconfigurations like GOPRIVATE issue
