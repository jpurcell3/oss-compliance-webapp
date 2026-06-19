# API Reference Document
## OSS Compliance Web Application

**Version:** 1.1  
**Last Updated:** 2026-06-12  
**Base URL:** `http://localhost:5001`

---

## Table of Contents
1. [Authentication](#authentication)
2. [Scanning APIs](#scanning-apis)
3. [PR Submission APIs](#pr-submission-apis)
4. [Report APIs](#report-apis)
5. [Configuration APIs](#configuration-apis)
6. [Admin Configuration APIs](#admin-configuration-apis)
7. [Error Codes](#error-codes)

---

## Authentication

### Overview
Currently, the application does not implement end-user authentication. External service authentication is handled via environment variables with encryption support:

- **GitHub API**: Token-based authentication via encrypted tokens stored in environment variables
- **Jenkins API**: Basic authentication via `JENKINS_USER` and `JENKINS_API_TOKEN`
- **Multi-User Support**: Multiple GitHub users per instance with encrypted credential storage

### Encryption (v0.5.0)
The application uses Fernet symmetric encryption (AES-128 CBC + HMAC) for credential security:

- **Algorithm**: Fernet (cryptography.fernet)
- **Key Storage**: ENCRYPTION_KEY environment variable
- **Runtime Decryption**: Tokens are decrypted only when needed for API calls
- **Fallback**: Plain text storage if encryption fails (with warning)

### Multi-User GitHub Configuration
GitHub instances can be configured with multiple users:

```json
{
  "instance_name": {
    "api_url": "https://api.github.com",
    "org": "organization",
    "users": {
      "default_user": {"token": "encrypted_token_1"},
      "user2": {"token": "encrypted_token_2"}
    }
  }
}
```

### Future Enhancement
LDAP/SSO integration is planned for future releases.

---

## Scanning APIs

### POST /scan
Scan a repository for compliance issues.

**Request Body:**
```json
{
  "scan_type": "local|remote|team",
  "repo_input": "string",
  "use_enhanced": true|false,
  "github_instance": "string (optional)",
  "team_name": "string (for team scans)"
}
```

**Parameters:**
- `scan_type` (required): Type of scan to perform
  - `local`: Scan a local repository path
  - `remote`: Scan remote GitHub repositories
  - `team`: Scan repositories belonging to a team
- `repo_input` (required): Repository path or names
  - For local: Absolute file system path
  - For remote: Comma-separated repository names
- `use_enhanced` (optional): Enable enhanced endpoint analysis (default: false)
- `github_instance` (optional): GitHub instance ID for remote scans
- `team_name` (required for team scans): Team configuration name

**Response (Success):**
```json
{
  "report": {
    "scan_summary": {
      "total_items": 150,
      "compliant_items": 120,
      "non_compliant_items": 30,
      "compliance_percentage": 80.0
    },
    "findings": [
      {
        "severity": "CRITICAL",
        "type": "go_module",
        "file": "go.mod",
        "issue": "Direct public GitHub dependency",
        "recommended_action": "Configure GOPROXY"
      }
    ],
    "scan_metadata": {
      "scanned_at": "2026-05-29T10:30:00",
      "repository_name": "my-service",
      "scan_method": "enhanced_endpoint_analyzer"
    }
  },
  "report_filename": "my-service_enhanced_oss_0529_1030.json",
  "markdown_filename": "my-service_enhanced_oss_0529_1030_summary.md"
}
```

**Response (Error):**
```json
{
  "error": "Repository path not found",
  "details": "The specified path does not exist or is not accessible"
}
```

**Status Codes:**
- `200 OK`: Scan completed successfully
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Scan execution failed

---

### GET /api/repositories
List available repositories from GitHub organization.

**Query Parameters:**
- `github_instance` (optional): GitHub instance ID
- `search` (optional): Search term to filter repositories
- `refresh` (optional): Force cache refresh (true/false)

**Response (Success):**
```json
{
  "repositories": [
    "service-1",
    "service-2",
    "service-3"
  ]
}
```

**Status Codes:**
- `200 OK`: Repositories retrieved successfully
- `403 Forbidden`: Authentication or permission issue
- `500 Internal Server Error`: API call failed

---

### POST /api/repositories/refresh
Force refresh the repository cache.

**Query Parameters:**
- `github_instance` (optional): GitHub instance ID

**Response (Success):**
```json
{
  "repositories": ["service-1", "service-2"],
  "message": "Repository cache refreshed successfully"
}
```

**Status Codes:**
- `200 OK`: Cache refreshed successfully
- `500 Internal Server Error`: Refresh failed

---

### GET /api/teams
Get team configurations.

**Response (Success):**
```json
{
  "teams": {
    "team-alpha": ["service-1", "service-2"],
    "team-beta": ["service-3", "service-4"]
  }
}
```

**Status Codes:**
- `200 OK`: Teams retrieved successfully
- `500 Internal Server Error`: Failed to load teams

---

### GET /api/teams/{team_name}/repositories
Get repositories for a specific team.

**Path Parameters:**
- `team_name` (required): Team configuration name

**Response (Success):**
```json
{
  "repositories": ["service-1", "service-2"]
}
```

**Status Codes:**
- `200 OK`: Team repositories retrieved successfully
- `404 Not Found`: Team not found
- `500 Internal Server Error**: Failed to load team repositories

---

## PR Submission APIs

### POST /api/pr/submit
Create a pull request with automated compliance fixes (enhanced with multi-user support).

**Request Body:**
```json
{
  "report_filename": "string",
  "submitter_username": "string",
  "submitter_email": "string",
  "github_instance": "string (optional)",
  "selected_user": "string (optional)"
}
```

**Parameters:**
- `report_filename` (required): Filename of the compliance report
- `submitter_username` (required): GitHub username of the submitter
- `submitter_email` (required): Email address of the submitter
- `github_instance` (optional): GitHub instance ID
- `selected_user` (optional): Selected GitHub user for multi-user instances

**Multi-User Selection Response:**
If multiple users are configured for the GitHub instance, returns user list for selection:

```json
{
  "success": true,
  "requires_user_selection": true,
  "available_users": [
    {
      "username": "user1",
      "email": "user1@example.com"
    },
    {
      "username": "user2",
      "email": "user2@example.com"
    }
  ],
  "message": "Please select a GitHub user for PR creation"
}
```

**Response (Success):**
```json
{
  "success": true,
  "pr_submission": {
    "id": 1,
    "repository_name": "my-service",
    "github_org": "ISG-Edge",
    "submitter_github_username": "user123",
    "submitter_email": "user@example.com",
    "pr_number": 123,
    "pr_title": "[OSS Compliance] Fix 5 compliance issues in my-service",
    "pr_url": "https://github.com/ISG-Edge/my-service/pull/123",
    "branch_name": "usr/user123/oss-compliance-fixes-20260529_103000",
    "base_branch": "main",
    "status": "created",
    "github_status": "open",
    "jenkins_status": "pending",
    "jenkins_build_url": "https://jenkins.example.com/job/oss-compliance-validation/45/",
    "fixes_applied": [
      {
        "file": "Dockerfile",
        "type": "go_module",
        "issue": "GOPRIVATE misconfiguration",
        "action": "Remove github.com from GOPRIVATE"
      }
    ],
    "created_at": "2026-05-29T10:30:00"
  },
  "pr_result": {
    "success": true,
    "pr_number": 123,
    "pr_url": "https://github.com/ISG-Edge/my-service/pull/123",
    "jenkins": {
      "success": true,
      "jenkins_job_url": "https://jenkins.example.com/job/oss-compliance-validation/buildWithParameters",
      "jenkins_build_number": 45,
      "jenkins_build_url": "https://jenkins.example.com/job/oss-compliance-validation/45/"
    }
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "GitHub service account lacks write permissions"
}
```

**Status Codes:**
- `200 OK`: PR created successfully
- `400 Bad Request**: Missing required parameters
- `404 Not Found`: Report not found
- `500 Internal Server Error`: PR creation failed

**GitHub Enterprise Compliance (v0.5.0):**
- Branch naming follows GitHub Enterprise pre-receive hook requirements
- Format: `usr/{username}/oss-compliance-fixes-{timestamp}`
- Supports official branches (`rel/`), feature branches (`pub/`), and user branches (`usr/{username}/`)

---

### GET /api/pr/{pr_submission_id}/status
Get the current status of a PR submission.

**Path Parameters:**
- `pr_submission_id` (required): PR submission database ID

**Response (Success):**
```json
{
  "success": true,
  "pr_submission": {
    "id": 1,
    "repository_name": "my-service",
    "pr_number": 123,
    "pr_url": "https://github.com/ISG-Edge/my-service/pull/123",
    "status": "created",
    "github_status": "merged",
    "jenkins_status": "success",
    "created_at": "2026-05-29T10:30:00",
    "updated_at": "2026-05-29T11:45:00"
  }
}
```

**Status Codes:**
- `200 OK`: Status retrieved successfully
- `404 Not Found`: PR submission not found
- `500 Internal Server Error`: Status check failed

---

### GET /api/pr/submissions
List all PR submissions with optional filtering.

**Query Parameters:**
- `repository` (optional): Filter by repository name
- `status` (optional): Filter by status (pending, created, failed, merged, closed)

**Response (Success):**
```json
{
  "success": true,
  "submissions": [
    {
      "id": 1,
      "repository_name": "my-service",
      "status": "merged",
      "created_at": "2026-05-29T10:30:00"
    },
    {
      "id": 2,
      "repository_name": "another-service",
      "status": "created",
      "created_at": "2026-05-29T11:00:00"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Submissions retrieved successfully
- `500 Internal Server Error`: Failed to retrieve submissions

---

## Report APIs

### GET /reports
List all compliance reports.

**Response (Success):**
```json
{
  "reports": [
    {
      "id": 1,
      "filename": "my-service_enhanced_oss_0529_1030.json",
      "repository_name": "my-service",
      "scan_type": "enhanced",
      "compliance_percentage": 80.0,
      "total_findings": 30,
      "created_at": "2026-05-29T10:30:00"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Reports retrieved successfully
- `500 Internal Server Error**: Failed to retrieve reports

---

### GET /report/{filename}
View a specific compliance report.

**Path Parameters:**
- `filename` (required): Report filename

**Response:**
Returns the report file content (JSON or HTML rendering).

**Status Codes:**
- `200 OK`: Report retrieved successfully
- `404 Not Found`: Report not found

---

### GET /export/{filename}
Export a report in specified format.

**Path Parameters:**
- `filename` (required): Report filename

**Query Parameters:**
- `format` (required): Export format (json, markdown, spec)

**Response:**
Returns the exported file content.

**Status Codes:**
- `200 OK**: Report exported successfully
- `404 Not Found`: Report not found
- `400 Bad Request`: Invalid format specified

---

### DELETE /report/{filename}
Delete a specific report.

**Path Parameters:**
- `filename` (required): Report filename

**Response (Success):**
```json
{
  "success": true,
  "message": "Report deleted successfully"
}
```

**Status Codes:**
- `200 OK`: Report deleted successfully
- `404 Not Found`: Report not found
- `500 Internal Server Error`: Deletion failed

---

## Configuration APIs

### GET /config
View current system configuration.

**Response (Success):**
```json
{
  "virtual_repos": {
    "docker": "isgedge-docker-virtual",
    "go": "isgedge-go-virtual",
    "npm": "isgedge-npm-virtual"
  },
  "github_instances": {
    "eos2git": {
      "name": "EOS2Git",
      "api_url": "https://api.eos2git.cec.lab.emc.com",
      "org": "ISG-Edge"
    }
  },
  "jenkins": {
    "urls": ["https://jenkins.example.com"],
    "user": "jenkins-user"
  },
  "artifactory": {
    "base": "isgedge.artifactory.cec.lab.emc.com"
  }
}
```

**Status Codes:**
- `200 OK`: Configuration retrieved successfully
- `500 Internal Server Error`: Failed to retrieve configuration

---

### POST /config
Update system configuration.

**Request Body:**
```json
{
  "virtual_repos": {
    "docker": "custom-docker-virtual",
    "go": "custom-go-virtual"
  },
  "github_instances": {
    "eos2git": {
      "name": "EOS2Git",
      "api_url": "https://api.eos2git.cec.lab.emc.com",
      "org": "ISG-Edge",
      "token": "new-token"
    }
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Configuration updated successfully"
}
```

**Status Codes:**
- `200 OK`: Configuration updated successfully
- `400 Bad Request`: Invalid configuration
- `500 Internal Server Error`: Update failed

---

### POST /save-endpoints
Save endpoint configuration to .env file.

**Request Body:**
```json
{
  "github_instances": {
    "eos2git": {
      "name": "EOS2Git",
      "api_url": "https://api.eos2git.cec.lab.emc.com",
      "org": "ISG-Edge",
      "token": "token-value"
    }
  },
  "jenkins": {
    "user": "jenkins-user",
    "urls": ["https://jenkins.example.com"],
    "token": "jenkins-token"
  },
  "artifactory": {
    "base": "isgedge.artifactory.cec.lab.emc.com"
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Configuration saved successfully"
}
```

**Status Codes:**
- `200 OK`: Configuration saved successfully
- `500 Internal Server Error`: Save failed

---

## Admin Configuration APIs

### GET /admin/config
Admin configuration page for system management.

**Response:**
Returns HTML configuration page with forms for:
- GitHub instance management
- Jenkins configuration
- Artifactory virtual repository settings
- Whitelist URL management

**Status Codes:**
- `200 OK`: Configuration page rendered successfully
- `500 Internal Server Error`: Page render failed

---

### POST /admin/test-endpoint
Test connectivity to external endpoints.

**Request Body:**
```json
{
  "endpoint_type": "github|jenkins|artifactory",
  "url": "https://example.com",
  "token": "optional-token",
  "username": "optional-username"
}
```

**Parameters:**
- `endpoint_type` (required): Type of endpoint to test
- `url` (required): Endpoint URL to test
- `token` (optional): Authentication token
- `username` (optional): Username for authentication

**Response (Success):**
```json
{
  "success": true,
  "endpoint_type": "github",
  "url": "https://api.github.com",
  "status": "reachable",
  "response_time_ms": 125,
  "message": "Endpoint is reachable and responding"
}
```

**Response (Error):**
```json
{
  "success": false,
  "endpoint_type": "jenkins",
  "url": "https://jenkins.example.com",
  "status": "unreachable",
  "error": "Connection timeout"
}
```

**Status Codes:**
- `200 OK`: Endpoint test completed
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Test failed

---

### POST /admin/save-endpoints
Save endpoint configuration to .env file with encryption support.

**Request Body:**
```json
{
  "github_instances": {
    "eos2git": {
      "name": "EOS2Git",
      "api_url": "https://api.eos2git.cec.lab.emc.com",
      "org": "ISG-Edge",
      "users": {
        "default_user": {"token": "encrypted_token_1"},
        "user2": {"token": "encrypted_token_2"}
      }
    }
  },
  "jenkins": {
    "user": "jenkins-user",
    "urls": ["https://jenkins.example.com"],
    "token": "jenkins-token"
  },
  "artifactory": {
    "base": "isgedge.artifactory.cec.lab.emc.com"
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Configuration saved successfully",
  "encryption_status": "active"
}
```

**Status Codes:**
- `200 OK`: Configuration saved successfully
- `400 Bad Request`: Invalid configuration
- `500 Internal Server Error`: Save failed

---

### POST /admin/update-github-config
Update GitHub instance configuration with multi-user support.

**Request Body:**
```json
{
  "instance_name": "eos2git",
  "name": "EOS2Git",
  "api_url": "https://api.eos2git.cec.lab.emc.com",
  "org": "ISG-Edge",
  "users": {
    "default_user": {"token": "ghp_xxx"},
    "user2": {"token": "ghp_yyy"}
  }
}
```

**Parameters:**
- `instance_name` (required): Unique identifier for the GitHub instance
- `name` (required): Display name for the instance
- `api_url` (required): GitHub API URL
- `org` (required): GitHub organization name
- `users` (required): Object containing user configurations with tokens

**Response (Success):**
```json
{
  "success": true,
  "message": "GitHub configuration updated successfully",
  "instance": {
    "instance_name": "eos2git",
    "name": "EOS2Git",
    "user_count": 2
  }
}
```

**Status Codes:**
- `200 OK`: Configuration updated successfully
- `400 Bad Request`: Invalid configuration
- `500 Internal Server Error`: Update failed

---

### POST /admin/update-jenkins-config
Update Jenkins configuration.

**Request Body:**
```json
{
  "user": "jenkins-user",
  "urls": ["https://jenkins.example.com", "https://jenkins2.example.com"],
  "token": "jenkins-api-token",
  "pr_validation_job": "oss-compliance-validation"
}
```

**Parameters:**
- `user` (required): Jenkins username
- `urls` (required): Array of Jenkins server URLs
- `token` (required): Jenkins API token
- `pr_validation_job` (optional): Name of PR validation job

**Response (Success):**
```json
{
  "success": true,
  "message": "Jenkins configuration updated successfully",
  "jenkins": {
    "user": "jenkins-user",
    "url_count": 2
  }
}
```

**Status Codes:**
- `200 OK`: Configuration updated successfully
- `400 Bad Request`: Invalid configuration
- `500 Internal Server Error`: Update failed

---

### POST /admin/update-artifactory-config
Update Artifactory configuration.

**Request Body:**
```json
{
  "base": "isgedge.artifactory.cec.lab.emc.com",
  "virtual_repos": {
    "docker": "isgedge-docker-virtual",
    "go": "isgedge-go-virtual",
    "npm": "isgedge-npm-virtual",
    "maven": "isgedge-maven-virtual"
  }
}
```

**Parameters:**
- `base` (required): Artifactory base URL
- `virtual_repos` (required): Object mapping ecosystem to virtual repository names

**Response (Success):**
```json
{
  "success": true,
  "message": "Artifactory configuration updated successfully",
  "artifactory": {
    "base": "isgedge.artifactory.cec.lab.emc.com",
    "virtual_repo_count": 4
  }
}
```

**Status Codes:**
- `200 OK`: Configuration updated successfully
- `400 Bad Request`: Invalid configuration
- `500 Internal Server Error`: Update failed

---

### POST /admin/update-whitelist-config
Update whitelist URL configuration.

**Request Body:**
```json
{
  "whitelist_urls": [
    "https://github.com",
    "https://gitlab.com",
    "https://bitbucket.org"
  ]
}
```

**Parameters:**
- `whitelist_urls` (required): Array of whitelisted URL patterns

**Response (Success):**
```json
{
  "success": true,
  "message": "Whitelist configuration updated successfully",
  "whitelist": {
    "url_count": 3
  }
}
```

**Status Codes:**
- `200 OK`: Configuration updated successfully
- `400 Bad Request`: Invalid configuration
- `500 Internal Server Error`: Update failed

---

## Error Codes

### Standard Error Response Format
```json
{
  "error": "Error message",
  "details": "Detailed error information",
  "code": "ERROR_CODE"
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_PARAMS` | Invalid request parameters | 400 |
| `MISSING_REQUIRED_FIELD` | Required field is missing | 400 |
| `NOT_FOUND` | Resource not found | 404 |
| `UNAUTHORIZED` | Authentication required | 401 |
| `FORBIDDEN` | Insufficient permissions | 403 |
| `RATE_LIMITED` | API rate limit exceeded | 429 |
| `INTERNAL_ERROR` | Internal server error | 500 |
| `SERVICE_UNAVAILABLE` | External service unavailable | 503 |

### Scanning-Specific Errors

| Code | Description |
|------|-------------|
| `REPOSITORY_NOT_FOUND` | Repository cannot be found or accessed |
| `UNSUPPORTED_FILE_TYPE` | File type not supported for scanning |
| `SCAN_TIMEOUT` | Scanning operation timed out |
| `GITHUB_API_ERROR` | GitHub API call failed |
| `JENKINS_API_ERROR` | Jenkins API call failed |

### PR Submission-Specific Errors

| Code | Description |
|------|-------------|
| `REPORT_NOT_FOUND` | Compliance report not found |
| `INSUFFICIENT_PERMISSIONS` | Service account lacks required permissions |
| `BRANCH_CREATION_FAILED` | Failed to create Git branch |
| `FIX_APPLICATION_FAILED` | Failed to apply automated fixes |
| `PR_CREATION_FAILED` | Failed to create pull request |
| `JENKINS_TRIGGER_FAILED` | Failed to trigger Jenkins job |

---

## Rate Limiting

### GitHub API Rate Limits
- **Authenticated**: 5,000 requests/hour
- **Unauthenticated**: 60 requests/hour
- **Strategy**: Implements exponential backoff and caching

### Application Rate Limits
- **No current limits**: Local deployment has no rate limiting
- **Future enhancement**: Per-user rate limiting planned

---

## Versioning

### API Versioning Strategy
- **Current Version**: v1 (implicit)
- **Version Format**: URL path versioning (e.g., `/api/v2/scan`)
- **Backward Compatibility**: Maintained for minor versions
- **Deprecation Policy**: 6-month notice for breaking changes

---

## Testing

### Example cURL Commands

#### Scan Repository
```bash
curl -X POST http://localhost:5001/scan \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "scan_type=local&repo_input=/path/to/repo&use_enhanced=true"
```

#### Create PR
```bash
curl -X POST http://localhost:5001/api/pr/submit \
  -H "Content-Type: application/json" \
  -d '{
    "report_filename": "my-service_enhanced_oss_0529_1030.json",
    "submitter_username": "user123",
    "submitter_email": "user@example.com"
  }'
```

#### Get Repositories
```bash
curl -X GET "http://localhost:5001/api/repositories?github_instance=eos2git"
```

#### Test Endpoint
```bash
curl -X POST http://localhost:5001/admin/test-endpoint \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint_type": "github",
    "url": "https://api.github.com"
  }'
```

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-06-12 | Added admin configuration APIs, multi-user GitHub support, credential encryption, GitHub Enterprise compliance |
| 1.0 | 2026-05-29 | Initial API documentation |

---

**Document Status**: Complete  
**Last Updated**: 2026-06-12  
**API Version**: 1.1