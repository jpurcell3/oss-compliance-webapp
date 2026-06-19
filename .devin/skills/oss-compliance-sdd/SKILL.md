# OSS Compliance Web Application - SDD Documentation Expert

## Description
Expert skill for maintaining, updating, and working with the Software Design Document (SDD) framework for the OSS Compliance Web Application. This skill provides comprehensive knowledge of the application's architecture, design decisions, and documentation standards.

## When to Use This Skill
Invoke this skill when:
- Updating SDD documentation after feature additions
- Reviewing architectural decisions
- Understanding system design and component interactions
- Documenting new features or changes
- Creating technical documentation
- Explaining system architecture to stakeholders
- Planning system enhancements

## Application Overview

### Purpose
The OSS Compliance Web Application automates the detection and remediation of open-source software (OSS) compliance issues in repositories, ensuring dependencies are sourced through approved Artifactory virtual repositories.

### Current Version
- **Application Version**: 0.5.0
- **SDD Version**: 1.2
- **Last Updated**: 2026-06-12

### Core Capabilities
1. **Repository Scanning**: Local and remote repository compliance scanning
2. **Enhanced Analysis**: Component-level endpoint analysis with runtime evidence
3. **Automated Remediation**: PR creation with compliance fixes
4. **Multi-User Support**: Multiple GitHub users per instance with encrypted credentials
5. **Admin Configuration**: Web-based configuration UI with credential management
6. **Reporting**: Comprehensive compliance reports in multiple formats

## SDD Document Structure

### Core Documents
1. **SDD_OVERVIEW.md** - Framework overview and document relationships
2. **HLD.md** - High-level design and architecture
3. **SDD_FRAMEWORK.md** - Detailed component design
4. **API_REFERENCE.md** - API endpoint documentation
5. **DEPLOYMENT_GUIDE.md** - Operations and deployment
6. **DATABASE_GUIDE.md** - Database schema and operations
7. **USER_GUIDE.md** - End-user documentation

### Document Hierarchy
```
HLD.md (System Context & Architecture)
  ↓
SDD_FRAMEWORK.md (Detailed Design)
  ↓
API_REFERENCE.md + USER_GUIDE.md + DEPLOYMENT_GUIDE.md + DATABASE_GUIDE.md
  ↓
README.md (Quick Start)
```

## Architecture Overview

### System Components

#### 1. Web UI Layer
- **Technology**: Flask templates with Tailwind CSS
- **Purpose**: User interface for scanning, reporting, and configuration
- **Key Features**: 
  - Repository selection with search
  - Real-time scan progress
  - Interactive reports with charts
  - Admin configuration forms

#### 2. Application Layer (Flask)
- **Routes**: Web pages and REST API endpoints
- **Session Management**: Flask sessions
- **Error Handling**: Centralized exception handling
- **Response Formatting**: JSON and HTML responses

#### 3. Business Logic Layer

**Scanner Services**:
- `ComplianceScanner`: Local repository scanning
- `RemoteRepositoryScanner`: Remote GitHub repository scanning
- `EnhancedScanner`: Component-level endpoint analysis
- `EndpointAnalyzer`: Runtime endpoint detection

**PR Services**:
- `RemoteRepositoryScanner.create_fix_pr()`: PR creation workflow
- `FixGenerator`: Automated fix generation
- Multi-user token management
- GitHub Enterprise compliance

**Configuration Services**:
- `ConfigManager`: YAML-based configuration loading with automatic token decryption
- GitHub instance management with encrypted user tokens
- Jenkins integration with encrypted token storage
- Artifactory virtual repository mapping
- Configuration validation and reloading

#### 4. Data Layer
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **ORM**: SQLAlchemy
- **Models**: Report, PRSubmission
- **File Storage**: JSON reports, markdown summaries

#### 5. External Integrations
- **GitHub API**: Repository operations, PR creation
- **Jenkins API**: Pipeline triggering
- **Artifactory**: Virtual repository validation

## Key Design Patterns

### 1. Layered Architecture
- Clear separation of concerns
- Web UI → Application → Business Logic → Data
- Each layer has defined responsibilities

