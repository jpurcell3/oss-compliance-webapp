# OSS Compliance Web Application - Development Expert

## Description
Expert skill for developing, debugging, and enhancing the OSS Compliance Web Application. Provides deep knowledge of the codebase, development patterns, and implementation details.

## When to Use This Skill
Invoke this skill when:
- Adding new features to the application
- Debugging issues or errors
- Refactoring existing code
- Understanding code implementation
- Writing tests
- Optimizing performance
- Implementing security enhancements
- Integrating with external APIs

## Application Architecture

### Technology Stack
- **Backend**: Python 3.11+, Flask 2.3.3
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **Frontend**: Jinja2 templates, Tailwind CSS, Vanilla JavaScript
- **Security**: cryptography (Fernet encryption)
- **External APIs**: GitHub API v3, Jenkins API

### Project Structure
```
oss-compliance-webapp/
├── app.py                      # Main Flask application
├── models.py                   # Database models
├── config_manager.py           # Configuration management (YAML + encryption)
├── compliance_scanner.py       # Base scanner class
├── remote_scanner.py           # GitHub integration & PR creation
├── enhanced_scanner.py         # Component-level analysis
├── endpoint_analyzer.py        # Runtime endpoint detection
├── markdown_generator.py       # Report generation
├── templates/                  # Jinja2 templates
│   ├── index.html             # Main scan page
│   ├── results.html           # Scan results display
│   ├── reports.html           # Report listing
│   ├── config_redesigned.html  # Configuration page (new)
│   └── config.html            # Legacy configuration page
├── static/                     # Static assets
├── reports/                    # Generated reports
├── cache/                      # Repository cache
├── instance/                   # Database files
├── config/                     # Configuration directory
│   └── app_config.yaml        # Main configuration file (encrypted tokens)
└── .devin/                     # Devin skills
```

## Core Components

### 1. WebComplianceScanner (app.py)

**Purpose**: Main orchestrator for scanning operations

**Key Methods**:
```python
def get_available_repositories(github_instance_id, force_refresh=False)
    # Fetches repositories from GitHub with caching
    
def get_github_instance(instance_id)
    # Retrieves GitHub instance configuration with decrypted tokens
    
def encrypt_token(token)
    # Encrypts tokens using Fernet
    
def decrypt_token(encrypted_token)
    # Decrypts tokens for API use
```

**Configuration Management**:
- Uses ConfigManager to load configuration from `config/app_config.yaml`
- Tokens are encrypted and stored as `token_encrypted` in YAML
- No .env file dependency
- Multi-user token management with encrypted storage
- Users stored as dict for scanner compatibility, converted to list for templates
- Handles Artifactory virtual repository mappings
- Provides whitelist URL management

### 2. RemoteRepositoryScanner (remote_scanner.py)

**Purpose**: GitHub repository scanning and PR creation

**Key Methods**:
```python
def scan_repository(repo_name, use_enhanced=True)
    # Scans a remote GitHub repository
    # Returns compliance report with findings
    
def create_fix_pr(repo_name, report_data)
    # Creates pull request with compliance fixes
    # Handles multi-user token selection
    # Generates compliance artifacts
    # Returns PR URL or error
    
def get_organization_repositories(force_refresh=False)
    # Lists all repositories in organization
    # Implements caching with 1-hour TTL
```

**PR Creation Workflow**:
1. Fetch authenticated user info (`GET /user`)
2. Get repository details (`GET /repos/{org}/{repo}`)
3. Get default branch SHA (`GET /repos/{org}/{repo}/git/ref/heads/{branch}`)
4. Create branch with compliant naming (`POST /repos/{org}/{repo}/git/refs`)
5. Generate compliance artifacts (4 files)
6. Commit files to branch (`PUT /repos/{org}/{repo}/contents/{path}`)
7. Create pull request (`POST /repos/{org}/{repo}/pulls`)

**Branch Naming**: `usr/{username}/oss-compliance-fixes-{timestamp}`

### 3. EnhancedScanner (enhanced_scanner.py)

**Purpose**: Component-level compliance analysis

