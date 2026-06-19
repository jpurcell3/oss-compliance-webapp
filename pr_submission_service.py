#!/usr/bin/env python3
"""
PR Submission Service for OSS Compliance
Handles GitHub PR creation and Jenkins pipeline integration for compliance fixes
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import urllib3
from fix_generator import FixGenerator

# Suppress InsecureRequestWarning when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PRSubmissionService:
    """Service for creating PRs with automated compliance fixes"""
    
    def __init__(self, github_instance_config=None, artifactory_base=None, virtual_repos=None):
        if github_instance_config:
            self.github_api_url = github_instance_config.get('api_url', 'https://api.github.com')
            self.github_token = github_instance_config.get('token')
            self.github_org = github_instance_config.get('org')
        else:
            # Fall back to environment variables
            self.github_api_url = os.getenv('GITHUB_API_URL', 'https://api.github.com')
            self.github_token = os.getenv('GITHUB_TOKEN')
            self.github_org = os.getenv('GITHUB_ORG')
        
        self.ssl_verify = os.getenv('SSL_VERIFY', 'true').lower() == 'true'
        
        # Jenkins configuration
        self.jenkins_user = os.getenv('JENKINS_USER')
        self.jenkins_token = os.getenv('JENKINS_API_TOKEN')
        self.jenkins_pr_validation_job = os.getenv('JENKINS_PR_VALIDATION_JOB', 'oss-compliance-validation')
        
        # Artifactory configuration for fix generation
        self.artifactory_base = artifactory_base or os.getenv('ARTIFACTORY_BASE', 'isgedge.artifactory.cec.lab.emc.com')
        self.virtual_repos = virtual_repos or self._load_virtual_repos()
        
        # Initialize fix generator
        self.fix_generator = FixGenerator(self.artifactory_base, self.virtual_repos)
        
        # Session for API calls
        self.session = requests.Session()
        self.session.verify = self.ssl_verify
        
        # Set up authentication
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
    
    def _load_virtual_repos(self) -> Dict:
        """Load virtual repositories from environment or config file"""
        import yaml
        
        # Try to load from config file first
        config_file = Path('config/virtual_repos.yaml')
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        
        # Fall back to environment variables
        env_repos = {}
        for key, value in os.environ.items():
            if key.startswith('VIRTUAL_REPO_'):
                repo_type = key.replace('VIRTUAL_REPO_', '').lower()
                env_repos[repo_type] = value
        
        return env_repos if env_repos else {
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
    
    def create_pr_for_fixes(self, report_data: Dict, submitter_username: str, 
                           submitter_email: str, github_instance_id: str = None) -> Dict:
        """
        Create a PR with automated fixes for compliance issues
        
        Args:
            report_data: The compliance report data
            submitter_username: GitHub username of the submitter
            submitter_email: Email of the submitter
            github_instance_id: ID of the GitHub instance to use
            
        Returns:
            Dictionary with PR creation results
        """
        try:
            # Extract repository information
            scan_metadata = report_data.get('scan_metadata', {})
            repo_name = scan_metadata.get('repository_name', '')
            github_org = scan_metadata.get('github_org', self.github_org)
            
            if not repo_name:
                return {
                    'success': False,
                    'error': 'Repository name not found in report data'
                }
            
            # Generate branch name with retry logic
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            branch_name = f"oss-compliance-fixes-{timestamp}"

            # Get the base branch (default to main)
            base_branch = self._get_default_branch(github_org, repo_name)

            # Create branch
            branch_created = self._create_branch(github_org, repo_name, branch_name, base_branch)
            if not branch_created['success']:
                # If branch already exists, add a suffix and retry
                if 'already exists' in branch_created.get('error', '').lower():
                    for i in range(1, 10):
                        alt_branch_name = f"oss-compliance-fixes-{timestamp}-{i}"
                        alt_result = self._create_branch(github_org, repo_name, alt_branch_name, base_branch)
                        if alt_result['success']:
                            branch_name = alt_branch_name
                            branch_created = alt_result
                            print(f"Using alternative branch name: {branch_name}")
                            break
                    else:
                        return {
                            'success': False,
                            'error': f"Could not create branch after multiple attempts: {branch_created['error']}"
                        }
                else:
                    return branch_created
            
            # Generate and apply fixes
            fixes_result = self._apply_fixes_to_branch(github_org, repo_name, branch_name, report_data)
            if not fixes_result['success']:
                return fixes_result
            
            # Create PR
            pr_result = self._create_pull_request(
                github_org, repo_name, branch_name, base_branch,
                submitter_username, submitter_email, report_data
            )
            
            if pr_result['success']:
                # Trigger Jenkins validation
                jenkins_result = self._trigger_jenkins_validation(
                    github_org, repo_name, pr_result['pr_number']
                )
                pr_result['jenkins'] = jenkins_result
            
            return pr_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create PR: {str(e)}'
            }
    
    def _get_default_branch(self, github_org: str, repo_name: str) -> str:
        """Get the default branch for a repository"""
        try:
            url = f"{self.github_api_url}/repos/{github_org}/{repo_name}"
            response = self.session.get(url)
            response.raise_for_status()
            repo_data = response.json()
            default_branch = repo_data.get('default_branch', 'main')
            print(f"Default branch for {github_org}/{repo_name}: {default_branch}")
            return default_branch
        except Exception as e:
            print(f"Error getting default branch: {e}")
            return 'main'
    
    def _create_branch(self, github_org: str, repo_name: str,
                      branch_name: str, base_branch: str) -> Dict:
        """Create a new branch from the base branch"""
        try:
            print(f"Attempting to create branch '{branch_name}' from '{base_branch}' in {github_org}/{repo_name}")

            # Check if branch already exists
            existing_branch_url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/git/refs/heads/{branch_name}"
            existing_response = self.session.get(existing_branch_url)
            if existing_response.status_code == 200:
                print(f"Branch '{branch_name}' already exists, using existing branch")
                return {
                    'success': True,
                    'branch_name': branch_name,
                    'existing': True,
                    'message': 'Branch already exists, using existing branch'
                }

            # Get the SHA of the base branch
            url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/git/refs/heads/{base_branch}"
            response = self.session.get(url)
            if response.status_code == 404:
                # Try to get list of available branches
                branches_url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/branches"
                branches_response = self.session.get(branches_url)
                if branches_response.status_code == 200:
                    branches = branches_response.json()
                    branch_names = [b['name'] for b in branches]
                    return {
                        'success': False,
                        'error': f"Base branch '{base_branch}' not found in repository. Available branches: {', '.join(branch_names[:5])}{'...' if len(branch_names) > 5 else ''}"
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Base branch '{base_branch}' not found and could not retrieve available branches"
                    }
            response.raise_for_status()
            base_sha = response.json()['object']['sha']
            print(f"Got base SHA: {base_sha}")

            # Create the new branch
            url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/git/refs"
            data = {
                'ref': f'refs/heads/{branch_name}',
                'sha': base_sha
            }
            response = self.session.post(url, json=data)
            if response.status_code == 422:
                error_data = response.json()
                return {
                    'success': False,
                    'error': f"Branch creation failed (422): {error_data.get('message', 'Unknown error')}. Details: {error_data}"
                }
            response.raise_for_status()

            print(f"Successfully created branch '{branch_name}'")
            return {
                'success': True,
                'branch_name': branch_name,
                'base_sha': base_sha,
                'existing': False
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create branch: {str(e)}'
            }
    
    def _apply_fixes_to_branch(self, github_org: str, repo_name: str, 
                              branch_name: str, report_data: Dict) -> Dict:
        """Apply automated fixes to the branch"""
        try:
            fixes_applied = []
            findings = report_data.get('findings', [])
            
            for finding in findings:
                if finding.get('severity') in ['critical', 'high']:
                    fix_result = self._apply_fix_for_finding(github_org, repo_name, branch_name, finding)
                    if fix_result['success']:
                        fixes_applied.append(fix_result['fix'])
            
            return {
                'success': True,
                'fixes_applied': fixes_applied,
                'total_fixes': len(fixes_applied)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to apply fixes: {str(e)}'
            }
    
    def _apply_fix_for_finding(self, github_org: str, repo_name: str, 
                              branch_name: str, finding: Dict) -> Dict:
        """Apply a fix for a specific finding"""
        try:
            file_path = finding.get('file', '')
            finding_type = finding.get('type', '')
            
            if not file_path:
                return {'success': False, 'error': 'No file path in finding'}
            
            # Get current file content
            url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/contents/{file_path}"
            params = {'ref': branch_name}
            response = self.session.get(url, params=params)
            
            if response.status_code == 404:
                return {'success': False, 'error': f'File not found: {file_path}'}
            
            response.raise_for_status()
            file_data = response.json()
            current_content = file_data.get('content', '')
            current_sha = file_data.get('sha', '')
            
            # Decode base64 content
            import base64
            decoded_content = base64.b64decode(current_content).decode('utf-8')
            
            # Apply fix based on finding type
            fixed_content = self._generate_fix_for_type(decoded_content, finding_type, finding)
            
            # Encode back to base64
            encoded_content = base64.b64encode(fixed_content.encode('utf-8')).decode('utf-8')
            
            # Update file
            url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/contents/{file_path}"
            data = {
                'message': f"Fix compliance issue: {finding.get('issue', 'Unknown')}",
                'content': encoded_content,
                'sha': current_sha,
                'branch': branch_name
            }
            response = self.session.put(url, json=data)
            response.raise_for_status()
            
            return {
                'success': True,
                'fix': {
                    'file': file_path,
                    'type': finding_type,
                    'issue': finding.get('issue', ''),
                    'action': finding.get('recommended_action', '')
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to apply fix for {file_path}: {str(e)}'
            }
    
    def _generate_fix_for_type(self, content: str, finding_type: str, finding: Dict) -> str:
        """Generate fixed content based on finding type"""
        # Use the fix generator to generate the fix
        return self.fix_generator.generate_fix(content, finding)
    
    def _create_pull_request(self, github_org: str, repo_name: str, branch_name: str,
                           base_branch: str, submitter_username: str, 
                           submitter_email: str, report_data: Dict) -> Dict:
        """Create a pull request"""
        try:
            # Generate PR title and description
            scan_metadata = report_data.get('scan_metadata', {})
            findings = report_data.get('findings', [])
            critical_count = sum(1 for f in findings if f.get('severity') == 'critical')
            high_count = sum(1 for f in findings if f.get('severity') == 'high')
            
            title = f"[OSS Compliance] Fix {critical_count + high_count} compliance issues in {repo_name}"
            
            description = f"""## OSS Compliance Fixes

