# Pre-Deployment Checklist

## MANDATORY: Complete BEFORE any `docker build` or deployment

This checklist MUST be completed and results shown to the user before rebuilding Docker or deploying any changes.

### 1. Syntax Validation
- [ ] Run Python syntax check on ALL modified files
- [ ] Command: `python -m py_compile <modified_file.py>`
- [ ] Show results to user

### 2. Attribute/Method Verification
- [ ] For EVERY new method/attribute/class referenced in changes:
  - [ ] Grep the codebase to verify it exists
  - [ ] Command: `grep -n "def method_name\|class ClassName\|ATTRIBUTE_NAME" <file.py>`
  - [ ] Show results to user
- [ ] Verify enum values exist before using them
- [ ] Verify function signatures match when calling them

### 3. Import Verification
- [ ] Check all imports are valid
- [ ] Verify imported modules/classes exist
- [ ] Command: `python -c "import module_name; print('OK')"`

### 4. Logic Review
- [ ] Trace through the change logic mentally
- [ ] Verify variable names are correct
- [ ] Check for typos in string literals
- [ ] Verify data types match expectations

### 5. Dependency Check
- [ ] If change affects multiple files, verify all files are updated consistently
- [ ] Check for cascading impacts (e.g., enum name changes need updates everywhere)

### 6. Regression Testing (if applicable)
- [ ] If regression suite exists, run it BEFORE deployment
- [ ] Command: `python regression_suite.py --base-url http://localhost:5001`
- [ ] Verify all tests pass
- [ ] Show results to user

### 7. Show Validation Results
- [ ] Present ALL validation results to user
- [ ] Include any warnings or errors found
- [ ] Explain what was verified
- [ ] Include regression test results if run

### 8. Wait for Approval
- [ ] **DO NOT proceed with `docker build` until user approves**
- [ ] User must explicitly say "deploy" or "build" or "proceed"

## Example Validation Output

```
PRE-DEPLOYMENT VALIDATION RESULTS:
==================================

1. SYNTAX CHECK:
   ✓ endpoint_analyzer.py - No syntax errors
   ✓ enhanced_scanner.py - No syntax errors

2. ATTRIBUTE VERIFICATION:
   ✓ ConfigurationLocation.REPO_FILE exists (line 29 in endpoint_analyzer.py)
   ✓ EndpointType.INTERNAL exists (line 20 in endpoint_analyzer.py)
   ✓ _classify_endpoint() method exists (line 569 in endpoint_analyzer.py)

3. IMPORT VERIFICATION:
   ✓ All imports valid

4. LOGIC REVIEW:
   ✓ Internal components will be classified as INTERNAL type
   ✓ Endpoint types will show correct counts

All validations passed. Ready for deployment.
Waiting for approval to rebuild Docker...
```

## Failure Protocol

If ANY validation fails:
1. **STOP immediately**
2. Show the error to the user
3. Fix the issue
4. Re-run the entire checklist
5. Do NOT proceed until all checks pass

## Notes

- This checklist applies to ALL code changes, no matter how small
- Syntax errors, missing attributes, and typos are NOT acceptable
- The user should not be a QA tester
- Validate BEFORE deploying, not after
