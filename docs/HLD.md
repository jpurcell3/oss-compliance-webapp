# High-Level Design (HLD)
## OSS Compliance Web Application

**Document Version:** 1.1  
**Application Version:** 0.5.0  
**Last Updated:** 2026-06-05  
**Status:** Active  
**Classification:** Internal

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-06-05 | System | Added PR creation workflow, credential encryption, multi-user GitHub support, admin configuration UI |
| 1.0 | 2026-05-29 | System | Initial High-Level Design |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Context](#2-system-context)
3. [Architecture Overview](#3-architecture-overview)
4. [Key Components](#4-key-components)
5. [Data Flow](#5-data-flow)
6. [Technology Stack](#6-technology-stack)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Security Architecture](#8-security-architecture)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Integration Points](#10-integration-points)

---

## 1. Introduction

### 1.1 Purpose
This High-Level Design (HLD) document provides a comprehensive overview of the OSS Compliance Web Application architecture. It focuses on system context, major components, data flows, and key architectural decisions without delving into implementation details.

### 1.2 Scope
This document covers:
- System context and boundaries
- High-level architecture and component relationships
- Major data flows and interactions
- Technology choices and rationale
- Non-functional requirements
- Security architecture at a high level
- Deployment architecture
- Integration points with external systems

### 1.3 Audience
- **Stakeholders**: Product managers, business analysts
- **Architects**: System architects, solution architects
- **Developers**: Development team leads
- **Operations**: DevOps engineers, system administrators
- **Security**: Security architects, compliance officers

### 1.4 References
- [SDD_FRAMEWORK.md](SDD_FRAMEWORK.md) - Detailed Software Design Document
- [USER_GUIDE.md](USER_GUIDE.md) - User documentation
- [API_REFERENCE.md](API_REFERENCE.md) - API documentation

---

## 2. System Context

### 2.1 Business Problem
Organizations need to ensure that open-source software (OSS) dependencies are sourced through approved artifact repositories rather than direct public sources. This is critical for:
- **Security**: Preventing supply chain attacks
- **Compliance**: Meeting regulatory requirements
- **Governance**: Maintaining control over software dependencies
- **Reliability**: Ensuring availability of dependencies

### 2.2 Solution Overview
The OSS Compliance Web Application provides:
- **Automated Scanning**: Scans repositories for compliance issues
- **Intelligent Analysis**: Enhanced endpoint analysis with runtime evidence
- **Automated Remediation**: PR generation with compliance fixes
- **Integration**: Seamless integration with GitHub and Jenkins
- **Reporting**: Comprehensive compliance reports and dashboards

### 2.3 System Boundaries

#### In Scope
- Repository scanning (local and remote)
- Compliance analysis and reporting
- PR creation and management
- Jenkins pipeline integration
- User interface for compliance management
- Database storage for reports and metadata

#### Out of Scope
- Repository hosting and management
- Artifactory administration
- User authentication and authorization (future enhancement)
- CI/CD pipeline orchestration beyond Jenkins triggering
- Dependency vulnerability scanning (separate tool)

### 2.4 Actors and Interactions

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Compliance  │────▶│   OSS       │────▶│   GitHub    │
│  Officer    │     │ Compliance  │     │   API       │
│             │     │    Web App  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ├─────────────┐
                           ▼             ▼
                    ┌─────────────┐ ┌─────────────┐
                    │ Artifactory │ │  Jenkins    │
                    │             │ │    API      │
                    └─────────────┘ └─────────────┘
```

#### Actor Definitions
- **Compliance Officer**: Reviews compliance reports and manages remediation
- **Developer**: Reviews compliance findings and implements fixes
- **DevOps Engineer**: Integrates compliance checks into CI/CD pipelines
- **Repository Owner**: Approves and manages compliance PRs
- **System**: Automated processes for scanning and PR creation

---

## 3. Architecture Overview

### 3.1 Architectural Style
The system follows a **layered web application architecture** with the following characteristics:

- **Client-Server Model**: Web browser client accessing server-side application
- **Layered Architecture**: Clear separation between presentation, application, service, and data layers
- **Stateless Design**: Application servers are stateless for horizontal scalability
- **Service-Oriented**: Modular service components with well-defined interfaces

### 3.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  (Web Browser - User Interface for Compliance Management)        │
└─────────────────────────────────────────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  (Flask Templates + JavaScript - Web UI Rendering)              │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                          │
│  (Flask Routes + Business Logic - Request/Response Handling)    │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                             │
│  (Scanning Services + PR Services + Fix Generation)             │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA ACCESS LAYER                          │
│  (Database Models + File System + External API Clients)          │
└─────────────────────────────────────────────────────────────────┘
                                   │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ PostgreSQL  │ │ File System │ │ External    │
            │  Database   │ │ (Reports)   │ │  APIs       │
            └─────────────┘ └─────────────┘ └─────────────┘
```

### 3.3 Key Architectural Decisions

#### Decision 1: Layered Architecture
**Rationale**: Separation of concerns, maintainability, testability
**Trade-off**: Slight performance overhead vs. improved organization

#### Decision 2: Service Layer Pattern
**Rationale**: Business logic isolation, reusability, testing
**Trade-off**: Additional complexity vs. better code organization

#### Decision 3: Stateless Design
**Rationale**: Horizontal scalability, fault tolerance
**Trade-off**: External session storage requirement

#### Decision 4: SQLite to PostgreSQL Path
**Rationale**: Development simplicity with production scalability
**Trade-off**: Migration complexity vs. deployment flexibility

### 3.4 Architectural Principles

1. **Separation of Concerns**: Each layer has distinct responsibilities
2. **Loose Coupling**: Components interact through well-defined interfaces
3. **High Cohesion**: Related functionality grouped together
4. **Open/Closed Principle**: Open for extension, closed for modification
5. **Single Responsibility**: Each component has one reason to change

---

## 4. Key Components

### 4.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         WEB APPLICATION                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Web UI     │  │   Flask App  │  │  Database    │          │
│  │  (Templates) │  │   (Routes)   │  │   (SQLite/   │          │
│  │              │  │              │  │ PostgreSQL)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │              SERVICE LAYER                            │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │     │
│  │  │  Scanner   │ │    PR      │ │    Fix     │       │     │
│  │  │  Services  │ │  Services  │ │ Generator  │       │     │
│  │  └────────────┘ └────────────┘ └────────────┘       │     │
│  └──────────────────────────────────────────────────────┘     │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │            EXTERNAL INTEGRATION LAYER                 │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │     │
│  │  │   GitHub   │ │  Jenkins   │ │Artifactory │       │     │
│  │  │    API     │ │    API     │ │   Config   │       │     │
│  │  └────────────┘ └────────────┘ └────────────┘       │     │
│  └──────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Descriptions

#### 4.2.1 Web UI Component
**Purpose**: User interface for compliance management
**Responsibilities**:
- Display scan results and reports
- Collect user input for scanning and PR creation
- Present configuration options
- Show system status and alerts

**Key Interfaces**:
- User input forms
- Dashboard displays
- Report visualization

#### 4.2.2 Flask Application Component
**Purpose**: Web application orchestration
**Responsibilities**:
- HTTP request handling
- Route management
- Session management
- Error handling
- Response formatting

**Key Interfaces**:
- REST API endpoints
- Web page routes
- Static file serving

#### 4.2.3 Database Component
**Purpose**: Data persistence and retrieval
**Responsibilities**:
- Store scan reports and metadata
- Track PR submissions and status
- Maintain configuration data
- Provide query capabilities

**Key Interfaces**:
- CRUD operations
- Query interfaces
- Relationship management

#### 4.2.4 Scanner Services Component
**Purpose**: Compliance scanning logic
**Responsibilities**:
- Local repository scanning
- Remote repository scanning
- Enhanced endpoint analysis
- Compliance rule evaluation

**Key Interfaces**:
- Scan initiation
- Result generation
- Report creation

#### 4.2.5 PR Services Component
**Purpose**: Pull request creation and management
**Responsibilities**:
- Branch creation
- Fix application
- PR creation
- Status tracking
- Jenkins integration

**Key Interfaces**:
- PR submission
- Status queries
- Jenkins triggering

#### 4.2.6 Fix Generator Component
**Purpose**: Automated compliance fix generation
**Responsibilities**:
- Analyze compliance issues
- Generate appropriate fixes
- Apply fixes to files
- Handle different file types

**Key Interfaces**:
- Fix generation
- File modification
- Type-specific handling

### 4.3 Component Interactions

#### 4.3.1 Scanning Interaction Flow
```
User → Web UI → Flask App → Scanner Service → Repository Files
                                              ↓
Scanner Service → Database ← Flask App → Web UI → User
```

#### 4.3.2 PR Creation Interaction Flow
```
User → Web UI → Flask App → PR Service → GitHub API
                                   ↓
PR Service → Fix Generator → File Modifications → GitHub API
                                   ↓
PR Service → Jenkins API → Database ← Flask App → Web UI → User
```

---

## 5. Data Flow

### 5.1 Scanning Data Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │───▶│   Web    │───▶│  Flask   │───▶│ Scanner  │
│ Request  │    │   UI     │    │   App    │    │ Service  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                   │
                                                   ▼
                                            ┌──────────┐
                                            │ Repository│
                                            │   Files   │
                                            └──────────┘
                                                   │
                                                   ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Scan    │◀───│  Report  │◀───│ Database │◀───│  Scan    │
│ Results  │    │ Storage  │    │          │    │ Analysis │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 5.2 PR Creation Data Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │───▶│   Web    │───▶│  Flask   │───▶│   PR     │
│ Request  │    │   UI     │    │   App    │    │ Service  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                   │
                    ┌──────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│   Fix    │ │  GitHub  │ │  Jenkins │
│ Generator│ │   API    │ │   API    │
└──────────┘ └──────────┘ └──────────┘
        │           │           │
        └───────────┼───────────┘
                    ▼
            ┌──────────┐
            │ Database │
            └──────────┘
                    │
                    ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│   PR     │◀───│  Flask   │◀───│  Status  │
│ Status   │    │   App    │    │  Update  │
└──────────┘    └──────────┘    └──────────┘
```

### 5.3 Enhanced PR Creation Workflow (v0.5.0)

The PR creation workflow has been significantly enhanced with multi-user support, credential encryption, and GitHub Enterprise compliance:

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User Initiates PR Creation from Scan Results              │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. System Identifies GitHub Instance from Scan Metadata      │
│    - Matches API URL and Organization                        │
│    - Retrieves encrypted user credentials                    │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Multi-User Selection (if multiple users configured)       │
│    - Display dropdown modal with available users             │
│    - User selects GitHub identity for PR creation            │
│    - Decrypt selected user's token                           │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. GitHub API Authentication & Repository Access             │
│    - Fetch authenticated user info (GET /user)               │
│    - Get repository details (GET /repos/{org}/{repo})        │
│    - Verify write permissions                                │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Branch Creation with Compliant Naming                     │
│    - Format: usr/{username}/oss-compliance-fixes-{timestamp} │
│    - Complies with GitHub Enterprise pre-receive hooks       │
│    - Based on default branch SHA                             │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Generate Compliance Artifacts                             │
│    - oss_compliance_setup.sh (environment setup script)      │
│    - OSS_COMPLIANCE_README.md (quick start guide)            │
│    - OSS_COMPLIANCE_REPORT.md (detailed analysis)            │
│    - OSS_COMPLIANCE_SPEC.json (automation spec)              │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. Commit Files to Branch                                    │
│    - Base64 encode file contents                             │
│    - PUT /repos/{org}/{repo}/contents/{path}                 │
│    - Individual commits for each file                        │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 8. Create Pull Request                                       │
│    - Title: "Fix: Implement OSS Compliance Endpoints"        │
│    - Body: Detailed description with file list               │
│    - Base: default branch, Head: compliance fixes branch     │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 9. Return PR URL to User                                     │
│    - Display success message with PR link                    │
│    - Open PR in new browser tab                              │
└──────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Multi-User Support**: Multiple GitHub users per instance with dropdown selection
- **Credential Encryption**: Fernet symmetric encryption for all tokens
- **Branch Naming Compliance**: Follows GitHub Enterprise pre-receive hook requirements
- **Comprehensive Artifacts**: Includes setup scripts, documentation, and automation specs
- **Error Handling**: Detailed logging and user-friendly error messages at each step

### 5.4 External System Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    OSS COMPLIANCE APP                        │
└─────────────────────────────────────────────────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   GitHub    │   │  Jenkins    │   │ Artifactory │
│  Enterprise │   │   Server    │   │   Server    │
└─────────────┘   └─────────────┘   └─────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Repository  │   │ Build Jobs  │   │ Virtual     │
│   Data      │   │  Execution  │   │  Repos      │
└─────────────┘   └─────────────┘   └─────────────┘
```

---

## 6. Technology Stack

### 6.1 Technology Rationale

#### Backend Framework: Flask
**Selected**: Flask 2.3.3
**Rationale**: 
- Lightweight and minimal overhead
- Flexible and extensible architecture
- Large ecosystem and community support
- Easy to learn and maintain

**Alternatives Considered**: Django, FastAPI
**Trade-off**: Less built-in functionality vs. greater flexibility

#### Database: SQLite/PostgreSQL
**Selected**: SQLite (development), PostgreSQL (production)
**Rationale**:
- SQLite: Zero configuration, portable, sufficient for development
- PostgreSQL: Production-grade, scalable, excellent ORM support
- Easy migration path between them

**Alternatives Considered**: MySQL, MongoDB
**Trade-off**: PostgreSQL's advanced features vs. simplicity

#### Frontend: Server-Side Rendering
**Selected**: Flask templates with vanilla JavaScript
**Rationale**:
- Simplicity in development and deployment
- Fast initial page load
- SEO-friendly
- Progressive enhancement possible

**Alternatives Considered**: React, Vue.js, Angular
**Trade-off**: Less interactive vs. simpler architecture

#### External APIs: REST
**Selected**: RESTful API integration
**Rationale**:
- Standardized approach
- Wide adoption and tooling support
- Stateless and scalable
- Easy to debug and test

**Alternatives Considered**: GraphQL, gRPC
**Trade-off**: Less flexible queries vs. simplicity

### 6.2 Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Backend** | Python | 3.9+ | Application runtime |
| | Flask | 2.3.3 | Web framework |
| | SQLAlchemy | 2.0+ | ORM and database toolkit |
| **Database** | SQLite | 3.x | Development database |
| | PostgreSQL | 14+ | Production database |
| **Frontend** | HTML5/CSS3 | - | User interface |
| | JavaScript | ES6+ | Client-side logic |
| | Tailwind CSS | 2.2.19 | Styling framework |
| **External APIs** | GitHub API | v3 | Repository operations |
| | Jenkins API | - | Pipeline integration |
| **Deployment** | Docker | Latest | Containerization |
| | Nginx | Latest | Reverse proxy |
| | Gunicorn | Latest | WSGI server |

---

## 7. Non-Functional Requirements

### 7.1 Performance Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Local Scan Time | < 30 seconds | End-to-end scan duration |
| Remote Scan Time | < 2 minutes | End-to-end scan duration |
| API Response Time | < 500ms | API endpoint response |
| Concurrent Users | 10+ simultaneous | Concurrent scanning operations |
| Database Query Time | < 100ms | Database query performance |

### 7.2 Scalability Requirements

| Requirement | Target | Approach |
|-------------|--------|----------|
| Horizontal Scaling | Support multiple instances | Stateless design |
| Vertical Scaling | Support increased resources | Efficient resource usage |
| Database Scaling | Support large datasets | PostgreSQL upgrade path |
| File Storage | Support large report volumes | External storage option |

### 7.3 Availability Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| System Uptime | 99% (monthly) | Downtime tracking |
| Recovery Time | < 1 hour | Disaster recovery |
| Data Backup | Daily | Backup frequency |
| Data Retention | 90 days | Report retention policy |

### 7.4 Security Requirements

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| Authentication | Token-based (external) | GitHub/Jenkins tokens |
| Authorization | Role-based (future) | User roles and permissions |
| Data Encryption | TLS 1.2+ | HTTPS encryption |
| Input Validation | All inputs | Parameter validation |
| Secret Management | Environment variables | No hardcoded secrets |

### 7.5 Maintainability Requirements

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| Code Quality | PEP 8 compliant | Linting and formatting |
| Documentation | Comprehensive | Inline and external docs |
| Testing | 80%+ coverage | Unit and integration tests |
| Monitoring | Health checks | Application monitoring |
| Logging | Structured logs | Centralized logging |

---

## 8. Security Architecture

### 8.1 Security Overview

The application implements a **defense-in-depth** security approach:

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Network   │  │ Application │  │    Data     │          │
│  │  Security   │  │  Security   │  │  Security   │          │
│  │  (HTTPS)    │  │ (Validation)│  │ (Encryption)│          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Network Security
- **TLS/SSL**: All communications encrypted with TLS 1.2+
- **Firewall**: Network-level access controls
- **DMZ**: Application servers in DMZ where applicable

### 8.3 Application Security
- **Input Validation**: All user inputs validated and sanitized
- **Output Encoding**: Proper encoding to prevent XSS
- **SQL Injection Prevention**: Parameterized queries only
- **CSRF Protection**: Token-based CSRF protection (future)

### 8.4 Data Security
- **Encryption at Rest**: Database encryption (optional)
- **Encryption in Transit**: TLS for all data transmission
- **Secret Management**: Environment variables for sensitive data
- **Access Control**: Principle of least privilege
- **Credential Encryption** (v0.5.0): Fernet symmetric encryption for all API tokens

### 8.5 Credential Encryption Architecture (v0.5.0)

The application implements **Fernet symmetric encryption** for secure credential storage:

```
┌──────────────────────────────────────────────────────────────┐
│                  CREDENTIAL ENCRYPTION FLOW                   │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. Admin Enters Credentials in UI                            │
│    - GitHub tokens, Jenkins tokens, etc.                     │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Encryption Key Generation/Retrieval                       │
│    - ENCRYPTION_KEY from environment variable                │
│    - Fernet.generate_key() if not exists                     │
│    - 32-byte URL-safe base64-encoded key                     │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Token Encryption                                           │
│    - Fernet(key).encrypt(token.encode())                     │
│    - Returns encrypted token as base64 string                │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Encrypted Storage in .env File                            │
│    - GITHUB_INSTANCE_{name}_USERS={"user": {"token": "..."}} │
│    - JENKINS_TOKEN=gAAAAA...                                  │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Runtime Decryption (when needed)                          │
│    - Fernet(key).decrypt(encrypted_token)                    │
│    - Used for API calls only, never logged                   │
└──────────────────────────────────────────────────────────────┘
```

**Security Features**:
- **Symmetric Encryption**: Fernet (AES-128 in CBC mode with HMAC)
- **Key Management**: Environment variable (ENCRYPTION_KEY)
- **Secure Storage**: Encrypted tokens in .env file
- **Runtime Decryption**: Tokens decrypted only when needed
- **No Plaintext Logging**: Tokens never logged in plaintext

**Key Rotation**: To rotate encryption key:
1. Generate new ENCRYPTION_KEY
2. Re-encrypt all existing tokens
3. Update .env file with new encrypted values

### 8.6 External Service Security
- **Token-Based Authentication**: Secure tokens for external APIs
- **Token Rotation**: Regular token rotation procedures
- **Rate Limiting**: Respect external API rate limits
- **Error Handling**: Secure error messages without sensitive data

---

## 9. Deployment Architecture

### 9.1 Development Architecture

```
Developer Workstation
├── Python 3.9+ Environment
├── SQLite Database
├── Local File System
└── Direct Execution
```

### 9.2 Production Architecture

```
                    ┌─────────────┐
                    │   Internet  │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Load Balancer│
                    │   (Nginx)   │
                    └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │  App #1  │  │  App #2  │  │  App #N  │
       │ (Flask)  │  │ (Flask)  │  │ (Flask)  │
       └──────────┘  └──────────┘  └──────────┘
              │            │            │
              └────────────┼────────────┘
                           ▼
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │  Database   │
                    └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │  File    │  │  Cache   │  │  Backup  │
       │ Storage  │  │  Server  │  │  System  │
       └──────────┘  └──────────┘  └──────────┘
```

### 9.3 Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Host                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Nginx     │  │   Flask     │  │ PostgreSQL  │          │
│  │  Container  │  │  Container  │  │  Container  │          │
│  │             │  │             │  │             │          │
│  │ :80/:443    │  │ :5001       │  │ :5432       │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│               ┌─────────────────┐                          │
│               │ Shared Volumes │                          │
│               │ (Reports, etc.) │                          │
│               └─────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### 9.4 High Availability Considerations

- **Load Balancing**: Multiple application instances behind load balancer
- **Database Replication**: PostgreSQL read replicas for scaling
- **Backup Strategy**: Regular database and file backups
- **Monitoring**: Health checks and automated failover
- **Disaster Recovery**: Off-site backup and recovery procedures

---

## 10. Integration Points

### 10.1 GitHub Integration

**Purpose**: Repository access and PR management

**Integration Type**: REST API

**Key Operations**:
- List organization repositories
- Download repository files
- Create branches
- Modify files
- Create pull requests
- Monitor PR status

**Authentication**: Personal access tokens

**Rate Limiting**: Implements exponential backoff

### 10.2 Jenkins Integration

**Purpose**: PR validation pipeline triggering

**Integration Type**: REST API

**Key Operations**:
- Trigger parameterized builds
- Monitor build status
- Retrieve build results

**Authentication**: Basic auth with API tokens

**Error Handling**: Graceful degradation on Jenkins failures

### 10.3 Artifactory Integration

**Purpose**: Configuration reference for compliance rules

**Integration Type**: Configuration only

**Key Operations**:
- Virtual repository configuration
- URL pattern validation
- Compliance rule definition

**Authentication**: Not required (configuration reference only)

### 10.4 Future Integration Points

#### Planned Integrations
- **LDAP/SSO**: User authentication and authorization
- **Slack/Teams**: Notification system for compliance alerts
- **CI/CD Platforms**: Native integration with popular CI/CD tools
- **Monitoring Systems**: Integration with Prometheus, Grafana
- **Ticketing Systems**: Automatic ticket creation for compliance issues

#### Integration Architecture Pattern
```
┌─────────────────────────────────────────────────────────────┐
│                  INTEGRATION LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Adapter    │  │  Adapter    │  │  Adapter    │          │
│  │  Pattern    │  │  Pattern    │  │  Pattern    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   GitHub    │  │  Jenkins    │  │  External   │          │
│  │   Service   │  │   Service   │  │  Services   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Appendix

### A. Glossary
- **OSS**: Open Source Software
- **HLD**: High-Level Design
- **LLD**: Low-Level Design
- **PR**: Pull Request
- **API**: Application Programming Interface
- **CI/CD**: Continuous Integration/Continuous Deployment

### B. Acronyms
- **SSL**: Secure Sockets Layer
- **TLS**: Transport Layer Security
- **DMZ**: Demilitarized Zone
- **XSS**: Cross-Site Scripting
- **CSRF**: Cross-Site Request Forgery

### C. References
- **Detailed Design**: [SDD_FRAMEWORK.md](SDD_FRAMEWORK.md)
- **API Documentation**: [API_REFERENCE.md](API_REFERENCE.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **User Documentation**: [USER_GUIDE.md](USER_GUIDE.md)

---

**Document Status**: Draft  
**Next Review**: 2026-06-29  
**Approved By**: Pending  
**Distribution**: Architecture Team, Development Team, Operations Team, Stakeholders