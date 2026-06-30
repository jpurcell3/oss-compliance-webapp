#!/usr/bin/env python3
"""
OSS Compliance Verification Web Application
A Flask-based web application for scanning repositories and generating compliance reports
"""

import os
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import zipfile
import tempfile
import urllib3
from playwright.sync_api import sync_playwright

# Suppress InsecureRequestWarning when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Encryption utilities for secure credential storage
from cryptography.fernet import Fernet

# Configuration management
from config_manager import get_config_manager, reload_config

def get_encryption_key():
    """Get the encryption key from environment or generate a new one."""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        # Generate a new key if not set
        key = Fernet.generate_key().decode()
        print(f"WARNING: Generated new encryption key: {key}")
        print("Please set ENCRYPTION_KEY environment variable with this value")
    return key.encode() if isinstance(key, str) else key

def encrypt_token(token: str) -> str:
    """Encrypt a token using Fernet encryption."""
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(token.encode())
        return encrypted.decode()
    except Exception as e:
        print(f"Error encrypting token: {e}")
        return token  # Fallback to plain text if encryption fails

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token using Fernet encryption."""
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"Error decrypting token: {e}")
        return encrypted_token  # Fallback to plain text if decryption fails

# Version information
__version__ = '0.5.0'

# Import the compliance scanners
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_scanner import ComplianceScanner
from remote_scanner import RemoteRepositoryScanner
from markdown_generator import generate_markdown_summary

# Import database models
from models import db, Report, PRSubmission

# Import PR submission service
from pr_submission_service import PRSubmissionService

# Global debug logging flag
_debug_logging_enabled = True

def set_debug_logging(enabled: bool):
    """Set global debug logging flag"""
    global _debug_logging_enabled
    _debug_logging_enabled = enabled

def debug_log(message: str):
    """Print debug message if debug logging is enabled"""
    if _debug_logging_enabled:
        print(f"DEBUG: {message}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REPORTS_FOLDER'] = 'reports'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Database configuration
# Ensure instance directory exists
instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_dir, exist_ok=True)

# Use instance/reports.db for consistency with docker-compose
db_path = os.path.join(instance_dir, 'reports.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

# Create tables if they don't exist (with error handling)
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    # Ignore errors if tables already exist
    if "already exists" not in str(e):
        print(f"Warning: Could not create database tables: {e}")

@app.context_processor
def inject_version():
    return {'version': __version__}

# Default approved virtual repositories
DEFAULT_VIRTUAL_REPOS = {
    'docker': 'isgedge-docker-virtual',
    'go': 'isgedge-go-virtual',
    'helm': 'isgedge-helm-virtual',
    'maven': 'isgedge-maven-virtual',
    'npm': 'isgedge-npm-virtual',
    'pypi': 'isgedge-pypi-virtual',
    'rpm': 'isgedge-rpm-virtual',
    'factoryos': 'isgedge-factoryos-virtual',
    'debian': 'isgedge-manufacturing-debian-virtual',
}

class WebComplianceScanner:
    def __init__(self):
        # Load configuration from YAML file (config/app_config.yaml)
        # Tokens are stored encrypted in the YAML file
        self.config_manager = get_config_manager()
        
        # Load Artifactory configuration
        artifactory_config = self.config_manager.get_artifactory_config()
        self.artifactory_base = artifactory_config.base_url
        self.virtual_repos = artifactory_config.virtual_repos
        
        # Load whitelist URLs
        self.whitelist_urls = self.config_manager.get_whitelist_urls()
        
        # Load GitHub instances from YAML
        self.github_instances = self._load_github_instances_from_config()
        
        # Load Jenkins configuration from YAML
        self.jenkins_config = self._load_jenkins_config_from_config()
        
        self.remote_scanner = None
        self.pipeline_scanner = None
    
    def _load_github_instances_from_config(self):
        """Load GitHub instances from ConfigManager"""
        instances = {}
        github_instances = self.config_manager.get_github_instances()
        
        for instance_id, instance in github_instances.items():
            # Convert ConfigManager format to dict for scanner compatibility
            users_dict = {}
            for user in instance.users:
                users_dict[user.username] = {
                    'token': user.token,
                    'email': user.email
                }
            
            instances[instance_id] = {
                'name': instance.name,
                'api_url': instance.api_url,
                'org': instance.org,
                'users': users_dict  # Dict for scanner compatibility
            }
        
        return instances
    
    def _load_jenkins_config_from_config(self):
        """Load Jenkins configuration from ConfigManager"""
        jenkins_config = self.config_manager.get_jenkins_config()
        if jenkins_config:
            return {
                'user': jenkins_config.user,
                'token': jenkins_config.token,
                'urls': jenkins_config.urls,
                'pr_validation_job': jenkins_config.pr_validation_job
            }
        return None
    
    def get_github_instance(self, instance_id):
        """Get a specific GitHub instance configuration"""
        return self.github_instances.get(instance_id, list(self.github_instances.values())[0] if self.github_instances else None)

    def get_all_github_instances(self):
        """Get all configured GitHub instances"""
        return self.github_instances
    
    def scan_repository(self, repo_path):
        """Scan a repository for compliance"""
        scanner = ComplianceScanner(repo_path, self.virtual_repos, self.artifactory_base, self.whitelist_urls)
        return scanner.scan_comprehensive()
    
    def scan_remote_repository(self, repo_name, github_instance_id=None):
        """Scan a remote repository for compliance"""
        github_config = self.get_github_instance(github_instance_id) if github_instance_id else list(self.github_instances.values())[0] if self.github_instances else None
        
        # Extract default user token for backward compatibility with RemoteRepositoryScanner
        if github_config and 'users' in github_config:
            # Get the first available user's token (prefer default_user)
            users = github_config['users']
            if 'default_user' in users:
                github_config['token'] = users['default_user']['token']
            elif users:
                # Use the first available user
                first_user = list(users.keys())[0]
                github_config['token'] = users[first_user]['token']
        
        # Debug logging
        if github_config:
            debug_log(f"Scan GitHub config - API URL: {github_config.get('api_url')}")
            debug_log(f"Scan GitHub config - Org: {github_config.get('org')}")
            debug_log(f"Scan GitHub config - Token present: {'Yes' if github_config.get('token') else 'No'}")
            if github_config.get('token'):
                debug_log(f"Scan GitHub config - Token (first 10 chars): {github_config['token'][:10]}...")
        
        self.remote_scanner = RemoteRepositoryScanner(github_config, self.whitelist_urls, self.jenkins_config)
        
        return self.remote_scanner.scan_remote_repository(repo_name)
    
    def scan_multiple_repositories(self, repo_names, github_instance_id=None):
        """Scan multiple remote repositories"""
        github_config = self.get_github_instance(github_instance_id) if github_instance_id else list(self.github_instances.values())[0] if self.github_instances else None
        self.remote_scanner = RemoteRepositoryScanner(github_config, self.whitelist_urls, self.jenkins_config)
        
        return self.remote_scanner.scan_multiple_repositories(repo_names)
    
    def scan_team_repositories(self, team_name, github_instance_id=None):
        """Scan repositories for a specific team"""
        github_config = self.get_github_instance(github_instance_id) if github_instance_id else list(self.github_instances.values())[0] if self.github_instances else None
        self.remote_scanner = RemoteRepositoryScanner(github_config, self.whitelist_urls)
        
        return self.remote_scanner.scan_team_repositories(team_name)
    
    def get_available_repositories(self, github_instance_id=None, force_refresh=False):
        """Get list of available repositories from GitHub organization"""
        github_config = self.get_github_instance(github_instance_id) if github_instance_id else list(self.github_instances.values())[0] if self.github_instances else None
        
        # Extract default user token for backward compatibility with RemoteRepositoryScanner
        if github_config and 'users' in github_config:
            # Get the first available user's token (prefer default_user)
            users = github_config['users']
            if 'default_user' in users:
                github_config['token'] = users['default_user']['token']
            elif users:
                # Use the first available user
                first_user = list(users.keys())[0]
                github_config['token'] = users[first_user]['token']
        
        # Debug logging
        if github_config:
            debug_log(f"GitHub config - API URL: {github_config.get('api_url')}")
            debug_log(f"GitHub config - Org: {github_config.get('org')}")
            debug_log(f"GitHub config - Token present: {'Yes' if github_config.get('token') else 'No'}")
            if github_config.get('token'):
                debug_log(f"GitHub config - Token (first 10 chars): {github_config['token'][:10]}...")
        
        self.remote_scanner = RemoteRepositoryScanner(github_config, self.whitelist_urls)
        
        try:
            return self.remote_scanner.get_organization_repositories(force_refresh=force_refresh)
        except Exception as e:
            print(f"Error getting repositories: {e}")
            return []
    
    def get_teams(self):
        """Get team configurations"""
        if not self.remote_scanner:
            self.remote_scanner = RemoteRepositoryScanner()
        
        return self.remote_scanner.get_teams()
    
    def filter_repositories(self, repositories, search_term=""):
        """Filter repositories based on search term"""
        if not self.remote_scanner:
            self.remote_scanner = RemoteRepositoryScanner()
        
        return self.remote_scanner.filter_repositories(repositories, search_term)
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.remote_scanner:
            self.remote_scanner.cleanup()
    
    def generate_spec_file(self, report_data):
        """Generate WindSurf automation spec from report"""
        spec = {
            'windsurf_automation_spec': {
                'version': '1.0',
                'description': 'Migrate OSS repository references to approved Artifactory virtual repositories',
                'target_repository': report_data.get('scan_summary', {}).get('repository_name', 'Unknown'),
                'execution_strategy': 'pipeline_level',
                'approved_virtual_repositories': self.virtual_repos,
                'artifactory_base_url': f'https://{self.artifactory_base}/artifactory',
                'changes': []
            }
        }
        
        # Generate changes based on findings
        for finding in report_data.get('findings', []):
            # Process filename for ID (f-strings can't contain backslashes in expressions)
            safe_filename = finding['file'].replace('/', '-').replace('\\', '-')
            change = {
                'id': f"fix-{finding['type']}-{safe_filename}",
                'type': 'file_modification',
                'target_file': finding['file'],
                'priority': finding['severity'],
                'action': self._get_action_for_type(finding['type']),
                'issue': finding['issue'],
                'recommended_action': finding['recommended_action'],
                'compliant': False
            }
            spec['windsurf_automation_spec']['changes'].append(change)
        
        return spec
    
    def _get_action_for_type(self, finding_type):
        """Get action type based on finding type"""
        actions = {
            'go_module': 'configure_goproxy',
            'python_requirements': 'configure_pip_index',
            'node_package': 'configure_npm_registry',
            'maven_pom': 'configure_maven_mirror',
            'jenkinsfile': 'replace_github_urls',
            'makefile': 'update_artifactory_urls'
        }
        return actions.get(finding_type, 'update_configuration')

@app.route('/')
def index():
    """Home page"""
    scanner = WebComplianceScanner()
    return render_template('index.html', 
                         virtual_repos=scanner.virtual_repos,
                         artifactory_base=scanner.artifactory_base,
                         github_instances=scanner.github_instances,
                         version=__version__)

@app.route('/scan', methods=['POST'])
def scan_repository():
    """Scan a repository for compliance"""
    scanner = WebComplianceScanner()
    
    # Get scan type and input
    scan_type = request.form.get('scan_type', 'local')
    github_instance_id = request.form.get('github_instance', None)
    
    # Validate input based on scan type
    if scan_type == 'local':
        repo_input = request.form.get('repo_input')
        if not repo_input:
            flash('Please provide a repository path', 'error')
            return redirect(url_for('index'))
    elif scan_type == 'remote':
        # Get repositories from radio button or manual input
        repo_input = request.form.get('repo_input', '')
        selected_repository = request.form.get('selected_repository', '')
        selected_repos = []
        
        # DEBUG: Log what we received
        print(f"DEBUG: scan_type=remote, repo_input='{repo_input}', selected_repository='{selected_repository}'")
        print(f"DEBUG: All form keys: {list(request.form.keys())}")
        
        # Priority 1: Check for radio button selection (new single-select UI)
        if selected_repository:
            repo_names = [selected_repository]
            print(f"DEBUG: Using selected_repository: {repo_names}")
        # Priority 2: Check for old checkbox selections (backward compatibility)
        elif any(key.startswith('repo_') and key != 'repo_input' for key in request.form.keys()):
            for key in request.form.keys():
                if key.startswith('repo_') and key != 'repo_input':
                    selected_repos.append(key.replace('repo_', ''))
            repo_names = selected_repos
            print(f"DEBUG: Using selected_repos (checkboxes): {repo_names}")
        # Priority 3: Check manual input in hidden field
        elif repo_input:
            repo_names = [name.strip() for name in repo_input.split(',') if name.strip()]
            print(f"DEBUG: Using repo_input, parsed to: {repo_names}")
        else:
            flash('Please select a repository', 'error')
            return redirect(url_for('index'))
    elif scan_type == 'team':
        team_name = request.form.get('team_name')
        if not team_name:
            flash('Please select a team', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid scan type', 'error')
        return redirect(url_for('index'))
    
    try:
        if scan_type == 'local':
            # Local repository scan
            report = scanner.scan_repository(repo_input)
            
            # Add or update scan metadata
            if 'scan_metadata' not in report:
                report['scan_metadata'] = {}
            
            report['scan_metadata'].update({
                'scanned_at': datetime.now().isoformat(),
                'repository_path': repo_input,
                'repository_type': 'local',
                'scan_method': 'compliance_scan',
                'virtual_repositories': scanner.virtual_repos,
                'artifactory_base': scanner.artifactory_base
            })
        elif scan_type == 'remote':
            # Remote repository scan
            if len(repo_names) == 1:
                report = scanner.scan_remote_repository(repo_names[0], github_instance_id)
            else:
                report = scanner.scan_multiple_repositories(repo_names, github_instance_id)
        elif scan_type == 'team':
            # Team-based scan (use traditional for now, can add pipeline option later)
            report = scanner.scan_team_repositories(team_name, github_instance_id)
        else:
            flash('Invalid scan type', 'error')
            return redirect(url_for('index'))
        
        # Determine repository name for filename
        if scan_type == 'local':
            repo_display_name = os.path.basename(os.path.abspath(repo_input))
        elif scan_type == 'remote':
            if len(repo_names) == 1:
                repo_display_name = repo_names[0].replace('/', '_')
            else:
                repo_display_name = "multiple_repos"
        elif scan_type == 'team':
            repo_display_name = f"team_{team_name}"
        else:
            repo_display_name = "unknown"

        # Add scan method to filename
        scan_method_display = "Compliance Scan"
        
        report_filename = f"{repo_display_name}_oss_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = Path(app.config['REPORTS_FOLDER']) / report_filename
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown summary for scans with ecosystem breakdown
        markdown_filename = None
        markdown_path_str = None
        if 'ecosystem_breakdown' in report:
            markdown_filename = report_filename.replace('.json', '_summary.md')
            markdown_path = Path(app.config['REPORTS_FOLDER']) / markdown_filename
            markdown_path_str = str(markdown_path)
            try:
                generate_markdown_summary(report, markdown_path_str)
                flash(f'{scan_method_display} scan completed! Report: {report_filename}, Summary: {markdown_filename}', 'success')
            except Exception as e:
                print(f"Warning: Could not generate markdown summary: {e}")
                flash(f'{scan_method_display} scan completed successfully! Report saved as {report_filename}', 'success')
        else:
            flash(f'{scan_method_display} scan completed successfully! Report saved as {report_filename}', 'success')
        
        # Save report to database
        try:
            report_record = Report.from_report_data(
                filename=report_filename,
                report_data=report,
                file_path=str(report_path),
                markdown_path=markdown_path_str
            )
            db.session.add(report_record)
            db.session.commit()
        except Exception as e:
            print(f"Warning: Could not save report to database: {e}")
            db.session.rollback()
        
        return render_template('results.html', report=report, report_filename=report_filename, markdown_filename=markdown_filename)
        
    except Exception as e:
        flash(f'Error scanning repository: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/repositories')
def get_repositories():
    """Get list of available repositories from GitHub organization"""
    scanner = WebComplianceScanner()
    github_instance_id = request.args.get('github_instance', None)
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        # Fall back to scanner (which checks file cache)
        repositories = scanner.get_available_repositories(github_instance_id, force_refresh=force_refresh)
        
        search_term = request.args.get('search', '')
        if search_term:
            repositories = scanner.filter_repositories(repositories, search_term)
        
        return jsonify({'repositories': repositories, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/repositories/refresh', methods=['POST'])
def refresh_repositories():
    """Force refresh the repository cache"""
    scanner = WebComplianceScanner()
    github_instance_id = request.args.get('github_instance', None)
    
    try:
        repositories = scanner.get_available_repositories(github_instance_id, force_refresh=True)
        return jsonify({'repositories': repositories, 'message': 'Repository cache refreshed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams')
def get_teams():
    """Get team configurations"""
    scanner = WebComplianceScanner()
    try:
        teams = scanner.get_teams()
        return jsonify({'teams': teams})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/<team_name>/repositories')
def get_team_repositories(team_name):
    """Get repositories for a specific team"""
    scanner = WebComplianceScanner()
    try:
        repositories = scanner.get_teams().get(team_name, [])
        return jsonify({'repositories': repositories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/scan/remote', methods=['POST'])
def scan_remote_repository():
    """Scan remote repositories for compliance"""
    scanner = WebComplianceScanner()
    
    # Get repository names
    repo_names = request.form.get('repo_names', '')
    if not repo_names:
        return jsonify({'error': 'No repository names provided'}), 400
    
    try:
        repo_list = [name.strip() for name in repo_names.split(',') if name.strip()]
        
        # Use comprehensive scanner
        if len(repo_list) == 1:
            report = scanner.scan_remote_repository(repo_list[0])
            repo_display_name = repo_list[0].replace('/', '_')
        else:
            report = scanner.scan_multiple_repositories(repo_list)
            repo_display_name = "multiple_repos"
        
        # Save report
        report_filename = f"{repo_display_name}_oss_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = Path(app.config['REPORTS_FOLDER']) / report_filename
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return jsonify({
            'success': True,
            'report_filename': report_filename,
            'report': report
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reports')
def list_reports():
    """List all available reports with pagination and filtering"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    min_compliance = request.args.get('min_compliance', type=float)
    max_compliance = request.args.get('max_compliance', type=float)
    scan_type = request.args.get('scan_type', '').strip()
    
    # Build query
    query = Report.query
    
    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                Report.repository_name.ilike(f'%{search}%'),
                Report.filename.ilike(f'%{search}%'),
                Report.github_org.ilike(f'%{search}%')
            )
        )
    
    # Apply compliance percentage filter
    if min_compliance is not None:
        query = query.filter(Report.compliance_percentage >= min_compliance)
    if max_compliance is not None:
        query = query.filter(Report.compliance_percentage <= max_compliance)
    
    # Apply scan type filter
    if scan_type:
        query = query.filter(Report.scan_type == scan_type)
    
    # Apply sorting
    if sort_order == 'desc':
        query = query.order_by(getattr(Report, sort_by).desc())
    else:
        query = query.order_by(getattr(Report, sort_by).asc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Convert to dict format for template
    reports = [report.to_dict() for report in pagination.items]
    
    return render_template('reports.html', 
                         reports=reports,
                         pagination=pagination,
                         search=search,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         min_compliance=min_compliance,
                         max_compliance=max_compliance,
                         scan_type=scan_type)

@app.route('/report/<filename>')
def view_report(filename):
    """View a specific report"""
    report_path = Path(app.config['REPORTS_FOLDER']) / filename
    
    if not report_path.exists():
        flash('Report not found', 'error')
        return redirect(url_for('list_reports'))
    
    try:
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        return render_template('results.html', report=report_data, report_filename=filename)
    except Exception as e:
        flash(f'Error loading report: {str(e)}', 'error')
        return redirect(url_for('list_reports'))

@app.route('/download/<filename>')
def download_report(filename):
    """Download a report file (JSON or markdown)"""
    report_path = Path(app.config['REPORTS_FOLDER']) / filename
    
    if not report_path.exists():
        flash('Report not found', 'error')
        return redirect(url_for('list_reports'))
    
    try:
        return send_file(report_path, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f'Error downloading report: {str(e)}', 'error')
        return redirect(url_for('list_reports'))

@app.route('/delete/<filename>', methods=['POST'])
def delete_report(filename):
    """Delete a specific report"""
    report_path = Path(app.config['REPORTS_FOLDER']) / filename
    
    if not report_path.exists():
        flash('Report not found', 'error')
        return redirect(url_for('list_reports'))
    
    try:
        # Delete from database
        report = Report.query.filter_by(filename=filename).first()
        if report:
            # Delete markdown file if exists
            if report.markdown_path and os.path.exists(report.markdown_path):
                os.remove(report.markdown_path)
            
            db.session.delete(report)
            db.session.commit()
        
        # Delete JSON file
        os.remove(report_path)
        flash(f'Report {filename} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting report: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('list_reports'))

@app.route('/api/reports/bulk-delete', methods=['POST'])
def bulk_delete_reports():
    """Delete multiple reports at once"""
    try:
        data = request.json
        filenames = data.get('filenames', [])
        
        if not filenames:
            return jsonify({'success': False, 'error': 'No filenames provided'}), 400
        
        deleted_count = 0
        errors = []
        
        for filename in filenames:
            try:
                report_path = Path(app.config['REPORTS_FOLDER']) / filename
                
                if not report_path.exists():
                    errors.append(f'{filename}: Report not found')
                    continue
                
                # Delete from database
                report = Report.query.filter_by(filename=filename).first()
                if report:
                    # Delete markdown file if exists
                    if report.markdown_path and os.path.exists(report.markdown_path):
                        os.remove(report.markdown_path)
                    
                    db.session.delete(report)
                    db.session.commit()
                
                # Delete JSON file
                os.remove(report_path)
                deleted_count += 1
                
            except Exception as e:
                errors.append(f'{filename}: {str(e)}')
                db.session.rollback()
        
        if errors:
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'errors': errors,
                'message': f'Deleted {deleted_count} reports with {len(errors)} errors'
            })
        else:
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Successfully deleted {deleted_count} reports'
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/export/<filename>')
def export_report(filename):
    """Export a report in various formats"""
    report_path = Path(app.config['REPORTS_FOLDER']) / filename
    export_format = request.args.get('format', 'json')
    
    if not report_path.exists():
        flash('Report not found', 'error')
        return redirect(url_for('list_reports'))
    
    try:
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        if export_format == 'json':
            return send_file(report_path, as_attachment=True, download_name=filename)
        
        elif export_format == 'markdown':
            # Generate markdown report
            md_content = generate_markdown_report(report_data)
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
            temp_file.write(md_content)
            temp_file.close()
            
            return send_file(temp_file.name, as_attachment=True, 
                           download_name=filename.replace('.json', '.md'))
        
        elif export_format == 'spec':
            # Generate WindSurf spec
            scanner = WebComplianceScanner()
            spec = scanner.generate_spec_file(report_data)
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
            yaml.dump(spec, temp_file, default_flow_style=False, indent=2)
            temp_file.close()
            
            return send_file(temp_file.name, as_attachment=True,
                           download_name=filename.replace('.json', '_spec.yaml'))
        
        elif export_format == 'pdf':
            # Generate PDF report
            pdf_file_path = generate_pdf_report(report_data, filename)
            return send_file(pdf_file_path, as_attachment=True,
                           download_name=filename.replace('.json', '.pdf'))
        
        else:
            flash('Invalid export format', 'error')
            return redirect(url_for('view_report', filename=filename))
            
    except Exception as e:
        flash(f'Error exporting report: {str(e)}', 'error')
        return redirect(url_for('view_report', filename=filename))

