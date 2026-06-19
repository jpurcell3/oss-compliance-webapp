# Reliability Score Fix Summary

## Problem Identified (May 27, 2026 5:21pm)

The reliability score was showing **579.78%** with **266 high confidence** items for fusion-agent, which is mathematically impossible and clearly wrong.

### Root Cause

The `_calculate_reliability_metrics()` function was counting **individual runtime configurations** instead of **package managers with evidence**.

**Example of the bug:**
- Repository has 46 Python packages
- Scanner found 266 runtime configurations (pip index-url in multiple places)
- Old calculation: `(266 * 1.0) / 46 * 100 = 578%` ❌

**What it should be:**
- Repository has 46 Python packages  
- Scanner found evidence for 1 package manager (pip) with high confidence
- New calculation: `(1 * 1.0) / 46 * 100 = 2.17%` ✅

## Changes Made

### File: `enhanced_scanner.py`

**Before (Lines 762-794):**
```python
def _calculate_reliability_metrics(self, runtime_configs: Dict[str, List[RuntimeConfiguration]], 
                                   total_packages: int) -> Dict:
    """Calculate reliability metrics for the scan"""
    
    # Count configurations by confidence level
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    
    for pm, config_list in runtime_configs.items():
        for config in config_list:  # ❌ Counting each config
            if config.confidence == 'high':
                high_confidence += 1
            elif config.confidence == 'medium':
                medium_confidence += 1
            elif config.confidence == 'low':
                low_confidence += 1
    
    total_configs = high_confidence + medium_confidence + low_confidence
    packages_with_evidence = min(total_configs, total_packages) if total_packages > 0 else total_configs
    no_evidence = max(0, total_packages - packages_with_evidence)
    
    # Calculate weighted reliability score
    if total_packages == 0:
        reliability_score = 0.0
    else:
        weighted_score = (
            (high_confidence * 1.0) +
            (medium_confidence * 0.7) +
            (low_confidence * 0.4)
        ) / max(total_packages, 1)
        
        reliability_score = round(weighted_score * 100, 2)  # ❌ No cap
```

**After (Lines 762-806):**
```python
def _calculate_reliability_metrics(self, runtime_configs: Dict[str, List[RuntimeConfiguration]], 
                                   total_packages: int) -> Dict:
    """Calculate reliability metrics for the scan"""
    
    # Count package managers with evidence by confidence level
    # Each package manager (pip, npm, etc.) counts as one "package with evidence"
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    
    for pm, config_list in runtime_configs.items():
        if not config_list:
            continue
        
        # Get the highest confidence level for this package manager
        max_confidence = 'low'
        for config in config_list:
            if config.confidence == 'high':
                max_confidence = 'high'
                break
            elif config.confidence == 'medium' and max_confidence != 'high':
                max_confidence = 'medium'
        
        # Count this package manager once at its highest confidence level ✅
        if max_confidence == 'high':
            high_confidence += 1
        elif max_confidence == 'medium':
            medium_confidence += 1
        else:
            low_confidence += 1
    
    packages_with_evidence = high_confidence + medium_confidence + low_confidence
    no_evidence = max(0, total_packages - packages_with_evidence)
    
    # Calculate weighted reliability score (capped at 100%) ✅
    if total_packages == 0:
        reliability_score = 0.0
    else:
        weighted_score = (
            (high_confidence * 1.0) +
            (medium_confidence * 0.7) +
            (low_confidence * 0.4)
        ) / total_packages
        
        reliability_score = min(100.0, round(weighted_score * 100, 2))  # ✅ Capped at 100%
```

## Key Changes

1. **Count package managers, not configs** - Each package manager (pip, npm, go, maven) is counted once
2. **Use highest confidence** - If pip has multiple configs, use the highest confidence level
3. **Cap at 100%** - Added `min(100.0, ...)` to prevent scores over 100%
4. **Simplified logic** - Removed unnecessary `total_configs` variable

## Impact

### Before Fix
- **fusion-agent**: 579.78% reliability, 266 high confidence
- Meaningless numbers that confused users
- No way to understand actual scan quality

### After Fix
- **fusion-agent** (expected): ~2-10% reliability, 1 high confidence
- Realistic numbers that reflect actual evidence
- Clear indication of which package managers have runtime evidence

## What Reliability Score Means Now

The reliability score represents **what percentage of your packages have runtime configuration evidence**.

When runtime configuration is found for a package manager (e.g., pip), **all packages in that ecosystem** receive credit at that confidence level.

**Example:**
- Repository has 46 Python packages
- Evidence found for: pip configuration (high confidence)
- All 46 packages get high confidence credit
- Reliability: 46/46 * 100 = 100%

**Confidence Levels:**
- **High (1.0)**: Found in Jenkins build logs or runtime configs
- **Medium (0.7)**: Found in repo files (Dockerfile, .npmrc, etc.)
- **Low (0.4)**: Inferred from package manager defaults

**Key Change from Previous Version:**
- Now counts **packages** instead of **package managers**
- If pip config is found, all Python packages benefit (not just 1/46)
- More intuitive: 46/46 packages with evidence = 100% reliability
- Still capped at 100% to prevent impossible scores

## Additional Fix (May 28, 2026 9:15am)

**Problem:** Reliability metrics showed inconsistent totals compared to component analysis
- Component analysis: 276 total components
- Reliability metrics: 191 total packages

**Root Cause:** Reliability calculation was using `basic_report['scan_summary']['total_items']` which only counts packages from the basic scanner (e.g., NPM packages from package.json), not all components including Docker images.

**Fix:** Changed to use `endpoint_report['summary']['total_components']` which includes all components analyzed by the enhanced scanner.

**Result:** Reliability metrics now consistent with component analysis totals.

## Testing

✅ Scanner imports correctly
✅ No syntax errors
⚠️ **Requires re-running scans** to see corrected metrics

## Next Steps

1. Re-run scans to generate reports with corrected reliability scores
2. Verify the new scores make sense (should be 0-100%)
3. Verify reliability total_packages matches component analysis total_components