**Key Methods**:
```python
def scan_repository(repo_path, github_api_url=None, github_org=None)
    # Performs enhanced component-level scanning
    # Returns detailed compliance report
    
def _analyze_go_modules(repo_path)
    # Analyzes Go dependencies from go.mod and go.sum
    
def _analyze_python_requirements(repo_path)
    # Analyzes Python dependencies from requirements files
    
def _analyze_node_packages(repo_path)
    # Analyzes Node.js dependencies from package.json
```

**Analysis Capabilities**:
- Component enumeration by ecosystem
- Endpoint classification (artifactory/direct_public/direct_private)
- Runtime evidence detection
- Compliance scoring
- Recommendation generation

### 4. EndpointAnalyzer (endpoint_analyzer.py)

**Purpose**: Runtime endpoint detection and classification

**Key Methods**:
```python
def analyze_endpoints(repo_path)
    # Detects runtime endpoint configurations
    # Returns endpoint analysis results
    
def _detect_go_proxy_config(repo_path)
    # Detects GOPROXY configuration
    
def _detect_python_index_config(repo_path)
    # Detects PIP_INDEX_URL configuration
    
def _detect_npm_registry_config(repo_path)
    # Detects NPM registry configuration
```

**Detection Methods**:
- Environment variable scanning
- Makefile parsing
- Jenkinsfile analysis
- Docker file inspection
- Shell script analysis

## Database Models

### Report Model
```python
class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    repository_name = db.Column(db.String(255), nullable=False)
    repository_type = db.Column(db.String(50))  # local/remote/remote_enhanced
    scan_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_findings = db.Column(db.Integer, default=0)
    critical_findings = db.Column(db.Integer, default=0)
    high_findings = db.Column(db.Integer, default=0)
    medium_findings = db.Column(db.Integer, default=0)
    low_findings = db.Column(db.Integer, default=0)
    compliance_score = db.Column(db.Float, default=0.0)
    
    # Relationship
    pr_submissions = db.relationship('PRSubmission', backref='report', lazy=True)
```

### PRSubmission Model
```python
class PRSubmission(db.Model):
    __tablename__ = 'pr_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    pr_url = db.Column(db.String(500))
    pr_number = db.Column(db.Integer)
    submitter_username = db.Column(db.String(100))
    submitter_email = db.Column(db.String(255))
    github_instance = db.Column(db.String(100))
    submission_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')  # pending/merged/closed
```

## API Routes

### Scanning Routes
```python
@app.route('/', methods=['GET', 'POST'])
def index():
    # Main scan page
    # Handles both local and remote scanning
    
@app.route('/scan', methods=['POST'])
def scan():
    # Processes scan requests
    # Supports local, remote, and remote_enhanced modes
```

### Reporting Routes
```python
@app.route('/reports')
def list_reports():
    # Lists all scan reports with pagination
    
@app.route('/report/<filename>')
def view_report(filename):
    # Displays detailed scan report
    
@app.route('/report/<filename>/delete', methods=['POST'])
def delete_report(filename):
    # Deletes a single report
    
@app.route('/reports/bulk-delete', methods=['POST'])
def bulk_delete_reports():
    # Deletes multiple reports
```

### PR Creation Routes
```python
@app.route('/create-pr/<filename>', methods=['POST'])
def create_pr(filename):
    # Creates pull request for compliance fixes
    # Handles multi-user token selection
    # Returns PR URL or user selection prompt
```

### Configuration Routes
```python
@app.route('/config')
def config():
    # Configuration page (new redesigned version)
    # Uses config_redesigned.html
    # Banner messages instead of alerts
    # User dropdown right-aligned
    
@app.route('/api/github-users/<instance_id>')
def get_github_users(instance_id):
    # Returns list of users for a GitHub instance
    # Includes has_token status
    
@app.route('/api/github-user/<instance_id>/<username>')
def get_github_user(instance_id, username):
    # Get specific user details
    # Returns token_hint (first 4 and last 4 chars)
    
@app.route('/api/github-user/<instance_id>/<username>', methods=['DELETE'])
def delete_github_user(instance_id, username):
    # Delete a user from configuration
    # Reloads config after deletion
    
@app.route('/update-github-user', methods=['POST'])
def update_github_user():
    # Add or update GitHub user
    # Encrypts token before saving to YAML
    # Reloads config after save
    
@app.route('/test-endpoint', methods=['POST'])
def test_endpoint():
    # Tests endpoint connectivity
    # Uses ConfigManager to get tokens
    # Supports user selection for GitHub
    # Returns banner message (no alert popup)
    
@app.route('/update-endpoint', methods=['POST'])
def update_endpoint():
    # Unified endpoint update for GitHub/Jenkins/Artifactory
    # Saves encrypted tokens to YAML
    # Reloads config after save
```