@app.route('/create-pr/<filename>', methods=['POST'])
def create_pr(filename):
    """Create a pull request for the specific report"""
    report_path = Path(app.config['REPORTS_FOLDER']) / filename
    
    if not report_path.exists():
        return jsonify({'success': False, 'error': 'Report not found'}), 404
        
    try:
        print(f"\n=== PR Creation Request ===")
        print(f"Filename: {filename}")
        print(f"Content-Type: {request.content_type}")
        print(f"Is JSON: {request.is_json}")
        
        with open(report_path, 'r') as f:
            report_data = json.load(f)
            
        metadata = report_data.get('scan_metadata', {})
        if metadata.get('repository_type') not in ['remote', 'remote_enhanced']:
            return jsonify({'success': False, 'error': 'PRs can only be created for single remote repositories'}), 400
            
        repo_name = metadata.get('repository_name')
        github_api_url = metadata.get('github_api_url')
        github_org = metadata.get('github_org')
        
        print(f"Repository: {repo_name}")
        print(f"GitHub API URL: {github_api_url}")
        print(f"GitHub Org: {github_org}")
        
        # Get selected user from request if provided
        selected_user = None
        try:
            if request.is_json:
                request_data = request.get_json(silent=True)
                if request_data:
                    selected_user = request_data.get('selected_user')
            else:
                selected_user = request.form.get('selected_user')
        except Exception as e:
            print(f"Warning: Could not parse request data: {e}")
            selected_user = None
        
        print(f"Selected user: {selected_user}")
        
        # Instantiate scanner and setup tokens manually based on the URL and Org
        scanner = WebComplianceScanner()
        
        print(f"Available GitHub instances: {list(scanner.github_instances.keys())}")
        
        # We need to find which github instance this is by URL
        matched_instance = None
        for key, val in scanner.github_instances.items():
            print(f"Checking instance '{key}': api_url={val.get('api_url')}, org={val.get('org')}")
            if val.get('api_url') == github_api_url and val.get('org') == github_org:
                matched_instance = key
                break
        
        if not matched_instance:
            print(f"ERROR: Could not match GitHub instance")
            print(f"Looking for: api_url={github_api_url}, org={github_org}")
            return jsonify({'success': False, 'error': f'Could not match GitHub instance. Looking for api_url={github_api_url}, org={github_org}'}), 400
        
        print(f"Matched instance: {matched_instance}")
        github_config = scanner.get_github_instance(matched_instance)
        
        # Extract users from the GitHub instance configuration
        users = github_config.get('users', {})
        print(f"Available users: {list(users.keys())}")
        
        if not users:
            return jsonify({'success': False, 'error': 'No users configured for this GitHub instance'}), 400
        
        # If no user selected and there are multiple users, return user list
        if not selected_user and len(users) > 1:
            user_list = list(users.keys())
            print(f"Multiple users available, requesting selection")
            return jsonify({
                'success': False, 
                'error': 'User selection required',
                'requires_user_selection': True,
                'users': user_list,
                'github_instance': matched_instance
            }), 400
        
        # Select the user (either selected or default)
        if selected_user and selected_user in users:
            user_token = users[selected_user]['token']
            print(f"Using selected user: {selected_user}")
        elif 'default_user' in users:
            user_token = users['default_user']['token']
            print(f"Using default_user")
        else:
            # Use the first available user
            first_user = list(users.keys())[0]
            user_token = users[first_user]['token']
            print(f"Using first available user: {first_user}")
        
        # Add the token to the github_config for the RemoteRepositoryScanner
        github_config['token'] = user_token
        print(f"Token configured: {'Yes' if user_token else 'No'}")
        
        remote_scanner = RemoteRepositoryScanner(github_config, scanner.whitelist_urls)
        
        print(f"Calling create_fix_pr...")
        result = remote_scanner.create_fix_pr(repo_name, report_data)
        print(f"PR creation result: {result}")
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"ERROR: Exception in create_pr: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'{type(e).__name__}: {str(e)}'}), 500