### 2. Service Layer Pattern
- Business logic encapsulated in service classes
- Reusable across different interfaces
- Testable in isolation

### 3. Repository Pattern
- Data access abstraction
- SQLAlchemy ORM for database operations
- File-based storage for reports

### 4. Strategy Pattern
- Different scanning strategies (local, remote, enhanced)
- Pluggable endpoint analyzers
- Configurable virtual repository mappings

## Security Architecture

### Credential Encryption (v0.5.0)

**Algorithm**: Fernet (AES-128 CBC + HMAC)

**Workflow**:
```python
# Encryption
ENCRYPTION_KEY → Fernet cipher → encrypt(token) → encrypted_token → app_config.yaml

# Decryption (runtime only)
app_config.yaml → encrypted_token → ConfigManager → decrypt() → plaintext_token → API call
```

**Key Features**:
- Symmetric encryption with authentication
- Environment variable key storage
- Runtime-only decryption
- No plaintext logging

### Multi-User GitHub Support

**Configuration Structure (app_config.yaml)**:
```yaml
github_instances:
  eos2git:
    name: ISG-Edge
    api_url: https://eos2git.cec.lab.emc.com/api/v3
    org: ISG-Edge
    users:
    - username: default_user
      token_encrypted: gAAAAABh...
      email: ''
    - username: user2
      token_encrypted: gAAAAABh...
      email: user2@example.com
jenkins:
  user: jenkins_user
  token_encrypted: gAAAAABh...
  urls:
  - https://jenkins.example.com
artifactory:
  base_url: artifactory.example.com
  user: artifactory_user
  token_encrypted: gAAAAABh...
  virtual_repos:
    docker: docker-virtual
    go: go-virtual
```

**User Selection Flow**:
1. Scan identifies GitHub instance
2. System retrieves available users
3. If multiple users: show dropdown modal
4. User selects identity for PR creation
5. Token decrypted and used for API calls

## PR Creation Workflow (v0.5.0)

### 9-Step Process

1. **User Initiation**: Click "Create Fix PR" on scan results
2. **Instance Matching**: Match GitHub instance from scan metadata
3. **User Selection**: Dropdown modal if multiple users configured
4. **Authentication**: Fetch user info and verify permissions
5. **Branch Creation**: Create branch with compliant naming (`usr/{username}/oss-compliance-fixes-{timestamp}`)
6. **Artifact Generation**:
   - `oss_compliance_setup.sh` - Environment setup script
   - `OSS_COMPLIANCE_README.md` - Quick start guide
   - `OSS_COMPLIANCE_REPORT.md` - Detailed analysis
   - `OSS_COMPLIANCE_SPEC.json` - Automation spec
7. **File Commits**: Commit each file to branch
8. **PR Creation**: Create pull request with description
9. **User Notification**: Display PR URL and open in new tab

### GitHub Enterprise Compliance

**Branch Naming Requirements**:
- Official branches: `rel/` prefix
- Feature branches: `pub/` prefix
- Private shared: `pvt/` prefix
- User branches: `usr/{username}/` prefix ✅ (used by app)

**Pre-receive Hook Validation**:
- Enforced by GitHub Enterprise
- Application fetches authenticated user info
- Constructs compliant branch name automatically

## Data Model

### Report Model
```python
class Report(db.Model):
    id: Integer (Primary Key)
    filename: String (Unique)
    repository_name: String
    repository_type: String (local/remote/remote_enhanced)
    scan_timestamp: DateTime
    total_findings: Integer
    critical_findings: Integer
    high_findings: Integer
    medium_findings: Integer
    low_findings: Integer
    compliance_score: Float
```

### PRSubmission Model
```python
class PRSubmission(db.Model):
    id: Integer (Primary Key)
    report_id: Integer (Foreign Key → Report)
    pr_url: String
    pr_number: Integer
    submitter_username: String
    submitter_email: String
    github_instance: String
    submission_timestamp: DateTime
    status: String (pending/merged/closed)
```

## API Endpoints

### Scanning APIs
- `POST /scan` - Initiate repository scan
- `GET /api/repositories` - List available repositories
- `POST /api/repositories/refresh` - Refresh repository cache