### API Routes
```python
@app.route('/api/repositories')
def get_repositories():
    # Returns list of available repositories
    
@app.route('/api/repositories/refresh', methods=['POST'])
def refresh_repositories():
    # Force refreshes repository cache
    
@app.route('/api/teams')
def get_teams():
    # Returns team configurations
```

## Security Implementation

### Credential Encryption

**Encryption Setup**:
```python
from cryptography.fernet import Fernet
import os

# Initialize cipher
encryption_key = os.getenv('ENCRYPTION_KEY')
if not encryption_key:
    encryption_key = Fernet.generate_key().decode()
cipher = Fernet(encryption_key.encode())
```

**Encryption Functions**:
```python
def encrypt_token(self, token: str) -> str:
    """Encrypt a token for secure storage"""
    if not token:
        return ""
    try:
        return self.cipher.encrypt(token.encode()).decode()
    except Exception as e:
        print(f"Error encrypting token: {e}")
        return ""

def decrypt_token(self, encrypted_token: str) -> str:
    """Decrypt a token for use"""
    if not encrypted_token:
        return ""
    try:
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        print(f"Error decrypting token: {e}")
        return ""
```

**Usage Pattern**:
```python
# Encrypting (user management via UI)
encrypted_token = scanner.encrypt_token(user_token)
# Store in app_config.yaml as token_encrypted

# Decrypting (API call via ConfigManager)
plaintext_token = user_obj.token  # Uses ConfigManager's decryption
# Use for API call, never log
```

### Multi-User Token Management

**Configuration Structure (app_config.yaml)**:
```yaml
github_instances:
  eos2git:
    name: ISG-Edge
    api_url: https://eos2git.cec.lab.emc.com/api/v3
    org: ISG-Edge
    users:
    - username: default_user
      token_encrypted: gAAAAABh...  # Encrypted token
      email: ''
    - username: jpurcell
      token_encrypted: gAAAAABh...  # Encrypted token
      email: jeff.purcell@dell.com
```

**User Selection Flow**:
```python
# 1. Get users from ConfigManager
config_manager = get_config_manager()
instance = config_manager.get_github_instance(instance_id)
users = instance.users  # List of GitHubUser objects

# 2. Check if user selection needed
if not selected_user and len(users) > 1:
    return jsonify({
        'success': False,
        'requires_user_selection': True,
        'users': [u.username for u in users]
    })

# 3. Select user object
user_obj = instance.get_user(selected_user) if selected_user else instance.get_default_user()

# 4. Use decrypted token (automatic via property)
github_config['token'] = user_obj.token  # Automatically decrypts
```

**ConfigManager Data Classes**:
```python
@dataclass
class GitHubUser:
    username: str
    token_encrypted: str  # Encrypted token stored in YAML
    email: str = ""
    
    @property
    def token(self) -> str:
        """Get decrypted token automatically"""
        if self.token_encrypted:
            from app import decrypt_token
            return decrypt_token(self.token_encrypted)
        return ""
```

## Frontend Implementation

### User Selection Modal (results.html)

**Modal Creation**:
```javascript
const modal = document.createElement('div');
modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
modal.innerHTML = `
    <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <h3>Select User for PR Creation</h3>
        <select id="user-select">
            ${data.users.map(u => `<option value="${u}">${u}</option>`).join('')}
        </select>
        <button id="submit-btn">Create PR</button>
        <button id="cancel-btn">Cancel</button>
    </div>
`;
```