def generate_markdown_report(report_data):
    """Generate markdown report from JSON data"""
    metadata = report_data.get('scan_metadata', {})
    summary = report_data.get('scan_summary', {})
    findings = report_data.get('findings', [])
    
    md = f"""# OSS Repository Compliance Report

**Generated:** {metadata.get('scanned_at', 'Unknown')}  
**Repository:** {metadata.get('repository_path', 'Unknown')}  
**Compliance Status:** {summary.get('compliance_percentage', 0)}% ({summary.get('compliant_checks', 0)} compliant, {summary.get('non_compliant_checks', 0)} non-compliant)  
**Artifactory Base:** {metadata.get('artifactory_base', 'Unknown')}

---

## Executive Summary

This report contains {summary.get('total_findings', 0)} compliance findings with the following severity breakdown:

"""
    
    # Count by severity
    critical = len([f for f in findings if f.get('severity') == 'CRITICAL'])
    high = len([f for f in findings if f.get('severity') == 'HIGH'])
    medium = len([f for f in findings if f.get('severity') == 'MEDIUM'])
    
    md += f"""- **Critical Issues:** {critical}
- **High Priority Issues:** {high}
- **Medium Priority Issues:** {medium}

---

## Detailed Findings

"""
    
    for i, finding in enumerate(findings, 1):
        md += f"""### {i}. {finding.get('severity', 'UNKNOWN')} Issue

**File:** `{finding.get('file', 'Unknown')}`  
**Type:** {finding.get('type', 'Unknown')}  
**Issue:** {finding.get('issue', 'Unknown')}  
**Recommended Action:** {finding.get('recommended_action', 'Unknown')}

---

"""
    
    md += f"""## Approved Virtual Repositories

{yaml.dump(metadata.get('virtual_repositories', {}), default_flow_style=False)}

---

## Recommendations

1. Address all CRITICAL issues immediately
2. Configure Jenkins shared library for HIGH priority issues
3. Re-run scan after fixes to verify 100% compliance

---

*Report generated by OSS Compliance Verification Web Application*
"""
    
    return md

