# SWE-1.6 Fix: Repository List and Group Listing Restoration

## Issue Description
After implementing the back button state fix in SWE-1.6, the repository list and group (team) listing were no longer displaying on the home page of the UI.

## Root Cause
The issue was caused by two JavaScript problems:

### 1. Broken Script Tag Structure
- There was a duplicate `<script>` tag opening without properly closing the previous one
- This caused the JavaScript parser to fail and prevented the repository loading functions from executing

### 2. Variable Scope Issue
- The `repoNamesInput` variable was declared inside the `DOMContentLoaded` event listener
- The `displayRepositories()` function (which uses `repoNamesInput`) was defined outside this scope
- This caused a `ReferenceError` when trying to update the hidden input field with selected repository names

## Fixes Applied

### Fix 1: Corrected Script Tag Structure
**File**: `templates/index.html`

**Before**:
```javascript
        teamReposDiv.classList.remove('hidden');
    }
<script>
    // Reset scan state on page load
    document.addEventListener('DOMContentLoaded', function() {
        // ...
    });
</script>
```

**After**:
```javascript
        teamReposDiv.classList.remove('hidden');
    }

    // Reset scan state on page load (moved into main DOMContentLoaded handler above)
    // This ensures the page loads in a clean state when using back button
</script>
```

### Fix 2: Fixed Variable Scope
**File**: `templates/index.html`

**Before**:
```javascript
<script>
    // Global cache for repositories
    let cachedRepositories = [];
    let currentGithubInstance = '';

    // ... later in DOMContentLoaded
    const repoNamesInput = document.getElementById('repo_names');
```

**After**:
```javascript
<script>
    // Global cache for repositories
    let cachedRepositories = [];
    let currentGithubInstance = '';
    let repoNamesInput; // Global reference to repo names input

    // ... later in DOMContentLoaded
    repoNamesInput = document.getElementById('repo_names'); // Assign to global variable
```

### Fix 3: Consolidated DOMContentLoaded Handler
Moved the scan state reset logic into the existing `DOMContentLoaded` handler to avoid duplicate event listeners:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Reset scan state on page load (prevents issues with back button)
    const scanStatus = document.getElementById('scan-status');
    if (scanStatus) {
        scanStatus.classList.add('hidden');
    }
    
    // ... rest of initialization code
});
```

## Testing
1. ✅ Repository list loads when "Remote Repository" scan type is selected
2. ✅ Repository search and filtering works correctly
3. ✅ "Select All" checkbox functions properly
4. ✅ Selected repositories are correctly added to the hidden `repo_names` input
5. ✅ Team listing loads when "Team Scan" type is selected
6. ✅ Team repositories display correctly when a team is selected
7. ✅ Back button state reset still works as intended

## Files Modified
- `templates/index.html` - Fixed JavaScript structure and variable scoping

## Impact
- **Positive**: Repository and team listing functionality fully restored
- **No Regression**: Back button state fix continues to work correctly
- **Performance**: No impact, same number of API calls

## Related Issues
- Original issue: SWE-1.6 back button state management
- This fix: Restoration of repository list and team listing functionality

## Date
January 2025