**Event Handling**:
```javascript
document.getElementById('submit-btn').addEventListener('click', async () => {
    const selectedUser = document.getElementById('user-select').value;
    document.body.removeChild(modal);
    await createPRWithUser(selectedUser);
});
```

### Repository Search and Selection (index.html)

**Search Implementation**:
```javascript
document.getElementById('repo-search').addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    const checkboxes = document.querySelectorAll('.repo-checkbox');
    
    checkboxes.forEach(checkbox => {
        const label = checkbox.nextElementSibling;
        const repoName = label.textContent.toLowerCase();
        const container = checkbox.parentElement;
        
        if (repoName.includes(searchTerm)) {
            container.style.display = '';
        } else {
            container.style.display = 'none';
        }
    });
});
```

**Refresh Button**:
```javascript
document.getElementById('refresh-repos').addEventListener('click', async function(e) {
    e.preventDefault();  // Prevent form submission
    e.stopPropagation(); // Stop event bubbling
    
    const githubInstance = document.querySelector('input[name="github_instance"]:checked')?.value;
    const response = await fetch(`/api/repositories/refresh?github_instance=${githubInstance}`, {
        method: 'POST'
    });
    const data = await response.json();
    displayRepositories(data.repositories);
});
```

## Common Development Patterns

### 1. Error Handling Pattern

**Backend**:
```python
try:
    # Operation
    result = perform_operation()
    return jsonify({'success': True, 'data': result})
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    return jsonify({'success': False, 'error': str(e)}), 500
```

**Frontend**:
```javascript
try {
    const response = await fetch(url, options);
    const data = await response.json();
    
    if (data.success) {
        // Handle success
    } else {
        alert('Error: ' + data.error);
    }
} catch (error) {
    alert('Error: ' + error.message);
} finally {
    // Cleanup (reset buttons, etc.)
}
```

### 2. Caching Pattern

**Repository Cache**:
```python
import json
from pathlib import Path
import time

cache_file = Path('cache') / f'{org}_{api_url_safe}_repos.json'
cache_ttl = 3600  # 1 hour

if cache_file.exists() and not force_refresh:
    cache_age = time.time() - cache_file.stat().st_mtime
    if cache_age < cache_ttl:
        with open(cache_file, 'r') as f:
            return json.load(f)

# Fetch fresh data
repositories = fetch_from_api()

# Save to cache
cache_file.parent.mkdir(exist_ok=True)
with open(cache_file, 'w') as f:
    json.dump(repositories, f)

return repositories
```

### 3. Configuration Loading Pattern

**ConfigManager Pattern**:
```python
from config_manager import get_config_manager

# Load configuration from YAML
config_manager = get_config_manager()

# Get GitHub instances
github_instances = config_manager.get_github_instances()

# Get specific instance
instance = config_manager.get_github_instance('eos2git')

# Get user with automatic token decryption
user = instance.get_user('jpurcell')
token = user.token  # Automatically decrypted

# Get Jenkins config
jenkins = config_manager.get_jenkins_config()
jenkins_token = jenkins.token  # Automatically decrypted

# Get Artifactory config
artifactory = config_manager.get_artifactory_config()
artifactory_token = artifactory.token  # Automatically decrypted
```

### 4. Database Query Pattern

**With Pagination**:
```python
page = request.args.get('page', 1, type=int)
per_page = 20

reports = Report.query.order_by(Report.scan_timestamp.desc()).paginate(
    page=page,
    per_page=per_page,
    error_out=False
)

return render_template('reports.html', 
                      reports=reports.items,
                      pagination=reports)
```

## Testing Guidelines

### Unit Testing

**Test Structure**:
```python
import unittest
from app import app, db
from models import Report

class TestReportModel(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_create_report(self):
        with app.app_context():
            report = Report(
                filename='test_report.json',
                repository_name='test-repo',
                repository_type='local'
            )
            db.session.add(report)
            db.session.commit()
            
            self.assertIsNotNone(report.id)
            self.assertEqual(report.repository_name, 'test-repo')
```

### Integration Testing