def generate_pdf_report(report_data, report_filename):
    """Generate PDF report from JSON data using Playwright for perfect HTML fidelity"""
    import os
    
    # Create a temporary file for the PDF
    temp_pdf = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
    
    # Render the HTML template with the report data (within app context)
    with app.app_context():
        html_content = render_template('results.html', report=report_data, report_filename=report_filename)
    
    # Use Playwright to convert HTML to PDF
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Set the HTML content
        page.set_content(html_content)
        
        # Generate PDF
        page.pdf(
            path=temp_pdf.name,
            format='A4',
            print_background=True,
            margin={
                'top': '0.5in',
                'right': '0.5in',
                'bottom': '0.5in',
                'left': '0.5in'
            }
        )
        
        browser.close()
    
    temp_pdf.close()
    return temp_pdf.name

@app.route('/config')
def config():
    """Configuration page - Redesigned version"""
    scanner = WebComplianceScanner()
    
    # Get all configuration from ConfigManager
    config_manager = get_config_manager()
    jenkins_config = config_manager.get_jenkins_config()
    app_settings = config_manager.get_app_settings()
    
    # Get Jenkins token and create hint
    jenkins_token = os.getenv('JENKINS_API_TOKEN', '')
    jenkins_token_hint = f"{jenkins_token[:4]}...{jenkins_token[-4:]}" if len(jenkins_token) > 8 else ''
    
    # Convert github_instances users dict to list for template
    github_instances_for_template = {}
    for instance_id, instance in scanner.github_instances.items():
        users_list = []
        for username, user_data in instance.get('users', {}).items():
            users_list.append({
                'username': username,
                'email': user_data.get('email', ''),
                'has_token': bool(user_data.get('token'))
            })
        
        github_instances_for_template[instance_id] = {
            'name': instance['name'],
            'api_url': instance['api_url'],
            'org': instance['org'],
            'users': users_list  # List for template iteration
        }
    
    config_data = {
        'github_instances': github_instances_for_template,
        'jenkins': {
            'user': jenkins_config.user,
            'token_hint': jenkins_token_hint,
            'urls': jenkins_config.urls
        },
        'artifactory': {
            'base': scanner.artifactory_base,
            'virtual_repos': scanner.virtual_repos,
            'user': os.getenv('ARTIFACTORY_USER', ''),
            'token_hint': ''  # Add token hint if ARTIFACTORY_TOKEN exists
        },
        'whitelist_urls': scanner.whitelist_urls,
        'app_settings': {
            'debug_logging': app_settings.debug_logging,
            'cache_ttl_hours': app_settings.cache_ttl_hours,
            'max_scan_threads': app_settings.max_scan_threads,
            'report_retention_days': app_settings.report_retention_days
        }
    }
    
    # Add artifactory token hint if exists
    artifactory_token = os.getenv('ARTIFACTORY_TOKEN', '')
    if artifactory_token and len(artifactory_token) > 8:
        config_data['artifactory']['token_hint'] = f"{artifactory_token[:4]}...{artifactory_token[-4:]}"
    
    return render_template('config_redesigned.html', config=config_data)

@app.route('/config/classic')
def config_classic():
    """Configuration page - Classic version (for backward compatibility)"""
    scanner = WebComplianceScanner()
    
    # Get all configuration from ConfigManager
    config_manager = get_config_manager()
    jenkins_config = config_manager.get_jenkins_config()
    
    # Get Jenkins token and create hint
    jenkins_token = os.getenv('JENKINS_API_TOKEN', '')
    jenkins_token_hint = f"{jenkins_token[:4]}...{jenkins_token[-4:]}" if len(jenkins_token) > 8 else ''
    
    config_data = {
        'github_instances': scanner.github_instances,
        'jenkins': {
            'user': jenkins_config.user,
            'token_hint': jenkins_token_hint,
            'urls': jenkins_config.urls
        },
        'artifactory': {
            'base': scanner.artifactory_base,
            'virtual_repos': scanner.virtual_repos,
            'user': os.getenv('ARTIFACTORY_USER', ''),
            'token_hint': ''  # Add token hint if ARTIFACTORY_TOKEN exists
        },
        'whitelist_urls': scanner.whitelist_urls,
        'app_settings': {
            'debug_logging': config_manager.get_app_settings().debug_logging
        }
    }
    
    # Add artifactory token hint if exists
    artifactory_token = os.getenv('ARTIFACTORY_TOKEN', '')
    if artifactory_token and len(artifactory_token) > 8:
        config_data['artifactory']['token_hint'] = f"{artifactory_token[:4]}...{artifactory_token[-4:]}"
    
    return render_template('config_unified.html', config=config_data)

