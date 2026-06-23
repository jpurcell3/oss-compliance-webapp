# OSS Compliance Web Application - OSS Advisor

## Description
Expert skill for running OSS Compliance Web Application operations from the command line. Provides CLI-based alternatives to all UI operations, using the same underlying scanner classes and configuration as the web interface. This skill enables automated, scripted, and interactive command-line access to repository scanning, compliance analysis, PR creation, and configuration management.

## When to Use This Skill
Invoke this skill when:
- Running repository scans from command line instead of UI
- Automating compliance checks in scripts/CI/CD pipelines
- Testing configuration without using the web interface
- Performing batch operations on multiple repositories
- Debugging scanner behavior with direct code access
- Creating pull requests programmatically
- Viewing and analyzing scan results in terminal format
- Testing GitHub/Jenkins/Artifactory connectivity

## Key Differences from UI
- **Terminal Output**: Results displayed in CLI-friendly format (tables, summaries, progress bars)
- **Interactive Prompts**: User selection for multi-user configurations
- **Scriptable**: Can be integrated into automation pipelines
- **Direct Code Access**: Uses same scanner classes as UI, not just API calls
- **Error Handling**: Provides detailed debugging information and suggestions
- **No Browser Required**: Operates entirely from command line

## Core Capabilities

### 1. Repository Scanning
- **Basic Scanning**: Standard compliance analysis
- **Enhanced Scanning**: Component-level endpoint analysis with runtime evidence
- **Local Repository Scanning**: Scan local filesystem paths
- **Remote Repository Scanning**: Scan GitHub repositories via API
- **Batch Scanning**: Scan multiple repositories in sequence
- **Scan History**: View and manage previous scan results

### 2. Repository Management
- **Repository Listing**: Browse available repositories by GitHub instance
- **Repository Filtering**: Search and filter repositories by name/pattern
- **Repository Details**: View repository metadata and configuration
- **Cache Management**: View, refresh, or clear repository cache

### 3. Configuration Management
- **Configuration Testing**: Verify GitHub/Jenkins/Artifactory connectivity
- **User Management**: List, add, update GitHub users with encrypted tokens
- **Instance Management**: View and manage GitHub instance configurations
- **Token Validation**: Test encrypted tokens and API access
- **Configuration Viewing**: Display current configuration in readable format

### 4. Report Management
- **Report Viewing**: Display scan results in terminal-friendly format
- **Report Filtering**: Filter reports by repository, date, severity
- **Report Export**: Export reports to JSON, Markdown, or spec format
- **Report Analysis**: Analyze trends and compliance metrics
- **Bulk Operations**: Delete multiple reports at once

### 5. PR Creation
- **Automated PR Creation**: Create pull requests with compliance fixes
- **User Selection**: Interactive user selection for multi-user configurations
- **Branch Management**: Create compliant branch names automatically
- **PR Tracking**: Track PR status and outcomes
- **Batch PR Creation**: Create PRs for multiple repositories

## Quick Start Examples

### Basic Repository Scan
```
"Invoke the oss-advisor skill to scan the fusion-stage repository on eos2git GitHub server using basic scanning"
```

### Enhanced Repository Scan
```
"Invoke the oss-advisor skill to perform an enhanced scan on the fusion-stage repository on eos2git with runtime endpoint analysis"
```

### List Available Repositories
```
"Invoke the oss-advisor skill to list all available repositories on the eos2git GitHub server"
```

### Test Configuration
```
"Invoke the oss-advisor skill to test the GitHub connectivity for the eos2git instance"
```

### View Scan Results
```
"Invoke the oss-advisor skill to show me the latest scan results for the fusion-stage repository"
```

### Create Pull Request
```
"Invoke the oss-advisor skill to create a pull request for the fusion-stage compliance fixes using the default user"
```

## Implementation Approach

When this skill is invoked, I will:

### 1. Load Configuration
```python
from config_manager import get_config_manager

# Load configuration from config/app_config.yaml
config_manager = get_config_manager()
github_instances = config_manager.get_github_instances()
```

### 2. Initialize Scanner
```python
from remote_scanner import RemoteRepositoryScanner

# Get specific GitHub instance
instance = config_manager.get_github_instance('eos2git')
user = instance.get_default_user()  # Auto-decrypted token

# Initialize scanner
scanner = RemoteRepositoryScanner(
    github_api_url=instance.api_url,
    github_org=instance.org,
    github_token=user.token
)
```

### 3. Perform Operation
```python
# Example: Basic scan
report = scanner.scan_repository('fusion-stage', use_enhanced=False)

# Example: Enhanced scan
report = scanner.scan_repository('fusion-stage', use_enhanced=True)

# Example: List repositories
repos = scanner.get_organization_repositories()
```

### 4. Display Results
```python
# Format results for terminal display
print(f"Scan completed for {report['repository_name']}")
print(f"Total findings: {report['total_findings']}")
print(f"Critical: {report['critical_findings']}")
print(f"High: {report['high_findings']}")
print(f"Compliance Score: {report['compliance_score']}%")
```