**API Testing**:
```python
def test_scan_endpoint(self):
    response = self.app.post('/scan', data={
        'repo_type': 'local',
        'repo_input': '/path/to/repo'
    })
    
    self.assertEqual(response.status_code, 200)
    # Additional assertions
```

## Performance Optimization

### Database Indexing
```python
class Report(db.Model):
    # Add indexes for frequently queried fields
    __table_args__ = (
        db.Index('idx_repository_name', 'repository_name'),
        db.Index('idx_scan_timestamp', 'scan_timestamp'),
    )
```

### Query Optimization
```python
# Use eager loading for relationships
reports = Report.query.options(
    db.joinedload(Report.pr_submissions)
).all()

# Use pagination for large result sets
reports = Report.query.paginate(page=page, per_page=20)
```

### Caching Strategy
- Repository lists: 1-hour TTL
- Scan results: Persistent (file-based)
- Configuration: Loaded once at startup

## Debugging Tips

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Print Debugging
```python
print(f"DEBUG: Variable value: {variable}")
print(f"DEBUG: API URL: {api_url}")
print(f"DEBUG: Token present: {'Yes' if token else 'No'}")
```

### Flask Debug Mode
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Common Issues

**Issue**: GitHub API rate limiting
**Solution**: Implement caching, use conditional requests

**Issue**: Token decryption failures
**Solution**: Verify ENCRYPTION_KEY consistency, check token_encrypted format in YAML

**Issue**: Database locked errors (SQLite)
**Solution**: Use PostgreSQL for production, implement retry logic

**Issue**: PR creation fails with 422
**Solution**: Check branch naming compliance, verify user permissions

**Issue**: No repositories showing on home page
**Solution**: Add token to `default_user` or delete `default_user` so scanner uses another user

**Issue**: "default_user has no token" error
**Solution**: Add token via Configuration → Users → Edit, or delete default_user

**Issue**: Config not reloading after changes
**Solution**: ConfigManager should auto-reload, check reload_config() calls

## Development Workflow

### Adding a New Feature

1. **Plan**:
   - Review architecture and identify affected components
   - Document design decisions
   - Create feature branch

2. **Implement**:
   - Follow existing patterns
   - Add error handling
   - Include logging
   - Write tests

3. **Test**:
   - Unit test new functions
   - Integration test API endpoints
   - Manual testing in UI

4. **Document**:
   - Update SDD documents
   - Add API documentation
   - Update user guide
   - Add code comments

5. **Review**:
   - Code review
   - Documentation review
   - Security review

6. **Deploy**:
   - Merge to main
   - Update version numbers
   - Deploy to production

### Code Style Guidelines

**Python (PEP 8)**:
- 4 spaces for indentation
- Max line length: 100 characters
- Use descriptive variable names
- Add docstrings to functions
- Type hints for function signatures

**JavaScript**:
- Use `const` and `let`, avoid `var`
- Use arrow functions
- Async/await for promises
- Descriptive variable names

**HTML/Templates**:
- Semantic HTML5 elements
- Tailwind CSS for styling
- Accessibility attributes (aria-*)

## Skill Capabilities

When this skill is invoked, I can help with:

✅ **Development Tasks**:
- Implement new features
- Debug issues and errors
- Refactor existing code
- Optimize performance
- Write tests

✅ **Integration Tasks**:
- Add new external API integrations
- Enhance GitHub/Jenkins integration
- Implement new scanning capabilities

✅ **Security Tasks**:
- Implement encryption
- Add authentication
- Secure API endpoints
- Validate inputs

✅ **Database Tasks**:
- Design new models
- Write queries
- Optimize performance
- Handle migrations

✅ **Frontend Tasks**:
- Create new UI components
- Implement interactive features
- Add client-side validation
- Improve UX

## Example Invocations

```
"Add support for scanning Maven repositories"
"Debug the PR creation failure for repository X"
"Implement batch scanning for multiple repositories"
"Add authentication to the admin configuration page"
"Optimize the repository listing query"
"Create a new endpoint for exporting reports to CSV"
```

---

**Skill Version**: 1.0  
**Last Updated**: 2026-06-05  
**Maintained By**: Development Team