@app.route('/test-endpoint', methods=['POST'])
def test_endpoint():
    """Test an endpoint connection with detailed validation"""
    endpoint_type = request.json.get('type')
    endpoint_url = request.json.get('url')
    token = request.json.get('token', '')
    username = request.json.get('user', '') or request.json.get('username', '')
    instance_id = request.json.get('instance_id', '') or request.json.get('endpoint_id', '')
    
    # Use ConfigManager to get configuration
    config_manager = get_config_manager()
    
    # If token not provided, try to fetch from backend
    if not token and instance_id:
        if endpoint_type == 'github':
            # Get token from GitHub instance using ConfigManager
            instance = config_manager.get_github_instance(instance_id)
            if instance:
                # Try to find the specified user or use default
                user_obj = None
                if username:
                    user_obj = instance.get_user(username)
                if not user_obj:
                    user_obj = instance.get_default_user()
                
                if user_obj:
                    token = user_obj.token
                    username = user_obj.username

                # Also get the endpoint URL from the instance
                if not endpoint_url:
                    endpoint_url = instance.api_url
        elif endpoint_type == 'jenkins':
            # Get Jenkins token using ConfigManager
            jenkins_config = config_manager.get_jenkins_config()
            token = jenkins_config.token
            if not username:
                username = jenkins_config.user
            # Get URL from config if not provided
            if not endpoint_url and jenkins_config.urls:
                # Use the URL at the specified index or first one
                try:
                    idx = int(instance_id) if instance_id else 0
                    endpoint_url = jenkins_config.urls[idx] if idx < len(jenkins_config.urls) else jenkins_config.urls[0]
                except:
                    endpoint_url = jenkins_config.urls[0]
                    
        elif endpoint_type == 'artifactory':
            # Get Artifactory token using ConfigManager
            artifactory_config = config_manager.get_artifactory_config()
            token = artifactory_config.token
            if not username:
                username = artifactory_config.user
            # Get URL from config if not provided
            if not endpoint_url:
                endpoint_url = artifactory_config.base_url
    
    # Get SSL verification setting from environment
    ssl_verify = os.getenv('SSL_VERIFY', 'false').lower() not in ('false', '0', 'no')
    
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        headers = {}
        auth = None
        
        if endpoint_type == 'github':
            # Enhanced GitHub testing with detailed validation
            if not token:
                return jsonify({
                    'success': False,
                    'error': 'GitHub token is required for testing'
                }), 400
            
            headers = {'Authorization': f'token {token}'}
            # Ensure URL ends with /user for authentication test
            test_url = endpoint_url.rstrip('/')
            if not test_url.endswith('/user'):
                test_url = f"{test_url}/user"
            
            response = requests.get(test_url, headers=headers, timeout=10, verify=ssl_verify)
            
            if response.status_code == 200:
                user_data = response.json()
                return jsonify({
                    'success': True,
                    'message': f'Successfully authenticated as {user_data.get("login", "unknown")}',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'details': {
                        'username': user_data.get('login'),
                        'name': user_data.get('name'),
                        'email': user_data.get('email'),
                        'scopes': response.headers.get('X-OAuth-Scopes', ''),
                        'token_type': response.headers.get('X-Accepted-OAuth-Scopes', '')
                    }
                })
            elif response.status_code == 401:
                return jsonify({
                    'success': False,
                    'error': 'Authentication failed',
                    'status_code': response.status_code,
                    'message': 'Invalid GitHub token. Please check your credentials.'
                }), 401
            else:
                return jsonify({
                    'success': False,
                    'error': f'Connection failed with status {response.status_code}',
                    'status_code': response.status_code,
                    'message': response.text[:200]
                }), response.status_code
                
        elif endpoint_type == 'jenkins':
            # Enhanced Jenkins testing with detailed validation
            if not username or not token:
                return jsonify({
                    'success': False,
                    'error': 'Jenkins username and token are required for testing'
                }), 400
            
            auth = HTTPBasicAuth(username, token)
            # Ensure URL doesn't have trailing slash
            endpoint_url = endpoint_url.rstrip('/')
            # Try multiple endpoints - some Jenkins instances have different paths
            test_urls = [
                f"{endpoint_url}/api/json",
                f"{endpoint_url}/me/api/json",
                f"{endpoint_url}/whoAmI/api/json"
            ]
            
            last_error = None
            for test_url in test_urls:
                try:
                    response = requests.get(test_url, headers=headers, auth=auth, timeout=10, verify=ssl_verify)
                    
                    # Jenkins returns 200 for successful auth, 403 if authenticated but no permission
                    # Both indicate the server is reachable and credentials work
                    if response.status_code == 200:
                        try:
                            jenkins_data = response.json()
                            return jsonify({
                                'success': True,
                                'message': f'Successfully authenticated to Jenkins',
                                'status_code': response.status_code,
                                'response_time': response.elapsed.total_seconds(),
                                'details': {
                                    'authenticated_as': jenkins_data.get('id', username),
                                    'display_name': jenkins_data.get('displayName', 'Unknown'),
                                    'jenkins_version': jenkins_data.get('hudson-version', 'Unknown'),
                                    'url': endpoint_url
                                }
                            })
                        except:
                            return jsonify({
                                'success': True,
                                'message': f'Successfully connected to Jenkins server',
                                'status_code': response.status_code,
                                'response_time': response.elapsed.total_seconds(),
                                'details': 'Server is reachable and authentication successful'
                            })
                    elif response.status_code == 403:
                        return jsonify({
                            'success': True,
                            'message': f'Successfully authenticated (limited permissions)',
                            'status_code': response.status_code,
                            'response_time': response.elapsed.total_seconds(),
                            'details': 'Authentication successful but user has limited permissions'
                        })
                    last_error = f"Status {response.status_code}"
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # If all attempts failed
            return jsonify({
                'success': False,
                'error': f'Could not connect to Jenkins server',
                'message': f'Tried {len(test_urls)} endpoints: {", ".join(test_urls)}. Last error: {last_error}'
            }), 503
            
        elif endpoint_type == 'artifactory':
            headers = {'X-JFrog-Art-Api': token} if token else {}
            test_url = f"https://{endpoint_url}/artifactory/api/system/ping"
            
            response = requests.get(test_url, headers=headers, timeout=10, verify=ssl_verify)
            
            if response.status_code == 200:
                return jsonify({
                    'success': True,
                    'message': f'Successfully connected to Artifactory',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'details': 'Artifactory server is reachable'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Connection failed with status {response.status_code}',
                    'status_code': response.status_code,
                    'message': response.text[:200]
                }), response.status_code
        else:
            return jsonify({'success': False, 'error': 'Unknown endpoint type'}), 400
            
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Connection timeout'}), 408
    except requests.exceptions.ConnectionError as e:
        return jsonify({'success': False, 'error': f'Connection error: {str(e)}'}), 503
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/save-endpoints', methods=['POST'])
def save_endpoints():
    """Save endpoint configuration to .env file"""
    try:
        data = request.json
        
        # Read existing .env file
        env_file = Path('.env')
        env_lines = []
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add configuration
        env_dict = {}
        for line in env_lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # Update with new values
        if 'github_instances' in data:
            for instance_id, instance_data in data['github_instances'].items():
                env_dict[f'GITHUB_INSTANCE_{instance_id}_NAME'] = instance_data.get('name', '')
                env_dict[f'GITHUB_INSTANCE_{instance_id}_API_URL'] = instance_data.get('api_url', '')
                env_dict[f'GITHUB_INSTANCE_{instance_id}_ORG'] = instance_data.get('org', '')
                if instance_data.get('token'):
                    env_dict[f'GITHUB_INSTANCE_{instance_id}_TOKEN'] = instance_data['token']
        
        if 'jenkins' in data:
            env_dict['JENKINS_USER'] = data['jenkins'].get('user', '')
            env_dict['JENKINS_URLS'] = ','.join(data['jenkins'].get('urls', []))
            if data['jenkins'].get('token'):
                env_dict['JENKINS_API_TOKEN'] = data['jenkins']['token']
        
        if 'artifactory' in data:
            env_dict['ARTIFACTORY_BASE'] = data['artifactory'].get('base', '')
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            for key, value in env_dict.items():
                f.write(f"{key}={value}\n")
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update-github-config', methods=['POST'])
def update_github_config():
    """Update GitHub instances configuration"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            github_instances = request.json.get('github_instances', {})
        else:
            import json
            github_instances_json = request.form.get('github_instances', '{}')
            github_instances = json.loads(github_instances_json)
        
        # Read existing .env file to preserve ORG settings
        env_file = Path('.env')
        env_lines = []
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add configuration
        env_dict = {}
        for line in env_lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # Preserve the existing GITHUB_INSTANCES list and ORG settings
        existing_instances = os.getenv('GITHUB_INSTANCES', '')
        if existing_instances:
            env_dict['GITHUB_INSTANCES'] = existing_instances
        
        # Remove existing GitHub instance user entries (but preserve ORG, NAME, API_URL)
        keys_to_remove = [k for k in env_dict.keys() if k.startswith('GITHUB_INSTANCE_') and ('_USERS' in k or '_TOKEN' in k)]
        for key in keys_to_remove:
            del env_dict[key]
        
        # Update user entries only (preserve ORG, NAME, API_URL from .env)
        for instance_id, instance_data in github_instances.items():
            # Handle users object (new structure)
            if instance_data.get('users'):
                # Encrypt tokens before storing
                encrypted_users = {}
                for username, user_data in instance_data['users'].items():
                    encrypted_users[username] = {
                        'token': encrypt_token(user_data.get('token', '')),
                        'email': user_data.get('email', '')
                    }
                # Store users as JSON in a single env var
                import json
                env_dict[f'GITHUB_INSTANCE_{instance_id}_USERS'] = json.dumps(encrypted_users)
            # Handle legacy token field (old structure)
            elif instance_data.get('token'):
                env_dict[f'GITHUB_INSTANCE_{instance_id}_TOKEN'] = encrypt_token(instance_data['token'])
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            for key, value in env_dict.items():
                f.write(f"{key}={value}\n")
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'GitHub configuration updated successfully'})
        else:
            flash('GitHub configuration updated successfully', 'success')
            return redirect(url_for('config'))
        
    except json.JSONDecodeError as e:
        if request.is_json:
            return jsonify({'success': False, 'error': f'Invalid JSON format: {str(e)}'}), 400
        else:
            flash(f'Invalid JSON format: {str(e)}', 'error')
            return redirect(url_for('config'))
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash(f'Error updating GitHub configuration: {str(e)}', 'error')
            return redirect(url_for('config'))

@app.route('/update-jenkins-config', methods=['POST'])
def update_jenkins_config():
    """Update Jenkins configuration"""
    try:
        jenkins_user = request.form.get('jenkins_user', '')
        jenkins_token = request.form.get('jenkins_token', '')
        jenkins_urls_str = request.form.get('jenkins_urls', '')
        
        # Read existing .env file
        env_file = Path('.env')
        env_lines = []
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add configuration
        env_dict = {}
        for line in env_lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # Update Jenkins configuration
        env_dict['JENKINS_USER'] = jenkins_user
        env_dict['JENKINS_URLS'] = jenkins_urls_str
        
        # Only update token if provided
        if jenkins_token:
            env_dict['JENKINS_API_TOKEN'] = jenkins_token
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            for key, value in env_dict.items():
                f.write(f"{key}={value}\n")
        
        flash('Jenkins configuration updated successfully', 'success')
        return redirect(url_for('config'))
        
    except Exception as e:
        flash(f'Error updating Jenkins configuration: {str(e)}', 'error')
        return redirect(url_for('config'))

@app.route('/update-artifactory-config', methods=['POST'])
def update_artifactory_config():
    """Update Artifactory configuration"""
    try:
        import json
        artifactory_base = request.form.get('artifactory_base', '')
        artifactory_token = request.form.get('artifactory_token', '')
        virtual_repos_json = request.form.get('virtual_repos', '{}')
        virtual_repos = json.loads(virtual_repos_json)
        
        # Read existing .env file
        env_file = Path('.env')
        env_lines = []
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add configuration
        env_dict = {}
        for line in env_lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # Update Artifactory configuration
        env_dict['ARTIFACTORY_BASE'] = artifactory_base
        
        # Only update token if provided
        if artifactory_token:
            env_dict['ARTIFACTORY_TOKEN'] = artifactory_token
        
        # Update virtual repositories
        keys_to_remove = [k for k in env_dict.keys() if k.startswith('VIRTUAL_REPO_')]
        for key in keys_to_remove:
            del env_dict[key]
        
        for repo_type, repo_name in virtual_repos.items():
            env_dict[f'VIRTUAL_REPO_{repo_type.upper()}'] = repo_name
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            for key, value in env_dict.items():
                f.write(f"{key}={value}\n")
        
        flash('Artifactory configuration updated successfully', 'success')
        return redirect(url_for('config'))
        
    except json.JSONDecodeError as e:
        flash(f'Invalid JSON format: {str(e)}', 'error')
        return redirect(url_for('config'))
    except Exception as e:
        flash(f'Error updating Artifactory configuration: {str(e)}', 'error')
        return redirect(url_for('config'))

@app.route('/update-whitelist-config', methods=['POST'])
def update_whitelist_config():
    """Update whitelist URLs configuration"""
    try:
        whitelist_urls_str = request.form.get('whitelist_urls', '')
        whitelist_urls = [url.strip() for url in whitelist_urls_str.split('\n') if url.strip()]
        
        # Read existing .env file
        env_file = Path('.env')
        env_lines = []
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add configuration
        env_dict = {}
        for line in env_lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # Update whitelist URLs
        env_dict['WHITELIST_URLS'] = ','.join(whitelist_urls)
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            for key, value in env_dict.items():
                f.write(f"{key}={value}\n")
        
        flash('Whitelist URLs updated successfully', 'success')
        return redirect(url_for('config'))
        
    except Exception as e:
        flash(f'Error updating whitelist URLs: {str(e)}', 'error')
        return redirect(url_for('config'))

@app.route('/update-app-settings', methods=['POST'])
def update_app_settings():
    """Update application settings including debug logging"""
    try:
        debug_logging = request.form.get('debug_logging') == 'true'
        cache_ttl = int(request.form.get('cache_ttl', 1))
        max_threads = int(request.form.get('max_threads', 4))
        retention_days = int(request.form.get('retention_days', 90))
        
        # Validate inputs
        cache_ttl = max(1, min(24, cache_ttl))
        max_threads = max(1, min(16, max_threads))
        retention_days = max(7, min(365, retention_days))
        
        # Update configuration using ConfigManager
        config_manager = get_config_manager()
        config_manager.update_config({
            'app_settings': {
                'debug_logging': debug_logging,
                'cache_ttl_hours': cache_ttl,
                'max_scan_threads': max_threads,
                'report_retention_days': retention_days
            }
        })
        
        # Update global debug logging flag in app.py
        set_debug_logging(debug_logging)
        
        # Update debug logging flag in remote_scanner.py
        try:
            from remote_scanner import set_debug_logging as set_remote_debug_logging
            set_remote_debug_logging(debug_logging)
        except ImportError:
            pass  # remote_scanner might not be imported yet
        
        flash('Application settings updated successfully', 'success')
        return redirect(url_for('config'))
        
    except Exception as e:
        flash(f'Error updating app settings: {str(e)}', 'error')
        return redirect(url_for('config'))

@app.route('/api/endpoint/<endpoint_type>/<instance_id>', methods=['GET'])
def get_endpoint(endpoint_type, instance_id):
    """Get endpoint details for editing"""
    try:
        scanner = WebComplianceScanner()
        
        if endpoint_type == 'github':
            if instance_id in scanner.github_instances:
                instance = scanner.github_instances[instance_id]
                return jsonify({
                    'success': True,
                    'name': instance.get('name', ''),
                    'api_url': instance.get('api_url', ''),
                    'org': instance.get('org', '')
                })
        elif endpoint_type == 'artifactory':
            return jsonify({
                'success': True,
                'base': scanner.artifactory_base,
                'user': os.getenv('ARTIFACTORY_USER', '')
            })
        elif endpoint_type == 'jenkins':
            config_manager = get_config_manager()
            jenkins_config = config_manager.get_jenkins_config()
            if jenkins_config and jenkins_config.urls:
                try:
                    idx = int(instance_id)
                    if 0 <= idx < len(jenkins_config.urls):
                        return jsonify({
                            'success': True,
                            'url': jenkins_config.urls[idx],
                            'user': jenkins_config.user
                        })
                except ValueError:
                    pass
            return jsonify({'success': False, 'message': 'Jenkins endpoint not found'}), 404
        
        return jsonify({'success': False, 'message': 'Endpoint not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/github-users/<instance_id>', methods=['GET'])
def get_github_users(instance_id):
    """Get all users for a GitHub instance"""
    try:
        config_manager = get_config_manager()
        instance = config_manager.get_github_instance(instance_id)
        
        if instance:
            # Convert GitHubUser objects to dicts for JSON response
            users = [
                {
                    'username': user.username,
                    'email': user.email,
                    'has_token': bool(user.token)
                }
                for user in instance.users
            ]
            return jsonify({
                'success': True,
                'users': users
            })
        
        return jsonify({'success': False, 'message': 'Instance not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/github-user/<instance_id>/<username>', methods=['GET'])
def get_github_user(instance_id, username):
    """Get specific user details"""
    try:
        config_manager = get_config_manager()
        instance = config_manager.get_github_instance(instance_id)
        
        if instance:
            user = instance.get_user(username)
            if user:
                # Create token hint if token exists
                token_hint = ''
                if user.token and len(user.token) > 8:
                    token_hint = f"{user.token[:4]}...{user.token[-4:]}"
                
                return jsonify({
                    'success': True,
                    'username': user.username,
                    'email': user.email,
                    'has_token': bool(user.token),
                    'token_hint': token_hint
                })
        
        return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/github-user/<instance_id>/<username>', methods=['DELETE'])
def delete_github_user(instance_id, username):
    """Delete a GitHub user"""
    try:
        config_manager = get_config_manager()
        github_instances = config_manager.get_github_instances()
        
        if instance_id not in github_instances:
            return jsonify({'success': False, 'message': 'Instance not found'}), 404
        
        # Load current config to get the users list
        config_path = Path('config/app_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        github_instances_data = config.get('github_instances', {})
        users = github_instances_data[instance_id].get('users', [])
        github_instances_data[instance_id]['users'] = [u for u in users if u.get('username') != username]
        
        # Update using ConfigManager for consistency
        updates = {
            'github_instances': {
                instance_id: {
                    'users': github_instances_data[instance_id]['users']
                }
            }
        }
        
        config_manager.update_config(updates, validate=False)
        
        return jsonify({'success': True, 'message': 'User deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/github-instance/<instance_id>', methods=['DELETE'])
def delete_github_instance(instance_id):
    """Delete a GitHub instance"""
    try:
        # Load current config to get the full structure
        config_path = Path('config/app_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        github_instances_data = config.get('github_instances', {})
        
        if instance_id not in github_instances_data:
            return jsonify({'success': False, 'message': 'Instance not found'}), 404
        
        # Check if this is the last instance - prevent deletion if it would leave zero instances
        if len(github_instances_data) <= 1:
            return jsonify({'success': False, 'message': 'Cannot delete the last GitHub instance. At least one instance must be configured.'}), 400
        
        # Delete the instance
        del github_instances_data[instance_id]
        
        # Write the updated config back to file directly
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        # Reload config manager to ensure changes are reflected
        reload_config()
        
        return jsonify({'success': True, 'message': 'GitHub instance deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/update-github-user', methods=['POST'])
def update_github_user():
    """Add or update a GitHub user"""
    try:
        instance_id = request.form.get('instance_id')
        username = request.form.get('username')
        email = request.form.get('email', '')
        token = request.form.get('token')
        
        config_manager = get_config_manager()
        github_instances = config_manager.get_github_instances()
        
        if instance_id not in github_instances:
            flash('GitHub instance not found', 'error')
            return redirect(url_for('config'))
        
        # Load current config to get the users list
        config_path = Path('config/app_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        github_instances_data = config.get('github_instances', {})
        users = github_instances_data[instance_id].get('users', [])
        
        # Check if user exists
        user_exists = False
        for user in users:
            if user.get('username') == username:
                user['email'] = email
                # Update token if provided
                if token:
                    user['token_encrypted'] = encrypt_token(token)
                user_exists = True
                break
        
        # Add new user if doesn't exist
        if not user_exists:
            new_user = {
                'username': username,
                'email': email
            }
            # Add encrypted token if provided
            if token:
                new_user['token_encrypted'] = encrypt_token(token)
            users.append(new_user)
        
        # Update using ConfigManager for consistency
        updates = {
            'github_instances': {
                instance_id: {
                    'users': users
                }
            }
        }
        
        config_manager.update_config(updates, validate=False)
        
        flash(f'User {username} saved successfully', 'success')
        return redirect(url_for('config'))
        
    except Exception as e:
        flash(f'Error saving user: {str(e)}', 'error')
        return redirect(url_for('config'))

@app.route('/update-endpoint', methods=['POST'])
def update_endpoint():
    """Unified endpoint update for GitHub/Jenkins/Artifactory"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()
        
        endpoint_type = data.get('type') or data.get('endpoint_type')
        
        config_manager = get_config_manager()
        
        if endpoint_type == 'github':
            # Get form field values (support both old and new field names)
            instance_id = data.get('instance_id') or data.get('endpoint_id')
            instance_name = data.get('endpoint_name') or data.get('name')
            api_url = data.get('endpoint_url') or data.get('url')
            org = data.get('endpoint_org') or data.get('org')
            
            # If no instance_id, create one from the name
            if not instance_id and instance_name:
                instance_id = instance_name.lower().replace(' ', '_').replace('-', '_')
            
            # Load current config to get existing users
            config_path = Path('config/app_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            github_instances = config.get('github_instances', {})
            
            if instance_id not in github_instances:
                # Create new instance
                github_instances[instance_id] = {
                    'name': instance_name,
                    'api_url': api_url,
                    'org': org,
                    'users': []
                }
            else:
                # Update existing instance
                github_instances[instance_id]['name'] = instance_name
                github_instances[instance_id]['api_url'] = api_url
                github_instances[instance_id]['org'] = org
            
            # Ensure users is a list
            if 'users' not in github_instances[instance_id]:
                github_instances[instance_id]['users'] = []
            
            # Handle user if provided (for backward compatibility)
            username = data.get('user') or data.get('endpoint_user')
            if username:
                user_exists = False
                
                for user in github_instances[instance_id]['users']:
                    if user['username'] == username:
                        user['email'] = data.get('email', '')
                        # Update token if provided
                        if data.get('token'):
                            user['token_encrypted'] = encrypt_token(data.get('token'))
                        user_exists = True
                        break
                
                if not user_exists:
                    new_user = {
                        'username': username,
                        'email': data.get('email', '')
                    }
                    # Add encrypted token if provided
                    if data.get('token'):
                        new_user['token_encrypted'] = encrypt_token(data.get('token'))
                    github_instances[instance_id]['users'].append(new_user)
            
            # Update using ConfigManager for consistency
            updates = {
                'github_instances': {
                    instance_id: github_instances[instance_id]
                }
            }
            
            config_manager.update_config(updates, validate=False)
            
        elif endpoint_type == 'jenkins':
            # Get form field values
            jenkins_url = data.get('endpoint_url') or data.get('url')
            jenkins_user = data.get('endpoint_user') or data.get('user')
            jenkins_token = data.get('endpoint_token') or data.get('token')
            instance_id = data.get('instance_id')
            
            # Load current config to get existing Jenkins config
            config_path = Path('config/app_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            jenkins = config.get('jenkins', {})
            jenkins['user'] = jenkins_user
            
            # Initialize URLs list if not exists
            if 'urls' not in jenkins:
                jenkins['urls'] = []
            
            # Update existing URL or add new one
            if jenkins_url:
                if instance_id is not None:
                    try:
                        idx = int(instance_id)
                        # Update existing URL at the specified index
                        if 0 <= idx < len(jenkins['urls']):
                            jenkins['urls'][idx] = jenkins_url
                        else:
                            # If index is out of bounds, append as new
                            if jenkins_url not in jenkins['urls']:
                                jenkins['urls'].append(jenkins_url)
                    except ValueError:
                        # If instance_id is not a valid integer, append as new
                        if jenkins_url not in jenkins['urls']:
                            jenkins['urls'].append(jenkins_url)
                else:
                    # No instance_id provided, append as new
                    if jenkins_url not in jenkins['urls']:
                        jenkins['urls'].append(jenkins_url)
            
            # Save encrypted token if provided
            if jenkins_token:
                jenkins['token_encrypted'] = encrypt_token(jenkins_token)
            
            # Update using ConfigManager for consistency
            updates = {
                'jenkins': jenkins
            }
            
            config_manager.update_config(updates, validate=False)
            
        elif endpoint_type == 'artifactory':
            # Get form field values
            artifactory_url = data.get('endpoint_url') or data.get('url')
            artifactory_user = data.get('endpoint_user') or data.get('user')
            artifactory_token = data.get('endpoint_token') or data.get('token')
            
            # Load current config to get existing Artifactory config
            config_path = Path('config/app_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            artifactory = config.get('artifactory', {})
            artifactory['base_url'] = artifactory_url
            
            # Save encrypted token if provided
            if artifactory_token:
                artifactory['token_encrypted'] = encrypt_token(artifactory_token)
            
            # Save username if provided
            if artifactory_user:
                artifactory['user'] = artifactory_user
            
            # Update using ConfigManager for consistency
            updates = {
                'artifactory': artifactory
            }
            
            config_manager.update_config(updates, validate=False)
        
        # Return appropriate response based on request type
        if request.is_json:
            return jsonify({'success': True, 'message': 'Endpoint updated successfully'})
        else:
            flash(f'{endpoint_type.capitalize()} endpoint updated successfully', 'success')
            return redirect(url_for('config'))
        
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash(f'Error updating endpoint: {str(e)}', 'error')
            return redirect(url_for('config'))

@app.route('/delete-endpoint', methods=['POST'])
def delete_endpoint():
    """Unified endpoint deletion for GitHub/Jenkins/Artifactory"""
    try:
        data = request.json
        endpoint_type = data.get('type')
        
        if endpoint_type == 'github':
            instance_id = data.get('endpoint_id')
            username = data.get('user')
            
            # Load YAML directly
            config_path = Path('config/app_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            github_instances = config.get('github_instances', {})
            
            if username:
                # Delete user from instance
                if instance_id in github_instances:
                    users = github_instances[instance_id].get('users', [])
                    github_instances[instance_id]['users'] = [
                        u for u in users if u['username'] != username
                    ]
            else:
                # Delete entire instance
                if instance_id in github_instances:
                    del github_instances[instance_id]
            
            # Save back to YAML
            config['github_instances'] = github_instances
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            # Reload config
            from config_manager import reload_config
            reload_config()
            
        elif endpoint_type == 'jenkins':
            url = data.get('url')
            
            # Load YAML directly
            config_path = Path('config/app_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            jenkins = config.get('jenkins', {})
            urls = jenkins.get('urls', [])
            
            if url in urls:
                urls.remove(url)
                jenkins['urls'] = urls
            
            # Save back to YAML
            config['jenkins'] = jenkins
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            # Reload config
            from config_manager import reload_config
            reload_config()
        
        return jsonify({'success': True, 'message': 'Endpoint deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update-repos-whitelist', methods=['POST'])
def update_repos_whitelist():
    """Update virtual repositories and whitelist URLs"""
    try:
        config_manager = get_config_manager()
        
        # Get virtual repos from table inputs (new format)
        repo_types = request.form.getlist('repo_type[]')
        repo_names = request.form.getlist('repo_name[]')
        
        virtual_repos = {}
        for pkg_type, repo_name in zip(repo_types, repo_names):
            if pkg_type.strip() and repo_name.strip():
                virtual_repos[pkg_type.strip()] = repo_name.strip()
        
        # Update artifactory config
        artifactory_config = config_manager.get_artifactory_config()
        artifactory_config.virtual_repos = virtual_repos
        config_manager.update_artifactory_config(artifactory_config)
        
        # Get whitelist URLs from tag inputs (new format)
        whitelist_urls = request.form.getlist('whitelist_url[]')
        whitelist_urls = [url.strip() for url in whitelist_urls if url.strip()]
        config_manager.update_whitelist_urls(whitelist_urls)
        
        flash('Configuration updated successfully', 'success')
        return redirect(url_for('config'))
        
    except Exception as e:
        flash(f'Error updating configuration: {str(e)}', 'error')
        return redirect(url_for('config'))

@app.route('/api/pr/submit', methods=['POST'])
def submit_pr():
    """Create a PR with automated compliance fixes"""
    try:
        data = request.json
        
        # Get required parameters
        report_filename = data.get('report_filename')
        submitter_username = data.get('submitter_username')
        submitter_email = data.get('submitter_email')
        github_instance_id = data.get('github_instance')
        
        if not all([report_filename, submitter_username, submitter_email]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        
        # Load the report data
        report_path = Path(app.config['REPORTS_FOLDER']) / report_filename
        if not report_path.exists():
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        # Get the report record from database
        report_record = Report.query.filter_by(filename=report_filename).first()
        if not report_record:
            return jsonify({'success': False, 'error': 'Report record not found in database'}), 404
        
        # Get GitHub instance configuration
        scanner = WebComplianceScanner()
        github_config = scanner.get_github_instance(github_instance_id) if github_instance_id else list(scanner.github_instances.values())[0]
        
        # Create PR submission service
        pr_service = PRSubmissionService(
            github_instance_config=github_config,
            artifactory_base=scanner.artifactory_base,
            virtual_repos=scanner.virtual_repos
        )
        
        # Create the PR
        pr_result = pr_service.create_pr_for_fixes(
            report_data=report_data,
            submitter_username=submitter_username,
            submitter_email=submitter_email,
            github_instance_id=github_instance_id
        )
        
        if not pr_result.get('success'):
            # Create failed PR submission record
            pr_submission = PRSubmission(
                report_id=report_record.id,
                repository_name=report_record.repository_name,
                github_org=report_record.github_org,
                github_instance=github_instance_id,
                submitter_github_username=submitter_username,
                submitter_email=submitter_email,
                status='failed',
                error_message=pr_result.get('error', 'Unknown error')
            )
            db.session.add(pr_submission)
            db.session.commit()
            
            return jsonify({'success': False, 'error': pr_result.get('error')}), 500
        
        # Create successful PR submission record
        pr_submission = PRSubmission(
            report_id=report_record.id,
            repository_name=report_record.repository_name,
            github_org=report_record.github_org,
            github_instance=github_instance_id,
            submitter_github_username=submitter_username,
            submitter_email=submitter_email,
            pr_number=pr_result.get('pr_number'),
            pr_title=pr_result.get('pr_title'),
            pr_url=pr_result.get('pr_url'),
            branch_name=pr_result.get('branch_name'),
            base_branch=pr_result.get('base_branch'),
            status='created',
            github_status='open',
            jenkins_status=pr_result.get('jenkins', {}).get('success') and 'pending' or 'not_triggered',
            jenkins_job_url=pr_result.get('jenkins', {}).get('jenkins_job_url'),
            jenkins_build_number=pr_result.get('jenkins', {}).get('jenkins_build_number'),
            jenkins_build_url=pr_result.get('jenkins', {}).get('jenkins_build_url'),
            fixes_applied=json.dumps(pr_result.get('fixes_applied', []))
        )
        db.session.add(pr_submission)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'pr_submission': pr_submission.to_dict(),
            'pr_result': pr_result
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pr/<int:pr_submission_id>/status', methods=['GET'])
def get_pr_status(pr_submission_id):
    """Get the status of a PR submission"""
    try:
        pr_submission = PRSubmission.query.get_or_404(pr_submission_id)
        
        # If PR is still open, check GitHub status
        if pr_submission.github_status == 'open' and pr_submission.pr_number:
            scanner = WebComplianceScanner()
            github_config = scanner.get_github_instance(pr_submission.github_instance) if pr_submission.github_instance else list(scanner.github_instances.values())[0]
            
            pr_service = PRSubmissionService(github_instance_config=github_config)
            status_result = pr_service.get_pr_status(
                pr_submission.github_org,
                pr_submission.repository_name,
                pr_submission.pr_number
            )
            
            if status_result.get('success'):
                pr_submission.github_status = status_result.get('state', 'unknown')
                if status_result.get('merged'):
                    pr_submission.github_status = 'merged'
                    pr_submission.status = 'merged'
                elif status_result.get('state') == 'closed':
                    pr_submission.github_status = 'closed'
                    pr_submission.status = 'closed'
                
                pr_submission.updated_at = datetime.utcnow()
                db.session.commit()
        
        return jsonify({'success': True, 'pr_submission': pr_submission.to_dict()})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pr/submissions', methods=['GET'])
def list_pr_submissions():
    """List all PR submissions, optionally filtered by repository"""
    try:
        repository_filter = request.args.get('repository')
        status_filter = request.args.get('status')
        
        query = PRSubmission.query
        
        if repository_filter:
            query = query.filter(PRSubmission.repository_name == repository_filter)
        
        if status_filter:
            query = query.filter(PRSubmission.status == status_filter)
        
        submissions = query.order_by(PRSubmission.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'submissions': [submission.to_dict() for submission in submissions]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Load debug logging setting from config
    try:
        config_manager = get_config_manager()
        app_settings = config_manager.get_app_settings()
        set_debug_logging(app_settings.debug_logging)
        
        # Also set debug logging in remote_scanner
        try:
            from remote_scanner import set_debug_logging as set_remote_debug_logging
            set_remote_debug_logging(app_settings.debug_logging)
        except ImportError:
            pass  # remote_scanner might not be available
        
        print(f"Debug logging: {'enabled' if app_settings.debug_logging else 'disabled'}")
    except Exception as e:
        print(f"Warning: Could not load debug logging setting from config: {e}")
        print("Debug logging: enabled (default)")
    
    # Run Flask with debug mode from environment variable
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5001)