This PR addresses compliance issues found in the repository.

**Submitted by:** {submitter_username} ({submitter_email})
**Scan Date:** {scan_metadata.get('scanned_at', 'Unknown')}
**Repository:** {github_org}/{repo_name}

### Issues Fixed
- **Critical Issues:** {critical_count}
- **High Issues:** {high_count}

### Changes Made
This PR includes automated fixes for the following compliance issues:

"""
            # Add details for each finding
            for finding in findings:
                if finding.get('severity') in ['critical', 'high']:
                    description += f"- **{finding.get('file', 'Unknown')}**: {finding.get('issue', 'Unknown')}\n"
                    description += f"  - Action: {finding.get('recommended_action', 'See report')}\n\n"
            
            description += f"""
### Validation
A Jenkins validation job has been triggered to verify these changes.

### Compliance Report
For detailed information about these findings, please refer to the full compliance report.

---
*This PR was automatically generated by the OSS Compliance Tool*
"""
            
            # Create PR
            url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/pulls"
            data = {
                'title': title,
                'body': description,
                'head': branch_name,
                'base': base_branch
            }
            response = self.session.post(url, json=data)
            response.raise_for_status()
            pr_data = response.json()
            
            return {
                'success': True,
                'pr_number': pr_data['number'],
                'pr_url': pr_data['html_url'],
                'pr_title': pr_data['title'],
                'branch_name': branch_name,
                'base_branch': base_branch
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create PR: {str(e)}'
            }
    
    def _trigger_jenkins_validation(self, github_org: str, repo_name: str, pr_number: int) -> Dict:
        """Trigger Jenkins validation job for the PR"""
        try:
            if not self.jenkins_user or not self.jenkins_token:
                return {
                    'success': False,
                    'error': 'Jenkins credentials not configured'
                }
            
            # Get Jenkins URL from environment
            jenkins_urls = [url.strip() for url in os.getenv('JENKINS_URLS', '').split(',') if url.strip()]
            if not jenkins_urls:
                return {
                    'success': False,
                    'error': 'Jenkins URL not configured'
                }
            
            jenkins_url = jenkins_urls[0]
            
            # Trigger the job with parameters
            job_url = f"{jenkins_url}/job/{self.jenkins_pr_validation_job}/buildWithParameters"
            auth = (self.jenkins_user, self.jenkins_token)
            
            params = {
                'GITHUB_ORG': github_org,
                'REPO_NAME': repo_name,
                'PR_NUMBER': str(pr_number)
            }
            
            response = self.session.post(job_url, auth=auth, params=params)
            response.raise_for_status()
            
            # Get the queue location to find the build number
            queue_url = response.headers.get('Location', '')
            if queue_url:
                # Try to get build info from queue
                try:
                    queue_response = self.session.get(queue_url, auth=auth)
                    queue_response.raise_for_status()
                    queue_data = queue_response.json()
                    
                    # Get the executable URL which contains the build number
                    executable_url = queue_data.get('executable', {}).get('url', '')
                    if executable_url:
                        build_number = executable_url.split('/')[-2].rstrip('/')
                        return {
                            'success': True,
                            'jenkins_job_url': job_url,
                            'jenkins_build_number': build_number,
                            'jenkins_build_url': executable_url
                        }
                except:
                    pass
            
            return {
                'success': True,
                'jenkins_job_url': job_url,
                'jenkins_build_url': f"{jenkins_url}/job/{self.jenkins_pr_validation_job}/"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to trigger Jenkins: {str(e)}'
            }
    
    def get_pr_status(self, github_org: str, repo_name: str, pr_number: int) -> Dict:
        """Get the current status of a PR"""
        try:
            url = f"{self.github_api_url}/repos/{github_org}/{repo_name}/pulls/{pr_number}"
            response = self.session.get(url)
            response.raise_for_status()
            pr_data = response.json()
            
            return {
                'success': True,
                'state': pr_data.get('state', 'unknown'),
                'merged': pr_data.get('merged', False),
                'mergeable': pr_data.get('mergeable', None),
                'title': pr_data.get('title', ''),
                'html_url': pr_data.get('html_url', '')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get PR status: {str(e)}'
            }