# Three-Tier Compliance Model (PLANNED FEATURE)

> **Status:** This feature is planned but not yet implemented. The infrastructure exists in `config_enumerator.py` but is not currently integrated into the enhanced scanner to avoid breaking existing functionality.

## Overview

The enhanced scanner will implement a **three-tier compliance evaluation model** that distinguishes between:

1. **Compliant + Optimal** - Using approved Artifactory server AND designated virtual repositories
2. **Compliant + Suboptimal** - Using any Artifactory server but NOT the designated virtual repositories
3. **Non-Compliant** - Using public/external sources (e.g., pypi.org, npmjs.com)

## Why This Matters

### The Problem
Previously, the scanner only reported **binary compliance**:
- ✅ Compliant (using any Artifactory)
- ❌ Non-Compliant (using public sources)

This meant that a repository using `hopjpd.artifactory.cec.lab.emc.com` (wrong server) or direct repository URLs instead of virtual repos would show as **100% compliant**, even though it wasn't following the designated standards.

### The Solution
The three-tier model now provides **optimization recommendations** for compliant repositories that could be improved:

- **Compliance Status**: Are you using Artifactory? (Yes/No)
- **Optimization Level**: Are you using the BEST configuration? (Optimal/Suboptimal)

## How It Works

### 1. Component Evaluation

Each component is evaluated against the three-tier model:

```json
{
  "component": {
    "name": "requests",
    "version": "2.31.0",
    "ecosystem": "python"
  },
  "actual_endpoint": {
    "url": "https://hopjpd.artifactory.cec.lab.emc.com/artifactory/pypi-remote/simple",
    "type": "runtime_proxied"
  },
  "compliance_status": "compliant",
  "optimization_level": "compliant_warn",
  "optimization_notes": [
    "Using hopjpd.artifactory.cec.lab.emc.com instead of approved isgedge.artifactory.cec.lab.emc.com",
    "Using direct repository 'pypi-remote' instead of virtual repository 'isgedge-pypi-virtual'"
  ],
  "recommended_config": {
    "url": "https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/pypi/isgedge-pypi-virtual/simple",
    "description": "Use the designated ISG Edge virtual repository for Python packages"
  }
}
```

### 2. Optimization Opportunities Summary

The report includes an `optimization_opportunities` section that summarizes suboptimal configurations:

```json
{
  "optimization_opportunities": {
    "total_suboptimal": 48,
    "by_ecosystem": {
      "python": {
        "optimal_count": 0,
        "suboptimal_count": 48,
        "issues": [
          {
            "description": "Using hopjpd.artifactory.cec.lab.emc.com instead of approved isgedge.artifactory.cec.lab.emc.com",
            "current_config": "https://hopjpd.artifactory.cec.lab.emc.com/artifactory/pypi-remote/simple",
            "recommended_config": "https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/pypi/isgedge-pypi-virtual/simple",
            "affected_components": 48
          }
        ]
      }
    }
  }
}
```

### 3. UI Display

The results page now shows:

1. **Compliance Summary** - Overall compliance percentage (binary: compliant vs non-compliant)
2. **Optimization Opportunities** - Collapsible section showing suboptimal configurations
   - Only appears when `total_suboptimal > 0`
   - Collapsed by default to avoid clutter
   - Clearly marked as "compliant but could be optimized"

## Evaluation Rules

### Compliant + Optimal (`compliant_optimal`)

**Criteria:**
- ✅ Using approved Artifactory server (`isgedge.artifactory.cec.lab.emc.com`)
- ✅ Using designated virtual repository (e.g., `isgedge-pypi-virtual`, `isgedge-go-virtual`)

**Example:**
```
https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/pypi/isgedge-pypi-virtual/simple
```

**Result:** No optimization recommendations

### Compliant + Suboptimal (`compliant_warn`)

**Criteria:**
- ✅ Using any Artifactory server (e.g., `hopjpd`, `isgedge`, `*.artifactory.cec.lab.emc.com`)
- ❌ BUT not using the designated virtual repository