### Reporting APIs
- `GET /reports` - List all reports
- `GET /report/<filename>` - View specific report
- `DELETE /report/<filename>` - Delete report
- `POST /reports/bulk-delete` - Bulk delete reports

### PR Creation APIs
- `POST /create-pr/<filename>` - Create pull request
  - Supports multi-user selection
  - Returns user list if selection needed
  - Creates PR with selected user's token

### Configuration APIs
- `GET /config` - Configuration page (new redesigned UI)
- `POST /update-github-user` - Add/update GitHub user with encrypted token
- `DELETE /api/github-user/<instance_id>/<username>` - Delete GitHub user
- `GET /api/github-users/<instance_id>` - List users for GitHub instance
- `GET /api/github-user/<instance_id>/<username>` - Get specific user details
- `POST /test-endpoint` - Test endpoint connectivity with user selection
- `POST /update-endpoint` - Unified endpoint update for GitHub/Jenkins/Artifactory
- `POST /update-repos-whitelist` - Update virtual repositories and whitelist URLs
- `POST /update-app-settings` - Update application settings including debug logging

## Technology Stack

### Backend
- **Framework**: Flask 2.3.3
- **Database**: SQLite (dev), PostgreSQL (prod)
- **ORM**: SQLAlchemy
- **Encryption**: cryptography (Fernet)
- **HTTP Client**: requests with retry logic

### Frontend
- **Templates**: Jinja2
- **Styling**: Tailwind CSS 2.2.19
- **JavaScript**: Vanilla ES6+
- **Charts**: Chart.js

### External APIs
- **GitHub API**: v3 (REST)
- **Jenkins API**: REST API
- **Artifactory**: REST API (validation only)

### Deployment
- **Container**: Docker
- **Web Server**: Gunicorn + Nginx
- **Process Manager**: systemd / Docker Compose

## Documentation Update Process

### When to Update SDD

**Trigger Events**:
1. New feature addition
2. Architecture changes
3. API endpoint modifications
4. Security enhancements
5. Technology stack changes
6. Major bug fixes affecting design

### Update Checklist

For each feature addition:

1. **SDD_OVERVIEW.md**:
   - [ ] Update document version
   - [ ] Update application version
   - [ ] Add revision history entry

2. **HLD.md**:
   - [ ] Update document version
   - [ ] Add high-level workflow diagrams
   - [ ] Document architectural decisions
   - [ ] Update component interactions
   - [ ] Add security considerations
   - [ ] Update revision history

3. **SDD_FRAMEWORK.md**:
   - [ ] Update document version
   - [ ] Add detailed component design
   - [ ] Include code examples
   - [ ] Document data model changes
   - [ ] Add security implementation details
   - [ ] Update revision history

4. **API_REFERENCE.md**:
   - [ ] Document new endpoints
   - [ ] Add request/response examples
   - [ ] Update error codes
   - [ ] Add usage examples

5. **DEPLOYMENT_GUIDE.md**:
   - [ ] Update configuration requirements
   - [ ] Add new environment variables
   - [ ] Update deployment steps if needed

6. **DATABASE_GUIDE.md**:
   - [ ] Document schema changes
   - [ ] Add migration procedures
   - [ ] Update backup/recovery procedures
   - [ ] Add performance considerations

7. **USER_GUIDE.md**:
   - [ ] Document new user-facing features
   - [ ] Add screenshots/examples
   - [ ] Update workflows

### Version Numbering

**Document Version**: MAJOR.MINOR
- **MAJOR**: Significant architectural changes
- **MINOR**: Feature additions, enhancements

**Application Version**: MAJOR.MINOR.PATCH
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

## Common Tasks

### Adding a New Feature

1. **Design Phase**:
   - Review existing architecture
   - Identify affected components
   - Document design decisions in HLD
   - Create detailed design in SDD_FRAMEWORK

2. **Implementation Phase**:
   - Follow existing patterns
   - Maintain layered architecture
   - Add appropriate error handling
   - Include logging

3. **Documentation Phase**:
   - Update all relevant SDD documents
   - Add API documentation
   - Update user guide
   - Create code examples

4. **Review Phase**:
   - Verify documentation completeness
   - Check for consistency across documents
   - Validate code examples
   - Update version numbers

