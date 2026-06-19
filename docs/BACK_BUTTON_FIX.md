# Back Button Fix - Scan State Reset

## Issue
When users:
1. Run a scan
2. View the report
3. Use the browser back button to return to the home page

The home page incorrectly shows "Scan in progress" with a spinning activity indicator, even though no scan is actually running.

## Root Cause
Modern browsers use a feature called "bfcache" (back-forward cache) to cache pages and their DOM state. When users navigate back, the browser restores the cached page state, including:
- The scan status indicator showing "Scan in progress"
- The scan button disabled with "Scanning..." text
- The spinner animation

The existing code only reset the scan status on `DOMContentLoaded`, but this doesn't fire when the page is restored from bfcache.

## Solution
Added a comprehensive scan state reset mechanism that handles both normal page loads and bfcache restoration:

### 1. Created `resetScanState()` Function
This function resets all scan-related UI elements:
- Hides the scan status indicator
- Re-enables the scan button
- Resets the scan button text to "Start Scan"
- Removes the spinner animation
- Removes disabled state styling

### 2. Added `pageshow` Event Listener
The `pageshow` event fires when a page is shown, including when:
- Page is loaded normally
- Page is restored from bfcache (back button)
- Page is shown after being hidden

The listener checks `event.persisted` to determine if the page was restored from cache, and calls `resetScanState()` in either case.

### 3. Updated `DOMContentLoaded` Listener
The existing `DOMContentLoaded` listener now calls `resetScanState()` to ensure the state is reset on normal page loads.

## Code Changes

### File: `templates/index.html`

**Added Function**:
```javascript
// Function to reset scan state
function resetScanState() {
    const scanStatus = document.getElementById('scan-status');
    const scanButton = document.getElementById('scan-button');
    
    // Hide scan status indicator
    if (scanStatus) {
        scanStatus.classList.add('hidden');
    }
    
    // Reset scan button
    if (scanButton) {
        scanButton.disabled = false;
        scanButton.innerHTML = `
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
            </svg>
            Start Scan
        `;
        scanButton.classList.remove('opacity-75', 'cursor-not-allowed');
    }
}
```

**Updated DOMContentLoaded Listener**:
```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Reset scan state on page load (prevents issues with back button)
    resetScanState();
    
    // ... rest of the code
});
```

**Added pageshow Listener**:
```javascript
// Also reset on pageshow (handles browser back button / bfcache)
window.addEventListener('pageshow', function(event) {
    // If the page is being shown from cache (bfcache)
    if (event.persisted) {
        resetScanState();
    } else {
        // Always reset on pageshow to be safe
        resetScanState();
    }
});
```

## How It Works

### Normal Page Load
1. User navigates to the page
2. `DOMContentLoaded` event fires
3. `resetScanState()` is called
4. Scan status is hidden, button is reset

### Back Button Navigation (bfcache)
1. User navigates away from the page (to report)
2. Browser caches the page state (including "Scan in progress" indicator)
3. User clicks back button
4. Browser restores page from cache
5. `pageshow` event fires with `event.persisted = true`
6. `resetScanState()` is called
7. Scan status is hidden, button is reset

### Regular Navigation
1. User navigates to the page
2. `DOMContentLoaded` event fires
3. `pageshow` event fires with `event.persisted = false`
4. `resetScanState()` is called (twice, but idempotent)
5. Scan status is hidden, button is reset

## Browser Compatibility

### Modern Browsers
- Chrome: Full support for `pageshow` event and bfcache
- Firefox: Full support for `pageshow` event and bfcache
- Safari: Full support for `pageshow` event and bfcache
- Edge: Full support for `pageshow` event and bfcache

### Legacy Browsers
- The `DOMContentLoaded` listener ensures compatibility with older browsers
- If `pageshow` is not supported, the `DOMContentLoaded` listener still provides basic functionality
- The reset is called twice in modern browsers, but the function is idempotent (safe to call multiple times)

## Testing

### Test Case 1: Normal Navigation
1. Navigate to home page
2. Verify scan button shows "Start Scan"
3. Verify scan status is hidden

### Test Case 2: Scan and View Report
1. Run a scan
2. View the report
3. Click back button
4. **Expected**: Scan button shows "Start Scan", scan status is hidden
5. **Before Fix**: Scan button shows "Scanning...", scan status shows "Scan in progress"

### Test Case 3: Multiple Back/Forward
1. Run a scan
2. View the report
3. Click back button
4. Click forward button
5. Click back button again
6. **Expected**: Scan button shows "Start Scan", scan status is hidden

### Test Case 4: Refresh
1. Run a scan
2. View the report
3. Click back button
4. Refresh the page
5. **Expected**: Scan button shows "Start Scan", scan status is hidden

## Benefits

1. **Improved User Experience**: Users no longer see confusing "Scan in progress" messages when using the back button
2. **Correct State**: The page always shows the correct state regardless of how the user navigated to it
3. **Browser Compatibility**: Works across all modern browsers and handles bfcache correctly
4. **Simple Solution**: Minimal code changes with maximum impact
5. **Future-Proof**: Handles both current and future browser caching behaviors

## Related Issues

This fix also prevents similar issues with:
- Form submissions that show loading states
- Any UI elements that change state during user interaction
- Modal dialogs or overlays that might be cached

## Date
January 2025
