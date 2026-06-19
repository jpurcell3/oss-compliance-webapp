# Changelog

All notable changes to the OSS Compliance Verification Web Application will be documented in this file.

## [0.3] - 2026-04-29

### 🎯 Compliance Intelligence Enhancements

#### Fixed
- **Internal Maven Dependency Recognition**: Maven coordinates with internal company groupIds (com.dell, com.emc, com.isgedge, com.vmware) are now correctly recognized as compliant Artifactory artifacts
  - Previously flagged internal dependencies like `com.dell.isgedge.hzp:qa-framework` as non-compliant
  - Now recognizes reverse domain name patterns as internal artifacts
  - Applied fix across all scanners (compliance_scanner, remote_scanner, pipeline_scanner)

- **Pipeline Scanner Method Signature**: Fixed `_analyze_repo_discrepancies()` method to accept required `repo_name` parameter
  - Resolved "takes 3 positional arguments but 4 were given" error
  - Updated method calls throughout codebase

- **GitHub Org Attribute Reference**: Fixed PipelineRepositoryScanner to use correct `github_org` attribute instead of non-existent `github_instances`

#### Enhanced
- **Jenkins GOPROXY Integration**: Go dependency compliance checking now considers Jenkins-level GOPROXY configuration
  - If Jenkins has GOPROXY configured globally, Go dependencies are considered compliant even without local configuration
  - Added `_check_jenkins_goproxy_config()` method to RemoteComplianceScanner
  - Integrated Jenkins GOPROXY status into Go module scanning logic
  - Added debug logging for Jenkins connection attempts

- **Repository List Filtering**: GitHub repository fetching now excludes archived repositories
  - Filters out repositories with `archived: true` status from GitHub API
  - Shows debug output with active vs archived repository counts
  - Improves repository list relevance by excluding inactive projects

#### Added
- **Repository Column in Findings Table**: Added repository name column to the detailed findings table in results UI
  - Each finding now shows which repository it belongs to
  - Fallback to scan summary repository name if finding lacks repository field
  - Improves traceability for multi-repository scans

### 🔧 Technical Changes

#### Core Files Modified
- `compliance_scanner.py`: Added internal Maven dependency recognition in `scan_maven_poms()`
- `remote_scanner.py`: 
  - Added Jenkins GOPROXY configuration checking
  - Enhanced Maven dependency compliance logic
  - Added archived repository filtering in `get_organization_repositories()`
  - Completed `_generate_recommendations()` method
- `pipeline_scanner.py`: 
  - Added internal Maven coordinate recognition in `_is_repo_compliant()`
  - Fixed method signature for `_analyze_repo_discrepancies()`
  - Fixed GitHub org attribute reference
- `templates/results.html`: Added repository column to findings table

### 📊 Impact

#### Before v0.3
- Internal Maven dependencies incorrectly flagged as non-compliant
- No consideration of Jenkins-level GOPROXY configuration
- Archived repositories cluttered repository selection list
- Findings table lacked repository context

#### After v0.3
- Internal Maven coordinates (com.dell.*, com.emc.*, etc.) correctly recognized as compliant
- Go dependencies benefit from Jenkins GOPROXY configuration
- Repository list shows only active, non-archived repositories
- Findings table includes repository names for better traceability

### 🎯 User Benefits
- **Accurate Maven Compliance**: Internal dependencies no longer generate false positives
- **Jenkins Integration**: Respects enterprise-level proxy configuration
- **Cleaner Repository List**: Only active repositories available for scanning
- **Better Traceability**: Repository names visible in findings for easier issue resolution

---

## [0.2] - 2026-04-27

### 🎯 Major Improvements

#### Fixed
- **Pipeline Compliance Calculation Bug**: Resolved "75% compliant with zero issues" mathematical impossibility
  - Fixed compliance calculation to count only valid repositories
  - Added repository validation to filter out parsing artifacts
  - Enhanced compliance logic for accurate GitHub Actions and external registry detection

- **UI Display Issues**: Eliminated null values and truncated text in results
  - Updated field name mapping between scanner and template
  - Removed CSS truncation classes from findings table
  - Added proper text wrapping for long issue descriptions

- **Multi-Repository Traceability**: Added repository context to every finding
  - Each finding now shows source repository name
  - File names include repository context (e.g., "repo-name: Pipeline Configuration")
  - Added "Repositories Scanned" counter for multi-repo scans
  - Fixed summary statistics aggregation

- **External Repository Path Display**: Fixed truncated Git repository URLs in recommendations
  - Now shows full repository paths instead of truncated versions
  - Enhanced issue descriptions to be more specific about external reference types

#### Enhanced
- **Actionable Recommendations**: Replaced generic messages with specific guidance
  - Grouped recommendations by issue type (Docker, Git, Registry)
  - Added affected repository lists with actual names and counts
  - Included specific replacement URLs and instructions
  - Added authentication issue detection with troubleshooting steps

- **Pipeline-Centric Analysis**: Improved pipeline configuration scanning
  - Enhanced GitHub Actions workflow detection
  - Better Docker image registry compliance checking
  - More accurate external dependency identification
  - Support for enterprise Docker registry resolution

#### Added
- **Authentication Issue Detection**: Clear error reporting when API access fails
- **Repository Count Display**: Shows number of repositories scanned in multi-repo results
- **Responsive UI Layout**: Dynamic grid layout for single vs multi-repository scans
- **Enhanced Debug Logging**: Detailed compliance calculation tracing

### 🔧 Technical Changes

#### Core Files Modified
- `pipeline_scanner.py`: Fixed compliance calculation logic and enhanced issue descriptions
- `app.py`: Added repository context to multi-repo scan findings
- `remote_scanner.py`: Updated traditional scanner for UI field compatibility
- `templates/results.html`: Removed truncation, added repository count display

#### New Files Added
- `IMPROVEMENTS_SUMMARY.md`: Comprehensive documentation of all fixes
- `test_compliance_fix.py`: Validates compliance calculation accuracy
- `test_multi_repo_traceability.py`: Verifies repository traceability functionality

### 📊 Impact

#### Before v0.2
- **Single Repo**: "75% compliant with 0 issues" (impossible)
- **Multi Repo**: Null values, truncated text, no repository traceability
- **Recommendations**: Generic "Update pipeline configurations" messages

#### After v0.2
- **Single Repo**: "42.86% compliant with 4 issues" (accurate and actionable)
- **Multi Repo**: "39% compliant, 156 total items, 59 issues across 61 repositories" with full traceability
- **Recommendations**: Specific actions like "Replace 2 external Docker images: docker.io/redis:alpine, quay.io/prometheus/node-exporter. Use: https://isgedge.artifactory.cec.lab.emc.com/artifactory/isgedge-docker-virtual"

### 🎯 User Benefits
- **Clear Traceability**: Know exactly which repository caused each compliance issue
- **Accurate Metrics**: Trust the compliance percentages and counts
- **Actionable Guidance**: Get specific instructions on how to fix each issue
- **Professional Results**: No more confusing null values or truncated text
- **Systematic Remediation**: Prioritize fixes by repository and severity

---

## [0.1] - 2026-04-17

### Added
- Initial release of OSS Compliance Verification Web Application
- Multi-language support for Go, Python, Node.js, Java/Maven projects
- Web interface for repository scanning
- Configuration management for virtual repositories
- Report generation in JSON, Markdown, and YAML formats
- Export options and report history
- Pipeline-centric scanning capability (initial implementation)