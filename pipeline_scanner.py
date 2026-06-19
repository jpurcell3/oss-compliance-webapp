#!/usr/bin/env python3
"""
Pipeline-Centric OSS Compliance Scanner
This module makes pipeline configurations the authoritative source for repository detection
rather than dependency files like req.txt, go.mod, etc.
"""

import os
import re
import json
import requests
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
from dotenv import load_dotenv
import urllib3
from urllib.parse import urlparse

# Suppress InsecureRequestWarning when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()


class PipelineRepositoryScanner:
    """
    Pipeline-centric scanner that treats pipeline configurations as the authoritative 
    source for determining which repositories are actually used by a project.
    """
    
    def __init__(self, github_instance_config=None, whitelist_urls=None):
        if github_instance_config:
            self.github_api_url = github_instance_config.get('api_url', 'https://api.github.com')
            self.github_token = github_instance_config.get('token')
            self.github_org = github_instance_config.get('org')
        else:
            self.github_api_url = os.getenv('GITHUB_API_URL', 'https://api.github.com')
            self.github_token = os.getenv('GITHUB_TOKEN')
            self.github_org = os.getenv('GITHUB_ORG')
        
        # Jenkins configuration
        self.jenkins_user = os.getenv('JENKINS_USER')
        self.jenkins_token = os.getenv('JENKINS_API_TOKEN')
        self.jenkins_urls = [url.strip() for url in os.getenv('JENKINS_URLS', '').split(',') if url.strip()]
        
        # Configuration
        self.ssl_verify = os.getenv('SSL_VERIFY', 'true').lower() == 'true'
        self.whitelist_urls = whitelist_urls or []
        self.artifactory_base = os.getenv('ARTIFACTORY_BASE', 'isgedge.artifactory.cec.lab.emc.com')
        self.virtual_repos = self._load_virtual_repos()
        
        # Session for API calls
        self.session = requests.Session()
        self.session.verify = self.ssl_verify
        
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
    
    def _load_virtual_repos(self) -> Dict:
        """Load virtual repositories from environment or config file"""
        config_file = Path('config/virtual_repos.yaml')
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        
        env_repos = {}
        for key, value in os.environ.items():
            if key.startswith('VIRTUAL_REPO_'):
                repo_type = key.replace('VIRTUAL_REPO_', '').lower()
                env_repos[repo_type] = value
        
        return env_repos if env_repos else {
            'docker': 'isgedge-docker-virtual',
            'helm': 'isgedge-helm-virtual',
            'maven': 'isgedge-maven-virtual',
            'npm': 'isgedge-npm-virtual',
            'pypi': 'isgedge-pypi-virtual',
            'rpm': 'isgedge-rpm-virtual',
            'factoryos': 'isgedge-factoryos-virtual',
            'debian': 'isgedge-manufacturing-debian-virtual',
        }
    
    def scan_pipeline_repositories(self, repo_name: str) -> Dict:
        """
        Scan a repository focusing on pipeline configurations as the authoritative source
        for repository usage rather than dependency files.
        """
        print(f"Starting pipeline-centric scan for repository: {repo_name}")
        
        # 1. Get pipeline configurations from multiple sources
        pipeline_configs = self._get_all_pipeline_configs(repo_name)
        
        # 2. Extract repository references from pipelines
        pipeline_repos = self._extract_repositories_from_pipelines(pipeline_configs)
        
        # 3. Get declared dependencies for comparison
        declared_deps = self._get_declared_dependencies(repo_name)
        
        # 4. Analyze discrepancies between pipeline usage and declared dependencies
        analysis = self._analyze_repo_discrepancies(pipeline_repos, declared_deps, repo_name)
        
        # 5. Generate compliance report focused on pipeline repository usage
        report = self._generate_pipeline_compliance_report(repo_name, pipeline_repos, declared_deps, analysis)
        
        return report
    
    def _get_all_pipeline_configs(self, repo_name: str) -> Dict:
        """Get pipeline configurations from all available sources"""
        configs = {
            'jenkinsfiles': [],
            'jenkins_jobs': {},
            'makefiles': [],
            'dockerfiles': [],
            'github_actions': [],
            'ci_configs': []
        }
        
        # Get repository files
        repo_files = self._download_pipeline_files(repo_name)
        
        # Extract configurations from different pipeline types
        configs['jenkinsfiles'] = self._extract_jenkinsfiles(repo_files)
        configs['makefiles'] = self._extract_makefiles(repo_files)
        configs['dockerfiles'] = self._extract_dockerfiles(repo_files)
        configs['github_actions'] = self._extract_github_actions(repo_files)
        configs['ci_configs'] = self._extract_ci_configs(repo_files)
        
        # Get Jenkins job configurations from API
        configs['jenkins_jobs'] = self._get_jenkins_job_configs(repo_name)
        
        return configs
    
    def _download_pipeline_files(self, repo_name: str) -> Dict[str, str]:
        """Download pipeline-related files from repository"""
        files = {}
        
        # Pipeline file patterns to look for
        pipeline_patterns = [
            'Jenkinsfile*',
            'Makefile*',
            'Dockerfile*',
            'docker-compose*.yml',
            'docker-compose*.yaml',
            '.github/workflows/*.yml',
            '.github/workflows/*.yaml',
            '.gitlab-ci.yml',
            '.travis.yml',
            'azure-pipelines.yml',
            'buildspec.yml',  # AWS CodeBuild
            'cloudbuild.yaml',  # Google Cloud Build
            'bitbucket-pipelines.yml',
            '*.jenkinsfile',
            'ci/*.yml',
            'ci/*.yaml',
            '.ci/*.yml',
            '.ci/*.yaml'
        ]
        
        # Get repository tree
        url = f"{self.github_api_url}/repos/{self.github_org}/{repo_name}/git/trees/main?recursive=1"
        try:
            print(f"DEBUG: Fetching repository tree from: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            tree = response.json()
            
            print(f"DEBUG: Repository tree contains {len(tree.get('tree', []))} items")
            
            # Find pipeline files
            pipeline_files = []
            for item in tree.get('tree', []):
                if item.get('type') == 'blob':
                    path = item.get('path', '')
                    # Check if file matches any pipeline pattern
                    for pattern in pipeline_patterns:
                        if self._matches_pattern(path, pattern):
                            pipeline_files.append(path)
                            print(f"DEBUG: Found pipeline file: {path} (matches pattern: {pattern})")
                            break
            
            print(f"DEBUG: Total pipeline files found: {len(pipeline_files)}")
            
            # Download each pipeline file
            for file_path in pipeline_files:
                print(f"DEBUG: Downloading pipeline file: {file_path}")
                content = self._download_file_content(repo_name, file_path)
                if content:
                    files[file_path] = content
                    print(f"DEBUG: Successfully downloaded {file_path} ({len(content)} chars)")
                else:
                    print(f"DEBUG: Failed to download {file_path}")
                    
        except Exception as e:
            print(f"Warning: Could not download pipeline files for {repo_name}: {e}")
        
        print(f"DEBUG: Returning {len(files)} pipeline files")
        return files
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a file path matches a pattern (supports basic wildcards)"""
        import fnmatch
        return fnmatch.fnmatch(path.lower(), pattern.lower())
    
    def _download_file_content(self, repo_name: str, file_path: str) -> Optional[str]:
        """Download content of a specific file from repository"""
        url = f"{self.github_api_url}/repos/{self.github_org}/{repo_name}/contents/{file_path}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            file_data = response.json()
            
            if file_data.get('encoding') == 'base64':
                import base64
                content = base64.b64decode(file_data['content']).decode('utf-8', errors='ignore')
                return content
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"INFO: Skipping {file_path} (not found in repository)")
            else:
                print(f"Warning: Could not download {file_path}: {e}")
        except Exception as e:
            print(f"Warning: Could not download {file_path}: {e}")
        
        return None
    
    def _extract_repositories_from_pipelines(self, pipeline_configs: Dict) -> Dict:
        """Extract repository references from all pipeline configurations"""
        repos = {
            'docker_images': set(),
            'git_repositories': set(),
            'package_repositories': set(),
            'artifact_repositories': set(),
            'registry_urls': set()
        }
        
        # Extract from Jenkinsfiles
        for jenkinsfile in pipeline_configs['jenkinsfiles']:
            self._extract_repos_from_jenkinsfile(jenkinsfile['content'], repos)
        
        # Extract from Jenkins jobs
        for job_name, job_config in pipeline_configs['jenkins_jobs'].items():
            self._extract_repos_from_jenkins_config(job_config.get('config', ''), repos)
        
        # Extract from Makefiles
        for makefile in pipeline_configs['makefiles']:
            self._extract_repos_from_makefile(makefile['content'], repos)
        
        # Extract from Dockerfiles
        for dockerfile in pipeline_configs['dockerfiles']:
            self._extract_repos_from_dockerfile(dockerfile['content'], repos)
        
        # Extract from GitHub Actions
        for action in pipeline_configs['github_actions']:
            self._extract_repos_from_github_action(action['content'], repos)
        
        # Extract from other CI configs
        for ci_config in pipeline_configs['ci_configs']:
            self._extract_repos_from_ci_config(ci_config['content'], repos)
        
        # Convert sets to lists for JSON serialization
        return {key: list(value) for key, value in repos.items()}
    
    def _extract_repos_from_jenkinsfile(self, content: str, repos: Dict[str, Set]):
        """Extract repository references from Jenkinsfile content"""
        # Look for various repository patterns in Jenkinsfiles
        patterns = {
            'git_repositories': [
                r'git\s+[\'"]([^\'"\s]+)[\'"]',
                r'checkout\s+scm.*?url:\s*[\'"]([^\'"\s]+)[\'"]',
                r'git\s+url:\s*[\'"]([^\'"\s]+)[\'"]',
                r'https?://github\.com/[^\s\'"]+',
                r'git@github\.com:[^\s\'"]+',
            ],
            'docker_images': [
                r'docker\.image\([\'"]([^\'"\s]+)[\'"]',
                r'FROM\s+([^\s]+)',
                r'docker\s+pull\s+([^\s\'\"]+)',
                r'image:\s*[\'"]?([^\s\'"]+)[\'"]?',
            ],
            'package_repositories': [
                r'pip\s+install.*?-i\s+([^\s]+)',
                r'npm\s+install.*?--registry\s+([^\s]+)',
                r'go\s+get\s+([^\s]+)',
                r'maven.*?-Dmaven\.repo\.url=([^\s]+)',
            ],
            'registry_urls': [
                r'https?://[^\s\'"]+\.artifactory\.[^\s\'"]+',
                r'https?://registry\.[^\s\'"]+',
                r'https?://[^\s\'"]+/artifactory/',
            ]
        }
        
        for repo_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]  # Take first group if tuple
                    
                    match = match.strip().strip('\'"')  # Clean up quotes and whitespace
                    
                    # Filter out obviously invalid matches
                    if self._is_valid_repository_reference(match, repo_type):
                        repos[repo_type].add(match)
                        print(f"DEBUG: Added {repo_type}: '{match}'")
                    else:
                        print(f"DEBUG: Filtered out invalid {repo_type}: '{match}'")
    
    def _is_valid_repository_reference(self, reference: str, repo_type: str) -> bool:
        """Check if a repository reference is valid and not a parsing artifact"""
        if not reference or len(reference) < 3:
            return False
        
        # Filter out common parsing artifacts
        invalid_patterns = [
            'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
            'run', 'echo', 'set', 'cd', 'ls', 'cat', 'grep', 'awk', 'sed',
            'sh', 'bash', 'cmd', 'exe', 'bin', 'usr', 'opt', 'var', 'tmp',
            'build', 'test', 'deploy', 'install', 'update', 'upgrade'
        ]
        
        # Check if it's just a common word
        if reference.lower() in invalid_patterns:
            return False
        
        # For docker images, require at least one slash or colon (registry/image:tag)
        if repo_type == 'docker_images':
            if ':' not in reference and '/' not in reference:
                return False
            # Must have some structure
            if len(reference.split('/')) == 1 and len(reference.split(':')) == 1:
                return False
        
        # For git repositories, should have some structure
        if repo_type == 'git_repositories':
            # Should have either http/https or contain a slash for org/repo
            if not (reference.startswith('http') or reference.startswith('git@') or '/' in reference):
                return False
        
        # For registry URLs, must be valid URLs
        if repo_type == 'registry_urls':
            if not (reference.startswith('http://') or reference.startswith('https://')):
                return False
        
        return True
    
    def _extract_repos_from_dockerfile(self, content: str, repos: Dict[str, Set]):
        """Extract repository references from Dockerfile content"""
        # FROM statements
        from_matches = re.findall(r'FROM\s+([^\s]+)', content, re.IGNORECASE)
        for match in from_matches:
            repos['docker_images'].add(match.strip())
        
        # RUN commands with package installations
        run_patterns = [
            r'pip\s+install.*?-i\s+([^\s]+)',
            r'npm\s+install.*?--registry\s+([^\s]+)',
            r'apt-get.*?update.*?-o\s+Acquire::http::Proxy="([^"]+)"',
            r'yum.*?--enablerepo=([^\s]+)',
        ]
        
        for pattern in run_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                repos['package_repositories'].add(match.strip())
    
    def _extract_repos_from_makefile(self, content: str, repos: Dict[str, Set]):
        """Extract repository references from Makefile content"""
        # Look for various repository patterns in Makefiles
        patterns = [
            r'git\s+clone\s+([^\s]+)',
            r'docker\s+pull\s+([^\s]+)',
            r'wget\s+([^\s]+)',
            r'curl.*?([https?://[^\s\'"]+)',
            r'go\s+get\s+([^\s]+)',
            r'pip\s+install.*?-i\s+([^\s]+)',
            r'npm\s+install.*?--registry\s+([^\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match.startswith('http'):
                    repos['registry_urls'].add(match.strip())
                elif 'github.com' in match or 'git@' in match:
                    repos['git_repositories'].add(match.strip())
                elif '/' in match and '.' in match:  # Likely a docker image
                    repos['docker_images'].add(match.strip())
                else:
                    repos['package_repositories'].add(match.strip())
    
    def _extract_repos_from_github_action(self, content: str, repos: Dict[str, Set]):
        """Extract repository references from GitHub Actions workflow"""
        try:
            workflow = yaml.safe_load(content)
            
            # Extract from uses: statements
            def extract_uses(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == 'uses' and isinstance(value, str):
                            repos['git_repositories'].add(value)
                        else:
                            extract_uses(value)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_uses(item)
            
            extract_uses(workflow)
            
            # Extract from run commands
            def extract_run_commands(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == 'run' and isinstance(value, str):
                            self._extract_repos_from_shell_command(value, repos)
                        else:
                            extract_run_commands(value)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_run_commands(item)
            
            extract_run_commands(workflow)
            
        except Exception as e:
            print(f"Error parsing GitHub Actions workflow: {e}")
    
    def _extract_repos_from_shell_command(self, command: str, repos: Dict[str, Set]):
        """Extract repository references from shell commands"""
        patterns = [
            r'git\s+clone\s+([^\s]+)',
            r'docker\s+pull\s+([^\s]+)',
            r'pip\s+install.*?-i\s+([^\s]+)',
            r'npm\s+install.*?--registry\s+([^\s]+)',
            r'go\s+get\s+([^\s]+)',
            r'wget\s+([^\s]+)',
            r'curl.*?(https?://[^\s\'"]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, command, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match.startswith('http'):
                    repos['registry_urls'].add(match.strip())
                elif 'github.com' in match or 'git@' in match:
                    repos['git_repositories'].add(match.strip())
                else:
                    repos['package_repositories'].add(match.strip())
    
    def _get_declared_dependencies(self, repo_name: str) -> Dict:
        """Get declared dependencies from traditional dependency files"""
        deps = {
            'go_modules': [],
            'python_packages': [],
            'node_packages': [],
            'maven_dependencies': []
        }
        
        # Download dependency files
        dep_files = ['go.mod', 'requirements.txt', 'package.json', 'pom.xml']
        
        for file_name in dep_files:
            content = self._download_file_content(repo_name, file_name)
            if content:
                if file_name == 'go.mod':
                    deps['go_modules'] = self._parse_go_mod(content)
                elif file_name == 'requirements.txt':
                    deps['python_packages'] = self._parse_requirements_txt(content)
                elif file_name == 'package.json':
                    deps['node_packages'] = self._parse_package_json(content)
                elif file_name == 'pom.xml':
                    deps['maven_dependencies'] = self._parse_pom_xml(content)
        
        return deps
    
    def _analyze_repo_discrepancies(self, pipeline_repos: Dict, declared_deps: Dict, repo_name: str) -> Dict:
        """Analyze discrepancies between pipeline repository usage and declared dependencies"""
        analysis = {
            'pipeline_only_repos': [],  # Repos used in pipelines but not declared
            'declared_only_deps': [],   # Dependencies declared but not used in pipelines
            'compliance_issues': [],    # Non-compliant repository usage
            'implicit_repositories': [],  # Repositories resolved through enterprise configuration
            'jenkins_env_config': {},  # Jenkins environment configuration
            'jenkins_has_goproxy': False,  # Whether Jenkins has GOPROXY configured
            'jenkins_goproxy_value': None,
            'recommendations': []
        }
        
        # Check Jenkins environment configuration for GOPROXY
        print(f"DEBUG: Checking Jenkins for {repo_name} GOPROXY configuration")
        jenkins_jobs = self._get_jenkins_job_configs(repo_name)
        analysis['jenkins_env_config'] = jenkins_jobs
        
        # Check if any Jenkins job has GOPROXY configured
        jenkins_has_goproxy = False
        jenkins_goproxy_value = None
        
        for job_name, job_config in jenkins_jobs.items():
            if job_config.get('env_config', {}).get('has_goproxy'):
                jenkins_has_goproxy = True
                jenkins_goproxy_value = job_config['env_config']['goproxy_value']
                print(f"DEBUG: Jenkins job {job_name} has GOPROXY: {jenkins_goproxy_value}")
                break
        
        analysis['jenkins_has_goproxy'] = jenkins_has_goproxy
        analysis['jenkins_goproxy_value'] = jenkins_goproxy_value
        
        # Check for repositories used in pipelines that aren't properly declared
        all_pipeline_repos = set()
        for repo_type, repos in pipeline_repos.items():
            all_pipeline_repos.update(repos)
        
        print(f"DEBUG: Analyzing {len(all_pipeline_repos)} pipeline repositories")
        
        # Check compliance of pipeline repositories (only valid ones)
        for repo_type, repos in pipeline_repos.items():
            print(f"DEBUG: Checking {len(repos)} repositories of type '{repo_type}'")
            for repo in repos:
                # Only process valid repository references
                if not self._is_valid_repository_reference(repo, repo_type):
                    print(f"DEBUG: Skipping invalid repository reference: '{repo}' (type: {repo_type})")
                    continue
                    
                print(f"DEBUG: Checking compliance of: '{repo}' (type: {repo_type})")
                is_compliant = self._is_repo_compliant(repo)
                print(f"DEBUG: Repository '{repo}' compliance result: {is_compliant}")
                
                if not is_compliant:
                    # Create more specific issue descriptions
                    if 'docker' in repo_type:
                        if 'docker.io' in repo:
                            issue_desc = f'External Docker Hub registry used: {repo}. Should use approved Artifactory registry.'
                        elif any(pattern in repo.lower() for pattern in ['quay.io', 'gcr.io', 'registry.redhat.io']):
                            issue_desc = f'External container registry used: {repo}. Should use approved Artifactory registry.'
                        else:
                            issue_desc = f'Non-compliant Docker image registry: {repo}'
                    elif 'git' in repo_type:
                        if '@' in repo and not repo.startswith('http'):
                            issue_desc = f'GitHub Actions workflow reference: {repo}. Should use internal workflows or approved external actions.'
                        elif 'github.com' in repo:
                            issue_desc = f'External GitHub repository used: {repo}. Should use internal Git repositories.'
                        else:
                            issue_desc = f'Non-compliant Git repository: {repo}'
                    elif 'registry' in repo_type:
                        issue_desc = f'External package registry used: {repo}. Should use Artifactory virtual repository.'
                    else:
                        issue_desc = f'Non-compliant repository used in pipeline: {repo}'
                    
                    issue = {
                        'repository': repo,
                        'type': repo_type,
                        'issue': issue_desc,
                        'severity': 'HIGH' if any(pattern in repo.lower() for pattern in ['github.com', 'docker.io']) else 'MEDIUM',
                        'file': 'Pipeline Configuration'  # Add file field for UI compatibility
                    }
                    analysis['compliance_issues'].append(issue)
                    print(f"DEBUG: Added compliance issue: {issue}")
                else:
                    # Check if it's an implicit repository (resolved through enterprise config)
                    if (':' in repo and '/' not in repo and not repo.startswith('http') and 
                        self.artifactory_base not in repo):
                        # This is likely resolved through enterprise Docker registry
                        analysis['implicit_repositories'].append({
                            'repository': repo,
                            'type': repo_type,
                            'resolution': 'Enterprise Docker registry configuration',
                            'note': 'Resolved through configured Docker daemon registries'
                        })
                        print(f"DEBUG: Added implicit repository: {repo}")
        
        print(f"DEBUG: Total compliance issues found: {len(analysis['compliance_issues'])}")
        print(f"DEBUG: Total implicit repositories found: {len(analysis['implicit_repositories'])}")
        
        # Generate specific recommendations based on findings
        if analysis['compliance_issues']:
            # Group issues by type for better recommendations
            docker_issues = [issue for issue in analysis['compliance_issues'] if 'docker' in issue['type']]
            git_issues = [issue for issue in analysis['compliance_issues'] if 'git' in issue['type']]
            registry_issues = [issue for issue in analysis['compliance_issues'] if 'registry' in issue['type']]
            
            if docker_issues:
                affected_images = [issue['repository'] for issue in docker_issues]
                analysis['recommendations'].append({
                    'priority': 'HIGH',
                    'action': f'Replace {len(docker_issues)} external Docker image(s) with approved Artifactory registry',
                    'details': f'Affected images: {", ".join(affected_images[:3])}{"..." if len(affected_images) > 3 else ""}. Use: https://{self.artifactory_base}/artifactory/{self.virtual_repos.get("docker", "isgedge-docker-virtual")}'
                })
            
            if git_issues:
                affected_repos = [issue['repository'] for issue in git_issues]
                analysis['recommendations'].append({
                    'priority': 'HIGH',
                    'action': f'Replace {len(git_issues)} external Git reference(s) with approved internal repositories',
                    'details': f'Affected repositories: {", ".join(affected_repos[:3])}{"..." if len(affected_repos) > 3 else ""}'
                })
            
            if registry_issues:
                affected_registries = [issue['repository'] for issue in registry_issues]
                analysis['recommendations'].append({
                    'priority': 'MEDIUM',
                    'action': f'Replace {len(registry_issues)} external registry reference(s) with Artifactory virtual repositories',
                    'details': f'Affected registries: {", ".join([reg.split("://")[1].split("/")[0] if "://" in reg else reg for reg in affected_registries[:2]])}{"..." if len(affected_registries) > 2 else ""}'
                })
        
        # Check if scan had authentication issues (no pipeline files found)
        total_repos_found = sum(len(repos) for repos in pipeline_repos.values())
        if total_repos_found == 0 and len(analysis['compliance_issues']) == 0:
            analysis['recommendations'].append({
                'priority': 'CRITICAL',
                'action': 'Authentication or access issue detected',
                'details': 'No pipeline files or repositories found. Check GitHub API token, Jenkins credentials, and repository access permissions.'
            })
        
        if analysis['implicit_repositories']:
            implicit_images = [repo['repository'] for repo in analysis['implicit_repositories']]
            analysis['recommendations'].append({
                'priority': 'LOW',
                'action': f'Consider making {len(analysis["implicit_repositories"])} Docker registry reference(s) explicit',
                'details': f'Images: {", ".join(implicit_images[:3])}{"..." if len(implicit_images) > 3 else ""}. While compliant through enterprise config, explicit references improve maintainability.'
            })
        
        return analysis
    
    def _is_repo_compliant(self, repo_url: str) -> bool:
        """Check if a repository URL is compliant with enterprise policies"""
        print(f"DEBUG: _is_repo_compliant called with: '{repo_url}'")
        
        if not repo_url or len(repo_url.strip()) < 3:
            print("DEBUG: Empty or too short repo_url, returning True")
            return True
        
        repo_url = repo_url.strip()
        
        # Check whitelist
        if self.is_url_whitelisted(repo_url):
            print(f"DEBUG: '{repo_url}' is whitelisted, returning True")
            return True
        
        # Check if it's using approved Artifactory virtual repos
        if self.artifactory_base in repo_url:
            print(f"DEBUG: '{repo_url}' contains artifactory_base '{self.artifactory_base}', returning True")
            return True
        
        # NEW: Check for Docker images with variable substitution pointing to Artifactory
        artifactory_variable_patterns = [
            '${ARTIFACTORY_URL}',
            '${ARTIFACTORY_BASE}',
            '${DOCKER_REGISTRY}',
            '${REGISTRY_URL}',
            '$ARTIFACTORY_URL',
            '$ARTIFACTORY_BASE',
            '$DOCKER_REGISTRY',
            '$REGISTRY_URL'
        ]
        
        for pattern in artifactory_variable_patterns:
            if repo_url.startswith(pattern):
                print(f"DEBUG: '{repo_url}' uses Artifactory variable pattern '{pattern}', returning True")
                return True
        
        # Check for internal/trusted organization references (ISG-Edge, etc.)
        trusted_organizations = [
            'isg-edge',
            'ISG-Edge',
            'fusion-e',
            'eos2git.cec.lab.emc.com'
        ]
        
        for trusted_org in trusted_organizations:
            if trusted_org.lower() in repo_url.lower():
                print(f"DEBUG: '{repo_url}' contains trusted organization '{trusted_org}', returning True")
                return True
        
        # Check for enterprise Docker registries (approved)
        approved_docker_registries = [
            'isgedge-sdp-docker-virtual',
            'global-docker-remote', 
            'isgedge-docker-controlled',
            'global-docker-gz',
            'isgedge-docker-virtual',  # Original one
        ]
        
        for approved_registry in approved_docker_registries:
            if approved_registry in repo_url.lower():
                print(f"DEBUG: '{repo_url}' uses approved Docker registry '{approved_registry}', returning True")
                return True
        
        # Non-compliant patterns (external registries)
        non_compliant_patterns = [
            'github.com',
            'gitlab.com',
            'bitbucket.org',
            'registry.npmjs.org',
            'pypi.org',
            'maven.org',
            'docker.io',
            'registry-1.docker.io',
            'hub.docker.com',
            'quay.io',
            'gcr.io',
            'registry.redhat.io'
        ]
        
        repo_lower = repo_url.lower()
        
        # Check standard non-compliant patterns FIRST
        for pattern in non_compliant_patterns:
            if pattern in repo_lower:
                print(f"DEBUG: '{repo_url}' contains non-compliant pattern '{pattern}', returning False")
                return False
        
        # Check for GitHub Actions references (org/repo@version pattern)
        if '/' in repo_url and '@' in repo_url and not repo_url.startswith('http'):
            # This looks like a GitHub Actions reference: org/repo@version or org/repo/.github/workflows/file@version
            print(f"DEBUG: '{repo_url}' appears to be a GitHub Actions reference, returning False")
            return False
        
        # Check for direct GitHub repository references (org/repo pattern without https)
        if ('/' in repo_url and not repo_url.startswith('http') and '@' not in repo_url):
            # This could be a GitHub repo reference
            parts = repo_url.split('/')
            if len(parts) >= 2 and len(parts[0]) > 2 and len(parts[1]) > 2:
                # Check if it looks like a GitHub org/repo pattern
                if not any(char in parts[0] for char in ['.', ':', 'http']):
                    print(f"DEBUG: '{repo_url}' appears to be a direct GitHub repository reference, returning False")
                    return False
        
        # Handle Docker images without explicit registry
        if ':' in repo_url and '/' not in repo_url and not repo_url.startswith('http'):
            # This looks like image:tag without registry (e.g., nginx:latest)
            # In enterprise environments, this typically resolves through configured registries
            # We'll consider this compliant if it's a standard pattern, but flag for review
            print(f"DEBUG: '{repo_url}' appears to be Docker image without explicit registry - assuming enterprise Docker registry resolution, returning True")
            return True
        
        # Handle Maven coordinates (groupId:artifactId:version pattern)
        if ':' in repo_url and '/' not in repo_url and not repo_url.startswith('http'):
            # This looks like a Maven coordinate (e.g., com.dell.isgedge.hzp:qa-framework)
            parts = repo_url.split(':')
            if len(parts) >= 2 and '.' in parts[0]:
                # Check if it's an internal Maven coordinate (starts with company domain)
                internal_maven_patterns = [
                    'com.dell',
                    'com.emc', 
                    'com.delltechnologies',
                    'com.isgedge',
                    'com.vmware'
                ]
                group_id = parts[0].lower()
                for internal_pattern in internal_maven_patterns:
                    if group_id.startswith(internal_pattern):
                        print(f"DEBUG: '{repo_url}' appears to be internal Maven coordinate (starts with {internal_pattern}), returning True")
                        return True
                # External Maven coordinates are non-compliant
                print(f"DEBUG: '{repo_url}' appears to be external Maven coordinate, returning False")
                return False
        
        print(f"DEBUG: '{repo_url}' does not match any non-compliant patterns, returning True")
        return True
    
    def is_url_whitelisted(self, url: str) -> bool:
        """Check if a URL matches any whitelisted patterns"""
        if not self.whitelist_urls:
            return False
        
        url_lower = url.lower()
        for whitelist_pattern in self.whitelist_urls:
            if whitelist_pattern.lower() in url_lower:
                return True
        return False
    
    def _generate_pipeline_compliance_report(self, repo_name: str, pipeline_repos: Dict, 
                                           declared_deps: Dict, analysis: Dict) -> Dict:
        """Generate a comprehensive compliance report focused on pipeline repository usage"""
        
        # Count only VALID repositories (those that pass validation)
        valid_pipeline_repos = 0
        for repo_type, repos in pipeline_repos.items():
            for repo in repos:
                if self._is_valid_repository_reference(repo, repo_type):
                    valid_pipeline_repos += 1
        
        # Calculate compliance based on valid repositories only
        non_compliant_repos = len(analysis['compliance_issues'])
        compliant_repos = valid_pipeline_repos - non_compliant_repos
        compliance_percentage = (compliant_repos / valid_pipeline_repos * 100) if valid_pipeline_repos > 0 else 100
        
        print(f"DEBUG: Compliance calculation - Valid repos: {valid_pipeline_repos}, Non-compliant: {non_compliant_repos}, Compliant: {compliant_repos}, Percentage: {compliance_percentage}%")
        
        # Convert API URL to web URL
        web_url = self.github_api_url.replace('api.', '').replace('/api/v3', '').replace('/api', '')
        repo_url = f"{web_url}/{self.github_org}/{repo_name}"
        
        # Add repository field and URLs to all findings
        findings = analysis['compliance_issues']
        for finding in findings:
            finding['repository'] = repo_name
            finding['repository_url'] = repo_url
            
            # Add file URL if file path exists
            if 'file' in finding and finding['file'] and finding['file'] != 'Pipeline Configuration':
                file_path = finding['file'].replace('\\', '/')
                finding['file_url'] = f"{repo_url}/blob/main/{file_path}"
        
        report = {
            'scan_summary': {
                'repository_name': repo_name,
                'scan_type': 'pipeline_centric',
                'total_items': valid_pipeline_repos,  # Template expects total_items
                'total_pipeline_repositories': valid_pipeline_repos,  # Keep for backward compatibility
                'compliant_items': compliant_repos,  # Template expects compliant_items
                'compliant_repositories': compliant_repos,  # Keep for backward compatibility
                'non_compliant_items': non_compliant_repos,  # Template expects non_compliant_items
                'non_compliant_repositories': non_compliant_repos,  # Keep for backward compatibility
                'compliance_percentage': round(compliance_percentage, 2),
                'pipeline_authority': True,
                'jenkins_has_goproxy': analysis['jenkins_has_goproxy'],
                'jenkins_goproxy_value': analysis['jenkins_goproxy_value']
            },
            'approved_virtual_repositories': self.virtual_repos,
            'findings': findings,
            'pipeline_analysis': analysis,
            'scan_metadata': {
                'scanned_at': datetime.now().isoformat(),
                'repository_type': 'remote_pipeline_centric',
                'repository_url': repo_url,
                'github_org': self.github_org or '',
                'repository_name': repo_name,
                'virtual_repositories': self.virtual_repos,
                'artifactory_base': self.artifactory_base,
                'scan_focus': 'pipeline_configurations'
            }
        }
        return report
    
    def _convert_issues_to_findings(self, issues: List[Dict]) -> List[Dict]:
        """Convert compliance issues to findings format"""
        findings = []
        
        for issue in issues:
            finding = {
                'file': 'Pipeline Configuration',
                'type': 'pipeline_repository',
                'issue': issue['issue'],
                'severity': issue['severity'],
                'repository_url': issue['repository'],
                'repository_type': issue['type'],
                'recommended_action': self._get_recommended_action(issue['repository'], issue['type'])
            }
            findings.append(finding)
        
        return findings
    
    def _get_recommended_action(self, repo_url: str, repo_type: str) -> str:
        """Get recommended action for fixing a repository compliance issue"""
        if 'docker' in repo_type:
            return f"Replace with approved Docker registry: https://{self.artifactory_base}/artifactory/{self.virtual_repos.get('docker', 'docker-virtual')}"
        elif 'git' in repo_type:
            return "Use approved internal Git repositories or configure pipeline to use Artifactory as proxy"
        elif 'npm' in repo_url.lower():
            return f"Configure NPM registry: https://{self.artifactory_base}/artifactory/api/npm/{self.virtual_repos.get('npm', 'npm-virtual')}/"
        elif 'pypi' in repo_url.lower() or 'pip' in repo_url.lower():
            return f"Configure PIP index: https://{self.artifactory_base}/artifactory/api/pypi/{self.virtual_repos.get('pypi', 'pypi-virtual')}/simple"
        elif 'maven' in repo_url.lower():
            return f"Configure Maven repository: https://{self.artifactory_base}/artifactory/{self.virtual_repos.get('maven', 'maven-virtual')}"
        else:
            return "Replace with approved Artifactory virtual repository"
    
    # Placeholder methods for file parsing (implement based on existing scanner logic)
    def _extract_jenkinsfiles(self, repo_files: Dict) -> List[Dict]:
        """Extract Jenkinsfile configurations"""
        jenkinsfiles = []
        for path, content in repo_files.items():
            if 'jenkinsfile' in path.lower():
                jenkinsfiles.append({'path': path, 'content': content})
        return jenkinsfiles
    
    def _extract_makefiles(self, repo_files: Dict) -> List[Dict]:
        """Extract Makefile configurations"""
        makefiles = []
        for path, content in repo_files.items():
            if 'makefile' in path.lower():
                makefiles.append({'path': path, 'content': content})
        return makefiles
    
    def _extract_dockerfiles(self, repo_files: Dict) -> List[Dict]:
        """Extract Dockerfile configurations"""
        dockerfiles = []
        for path, content in repo_files.items():
            if 'dockerfile' in path.lower() or path.lower().startswith('dockerfile'):
                dockerfiles.append({'path': path, 'content': content})
        return dockerfiles
    
    def _extract_github_actions(self, repo_files: Dict) -> List[Dict]:
        """Extract GitHub Actions workflow configurations"""
        actions = []
        for path, content in repo_files.items():
            if '.github/workflows/' in path.lower() and (path.endswith('.yml') or path.endswith('.yaml')):
                actions.append({'path': path, 'content': content})
        return actions
    
    def _extract_ci_configs(self, repo_files: Dict) -> List[Dict]:
        """Extract other CI configuration files"""
        ci_configs = []
        ci_files = ['.gitlab-ci.yml', '.travis.yml', 'azure-pipelines.yml', 'buildspec.yml', 
                   'cloudbuild.yaml', 'bitbucket-pipelines.yml']
        
        for path, content in repo_files.items():
            if any(ci_file in path.lower() for ci_file in ci_files):
                ci_configs.append({'path': path, 'content': content})
        return ci_configs
    
    def _extract_repos_from_jenkins_config(self, config: str, repos: Dict[str, Set]):
        """Extract repository references from Jenkins job configuration XML"""
        # This is similar to jenkinsfile extraction but for XML configs
        self._extract_repos_from_jenkinsfile(config, repos)
    
    def _extract_repos_from_ci_config(self, content: str, repos: Dict[str, Set]):
        """Extract repository references from CI configuration files"""
        # This can handle various CI formats
        self._extract_repos_from_shell_command(content, repos)
    
    def _get_jenkins_job_configs(self, repo_name: str) -> Dict:
        """Get Jenkins job configurations from API and extract environment variables"""
        jenkins_configs = {}
        
        for jenkins_url in self.jenkins_urls:
            try:
                jobs_url = f"{jenkins_url}/api/json"
                auth = (self.jenkins_user, self.jenkins_token) if self.jenkins_user and self.jenkins_token else None
                
                response = self.session.get(jobs_url, auth=auth)
                response.raise_for_status()
                
                jobs_data = response.json()
                self._find_jenkins_jobs(jobs_data.get('jobs', []), repo_name, jenkins_url, jenkins_configs, auth)
                
            except Exception as e:
                print(f"Warning: Could not access Jenkins at {jenkins_url} - continuing without Jenkins data")
        
        return jenkins_configs
    
    def _extract_jenkins_environment_config(self, config_xml: str) -> Dict:
        """Extract environment variables and tool configurations from Jenkins job XML"""
        env_config = {
            'env_vars': [],
            'tool_configurations': [],
            'build_wrappers': [],
            'has_goproxy': False,
            'goproxy_value': None
        }
        
        try:
            # Parse XML configuration
            import xml.etree.ElementTree as ET
            root = ET.fromstring(config_xml)
            
            # Check for environment variables in properties
            for prop in root.findall('.//hudson.model.ParametersDefinitionProperty'):
                for parameter in prop.findall('parameterDefinition'):
                    name = parameter.find('name')
                    if name is not None:
                        param_name = name.text
                        default_value = parameter.find('defaultValue')
                        if default_value is not None:
                            env_config['env_vars'].append({
                                'name': param_name,
                                'value': default_value.text
                            })
                            if param_name.upper() == 'GOPROXY':
                                env_config['has_goproxy'] = True
                                env_config['goproxy_value'] = default_value.text
            
            # Check for environment variables in EnvInject plugin
            for envinject in root.findall('.//EnvInjectPlugin'):
                for info in envinject.findall('info'):
                    properties = info.find('properties')
                    if properties is not None:
                        for prop in properties.findall('*'):
                            if prop.text:
                                env_config['env_vars'].append({
                                    'name': prop.tag,
                                    'value': prop.text
                                })
                                if prop.tag.upper() == 'GOPROXY':
                                    env_config['has_goproxy'] = True
                                    env_config['goproxy_value'] = prop.text
            
            # Check for Go tool configuration
            for go_tool in root.findall('.//hudson.tasks.Shell') or root.findall('.//hudson.plugins.golang.GoTool'):
                env_config['tool_configurations'].append({
                    'type': 'GoTool',
                    'has_goproxy': 'GOPROXY' in str(go_tool).upper()
                })
            
            # Check for build wrappers
            for wrapper in root.findall('.//buildWrappers'):
                for wrapper_config in wrapper.findall('*'):
                    wrapper_name = wrapper_config.tag
                    env_config['build_wrappers'].append({
                        'type': wrapper_name,
                        'config': str(wrapper_config)
                    })
                    
        except Exception as e:
            print(f"Error parsing Jenkins XML config: {e}")
        
        return env_config
    
    def _find_jenkins_jobs(self, jobs: List[Dict], repo_name: str, jenkins_url: str, configs: Dict, auth: Optional[Tuple]):
        """Recursively find Jenkins jobs related to repository"""
        for job in jobs:
            job_name = job.get('name', '')
            job_url = job.get('url', '')
            
            if repo_name.lower() in job_name.lower():
                try:
                    config_url = f"{job_url}config.xml"
                    response = self.session.get(config_url, auth=auth)
                    response.raise_for_status()
                    
                    # Extract environment configuration from Jenkins job XML
                    env_config = self._extract_jenkins_environment_config(response.text)
                    
                    configs[job_name] = {
                        'url': job_url,
                        'config': response.text,
                        'jenkins_server': jenkins_url,
                        'env_config': env_config
                    }
                    print(f"DEBUG: Jenkins job {job_name} has GOPROXY: {env_config['has_goproxy']}")
                    if env_config['has_goproxy']:
                        print(f"DEBUG: GOPROXY value: {env_config['goproxy_value']}")
                    
                except Exception as e:
                    print(f"Error getting Jenkins config for job {job_name}: {e}")
            
            if job.get('jobs'):
                self._find_jenkins_jobs(job['jobs'], repo_name, jenkins_url, configs, auth)
    
    def _parse_go_mod(self, content: str) -> List[str]:
        """Parse go.mod file for dependencies"""
        deps = []
        in_require = False
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('require ('):
                in_require = True
            elif line == ')':
                in_require = False
            elif in_require and line and not line.startswith('//'):
                parts = line.split()
                if len(parts) >= 2:
                    deps.append(parts[0])
            elif line.startswith('require ') and not line.startswith('//'):
                parts = line[7:].strip().split()
                if len(parts) >= 2:
                    deps.append(parts[0])
        return deps
    
    def _parse_requirements_txt(self, content: str) -> List[str]:
        """Parse requirements.txt file for dependencies"""
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove version specifiers
                dep = re.split(r'[>=<!=]', line)[0].strip()
                if dep:
                    deps.append(dep)
        return deps
    
    def _parse_package_json(self, content: str) -> List[str]:
        """Parse package.json file for dependencies"""
        try:
            data = json.loads(content)
            deps = []
            for dep_type in ['dependencies', 'devDependencies', 'peerDependencies']:
                if dep_type in data:
                    deps.extend(data[dep_type].keys())
            return deps
        except Exception:
            return []
    
    def _parse_pom_xml(self, content: str) -> List[str]:
        """Parse pom.xml file for dependencies"""
        deps = []
        # Simple regex-based parsing for Maven dependencies
        dep_pattern = r'<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>'
        matches = re.findall(dep_pattern, content, re.IGNORECASE | re.DOTALL)
        for group_id, artifact_id in matches:
            deps.append(f"{group_id.strip()}:{artifact_id.strip()}")
        return deps
    
    def cleanup(self):
        """Clean up any temporary resources"""
        pass