## Advanced Usage Patterns

### Batch Repository Scanning
```
"Invoke the oss-advisor skill to scan all repositories starting with 'fusion-' on eos2git and generate a summary report"
```

### Multi-User PR Creation
```
"Invoke the oss-advisor skill to create a PR for fusion-stage using user 'jpurcell' from the eos2git instance"
```

### Configuration Validation
```
"Invoke the oss-advisor skill to validate all GitHub instances in the configuration and report any connectivity issues"
```

### Scan Result Analysis
```
"Invoke the oss-advisor skill to analyze the last 10 scans for fusion-stage and show compliance trends"
```

### Cache Management
```
"Invoke the oss-advisor skill to clear the repository cache for eos2git and refresh the repository list"
```

## Error Handling and Debugging

### Common Issues and Solutions

**Issue**: GitHub API rate limiting
```
"Invoke the oss-advisor skill to debug the rate limiting issue when scanning fusion-stage"
```
**Solution**: Check cache status, implement backoff, verify token permissions

**Issue**: Token decryption failure
```
"Invoke the oss-advisor skill to troubleshoot token decryption for the eos2git instance"
```
**Solution**: Verify ENCRYPTION_KEY, check token_encrypted format in YAML

**Issue**: Repository not found
```
"Invoke the oss-advisor skill to verify that fusion-stage exists in the eos2git organization"
```
**Solution**: Check repository name spelling, verify organization name, test API access

**Issue**: Enhanced scan timeout
```
"Invoke the oss-advisor skill to optimize the enhanced scan performance for fusion-stage"
```
**Solution**: Adjust timeout settings, analyze bottleneck components, implement caching

## Output Formats

### Terminal-Friendly Output

**Scan Summary**:
```
╔════════════════════════════════════════════════════════════╗
║           OSS Compliance Scan Results                      ║
╠════════════════════════════════════════════════════════════╣
║ Repository: fusion-stage                                   ║
║ Instance: eos2git (ISG-Edge)                              ║
║ Scan Type: Enhanced                                       ║
║ Timestamp: 2026-06-23 15:30:45                            ║
╠════════════════════════════════════════════════════════════╣
║ Total Findings: 42                                        ║
║ Critical: 5    ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ║
║ High: 15        ████████████████░░░░░░░░░░░░░░░░░░░░░  ║
║ Medium: 18     ████████████████████████░░░░░░░░░░░░░░  ║
║ Low: 4          ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ║
╠════════════════════════════════════════════════════════════╣
║ Compliance Score: 78.5%                                   ║
║ Status: NEEDS ATTENTION                                   ║
╚════════════════════════════════════════════════════════════╝
```

**Repository List**:
```
Available Repositories on eos2git (ISG-Edge):
┌─────────────────────────────┬──────────┬──────────────┐
│ Repository Name             │ Archived │ Last Updated │
├─────────────────────────────┼──────────┼──────────────┤
│ fusion-stage                │ No       │ 2 hours ago  │
│ fusion-stage-backend        │ No       │ 1 day ago    │
│ fusion-cli                  │ No       │ 3 hours ago  │
│ fusion-manager              │ No       │ 5 hours ago  │
│ ...                         │ ...      │ ...          │
└─────────────────────────────┴──────────┴──────────────┘
Total: 334 repositories (287 active, 47 archived)
```

### JSON Output (for scripting)
```json
{
  "repository": "fusion-stage",
  "instance": "eos2git",
  "scan_type": "enhanced",
  "findings": {
    "total": 42,
    "critical": 5,
    "high": 15,
    "medium": 18,
    "low": 4
  },
  "compliance_score": 78.5,
  "timestamp": "2026-06-23T15:30:45Z"
}
```

## Configuration Requirements

### Required Configuration Files
- `config/app_config.yaml` - Main configuration with encrypted tokens
- `.env` (optional) - Environment variables for ENCRYPTION_KEY, SECRET_KEY

### Required Environment Variables
- `ENCRYPTION_KEY` - Fernet encryption key for token decryption (required)
- `SECRET_KEY` - Flask secret key (optional, has default)
- `SSL_VERIFY` - SSL verification for API calls (optional, defaults to false)
- `DEBUG_LOGGING` - Enable debug logging (optional, defaults to true)

### Configuration Validation
Before performing operations, the skill will:
1. Verify configuration file exists and is valid YAML
2. Check ENCRYPTION_KEY is available
3. Validate GitHub instance configurations
4. Test token decryption
5. Verify API connectivity

## Integration with Existing Codebase

### Uses Same Components as UI
- **ConfigManager**: Configuration loading and token decryption
- **RemoteRepositoryScanner**: GitHub integration and scanning
- **EnhancedScanner**: Component-level analysis
- **EndpointAnalyzer**: Runtime endpoint detection
- **Database Models**: Report and PRSubmission models

### No Code Modifications Required
- Skill uses existing classes and methods
- No changes to app.py or scanner files
- No database schema changes
- No configuration file format changes
- Skill is purely additive - provides new interface to existing functionality

