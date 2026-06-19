# Development Workflow

## Standard Change Process

### Phase 1: Understand the Problem
1. Read the user's request carefully
2. Identify the root cause
3. Locate the relevant code
4. Plan the fix

### Phase 2: Make Changes
1. Edit the necessary files
2. Keep changes focused and minimal
3. Document what was changed and why

### Phase 3: PRE-DEPLOYMENT VALIDATION (MANDATORY)
**⚠️ STOP: You MUST complete the Pre-Deployment Checklist before proceeding**

See: `.devin/PRE_DEPLOYMENT_CHECKLIST.md`

Required steps:
1. Run syntax checks on ALL modified files
2. Verify ALL new methods/attributes/enums exist
3. Check imports are valid
4. Review logic for errors
5. **Show validation results to user**
6. **Wait for explicit approval**

### Phase 4: Deployment (Only After Approval)
1. Rebuild Docker image
2. Restart containers
3. Verify application is running

### Phase 5: Verification
1. Test the change works as expected
2. Check for any new errors
3. Confirm with user

## Key Rules

### NEVER Skip Validation
- No matter how small the change
- No matter how confident you are
- No exceptions

### ALWAYS Wait for Approval
- After showing validation results
- User must explicitly approve deployment
- Do not assume approval

### NEVER Deploy Broken Code
- If validation fails, fix it first
- Re-run full validation after fixes
- Do not proceed until all checks pass

## Common Mistakes to Avoid

❌ Using attributes that don't exist (e.g., `ConfigurationLocation.COMPONENT_SOURCE`)
❌ Calling methods with wrong names (e.g., `_classify_endpoint_type()` vs `_classify_endpoint()`)
❌ Typos in enum values
❌ Missing imports
❌ Syntax errors
❌ Deploying without validation
❌ Deploying without user approval

## Validation Commands Reference

### Syntax Check
```bash
python -m py_compile file.py
```

### Find Method/Class Definition
```bash
grep -n "def method_name\|class ClassName" file.py
```

### Find Enum Value
```bash
grep -n "ENUM_VALUE" file.py
```

### Test Import
```bash
python -c "import module; print('OK')"
```

### Check All Python Files for Errors
```bash
python -m compileall -q .
```

## Example Workflow Execution

```
USER: Fix the endpoint classification for eos2git modules

ASSISTANT: 
[Phase 1: Understand]
- eos2git modules are being classified as direct_public
- Should be classified as internal
- Need to update endpoint_analyzer.py

[Phase 2: Make Changes]
- Updated EndpointType enum to use INTERNAL instead of DIRECT_PRIVATE
- Modified _find_applicable_endpoint() to check trusted sources first
- Updated UI labels

[Phase 3: PRE-DEPLOYMENT VALIDATION]
Running validation checks...

1. SYNTAX CHECK:
   $ python -m py_compile endpoint_analyzer.py
   ✓ No syntax errors

2. ATTRIBUTE VERIFICATION:
   $ grep -n "INTERNAL" endpoint_analyzer.py
   20:    INTERNAL = "internal"
   ✓ EndpointType.INTERNAL exists
   
   $ grep -n "ConfigurationLocation.REPO_FILE" endpoint_analyzer.py
   658:                config_location=ConfigurationLocation.REPO_FILE,
   $ grep -n "REPO_FILE" endpoint_analyzer.py
   29:    REPO_FILE = "repository_file"
   ✓ ConfigurationLocation.REPO_FILE exists

3. LOGIC REVIEW:
   ✓ Trusted sources checked first
   ✓ Correct endpoint type assigned

All validations passed. Ready for deployment.

**Waiting for your approval to rebuild Docker...**

USER: proceed

ASSISTANT: [Phase 4: Deployment]
Building Docker image...
[continues with deployment]
```

## Enforcement

This workflow is MANDATORY. Skipping validation is not acceptable and wastes the user's time.

If you find yourself about to run `docker build` without completing validation:
1. STOP
2. Go back to Phase 3
3. Complete the checklist
4. Show results to user
5. Wait for approval
