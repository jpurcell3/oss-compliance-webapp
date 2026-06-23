# Software Design Document (SDD) Framework
## OSS Compliance Web Application

**Document Version:** 1.2
**Application Version:** 1.0
**Last Updated:** 2026-06-23
**Status:** Active

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2 | 2026-06-23 | System | Added multi-tier caching strategy (frontend sessionStorage + file-based cache), exact match auto-selection for repository search, improved cache hierarchy and invalidation |
| 1.1 | 2026-06-05 | System | Added PR creation workflow, credential encryption, multi-user GitHub support, admin configuration UI |
| 1.0 | 2026-05-29 | System | Initial SDD Framework |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architecture](#3-architecture)
4. [Component Design](#4-component-design)
5. [Data Model](#5-data-model)
6. [Interface Design](#6-interface-design)
7. [Security Design](#7-security-design)
8. [Performance Considerations](#8-performance-considerations)
9. [Scalability Design](#9-scalability-design)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Technology Stack](#11-technology-stack)
12. [Development Standards](#12-development-standards)

---

## 1. Introduction

### 1.1 Purpose
This Software Design Document (SDD) describes the architecture, components, and design decisions for the OSS Compliance Web Application. This document serves as the technical blueprint for implementation, maintenance, and evolution of the system.

### 1.2 Scope
This document covers:
- Overall system architecture and design
- Component interactions and responsibilities
- Data models and database schema
- API interfaces and contracts
- Security mechanisms and controls
- Performance and scalability considerations
- Deployment and infrastructure requirements

### 1.3 Definitions, Acronyms, and Abbreviations
- **OSS**: Open Source Software
- **SDD**: Software Design Document
- **API**: Application Programming Interface
- **PR**: Pull Request
- **CI/CD**: Continuous Integration/Continuous Deployment
- **SLA**: Service Level Agreement

### 1.4 References
- [README.md](README.md) - Project overview and setup
- [USER_GUIDE.md](USER_GUIDE.md) - User documentation
- [ENHANCED_SCAN_GUIDE.md](ENHANCED_SCAN_GUIDE.md) - Enhanced scanning documentation

---

## 2. System Overview

### 2.1 System Purpose
The OSS Compliance Web Application is a Flask-based web application designed to scan software repositories and verify compliance with approved Artifactory virtual repositories. The system helps organizations ensure that open-source software dependencies are sourced through approved artifact repositories rather than direct public sources.

### 2.2 System Goals
- **Compliance Verification**: Automatically detect non-compliant OSS dependencies
- **Remediation Automation**: Provide automated fixes through PR generation
- **Integration Support**: Integrate with GitHub and Jenkins for workflow automation
- **Reporting**: Generate comprehensive compliance reports
- **User-Friendly Interface**: Provide intuitive web-based interface

### 2.3 System Functions

#### 2.3.1 Repository Scanning
- Scan local repositories for compliance issues
- Scan remote GitHub repositories via API
- Support multiple programming languages (Go, Python, Node.js, Java/Maven)
- Enhanced endpoint analysis with runtime evidence

#### 2.3.2 Compliance Analysis
- Detect direct external URL references
- Identify missing proxy configurations
- Verify virtual repository usage
- Generate severity-based findings

#### 2.3.3 PR Submission
- Create automated fix branches
- Generate pull requests with detailed descriptions
- Trigger Jenkins validation pipelines
- Track PR status and outcomes

#### 2.3.4 Reporting
- Generate JSON, Markdown, and specification reports
- Maintain historical scan data
- Export reports in multiple formats
- Provide executive summaries

### 2.4 User Characteristics
- **Compliance Officers**: Need to verify and track compliance across repositories
- **Developers**: Need to understand and fix compliance issues in their code
- **DevOps Engineers**: Need to integrate compliance checks into CI/CD pipelines
- **Repository Owners**: Need to manage and approve compliance fixes

### 2.5 Operating Environment
- **Development**: Local development environments with Python 3.9+
- **Production**: Containerized deployment (Docker) or traditional server deployment
- **Integration**: Requires access to Artifactory, GitHub, and Jenkins instances
- **Network**: Internet connectivity for remote repository scanning

### 2.6 Design and Implementation Constraints
- **Language**: Python 3.9+
- **Framework**: Flask web framework
- **Database**: SQLite (default), upgradable to PostgreSQL
- **Authentication**: Token-based for external services
- **Deployment**: Must support both containerized and traditional deployment

---

## 3. Architecture

### 3.1 Architectural Overview
The system follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                      │
│  (Web Interface - Flask Templates, JavaScript, CSS)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (Flask Routes, Business Logic, Request/Response Handling)  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  (Scanning Services, PR Services, Fix Generation, etc.)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Access Layer                      │
│  (Database Models, File System Operations, External APIs)   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services Layer                   │
│  (GitHub API, Jenkins API, Artifactory, File System)        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Architectural Patterns

#### 3.2.1 MVC Pattern (Model-View-Controller)
- **Model**: Database models in `models.py`
- **View**: HTML templates in `templates/` directory
- **Controller**: Flask routes in `app.py`

#### 3.2.2 Service Layer Pattern
- Business logic separated into service classes
- `ComplianceScanner` - Core scanning logic
- `RemoteRepositoryScanner` - Remote repository operations
- `EnhancedComplianceScanner` - Advanced analysis
- `PRSubmissionService` - PR creation and management
- `FixGenerator` - Automated fix generation

#### 3.2.3 Repository Pattern
- Database access abstracted through SQLAlchemy ORM
- File system operations encapsulated in service classes
- External API calls isolated in dedicated services

### 3.3 System Component Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Web UI     │────▶│  Flask App   │────▶│   Database   │
│  (Templates) │     │   (Routes)   │     │  (SQLite)    │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ├──────────────┐
                            ▼              ▼
                     ┌──────────┐  ┌──────────┐
                     │ Scanner  │  │   PR     │
                     │ Services │  │ Services │
                     └──────────┘  └──────────┘
                            │              │
                            └──────┬───────┘
                                   ▼
                          ┌────────────────┐
                          │ External APIs  │
                          │ (GitHub, Jenkins│
                          │  Artifactory)  │
                          └────────────────┘
```

### 3.4 Technology Stack Rationale

#### 3.4.1 Backend Framework: Flask
- **Lightweight**: Minimal overhead for simple web applications
- **Flexibility**: Easy to extend with custom middleware
- **Ecosystem**: Rich ecosystem of extensions
- **Simplicity**: Low learning curve for development team

#### 3.4.2 Database: SQLite (with PostgreSQL upgrade path)
- **Zero Configuration**: No database server setup required for development
- **Portability**: Single-file database for easy deployment
- **Scalability**: Can upgrade to PostgreSQL for production
- **ORM Support**: Excellent SQLAlchemy support

#### 3.4.3 Frontend: Server-Side Rendering
- **Simplicity**: No complex frontend build process
- **Performance**: Fast initial page load
- **SEO Friendly**: Search engine optimized
- **Progressive Enhancement**: Works without JavaScript

---

## 4. Component Design

### 4.1 Core Components

#### 4.1.1 Flask Application (`app.py`)
**Responsibility**: Main application orchestration and request handling

**Key Functions**:
- Route definitions and request mapping
- Request validation and error handling
- Session management and security
- Integration with service layer

**Key Routes**:
```python
# Scanning endpoints
POST /scan                    # Scan repository
GET  /api/repositories        # List available repositories
POST /api/repositories/refresh # Refresh repository cache

# PR submission endpoints
POST /api/pr/submit           # Create PR with fixes
GET  /api/pr/<id>/status      # Get PR status
GET  /api/pr/submissions      # List PR submissions

# Report endpoints
GET  /reports                 # List all reports
GET  /report/<filename>       # View specific report
GET  /export/<filename>       # Export report
```

#### 4.1.2 Compliance Scanner (`compliance_scanner.py`)
**Responsibility**: Core compliance checking logic

**Key Methods**:
```python
class ComplianceScanner:
    def scan_go_module(file_path, virtual_repos, artifactory_base)
    def scan_python_requirements(file_path, virtual_repos, artifactory_base)
    def scan_node_package(file_path, virtual_repos, artifactory_base)
    def scan_maven_pom(file_path, virtual_repos, artifactory_base)
    def scan_jenkinsfile(file_path, virtual_repos, artifactory_base)
```

**Design Decisions**:
- **File-Based Analysis**: Each file type analyzed independently
- **Pattern Matching**: Uses regex patterns for compliance detection
- **Severity Classification**: Issues classified by impact and risk

#### 4.1.3 Remote Repository Scanner (`remote_scanner.py`)
**Responsibility**: GitHub API integration and remote repository operations

**Key Methods**:
```python
class RemoteRepositoryScanner:
    def get_organization_repositories(force_refresh=False)
    def download_repository_files(repo_name)
    def get_jenkins_build_configs(repo_name)
    def scan_remote_repository(repo_name, use_enhanced=False)
```

**Design Decisions**:
- **Caching**: Repository lists cached to reduce API calls
- **Rate Limiting**: Handles GitHub API rate limits gracefully
- **Error Recovery**: Continues processing on individual file failures

#### 4.1.4 Enhanced Scanner (`enhanced_scanner.py`)
**Responsibility**: Advanced compliance analysis with runtime evidence

**Key Features**:
- **Endpoint Analysis**: Classifies dependency endpoints by type
- **Runtime Evidence**: Analyzes actual usage patterns
- **Reliability Scoring**: Calculates confidence scores for findings
- **Executive Summary**: Generates high-level compliance overview

#### 4.1.5 PR Submission Service (`pr_submission_service.py`)
**Responsibility**: Pull request creation and management

**Key Methods**:
```python
class PRSubmissionService:
    def create_pr_for_fixes(report_data, submitter_username, submitter_email)
    def _create_branch(github_org, repo_name, branch_name, base_branch)
    def _apply_fixes_to_branch(github_org, repo_name, branch_name, report_data)
    def _create_pull_request(github_org, repo_name, branch_name, base_branch, ...)
    def _trigger_jenkins_validation(github_org, repo_name, pr_number)
```

**Design Decisions**:
- **Service Account**: Uses configured service account for all operations
- **Branch Naming**: Timestamp-based branch names to avoid conflicts
- **Error Handling**: Comprehensive error handling with rollback capability
- **Status Tracking**: Database tracking of entire PR lifecycle

#### 4.1.6 Fix Generator (`fix_generator.py`)
**Responsibility**: Automated fix generation for compliance issues

**Key Methods**:
```python
class FixGenerator:
    def generate_fix(content, finding)
    def _fix_go_module(content, finding)
    def _fix_python_requirements(content, finding)
    def _fix_node_package(content, finding)
    def _fix_maven_pom(content, finding)
```

**Design Decisions**:
- **Pattern-Based**: Uses established patterns for common fixes
- **Non-Destructive**: Preserves original file structure and comments
- **Type-Specific**: Different strategies for different file types
- **Fallback**: Returns original content if fix cannot be applied

### 4.2 Component Interactions

#### 4.2.1 Scanning Workflow
```
User Request → Flask Route → Scanner Selection → File Analysis → 
Report Generation → Database Storage → Response to User
```

#### 4.2.2 PR Creation Workflow
```
User Request → Flask Route → PR Service → Branch Creation → 
Fix Application → PR Creation → Jenkins Trigger → 
Database Update → Response to User
```

#### 4.2.3 Remote Scanning Workflow
```
User Request → Flask Route → Remote Scanner → GitHub API → 
File Download → Local Analysis → Report Generation → Cleanup
```

---

## 5. Data Model

### 5.1 Database Schema

#### 5.1.1 Reports Table
```python
class Report(db.Model):
    id: Integer (Primary Key)
    filename: String (255, Unique, Indexed)
    repository_name: String (255, Indexed)
    scan_type: String (50)
    compliance_percentage: Float
    total_findings: Integer
    critical_issues: Integer
    high_issues: Integer
    compliant_items: Integer
    non_compliant_items: Integer
    created_at: DateTime
    file_path: Text
    markdown_path: Text
    github_org: String (255, Indexed)
    github_instance: String (100)
    scan_metadata: Text (JSON)
```

**Rationale**:
- **Indexed Fields**: Frequently queried fields optimized for performance
- **JSON Metadata**: Flexible storage for scan-specific data
- **File References**: Separate storage for large report files

#### 5.1.2 PR Submissions Table
```python
class PRSubmission(db.Model):
    id: Integer (Primary Key)
    report_id: Integer (Foreign Key → reports.id)
    repository_name: String (255, Indexed)
    github_org: String (255, Indexed)
    github_instance: String (100)
    submitter_github_username: String (255)
    submitter_email: String (255)
    pr_number: Integer
    pr_title: String (255)
    pr_url: Text
    branch_name: String (255)
    base_branch: String (100)
    status: String (50)  # pending, created, failed, merged, closed
    github_status: String (50)  # open, merged, closed
    jenkins_status: String (50)  # pending, running, success, failed
    jenkins_job_url: Text
    jenkins_build_number: Integer
    jenkins_build_url: Text
    fixes_applied: Text (JSON)
    error_message: Text
    created_at: DateTime
    updated_at: DateTime
```

**Rationale**:
- **Foreign Key**: Links PR to original compliance report
- **Status Tracking**: Separate status fields for different systems
- **Audit Trail**: Created/updated timestamps for tracking
- **Error Logging**: Error messages preserved for troubleshooting

### 5.2 File Structure

```
oss-compliance-webapp/
├── app.py                      # Main Flask application
├── models.py                   # Database models
├── compliance_scanner.py       # Basic scanning logic
├── remote_scanner.py           # Remote repository operations
├── enhanced_scanner.py         # Advanced analysis
├── pr_submission_service.py    # PR creation and management
├── fix_generator.py            # Automated fix generation
├── markdown_generator.py       # Report generation
├── endpoint_analyzer.py        # Runtime analysis
├── config_enumerator.py        # Configuration discovery
├── pipeline_scanner.py         # Pipeline analysis
├── init_db.py                  # Database initialization
├── migrate_add_pr_submissions.py # Database migration
├── requirements.txt            # Python dependencies
├── .env.example               # Configuration template
├── templates/                 # HTML templates
│   ├── index.html            # Home page
│   ├── results.html          # Scan results
│   ├── reports.html          # Report list
│   └── config.html           # Configuration page
├── reports/                   # Generated reports (auto-created)
├── uploads/                   # Uploaded files (auto-created)
├── config/                    # Configuration files (auto-created)
└── cache/                     # Repository cache (auto-created)
```

### 5.3 Data Flow

#### 5.3.1 Scan Data Flow
```
Repository Files → Scanner Analysis → Findings Generation → 
Report Assembly → File Storage → Database Record → User Display
```

#### 5.3.2 PR Data Flow
```
Compliance Report → Fix Generation → Branch Creation → 
File Modifications → PR Creation → Jenkins Trigger → 
Status Tracking → Database Update
```

---

## 6. Interface Design

### 6.1 User Interfaces

#### 6.1.1 Main Interface (Home Page)
**Purpose**: Repository scanning initiation

**Key Elements**:
- Scan type selection (Local/Remote/Team)
- Repository path/input fields
- Scan method selection (Basic/Enhanced)
- GitHub instance selection
- Repository selection (for remote scans)
- Repository search with exact match auto-selection
- Start scan button

**Repository Search Features**:
- **Real-time Filtering**: Local filtering of repository list as user types
- **Exact Match Auto-Selection**: When search term exactly matches one repository name, that repository is automatically selected
- **Partial Match Display**: Shows repositories containing the search term without auto-selection
- **Case-Insensitive Matching**: Search works regardless of letter case
- **Search Behavior**:
  - Single exact match → Auto-selects repository radio button
  - Multiple matches → Filters list but no auto-selection
  - No matches → Shows empty list
  - Partial matches → Filters list but no auto-selection

#### 6.1.2 Results Interface
**Purpose**: Display scan findings and recommendations

**Key Elements**:
- Executive summary with compliance metrics
- Critical issues alert box
- Ecosystem breakdown cards
- Detailed findings list
- Recommended actions
- Export options (JSON/Markdown/Spec)
- PR creation button

#### 6.1.3 Reports Interface
**Purpose**: Historical report management

**Key Elements**:
- Report list with filtering
- Report metadata display
- Export and delete options
- Date and repository sorting

#### 6.1.4 Configuration Interface
**Purpose**: System configuration management

**Key Elements**:
- Virtual repository configuration
- GitHub instance management
- Jenkins connection settings
- Whitelist URL management

### 6.2 API Interfaces

#### 6.2.1 Scanning APIs
```python
POST /scan
Request: {
    "scan_type": "local|remote|team",
    "repo_input": "path or repository names",
    "use_enhanced": true|false,
    "github_instance": "instance_id"
}
Response: {
    "report": {...},
    "report_filename": "string",
    "markdown_filename": "string"
}
```

#### 6.2.2 PR Submission APIs
```python
POST /api/pr/submit
Request: {
    "report_filename": "string",
    "submitter_username": "string",
    "submitter_email": "string",
    "github_instance": "string"
}
Response: {
    "success": true|false,
    "pr_submission": {...},
    "pr_result": {...}
}
```

#### 6.2.3 Repository APIs
```python
GET /api/repositories?github_instance=instance_id&search=term
Response: {
    "repositories": ["repo1", "repo2", ...]
}
```

### 6.3 External Service Interfaces

#### 6.3.1 GitHub API Integration
**Authentication**: Token-based authentication
**Rate Limiting**: Implements exponential backoff
**Error Handling**: Graceful degradation on API failures

**Key Endpoints Used**:
- `GET /orgs/{org}/repos` - List organization repositories
- `GET /repos/{org}/{repo}/contents/{path}` - Get file contents
- `POST /repos/{org}/{repo}/git/refs` - Create branches
- `PUT /repos/{org}/{repo}/contents/{path}` - Update files
- `POST /repos/{org}/{repo}/pulls` - Create pull requests

#### 6.3.2 Jenkins API Integration
**Authentication**: Basic authentication with API token
**Job Triggering**: Parameterized job triggering
**Status Monitoring**: Build status polling

**Key Endpoints Used**:
- `GET /api/json` - Get Jenkins server information
- `POST /job/{job_name}/buildWithParameters` - Trigger parameterized builds
- `GET /queue/item/{id}/api/json` - Get queue item status

---

## 7. Security Design

### 7.1 Authentication and Authorization

#### 7.1.1 External Service Authentication
- **GitHub**: Personal access tokens with appropriate scopes
- **Jenkins**: API tokens with job build permissions
- **Artifactory**: API keys for repository access (if needed)

**Token Storage**:
- Environment variables for sensitive data
- Never logged or displayed in error messages
- Rotation capability for security compliance

#### 7.1.2 User Authentication
- **Current Implementation**: No built-in user authentication
- **Future Enhancement**: LDAP/SSO integration planned
- **Access Control**: Network-level restrictions recommended

### 7.2 Data Protection

#### 7.2.1 Sensitive Data Handling
- **Tokens**: Stored in environment variables only
- **Credentials**: Never written to logs or reports
- **Personal Information**: Submitter information stored in database

#### 7.2.2 Data Encryption

**Encryption in Transit**:
- **HTTPS**: TLS 1.2+ recommended for production
- **API Calls**: All external API calls use HTTPS

**Encryption at Rest** (v0.5.0):
- **Database**: SQLite/PostgreSQL encryption optional
- **Credential Encryption**: Fernet symmetric encryption for all API tokens

**Credential Encryption Implementation** (v0.5.0):

```python
from cryptography.fernet import Fernet
import os

class CredentialManager:
    def __init__(self):
        # Get or generate encryption key
        self.encryption_key = os.getenv('ENCRYPTION_KEY')
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
        self.cipher = Fernet(self.encryption_key.encode())
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token for use"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
```

**Encryption Workflow**:
1. **Key Generation**: ENCRYPTION_KEY generated once and stored in environment
2. **Token Encryption**: All GitHub/Jenkins tokens encrypted before storage
3. **Secure Storage**: Encrypted tokens stored in .env file
4. **Runtime Decryption**: Tokens decrypted only when needed for API calls
5. **No Logging**: Decrypted tokens never logged or displayed

**Security Properties**:
- **Algorithm**: Fernet (AES-128 in CBC mode with HMAC for authentication)
- **Key Size**: 32-byte URL-safe base64-encoded key
- **Authentication**: Built-in message authentication (HMAC)
- **Timestamp**: Encryption includes timestamp for freshness verification

### 7.3 Input Validation

#### 7.3.1 File Path Validation
- **Directory Traversal Prevention**: Path sanitization
- **File Type Validation**: Extension checking
- **Size Limits**: Maximum file size enforcement

#### 7.3.2 API Input Validation
- **Type Checking**: Parameter type validation
- **Length Limits**: String length restrictions
- **Pattern Validation**: Format validation for URLs, emails

### 7.4 Error Handling

#### 7.4.1 Error Message Security
- **No Stack Traces**: Detailed errors only in debug mode
- **Sanitized Messages**: User-facing errors sanitized
- **Logging**: Detailed errors logged server-side

#### 7.4.2 Exception Handling
- **Graceful Degradation**: Partial failures don't crash system
- **Retry Logic**: Automatic retry for transient failures
- **User Feedback**: Clear error messages for users

---

## 8. Performance Considerations

### 8.1 Performance Requirements
- **Scan Time**: Local scans < 30 seconds, Remote scans < 2 minutes
- **Response Time**: API responses < 500ms (excluding external calls)
- **Concurrent Users**: Support 10+ concurrent scanning operations
- **Database Queries**: All queries < 100ms with proper indexing

### 8.2 Performance Optimization Strategies

#### 8.2.1 Caching
- **Repository Cache**: Multi-tier caching strategy for optimal performance
  - **Frontend sessionStorage**: Browser-based caching for page reload persistence
  - **File-based Cache**: Server-side cache with 24-hour TTL for repository lists
  - **Cache Hierarchy**: Frontend cache checked first, falls back to file cache
- **Scan Results**: Database storage for historical data
- **Static Assets**: Browser caching for CSS/JS files

**Cache Behavior**:
- **Frontend sessionStorage**: Persists across page reloads within browser session
- **File Cache**: Reduces GitHub API calls with 24-hour TTL
- **Cache Invalidation**: Manual refresh clears all cache layers
- **Cache Keys**: GitHub instance-specific cache keys for multi-instance support

#### 8.2.2 Database Optimization
- **Indexing**: Frequently queried fields indexed
- **Query Optimization**: Efficient ORM query construction
- **Connection Pooling**: SQLAlchemy connection pooling

#### 8.2.3 API Rate Limiting
- **GitHub API**: Implements rate limit handling
- **Exponential Backoff**: Automatic retry with increasing delays
- **Request Batching**: Minimizes API calls through batching

### 8.3 Resource Management

#### 8.3.1 Memory Management
- **File Cleanup**: Automatic cleanup of temporary files
- **Stream Processing**: Large files processed in streams
- **Object Lifecycle**: Proper object disposal and cleanup

#### 8.3.2 Disk Space Management
- **Report Rotation**: Optional automatic report cleanup
- **Cache Management**: Configurable cache size limits
- **Temporary Files**: Automatic cleanup after processing

---

## 9. Scalability Design

### 9.1 Horizontal Scaling

#### 9.1.1 Stateless Design
- **Session Storage**: Client-side or external session storage
- **File Storage**: External file storage for reports
- **Database**: External database for multi-instance deployment

#### 9.1.2 Load Balancing
- **Application Layer**: HTTP load balancer support
- **Database Layer**: Connection pooling and read replicas
- **Cache Layer**: Distributed caching for multi-instance scenarios

### 9.2 Vertical Scaling

#### 9.2.1 Resource Optimization
- **Async Processing**: Background task processing for long operations
- **Connection Limits**: Configurable connection pool sizes
- **Memory Limits**: Configurable memory constraints

#### 9.2.2 Database Scaling
- **SQLite to PostgreSQL**: Migration path for larger deployments
- **Partitioning**: Table partitioning for large report datasets
- **Archiving**: Automated archival of old reports

### 9.3 Growth Accommodation

#### 9.3.1 Repository Scaling
- **Pagination**: Large repository lists paginated
- **Caching Strategy**: Intelligent cache invalidation
- **Parallel Processing**: Concurrent repository scanning

#### 9.3.2 Report Scaling
- **Compression**: Report file compression for storage
- **Indexing**: Efficient report search and filtering
- **Archival**: Automated archival of historical reports

---

## 10. Deployment Architecture

### 10.1 Development Environment
```
Developer Machine → Local Python Environment → SQLite Database → Local File System
```

### 10.2 Production Environment

#### 10.2.1 Containerized Deployment (Recommended)
```
┌─────────────┐
│   Nginx     │ ← Reverse Proxy & SSL Termination
└─────────────┘
       │
       ▼
┌─────────────┐
│   Docker    │ ← Application Container
└─────────────┘
       │
       ├──────────────┐
       ▼              ▼
┌─────────────┐ ┌─────────────┐
│ PostgreSQL  │ │  File Store │ ← External Services
└─────────────┘ └─────────────┘
```

#### 10.2.2 Traditional Deployment
```
Load Balancer → Web Server (Apache/Nginx) → WSGI Server (Gunicorn) → Flask App → PostgreSQL
```

### 10.3 Infrastructure Requirements

#### 10.3.1 Minimum Requirements
- **CPU**: 2 cores
- **Memory**: 4GB RAM
- **Disk**: 20GB SSD
- **Network**: 1 Gbps

#### 10.3.2 Recommended Requirements
- **CPU**: 4+ cores
- **Memory**: 8GB+ RAM
- **Disk**: 50GB+ SSD
- **Network**: 1+ Gbps
- **Backup**: Regular database backups

### 10.4 Monitoring and Logging

#### 10.4.1 Application Monitoring
- **Health Checks**: `/health` endpoint
- **Performance Metrics**: Response time tracking
- **Error Tracking**: Exception monitoring

#### 10.4.2 Logging Strategy
- **Application Logs**: Flask application logs
- **Access Logs**: HTTP request logging
- **Error Logs**: Separate error log files
- **Audit Logs**: PR submission tracking

---

## 11. Technology Stack

### 11.1 Backend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.9+ | Primary programming language |
| Flask | 2.3.3 | Web framework |
| SQLAlchemy | 2.0+ | ORM and database toolkit |
| PyYAML | 6.0.1 | YAML configuration parsing |
| Requests | 2.31.0 | HTTP client for API calls |
| python-dotenv | 1.0.0 | Environment variable management |

### 11.2 Frontend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| HTML5 | - | Page structure |
| CSS3 | - | Styling (Tailwind CSS via CDN) |
| JavaScript | ES6+ | Client-side interactivity |
| Chart.js | Latest | Data visualization |

### 11.3 Database Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| SQLite | 3.x | Development database (default) |
| PostgreSQL | 14+ | Production database (optional) |

### 11.4 Deployment Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Docker | Latest | Containerization |
| Docker Compose | Latest | Multi-container orchestration |
| Nginx | Latest | Reverse proxy and static file serving |
| Gunicorn | Latest | WSGI HTTP server |

### 11.5 External Dependencies

| Service | Purpose | Integration Method |
|---------|---------|-------------------|
| GitHub API | Repository operations | REST API |
| Jenkins API | Pipeline integration | REST API |
| Artifactory | Artifact repository | HTTP/HTTPS |

---

## 12. Development Standards

### 12.1 Coding Standards

#### 12.1.1 Python Code Style
- **PEP 8**: Follow Python style guide
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Google-style docstrings for functions
- **Line Length**: Maximum 100 characters per line

#### 12.1.2 Naming Conventions
- **Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_CASE
- **Private Members**: _leading_underscore

### 12.2 Version Control

#### 12.2.1 Git Workflow
- **Branch Strategy**: Feature branch workflow
- **Commit Messages**: Conventional commit format
- **Code Review**: Required for all changes
- **Branch Naming**: `feature/description`, `fix/description`

#### 12.2.2 Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

**Types**: feat, fix, docs, style, refactor, test, chore

### 12.3 Testing Standards

#### 12.3.1 Test Coverage
- **Unit Tests**: Core business logic
- **Integration Tests**: API endpoints
- **End-to-End Tests**: Critical user workflows
- **Target Coverage**: 80%+ code coverage

#### 12.3.2 Testing Framework
- **Framework**: pytest
- **Mocking**: unittest.mock for external dependencies
- **Fixtures**: pytest fixtures for test setup
- **CI Integration**: Automated test execution

### 12.4 Documentation Standards

#### 12.4.1 Code Documentation
- **Function Docstrings**: Purpose, parameters, return values
- **Class Docstrings**: Class purpose and usage
- **Module Docstrings**: Module overview and exports
- **Inline Comments**: Complex logic explanation

#### 12.4.2 API Documentation
- **Endpoint Documentation**: Purpose, parameters, responses
- **Error Codes**: Standardized error responses
- **Examples**: Usage examples for each endpoint
- **Versioning**: API versioning strategy

### 12.5 Security Standards

#### 12.5.1 Code Security
- **Input Validation**: All user inputs validated
- **Output Encoding**: Proper output encoding to prevent XSS
- **SQL Injection**: Parameterized queries only
- **Dependency Updates**: Regular security dependency updates

#### 12.5.2 Secret Management
- **No Hardcoded Secrets**: All secrets in environment variables
- **Secret Rotation**: Regular secret rotation procedures
- **Access Control**: Principle of least privilege
- **Audit Trail**: Secret access logging

---

## Appendix

### A. Configuration Reference
See [USER_GUIDE.md](USER_GUIDE.md) for detailed configuration instructions

### B. API Endpoint Reference
See [API_REFERENCE.md](API_REFERENCE.md) for complete API documentation

### C. Database Schema Reference
See section 5. Data Model for detailed schema information

### D. Error Code Reference
See [API_REFERENCE.md](API_REFERENCE.md#Error Codes) for complete error code listing

### E. Performance Metrics
See section 8. Performance Considerations for performance requirements and metrics

### F. Deployment Checklist
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for comprehensive deployment instructions

### G. Supporting Documents
- **[HLD.md](HLD.md)** - High-Level Design document with system context and architecture
- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive user documentation
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API reference
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Deployment and operations guide
- **[README.md](README.md)** - Project overview and quick start
- **[ENHANCED_SCAN_GUIDE.md](ENHANCED_SCAN_GUIDE.md)** - Enhanced scanning documentation

---

**Document Status**: Draft  
**Next Review Date**: 2026-06-29  
**Approved By**: Pending  
**Distribution**: Development Team, Architecture Team, Operations Team