## Security Considerations

### Credential Handling
- Tokens are decrypted only in memory during operation
- No plaintext tokens are logged or stored
- Decrypted tokens are never written to disk
- Skill respects the same security model as the UI

### Access Control
- Uses same user authentication as configuration
- Respects multi-user token management
- No elevated privileges beyond existing configuration
- All operations use existing token permissions

## Performance Considerations

### Caching Strategy
- Repository lists cached (24-hour TTL)
- Scan results stored in database
- Configuration loaded once per session
- Cache can be cleared/refreshed on demand

### Resource Management
- Memory-efficient scanning for large repositories
- Streaming for large file processing
- Timeout handling for long-running operations
- Progress reporting for user feedback

## Testing and Validation

### Pre-Flight Checks
Before performing operations, the skill will:
1. Validate configuration file format
2. Test GitHub API connectivity
3. Verify repository accessibility
4. Check token permissions
5. Validate required dependencies

### Error Recovery
- Automatic retry for transient failures
- Graceful degradation on partial failures
- Detailed error messages with suggestions
- Rollback capabilities for destructive operations

## Example Workflows

### Workflow 1: First-Time Repository Scan
```
1. "Invoke the oss-advisor skill to test the eos2git GitHub configuration"
2. "Invoke the oss-advisor skill to list repositories on eos2git"
3. "Invoke the oss-advisor skill to scan fusion-stage on eos2git using enhanced scanning"
4. "Invoke the oss-advisor skill to show the scan results for fusion-stage"
```

### Workflow 2: PR Creation for Compliance Fixes
```
1. "Invoke the oss-advisor skill to scan fusion-stage on eos2git"
2. "Invoke the oss-advisor skill to analyze the scan results for fusion-stage"
3. "Invoke the oss-advisor skill to create a PR for fusion-stage compliance fixes"
4. "Invoke the oss-advisor skill to track the PR status"
```

### Workflow 3: Batch Repository Analysis
```
1. "Invoke the oss-advisor skill to list all repositories on eos2git"
2. "Invoke the oss-advisor skill to scan all fusion-* repositories on eos2git"
3. "Invoke the oss-advisor skill to generate a summary report for all fusion-* scans"
4. "Invoke the oss-advisor skill to identify repositories with compliance scores below 80%"
```

## Limitations and Constraints

### Current Limitations
- No real-time progress updates (except final results)
- Limited interactive capabilities compared to UI
- No visual charts or graphs
- Requires command-line familiarity
- Dependent on existing configuration setup

### Planned Enhancements
- Real-time progress bars for long operations
- Interactive mode with step-by-step workflows
- Integration with CI/CD pipelines
- Export to multiple formats (PDF, Excel)
- Scheduled scan automation

## Troubleshooting

### Skill Invocation Issues
**Problem**: Skill not found or not loading
**Solution**: 
- Verify skill file exists at `.devin/skills/oss-advisor/SKILL.md`
- Check file permissions
- Ensure skill syntax is valid

### Configuration Issues
**Problem**: Configuration not loading
**Solution**:
- Verify `config/app_config.yaml` exists
- Check YAML syntax is valid
- Ensure ENCRYPTION_KEY environment variable is set
- Validate file encoding is UTF-8

### Scanner Issues
**Problem**: Scanner not initializing
**Solution**:
- Check required dependencies are installed
- Verify Python version compatibility (3.11+)
- Ensure scanner files are present and importable
- Check for import errors in Python path

### API Issues
**Problem**: GitHub API calls failing
**Solution**:
- Verify token has required permissions
- Check API rate limits
- Test network connectivity
- Validate SSL verification settings

## Skill Maintenance

### Version History
- **v1.0** (2026-06-23): Initial CLI skill creation
  - Repository scanning (basic and enhanced)
  - Repository listing and management
  - Configuration testing and validation
  - Report viewing and analysis
  - PR creation workflow

### Future Updates
- Add batch operations support
- Implement interactive workflows
- Add CI/CD integration examples
- Enhance error handling and recovery
- Add performance monitoring and reporting

## Support and Documentation

### Related Documentation
- [oss-compliance-dev skill](../oss-compliance-dev/SKILL.md) - Development and debugging
- [oss-compliance-sdd skill](../oss-compliance-sdd/SKILL.md) - Architecture and design
- [USER_GUIDE.md](../../../docs/USER_GUIDE.md) - User interface documentation
- [API_REFERENCE.md](../../../docs/API_REFERENCE.md) - API endpoint documentation

### Getting Help
- For skill issues: Check skill invocation and file structure
- For scanner issues: Invoke oss-compliance-dev skill
- For architecture questions: Invoke oss-compliance-sdd skill
- For configuration help: Refer to USER_GUIDE.md

---

**Skill Version**: 1.0  
**Last Updated**: 2026-06-23  
**Maintained By**: Development Team  
**Dependencies**: oss-compliance-webapp v1.0+