### Troubleshooting Architecture Issues

**Common Issues**:

1. **Tight Coupling**: Components directly dependent on each other
   - **Solution**: Use service layer pattern, dependency injection

2. **Circular Dependencies**: Components importing each other
   - **Solution**: Refactor to use interfaces, move shared code to utilities

3. **God Objects**: Classes with too many responsibilities
   - **Solution**: Split into smaller, focused classes following SRP

4. **Inconsistent Error Handling**: Different error handling approaches
   - **Solution**: Centralize error handling, use consistent patterns

## Best Practices

### Code Organization
- Follow layered architecture
- Keep business logic in service classes
- Use dependency injection
- Maintain single responsibility principle

### Security
- Always encrypt credentials before storage
- Never log decrypted tokens
- Validate all user inputs
- Use parameterized queries
- Follow principle of least privilege

### Documentation
- Update SDD documents with code changes
- Include code examples in documentation
- Keep diagrams up to date
- Maintain revision history

### Testing
- Unit test business logic
- Integration test API endpoints
- Test error handling paths
- Validate security controls

## Quick Reference

### File Locations
- **SDD Documents**: `docs/` directory (`*.md`)
- **Application Code**: `app.py`, `config_manager.py`, `*_scanner.py`, `*_analyzer.py`
- **Templates**: `templates/` (index.html, config_redesigned.html, results.html, etc.)
- **Database Models**: `models.py`
- **Database Scripts**: `init_db.py`, `migrate_add_pr_submissions.py`
- **Configuration**: `config/app_config.yaml` (main configuration with encrypted tokens)
- **Reports**: `reports/`
- **Cache**: `cache/`
- **Database**: `instance/reports.db` (SQLite)

### Key Classes
- `ConfigManager`: Configuration management with YAML loading and token decryption
- `WebComplianceScanner`: Main scanner orchestrator
- `RemoteRepositoryScanner`: GitHub integration and PR creation
- `EnhancedScanner`: Component-level analysis
- `EndpointAnalyzer`: Runtime endpoint detection
- `Report`: Database model for scan reports
- `PRSubmission`: Database model for PR tracking

### Environment Variables
- `ENCRYPTION_KEY`: Fernet encryption key (required for token encryption/decryption)
- `SECRET_KEY`: Flask secret key (optional, has default)
- `DATABASE_URL`: Database connection string (optional, defaults to SQLite)
- `SSL_VERIFY`: SSL verification for API calls (optional, defaults to false)
- `DEBUG_LOGGING`: Enable debug logging (optional, defaults to true)

**Note**: All endpoint configuration (GitHub, Jenkins, Artifactory) is now stored in `config/app_config.yaml` with encrypted tokens, not in environment variables.

## Support and Maintenance

### Documentation Review Schedule
- **Quarterly**: Full SDD document review
- **As Needed**: Updates for significant changes
- **Pre-Release**: Review before major releases

### Contact
- **Document Owner**: Architecture Team
- **Technical Review**: Development Team
- **User Review**: Product Management and QA

## Skill Capabilities

When this skill is invoked, I can help with:

✅ **Documentation Tasks**:
- Update SDD documents for new features
- Create architecture diagrams
- Document design decisions
- Write API documentation
- Generate code examples

✅ **Architecture Tasks**:
- Review architectural decisions
- Identify design patterns
- Suggest improvements
- Validate component interactions
- Assess security implications

✅ **Planning Tasks**:
- Evaluate feature feasibility
- Identify affected components
- Estimate documentation effort
- Plan refactoring efforts

✅ **Review Tasks**:
- Verify documentation completeness
- Check consistency across documents
- Validate technical accuracy
- Review code examples

## Example Invocations

```
"Update the SDD for the new batch scanning feature"
"Document the credential rotation process"
"Create architecture diagram for the PR creation workflow"
"Review security implications of the new API endpoint"
"Generate API documentation for the new reporting endpoints"
"Document database schema changes for the new feature"
"Update deployment guide for the new encryption requirements"
"Add database migration procedures to the documentation"
```

---

**Skill Version**: 1.1  
**Last Updated**: 2026-06-12  
**Maintained By**: Architecture Team