**Common Issues:**
1. **Wrong Artifactory Server**
   ```
   Current:  https://hopjpd.artifactory.cec.lab.emc.com/...
   Optimal:  https://isgedge.artifactory.cec.lab.emc.com/...
   ```

2. **Direct Repository Instead of Virtual**
   ```
   Current:  .../artifactory/pypi-remote/simple
   Optimal:  .../artifactory/api/pypi/isgedge-pypi-virtual/simple
   ```

3. **Generic Virtual Repo Instead of Team-Specific**
   ```
   Current:  .../artifactory/api/pypi/pypi-virtual/simple
   Optimal:  .../artifactory/api/pypi/isgedge-pypi-virtual/simple
   ```

**Result:** Optimization recommendations provided

### Non-Compliant (`non_compliant`)

**Criteria:**
- ❌ Using public/external sources (e.g., `pypi.org`, `npmjs.com`, `proxy.golang.org`)

**Example:**
```
https://pypi.org/simple
```

**Result:** Critical compliance issues reported

## Benefits

### For Teams
1. **Clear Compliance Status** - Know if you're meeting minimum requirements
2. **Optimization Guidance** - Understand how to improve your configuration
3. **Standardization** - Move towards consistent use of designated virtual repos

### For Management
1. **Compliance Metrics** - Track how many repos are compliant
2. **Optimization Metrics** - Track how many repos are using optimal configurations
3. **Risk Assessment** - Identify repos that need attention

### For Security
1. **Approved Sources** - Ensure all dependencies come from approved Artifactory servers
2. **Virtual Repo Benefits** - Leverage caching, scanning, and access control
3. **Audit Trail** - Track which repos are using which configurations

## Configuration

The three-tier model uses the existing configuration:

### Approved Artifactory Servers
```python
APPROVED_ARTIFACTORY_SERVERS = [
    'isgedge.artifactory.cec.lab.emc.com'
]
```

### Designated Virtual Repositories
```python
DEFAULT_VIRTUAL_REPOS = {
    'python': 'isgedge-pypi-virtual',
    'go': 'isgedge-go-virtual',
    'maven': 'isgedge-maven-virtual',
    'npm': 'isgedge-npm-virtual',
    'docker': 'isgedge-docker-virtual'
}
```

## Example Scenarios

### Scenario 1: Optimal Configuration ✅
```
Repository: my-python-app
Endpoint: https://isgedge.artifactory.cec.lab.emc.com/artifactory/api/pypi/isgedge-pypi-virtual/simple
Result: Compliant + Optimal (no recommendations)
```

### Scenario 2: Wrong Server ⚠️
```
Repository: legacy-app
Endpoint: https://hopjpd.artifactory.cec.lab.emc.com/artifactory/api/pypi/isgedge-pypi-virtual/simple
Result: Compliant + Suboptimal
Recommendation: Switch to isgedge.artifactory.cec.lab.emc.com
```

### Scenario 3: Direct Repository ⚠️
```
Repository: old-service
Endpoint: https://isgedge.artifactory.cec.lab.emc.com/artifactory/pypi-remote/simple
Result: Compliant + Suboptimal
Recommendation: Use virtual repo isgedge-pypi-virtual instead of direct pypi-remote
```

### Scenario 4: Public Source ❌
```
Repository: non-compliant-app
Endpoint: https://pypi.org/simple
Result: Non-Compliant
Recommendation: Configure PIP_INDEX_URL to use isgedge-pypi-virtual
```

## Migration Path

For repositories showing as "Compliant + Suboptimal":

1. **Review Optimization Opportunities** - Check the report for specific recommendations
2. **Update Configuration** - Change to the recommended virtual repository URL
3. **Test** - Verify builds still work with the new configuration
4. **Rescan** - Run the scanner again to confirm optimal status

## Summary

The three-tier compliance model provides:
- ✅ **Clear compliance status** - Are you using Artifactory?
- ✅ **Optimization guidance** - Are you using the BEST configuration?
- ✅ **Actionable recommendations** - How to improve your setup
- ✅ **Non-intrusive UI** - Optimization section is collapsible and only shown when relevant

This allows teams to achieve compliance first, then optimize their configurations over time without being overwhelmed by recommendations.
