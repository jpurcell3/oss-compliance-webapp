#!/usr/bin/env python3
"""
Remote Repository Scanner for OSS Compliance
Integrates with GitHub API and Jenkins API for remote repository access
"""

import os
import re
import json
import requests
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import urllib3

# Suppress InsecureRequestWarning when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

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

# Import enhanced scanner for advanced analysis
try:
    from enhanced_scanner import EnhancedComplianceScanner
    ENHANCED_SCANNER_AVAILABLE = True
except ImportError:
    ENHANCED_SCANNER_AVAILABLE = False
    print("Warning: EnhancedComplianceScanner not available. Enhanced scanning disabled.")

class RemoteRepositoryScanner:
    def __init__(self, github_instance_config=None, whitelist_urls=None, jenkins_config=None):
        if github_instance_config:
            # Use provided GitHub instance configuration
            self.github_api_url = github_instance_config.get('api_url', 'https://api.github.com')
            self.github_token = github_instance_config.get('token')
            self.github_org = github_instance_config.get('org')
        else:
            # Fall back to environment variables for backward compatibility
            self.github_api_url = os.getenv('GITHUB_API_URL', 'https://api.github.com')
            self.github_token = os.getenv('GITHUB_TOKEN')
            self.github_org = os.getenv('GITHUB_ORG')
        
        self.github_repo_filter = os.getenv('GITHUB_REPO_FILTER', '')
        # CRITICAL: SSL verification must be disabled for corporate proxies with self-signed certs
        ssl_verify_env = os.getenv('SSL_VERIFY', 'false').lower()
        self.ssl_verify = ssl_verify_env == 'true'
        debug_log(f"SSL_VERIFY from env: '{ssl_verify_env}', ssl_verify set to: {self.ssl_verify}")
        self.whitelist_urls = whitelist_urls or []
        
        # Load manual Jenkins job mappings
        self.jenkins_job_mappings = self._load_jenkins_job_mappings()
        
        # Jenkins configuration - prioritize passed config over environment variables
        if jenkins_config:
            self.jenkins_user = jenkins_config.get('user')
            self.jenkins_token = jenkins_config.get('token')
            self.jenkins_urls = jenkins_config.get('urls', [])
            debug_log(f"Jenkins config loaded from YAML - User: {self.jenkins_user}, URLs: {len(self.jenkins_urls)}")
        else:
            # Fall back to environment variables
            self.jenkins_user = os.getenv('JENKINS_USER')
            self.jenkins_token = os.getenv('JENKINS_API_TOKEN')
            self.jenkins_urls = [url.strip() for url in os.getenv('JENKINS_URLS', '').split(',') if url.strip()]
            debug_log(f"Jenkins config loaded from ENV - User: {self.jenkins_user}, URLs: {len(self.jenkins_urls)}")
        
        # Virtual repositories and Artifactory config
        self.artifactory_base = os.getenv('ARTIFACTORY_BASE', 'isgedge.artifactory.cec.lab.emc.com')
        self.virtual_repos = self._load_virtual_repos()
        
        # Local storage for remote files
        self.temp_dir = Path(tempfile.mkdtemp(prefix='oss_compliance_'))
        self.repos_dir = self.temp_dir / 'repositories'
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        
        # Repository cache configuration
        self.cache_dir = Path('cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_ttl_hours = int(os.getenv('REPO_CACHE_TTL_HOURS', '24'))
        
        # Session for API calls
        self.session = requests.Session()
        self.session.verify = self.ssl_verify
        
        # Set up authentication
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
    
    def _load_virtual_repos(self) -> Dict:
        """Load virtual repositories from environment or config file"""
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
            'helm': 'isgedge-helm-virtual',
            'maven': 'isgedge-maven-virtual',
            'npm': 'isgedge-npm-virtual',
            'pypi': 'isgedge-pypi-virtual',
            'rpm': 'isgedge-rpm-virtual',
            'factoryos': 'isgedge-factoryos-virtual',
            'debian': 'isgedge-manufacturing-debian-virtual',
        }
    
    def get_organization_repositories(self, force_refresh: bool = False) -> List[str]:
        """Get list of repositories in the organization with caching"""
        if not self.github_org or not self.github_token:
            raise ValueError("GitHub organization and token are required")
        
        # Generate cache key based on org and API URL
        cache_key = f"{self.github_org}_{self.github_api_url.replace('://', '_').replace('/', '_')}"
        cache_file = self.cache_dir / f"{cache_key}_repos.json"
        
        # Check cache if not forcing refresh
        if not force_refresh and cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Check if cache is still valid
                cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
                if datetime.now() - cache_time < timedelta(hours=self.cache_ttl_hours):
                    cached_repos = cache_data.get('repositories', [])
                    # Sort cached repositories alphabetically
                    cached_repos.sort()
                    print(f"Using cached repository list ({len(cached_repos)} repos)")
                    return cached_repos
            except Exception as e:
                print(f"Error reading cache: {e}, will fetch from API")
        
        # Fetch from API
        url = f"{self.github_api_url}/orgs/{self.github_org}/repos"
        params = {'per_page': 100, 'type': 'sources'}
        
        all_repos = []
        page = 1
        
        while True:
            params['page'] = page
            try:
                response = self.session.get(url, params=params)
                
                # Check for 403 Forbidden errors specifically
                if response.status_code == 403:
                    error_msg = f"403 Forbidden error when accessing GitHub API. "
                    if response.headers.get('X-RateLimit-Remaining') == '0':
                        error_msg += "GitHub API rate limit exceeded. "
                    else:
                        error_msg += "Authentication or permission issue. "
                    
                    error_msg += f"URL: {url}, Status: {response.status_code}"
                    print(f"ERROR: {error_msg}")
                    print(f"GitHub Token configured: {'Yes' if self.github_token else 'No'}")
                    print(f"GitHub Organization: {self.github_org}")
                    print(f"GitHub API URL: {self.github_api_url}")
                    raise PermissionError(error_msg)
                
                response.raise_for_status()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    error_msg = f"403 Forbidden error when accessing GitHub API: {e}"
                    print(f"ERROR: {error_msg}")
                    print(f"This is typically caused by:")
                    print(f"1. Invalid or expired GitHub token")
                    print(f"2. Insufficient permissions for the organization")
                    print(f"3. GitHub API rate limiting")
                    print(f"4. Token does not have access to the organization")
                    raise PermissionError(error_msg) from e
                else:
                    print(f"HTTP error occurred: {e}")
                    raise
            
            repos = response.json()
            if not repos:
                break
            
            # Filter out archived repositories
            active_repos = [repo for repo in repos if not repo.get('archived', False)]
            print(f"Fetched {len(repos)} repos, {len(active_repos)} active (excluding {len(repos) - len(active_repos)} archived)")
            
            all_repos.extend(active_repos)
            page += 1
        
        # Extract repository names from filtered list
        repo_names = [repo['name'] for repo in all_repos]
        
        # Apply filter if specified
        if self.github_repo_filter:
            filter_pattern = re.compile(self.github_repo_filter, re.IGNORECASE)
            filtered_repos = [repo for repo in repo_names if filter_pattern.search(repo)]
            repos_to_cache = filtered_repos
        else:
            repos_to_cache = repo_names
        
        # Sort repositories alphabetically
        repos_to_cache.sort()
        
        # Save to cache
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'repositories': repos_to_cache,
                'org': self.github_org,
                'api_url': self.github_api_url
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Cached {len(repos_to_cache)} repositories")
        except Exception as e:
            print(f"Error saving cache: {e}")
        
        return repos_to_cache
    
    def get_teams(self) -> Dict[str, List[str]]:
        """Get team configurations from teams.json file"""
        teams_file = Path('teams.json')
        if not teams_file.exists():
            return {}
        
        try:
            with open(teams_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading teams configuration: {e}")
            return {}
    
    def get_team_repositories(self, team_name: str) -> List[str]:
        """Get repositories for a specific team"""
        teams = self.get_teams()
        team_repos = teams.get(team_name, [])
        return sorted(team_repos)  # Sort team repositories alphabetically
    
    def filter_repositories(self, repositories: List[str], search_term: str = "") -> List[str]:
        """Filter repositories based on search term"""
        if not search_term:
            return sorted(repositories)  # Ensure alphabetical order
        
        search_lower = search_term.lower().strip()
        filtered = [repo for repo in repositories if search_lower in repo.lower()]
        return sorted(filtered)  # Sort filtered results alphabetically
    
    def download_repository_files(self, repo_name: str) -> Path:
        """Download relevant files from a remote repository"""
        repo_dir = self.repos_dir / repo_name
        repo_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Downloading files from repository: {repo_name}")
        
        # Get repository contents - handle both "org/repo" and "repo" formats
        if '/' in repo_name:
            # repo_name already includes org
            url = f"{self.github_api_url}/repos/{repo_name}/contents"
        else:
            # repo_name is just the repo name, add org
            url = f"{self.github_api_url}/repos/{self.github_org}/{repo_name}/contents"
        
        # Debug logging
        debug_log(f"Requesting URL: {url}")
        debug_log(f"Token present: {'Yes' if self.github_token else 'No'}")
        if self.github_token:
            debug_log(f"Token (first 10 chars): {self.github_token[:10]}...")
        debug_log(f"Auth header: {self.session.headers.get('Authorization', 'Not set')}")
        debug_log(f"SSL Verify setting: {self.ssl_verify}")
        debug_log(f"Session verify setting: {self.session.verify}")
        
        try:
            response = self.session.get(url)
            
            # Check for 401 Unauthorized errors specifically
            if response.status_code == 401:
                error_msg = f"401 Unauthorized error when accessing repository {repo_name}. "
                error_msg += f"URL: {url}, Status: {response.status_code}"
                print(f"ERROR: {error_msg}")
                print(f"This typically means:")
                print(f"1. The GitHub token is invalid or expired")
                print(f"2. The token does not have the required permissions (read access to repository contents)")
                print(f"3. The repository might be private and the token doesn't have access")
                print(f"4. The token might be for a different user/organization")
                raise PermissionError(error_msg)
            
            # Check for 403 Forbidden errors specifically
            if response.status_code == 403:
                error_msg = f"403 Forbidden error when accessing repository {repo_name}. "
                if response.headers.get('X-RateLimit-Remaining') == '0':
                    error_msg += "GitHub API rate limit exceeded. "
                else:
                    error_msg += "Authentication or permission issue. "
                
                error_msg += f"URL: {url}, Status: {response.status_code}"
                print(f"ERROR: {error_msg}")
                print(f"This could mean:")
                print(f"1. The repository {repo_name} does not exist or is not accessible")
                print(f"2. Your GitHub token does not have access to this repository")
                print(f"3. The repository might be private and you don't have permissions")
                raise PermissionError(error_msg)
            
            response.raise_for_status()
            contents = response.json()
            
            # Download relevant files
            self._download_files_recursive(contents, repo_name, repo_dir)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                error_msg = f"403 Forbidden error when accessing repository {repo_name}: {e}"
                print(f"ERROR: {error_msg}")
                print(f"Repository: {self.github_org}/{repo_name}")
                print(f"Check that:")
                print(f"1. The repository exists and is accessible")
                print(f"2. Your GitHub token has access to this repository")
                print(f"3. The repository is not private without proper permissions")
                raise PermissionError(error_msg) from e
            else:
                print(f"HTTP error occurred while downloading {repo_name}: {e}")
                raise
        except Exception as e:
            print(f"Error downloading repository {repo_name}: {e}")
            raise
        
        return repo_dir
    
    def _download_files_recursive(self, contents: List[Dict], repo_name: str, base_dir: Path, current_path: str = ""):
        """Recursively download relevant files from repository"""
        relevant_files = [
            'go.mod', 'requirements.txt', 'package.json', 'pom.xml', 
            'Jenkinsfile', 'Makefile', 'Dockerfile', 'docker-compose.yml'
        ]
        
        for item in contents:
            if item.get('type') == 'file':
                file_name = item['name']
                
                # Check if this is a relevant file
                if file_name in relevant_files or file_name.endswith('.txt') or file_name.endswith('.json') or file_name.endswith('.xml') or file_name.endswith('.mod'):
                    self._download_file(item, base_dir, current_path)
            
            elif item.get('type') == 'dir':
                # Recursively explore directories (limit depth to avoid API limits)
                if len(current_path.split('/')) < 3:  # Limit depth
                    dir_url = item['url']
                    try:
                        response = self.session.get(dir_url)
                        
                        # Check for 403 errors
                        if response.status_code == 403:
                            print(f"Warning: 403 Forbidden when accessing directory {current_path}/{item['name']} in {repo_name}")
                            # Skip this directory and continue
                            continue
                        
                        response.raise_for_status()
                        dir_contents = response.json()
                        new_path = f"{current_path}/{item['name']}" if current_path else item['name']
                        self._download_files_recursive(dir_contents, repo_name, base_dir, new_path)
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 403:
                            print(f"Warning: 403 Forbidden when accessing directory {current_path}/{item['name']} in {repo_name}")
                            # Skip this directory and continue
                            continue
                        else:
                            # Silently skip other HTTP errors
                            pass
                    except Exception as e:
                        # Silently skip directory exploration errors
                        pass
    
    def _download_file(self, file_info: Dict, base_dir: Path, current_path: str):
        """Download a single file from GitHub"""
        try:
            download_url = file_info['download_url']
            response = self.session.get(download_url)
            
            # Check for 403 errors
            if response.status_code == 403:
                print(f"Warning: 403 Forbidden when downloading file {file_info['name']} from {current_path}")
                # Skip this file and continue
                return
            
            response.raise_for_status()
            
            # Create directory structure
            if current_path:
                file_dir = base_dir / current_path
                file_dir.mkdir(parents=True, exist_ok=True)
                file_path = file_dir / file_info['name']
            else:
                file_path = base_dir / file_info['name']
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(response.text)
            
            print(f"Downloaded: {file_path.relative_to(self.repos_dir)}")
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"Warning: 403 Forbidden when downloading file {file_info['name']} from {current_path}")
                # Skip this file and continue
                return
            else:
                # Silently skip other HTTP errors - some files may not be accessible
                pass
        except Exception as e:
            # Silently skip file download errors - some files may not be accessible
            pass
    
    def _load_jenkins_job_mappings(self) -> Dict:
        """Load manual Jenkins job mappings from config file"""
        mappings_file = Path(__file__).parent / 'config' / 'jenkins_job_mappings.yaml'
        
        if not mappings_file.exists():
            debug_log("No Jenkins job mappings file found")
            return {}
        
        try:
            with open(mappings_file, 'r') as f:
                data = yaml.safe_load(f)
                mappings = data.get('jenkins_job_mappings', {})
                if mappings:
                    debug_log(f"Loaded {len(mappings)} manual Jenkins job mappings")
                return mappings
        except Exception as e:
            debug_log(f"Error loading Jenkins job mappings: {e}")
            return {}
    
    def get_jenkins_build_configs(self, repo_name: str) -> Dict:
        """Get Jenkins build configurations for a repository"""
        jenkins_configs = {}
        
        # Check for manual job mappings first
        manual_jobs = self.jenkins_job_mappings.get(repo_name, [])
        if manual_jobs:
            debug_log(f"Found {len(manual_jobs)} manual job mappings for {repo_name}: {manual_jobs}")
        
        for jenkins_url in self.jenkins_urls:
            try:
                # Get jobs that might be related to this repository
                jobs_url = f"{jenkins_url}/api/json"
                auth = (self.jenkins_user, self.jenkins_token) if self.jenkins_user and self.jenkins_token else None
                
                response = self.session.get(jobs_url, auth=auth)
                
                # Check for 403 errors specifically
                if response.status_code == 403:
                    print(f"Warning: 403 Forbidden when accessing Jenkins at {jenkins_url}")
                    print(f"Jenkins authentication may be configured incorrectly or user lacks permissions")
                    # Continue without Jenkins data from this server
                    continue
                
                response.raise_for_status()
                
                jobs_data = response.json()
                self._find_jenkins_jobs(jobs_data.get('jobs', []), repo_name, jenkins_url, jenkins_configs, auth)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print(f"Warning: 403 Forbidden when accessing Jenkins at {jenkins_url}")
                    print(f"This typically indicates authentication or permission issues with Jenkins")
                    # Continue without Jenkins data from this server
                    continue
                else:
                    print(f"Warning: HTTP error accessing Jenkins at {jenkins_url}: {e}")
                    # Continue without Jenkins data from this server
                    continue
            except Exception as e:
                print(f"Warning: Could not access Jenkins at {jenkins_url} - continuing without Jenkins data: {e}")
        
        return jenkins_configs
    
    def _matches_repository(self, job_name: str, repo_name: str, job_config: str = None) -> bool:
        """Check if Jenkins job matches repository using multiple strategies"""
        job_lower = job_name.lower()
        repo_lower = repo_name.lower()
        
        # Strategy 1: Exact substring match
        if repo_lower in job_lower:
            debug_log(f"Job '{job_name}' matches repo '{repo_name}' (exact substring)")
            return True
        
        # Strategy 2: Match with underscores/hyphens normalized
        repo_normalized = repo_lower.replace('-', '').replace('_', '')
        job_normalized = job_lower.replace('-', '').replace('_', '')
        if repo_normalized in job_normalized:
            debug_log(f"Job '{job_name}' matches repo '{repo_name}' (normalized)")
            return True
        
        # Strategy 3: Match individual words (for multi-word repos)
        repo_words = set(repo_lower.replace('-', ' ').replace('_', ' ').split())
        job_words = set(job_lower.replace('-', ' ').replace('_', ' ').split())
        
        # Remove common words that don't help matching
        common_words = {'multibranch', 'pipeline', 'build', 'test', 'deploy', 'service', 'svc'}
        repo_words = repo_words - common_words
        job_words = job_words - common_words
        
        # If 2+ significant words match, consider it a match
        matching_words = repo_words.intersection(job_words)
        if len(repo_words) >= 2 and len(matching_words) >= 2:
            debug_log(f"Job '{job_name}' matches repo '{repo_name}' (word match: {matching_words})")
            return True
        
        # Strategy 4: Acronym matching (e.g., "dsp-catalog-svc" -> "dcs")
        if len(repo_words) >= 2:
            repo_acronym = ''.join([word[0] for word in sorted(repo_words) if word and len(word) > 0])
            if len(repo_acronym) >= 2 and repo_acronym in job_lower:
                debug_log(f"Job '{job_name}' matches repo '{repo_name}' (acronym: {repo_acronym})")
                return True
        
        # Strategy 5: GitHub URL matching in job config (if available)
        if job_config:
            # Look for GitHub URL patterns in config
            github_patterns = [
                repo_lower,
                f"/{repo_lower}.git",
                f"/{repo_lower}/",
            ]
            
            config_lower = job_config.lower()
            for pattern in github_patterns:
                if pattern in config_lower:
                    debug_log(f"Job '{job_name}' matches repo '{repo_name}' (GitHub URL in config)")
                    return True
        
        return False
    
    def _find_jenkins_jobs(self, jobs: List[Dict], repo_name: str, jenkins_url: str, configs: Dict, auth: Optional[Tuple]):
        """Recursively find Jenkins jobs related to repository"""
        # Get manual job mappings for this repository
        manual_jobs = self.jenkins_job_mappings.get(repo_name, [])
        
        for job in jobs:
            job_name = job.get('name', '')
            job_url = job.get('url', '')
            job_lower = job_name.lower()
            
            # Check if this job is in the manual mappings
            is_manual_match = job_name in manual_jobs
            if is_manual_match:
                debug_log(f"Job '{job_name}' matches repo '{repo_name}' (manual mapping)")
            
            # First check if job name matches using fuzzy matching or manual mapping
            name_matches = is_manual_match or self._matches_repository(job_name, repo_name)
            
            # If name doesn't match, try fetching config to check GitHub URL
            # (but only for a subset to avoid too many API calls)
            config_text = None
            should_check_config = False
            
            if name_matches:
                should_check_config = True
            else:
                # For jobs that don't match by name, check if they might match by URL
                # Only check jobs with certain keywords to limit API calls
                job_keywords = ['catalog', 'dsp', 'service', 'svc', 'api', 'ui', 'backend', 'frontend']
                if any(keyword in job_lower for keyword in job_keywords):
                    should_check_config = True
            
            if should_check_config:
                try:
                    # Get Jenkins job config
                    config_url = f"{job_url}config.xml"
                    response = self.session.get(config_url, auth=auth)
                    
                    # Check for 403 errors
                    if response.status_code == 403:
                        debug_log(f"403 Forbidden when accessing Jenkins job config for {job_name}")
                        # Skip this job and continue
                        if job.get('jobs'):
                            self._find_jenkins_jobs(job['jobs'], repo_name, jenkins_url, configs, auth)
                        continue
                    
                    response.raise_for_status()
                    config_text = response.text
                    
                    # Check if config contains GitHub URL (if name didn't match)
                    if not name_matches:
                        if self._matches_repository(job_name, repo_name, config_text):
                            debug_log(f"Job '{job_name}' matched by GitHub URL in config")
                            name_matches = True
                    
                    # If we have a match (by name or URL), store the config
                    if name_matches:
                        configs[job_name] = {
                            'url': job_url,
                            'config': config_text,
                            'jenkins_server': jenkins_url
                        }
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 403:
                        debug_log(f"403 Forbidden when accessing Jenkins job config for {job_name}")
                    else:
                        debug_log(f"Error getting Jenkins config for job {job_name}: {e}")
                    # Continue to check nested jobs
                except Exception as e:
                    debug_log(f"Error getting Jenkins config for job {job_name}: {e}")
            
            # Recursively check nested jobs
            if job.get('jobs'):
                self._find_jenkins_jobs(job['jobs'], repo_name, jenkins_url, configs, auth)
    
    def scan_remote_repository(self, repo_name: str) -> Dict:
        """Scan a remote repository for OSS compliance"""
        print(f"Starting remote scan for repository: {repo_name}")
        
        # Download repository files
        repo_dir = self.download_repository_files(repo_name)
        
        # Get Jenkins configurations
        jenkins_configs = self.get_jenkins_build_configs(repo_name)
        
        # Perform compliance scan
        scanner = RemoteComplianceScanner(repo_dir, self.virtual_repos, self.artifactory_base, jenkins_configs, self.whitelist_urls)
        report = scanner.scan()
        
        # Add repository field to all findings
        for finding in report.get('findings', []):
            finding['repository'] = repo_name
            # Construct repository URL for web link
            # Convert API URL to web URL
            web_url = self.github_api_url.replace('api.', '').replace('/api/v3', '').replace('/api', '')
            finding['repository_url'] = f"{web_url}/{self.github_org}/{repo_name}"
        
        # Add metadata
        report['scan_metadata'] = {
            'scanned_at': datetime.now().isoformat(),
            'repository_name': repo_name,
            'repository_type': 'remote',
            'github_org': self.github_org,
            'github_api_url': self.github_api_url,
            'virtual_repositories': self.virtual_repos,
            'artifactory_base': self.artifactory_base,
            'jenkins_configs_found': len(jenkins_configs)
        }
        
        return report
    
    def scan_remote_repository_enhanced(self, repo_name: str) -> Dict:
        """
        Scan a remote repository using the enhanced endpoint analyzer.
        Downloads the repository to a temp directory and runs comprehensive analysis.
        """
        if not ENHANCED_SCANNER_AVAILABLE:
            raise RuntimeError("Enhanced scanner is not available. Cannot perform enhanced scan.")
        
        print(f"\n{'='*60}")
        print(f"Enhanced scan for remote repository: {repo_name}")
        print(f"{'='*60}")
        
        try:
            # Download repository files to temp directory
            print(f"Downloading repository files...")
            repo_dir = self.download_repository_files(repo_name)
            print(f"Repository downloaded to: {repo_dir}")
            
            # Run enhanced compliance scan on downloaded files
            print(f"Running enhanced endpoint analysis...")
            enhanced_scanner = EnhancedComplianceScanner(
                repo_root=str(repo_dir),
                virtual_repos=self.virtual_repos,
                artifactory_base=self.artifactory_base,
                whitelist_urls=self.whitelist_urls,
                repo_name=repo_name,
                jenkins_urls=self.jenkins_urls,
                jenkins_user=self.jenkins_user,
                jenkins_token=self.jenkins_token
            )
            
            report = enhanced_scanner.scan_comprehensive()
            
            # Update metadata to indicate remote scan
            if 'scan_metadata' not in report:
                report['scan_metadata'] = {}
            
            report['scan_metadata'].update({
                'repository_name': repo_name,
                'repository_type': 'remote_enhanced',
                'scan_method': 'enhanced_endpoint_analyzer',
                'github_org': self.github_org,
                'github_api_url': self.github_api_url,
                'temp_directory': str(repo_dir)
            })
            
            # Update summary to include repository name
            if 'summary' in report:
                report['summary']['repository_name'] = repo_name
            
            # Add repository URL and file URLs to findings
            web_url = self.github_api_url.replace('api.', '').replace('/api/v3', '').replace('/api', '')
            repo_url = f"{web_url}/{self.github_org}/{repo_name}"

            # Add repository URL to metadata
            report['scan_metadata']['repository_url'] = repo_url
            
            # Fetch and add default branch
            try:
                repo_info_url = f"{self.github_api_url}/repos/{self.github_org}/{repo_name}"
                repo_info_resp = self.session.get(repo_info_url)
                if repo_info_resp.status_code == 200:
                    repo_info = repo_info_resp.json()
                    report['scan_metadata']['default_branch'] = repo_info.get('default_branch', 'main')
                else:
                    report['scan_metadata']['default_branch'] = 'main'
            except Exception as e:
                print(f"Could not fetch default branch: {e}")
                report['scan_metadata']['default_branch'] = 'main'

            for finding in report.get('findings', []):
                finding['repository'] = repo_name
                finding['repository_url'] = repo_url

                if 'file' in finding and finding['file']:
                    file_path = finding['file'].replace('\\', '/')
                    default_branch = report['scan_metadata'].get('default_branch', 'main')
                    finding['file_url'] = f"{repo_url}/blob/{default_branch}/{file_path}"
            
            print(f"Enhanced scan completed for {repo_name}")
            return report
            
        except Exception as e:
            print(f"FATAL ERROR in enhanced scan for {repo_name}: {e}")
            import traceback
            traceback.print_exc()
            # Re-raise the exception instead of falling back to basic scan
            raise RuntimeError(f"Enhanced scan failed for {repo_name}: {e}") from e
    
    def scan_multiple_repositories(self, repo_names: List[str]) -> Dict:
        """Scan multiple repositories and return combined report"""
        all_reports = {}
        combined_findings = []
        total_compliant = 0
        total_non_compliant = 0
        
        for repo_name in repo_names:
            try:
                print(f"\n{'='*50}")
                print(f"Scanning repository: {repo_name}")
                print(f"{'='*50}")
                
                report = self.scan_remote_repository(repo_name)
                all_reports[repo_name] = report
                
                # Aggregate findings with repository context
                repo_findings = report.get('findings', [])
                for finding in repo_findings:
                    # Add repository context to each finding
                    finding['repository'] = repo_name
                    finding['source_repository'] = repo_name  # Keep for backward compatibility
                    finding['file'] = f"{repo_name}: {finding.get('file', 'Unknown')}"
                    # Construct repository URL for web link
                    web_url = self.github_api_url.replace('api.', '').replace('/api/v3', '').replace('/api', '')
                    finding['repository_url'] = f"{web_url}/{self.github_org}/{repo_name}"
                combined_findings.extend(repo_findings)
                total_compliant += report.get('scan_summary', {}).get('compliant_checks', 0)
                total_non_compliant += report.get('scan_summary', {}).get('non_compliant_checks', 0)
                
            except Exception as e:
                print(f"Error scanning repository {repo_name}: {e}")
                all_reports[repo_name] = {'error': str(e)}
        
        # Create combined report
        total_checks = total_compliant + total_non_compliant
        combined_report = {
            'scan_summary': {
                'total_items': total_checks,  # UI expects total_items
                'total_findings': len(combined_findings),
                'compliant_items': total_compliant,  # UI expects compliant_items
                'compliant_checks': total_compliant,  # Keep for backward compatibility
                'non_compliant_items': total_non_compliant,  # UI expects non_compliant_items
                'non_compliant_checks': total_non_compliant,  # Keep for backward compatibility
                'compliance_percentage': round((total_compliant / total_checks) * 100, 2) if total_checks > 0 else 100,
                'repositories_scanned': len(repo_names),
                'repository_name': f"Multi-repo scan ({len(repo_names)} repositories)"
            },
            'approved_virtual_repositories': self.virtual_repos,
            'findings': combined_findings,
            'individual_reports': all_reports,
            'recommendations': self._generate_multi_repo_recommendations(combined_findings)
        }
        
        # Add metadata
        combined_report['scan_metadata'] = {
            'scanned_at': datetime.now().isoformat(),
            'repository_type': 'remote_multi',
            'github_org': self.github_org,
            'github_api_url': self.github_api_url,
            'repositories': repo_names,
            'virtual_repositories': self.virtual_repos,
            'artifactory_base': self.artifactory_base
        }
        
        return combined_report
    
    def scan_multiple_repositories_enhanced(self, repo_names: List[str]) -> Dict:
        """Scan multiple repositories with enhanced endpoint analysis"""
        if not ENHANCED_SCANNER_AVAILABLE:
            print("Enhanced scanner not available. Falling back to basic scan.")
            return self.scan_multiple_repositories(repo_names)
        
        all_reports = {}
        combined_findings = []
        total_components = 0
        total_compliant = 0
        total_non_compliant = 0
        
        for repo_name in repo_names:
            try:
                print(f"\n{'='*50}")
                print(f"Enhanced scan for: {repo_name}")
                print(f"{'='*50}")
                
                report = self.scan_remote_repository_enhanced(repo_name)
                all_reports[repo_name] = report
                
                # Aggregate findings with repository context
                repo_findings = report.get('findings', [])
                for finding in repo_findings:
                    # Ensure repository context is set
                    if 'repository' not in finding:
                        finding['repository'] = repo_name
                    finding['source_repository'] = repo_name
                combined_findings.extend(repo_findings)
                
                # Aggregate component statistics
                if 'summary' in report and 'component_analysis' in report['summary']:
                    comp_analysis = report['summary']['component_analysis']
                    total_components += comp_analysis.get('total_components', 0)
                    total_compliant += comp_analysis.get('compliant_components', 0)
                    total_non_compliant += comp_analysis.get('non_compliant_components', 0)
                
            except Exception as e:
                print(f"Error in enhanced scan for {repo_name}: {e}")
                all_reports[repo_name] = {'error': str(e)}
        
        # Create combined report
        compliance_percentage = round((total_compliant / total_components * 100) if total_components > 0 else 100, 2)
        
        combined_report = {
            'summary': {
                'scan_type': 'remote_multi_enhanced',
                'repository_name': f"Multi-repo enhanced scan ({len(repo_names)} repositories)",
                'scan_timestamp': datetime.now().isoformat(),
                'component_analysis': {
                    'total_components': total_components,
                    'compliant_components': total_compliant,
                    'non_compliant_components': total_non_compliant,
                    'component_compliance_percentage': compliance_percentage
                },
                'repositories_scanned': len(repo_names)
            },
            'approved_virtual_repositories': self.virtual_repos,
            'findings': combined_findings,
            'individual_reports': all_reports,
            'scan_metadata': {
                'scanned_at': datetime.now().isoformat(),
                'repository_type': 'remote_multi_enhanced',
                'scan_method': 'enhanced_endpoint_analyzer',
                'github_org': self.github_org,
                'github_api_url': self.github_api_url,
                'repositories': repo_names,
                'virtual_repositories': self.virtual_repos,
                'artifactory_base': self.artifactory_base
            }
        }
        
        return combined_report
    
    def scan_team_repositories(self, team_name: str) -> Dict:
        """Scan all repositories for a specific team"""
        team_repos = self.get_team_repositories(team_name)
        
        if not team_repos:
            raise ValueError(f"No repositories found for team: {team_name}")
        
        print(f"Scanning {len(team_repos)} repositories for team: {team_name}")
        print(f"Repositories: {', '.join(team_repos)}")
        
        combined_report = self.scan_multiple_repositories(team_repos)
        
        # Update metadata to reflect team scan
        combined_report['scan_metadata']['scan_type'] = 'team'
        combined_report['scan_metadata']['team_name'] = team_name
        combined_report['scan_summary']['repository_name'] = f"Team {team_name} scan ({', '.join(team_repos)})"
        
        return combined_report

    def create_fix_pr(self, repo_name: str, report_data: Dict) -> Dict:
        """Create a GitHub Pull Request with automated fixes and an action plan."""
        if not self.github_token:
            return {"success": False, "error": "GitHub token not configured"}

        api_base = self.github_api_url
        org = self.github_org

        # Test connection first
        print(f"Testing GitHub connection...")
        print(f"API Base: {api_base}")
        print(f"Organization: {org}")
        print(f"Repository: {repo_name}")
        print(f"Token present: {'Yes' if self.github_token else 'No'}")
        if self.github_token:
            print(f"Token (first 10 chars): {self.github_token[:10]}...")
        
        # 1. Get repository info to find default branch
        repo_url = f"{api_base}/repos/{org}/{repo_name}"
        print(f"Fetching repository info from: {repo_url}")
        
        try:
            resp = self.session.get(repo_url)
            print(f"Repository info response status: {resp.status_code}")
            
            if resp.status_code != 200:
                error_detail = resp.text[:500] if resp.text else "No response body"
                print(f"Error response: {error_detail}")
                return {"success": False, "error": f"Could not fetch repository info (HTTP {resp.status_code}): {error_detail}"}
            
            repo_info = resp.json()
            default_branch = repo_info.get('default_branch', 'main')
            print(f"Default branch: {default_branch}")
        except Exception as e:
            print(f"Exception while fetching repository info: {e}")
            return {"success": False, "error": f"Exception while fetching repository info: {str(e)}"}

        # 2. Get the commit SHA for the default branch
        ref_url = f"{api_base}/repos/{org}/{repo_name}/git/ref/heads/{default_branch}"
        print(f"Fetching branch reference from: {ref_url}")
        
        try:
            resp = self.session.get(ref_url)
            print(f"Branch reference response status: {resp.status_code}")
            
            if resp.status_code != 200:
                error_detail = resp.text[:500] if resp.text else "No response body"
                print(f"Error response: {error_detail}")
                return {"success": False, "error": f"Could not get default branch reference (HTTP {resp.status_code}): {error_detail}"}
            
            ref_data = resp.json()
            base_sha = ref_data['object']['sha']
            print(f"Base SHA: {base_sha}")
        except Exception as e:
            print(f"Exception while fetching branch reference: {e}")
            return {"success": False, "error": f"Exception while fetching branch reference: {str(e)}"}

        # 3. Get authenticated user info for branch naming
        user_url = f"{api_base}/user"
        try:
            user_resp = self.session.get(user_url)
            if user_resp.status_code == 200:
                user_data = user_resp.json()
                username = user_data.get('login', 'oss-compliance')
                print(f"Authenticated as user: {username}")
            else:
                username = 'oss-compliance'
                print(f"Could not get user info, using default username: {username}")
        except Exception as e:
            username = 'oss-compliance'
            print(f"Exception getting user info, using default username: {username}")
        
        # 3. Create a new branch with compliant naming (usr/<username>/<branch-name>)
        import time
        branch_name = f"usr/{username}/oss-compliance-fixes-{int(time.time())}"
        create_ref_url = f"{api_base}/repos/{org}/{repo_name}/git/refs"
        print(f"Creating branch '{branch_name}' at: {create_ref_url}")
        
        try:
            resp = self.session.post(create_ref_url, json={
                "ref": f"refs/heads/{branch_name}",
                "sha": base_sha
            })
            print(f"Create branch response status: {resp.status_code}")
            
            if resp.status_code != 201:
                error_detail = resp.text[:500] if resp.text else "No response body"
                print(f"Error response: {error_detail}")
                return {"success": False, "error": f"Failed to create branch (HTTP {resp.status_code}): {error_detail}"}
            
            print(f"Branch '{branch_name}' created successfully")
        except Exception as e:
            print(f"Exception while creating branch: {e}")
            return {"success": False, "error": f"Exception while creating branch: {str(e)}"}

        # 4. Prepare files to commit
        import base64
        files_to_commit = []
        
        # We will generate a setup script that injects the right environment variables
        env_script = "#!/bin/bash\n# Source this script in your CI pipeline before building to ensure OSS compliance\n\n"
        
        has_go = any(f['type'] == 'go_module' for f in report_data.get('findings', []))
        has_python = any(f['type'] == 'python_requirements' for f in report_data.get('findings', []))
        has_node = any(f['type'] == 'node_package' for f in report_data.get('findings', []))
        
        if has_go:
            go_repo = self.virtual_repos.get("go", "go-virtual")
            env_script += f"export GOPROXY=https://{self.artifactory_base}/artifactory/api/go/{go_repo},direct\n"
            env_script += f"export GONOSUMDB=*\n"
        
        if has_python:
            pypi_repo = self.virtual_repos.get("pypi", "pypi-virtual")
            env_script += f"export PIP_INDEX_URL=https://{self.artifactory_base}/artifactory/api/pypi/{pypi_repo}/simple\n"
            
        if has_node:
            npm_repo = self.virtual_repos.get("npm", "npm-virtual")
            env_script += f"export npm_config_registry=https://{self.artifactory_base}/artifactory/api/npm/{npm_repo}/\n"

        files_to_commit.append({
            "path": "oss_compliance_setup.sh",
            "content": env_script,
            "message": "Add OSS compliance environment setup script"
        })
        
        # Generate an actionable README guide
        readme_content = "# OSS Compliance Remediation Plan\n\n"
        readme_content += "This PR provides automated scripts and instructions to fix your repository's OSS compliance issues.\n\n"
        readme_content += "### How to apply these fixes:\n"
        readme_content += "1. **CI Pipeline Integration**: In your `Jenkinsfile`, `Makefile`, or CI script, add the following before your build commands:\n"
        readme_content += "   ```bash\n   source oss_compliance_setup.sh\n   ```\n"
        readme_content += "   This will automatically inject the correct Artifactory endpoints for GOPROXY, PIP_INDEX_URL, and NPM registries.\n\n"
        readme_content += "### Specific Findings Addressed:\n"
        for finding in report_data.get('findings', []):
            readme_content += f"- **{finding['file']}**: {finding['issue']} -> Action: `{finding['recommended_action']}`\n"
            
        files_to_commit.append({
            "path": "OSS_COMPLIANCE_README.md",
            "content": readme_content,
            "message": "Add OSS compliance remediation guide"
        })
        
        # Generate markdown report
        try:
            from markdown_generator import generate_markdown_summary
            markdown_report = generate_markdown_summary(report_data)
            files_to_commit.append({
                "path": "OSS_COMPLIANCE_REPORT.md",
                "content": markdown_report,
                "message": "Add detailed OSS compliance report (markdown format)"
            })
            print("Added markdown report to PR")
        except Exception as e:
            print(f"Warning: Could not generate markdown report: {e}")
        
        # Generate spec file
        try:
            import json
            spec_data = {
                'windsurf_automation_spec': {
                    'version': '1.0',
                    'description': 'Migrate OSS repository references to approved Artifactory virtual repositories',
                    'target_repository': repo_name,
                    'execution_strategy': 'pipeline_level',
                    'approved_virtual_repositories': self.virtual_repos,
                    'artifactory_base_url': f'https://{self.artifactory_base}/artifactory',
                    'changes': []
                }
            }
            
            # Generate changes based on findings
            for finding in report_data.get('findings', []):
                safe_filename = finding['file'].replace('/', '-').replace('\\', '-')
                change = {
                    'id': f"fix-{finding['type']}-{safe_filename}",
                    'type': 'file_modification',
                    'target_file': finding['file'],
                    'priority': finding['severity'],
                    'action': finding.get('recommended_action', 'Update to use approved virtual repository'),
                    'issue': finding['issue'],
                    'recommended_action': finding['recommended_action'],
                    'compliant': False
                }
                spec_data['windsurf_automation_spec']['changes'].append(change)
            
            spec_content = json.dumps(spec_data, indent=2)
            files_to_commit.append({
                "path": "OSS_COMPLIANCE_SPEC.json",
                "content": spec_content,
                "message": "Add OSS compliance automation spec"
            })
            print("Added spec file to PR")
        except Exception as e:
            print(f"Warning: Could not generate spec file: {e}")

        # 5. Commit files to the new branch
        for file_data in files_to_commit:
            content_b64 = base64.b64encode(file_data["content"].encode('utf-8')).decode('utf-8')
            put_file_url = f"{api_base}/repos/{org}/{repo_name}/contents/{file_data['path']}"
            resp = self.session.put(put_file_url, json={
                "message": file_data['message'],
                "content": content_b64,
                "branch": branch_name
            })
            if resp.status_code not in (200, 201):
                # Ignore failures for individual files, try to proceed
                print(f"Warning: Failed to commit {file_data['path']}: {resp.text}")

        # 6. Create the Pull Request
        pr_url = f"{api_base}/repos/{org}/{repo_name}/pulls"
        pr_body = (
            "## Automated OSS Compliance Fixes\n\n"
            "This PR was automatically generated by the OSS Compliance Web App to help your repository meet enterprise compliance standards.\n\n"
            "### What's inside:\n"
            "- `oss_compliance_setup.sh`: A ready-to-use script that sets up the correct Artifactory endpoints (`GOPROXY`, `PIP_INDEX_URL`, `npm_config_registry`).\n"
            "- `OSS_COMPLIANCE_README.md`: Quick start guide with findings and integration instructions.\n"
            "- `OSS_COMPLIANCE_REPORT.md`: Detailed compliance analysis report with executive summary and recommendations.\n"
            "- `OSS_COMPLIANCE_SPEC.json`: Machine-readable automation spec for WindSurf or other automation tools.\n\n"
            "**Action Required**: Merge this PR and update your `Jenkinsfile` or `Makefile` to source `oss_compliance_setup.sh` before running build commands."
        )
        resp = self.session.post(pr_url, json={
            "title": "Fix: Implement OSS Compliance Endpoints (Artifactory)",
            "body": pr_body,
            "head": branch_name,
            "base": default_branch
        })

        print(f"Create PR response status: {resp.status_code}")
        
        if resp.status_code == 201:
            try:
                pr_data = resp.json()
                pr_url = pr_data.get('html_url')
                print(f"PR created successfully: {pr_url}")
                return {"success": True, "pr_url": pr_url}
            except Exception as e:
                print(f"Exception while parsing PR response: {e}")
                return {"success": False, "error": f"PR may have been created but failed to parse response: {str(e)}"}
        else:
            error_detail = resp.text[:500] if resp.text else "No response body"
            print(f"Error response: {error_detail}")
            
            # Try to parse as JSON for better error message
            try:
                error_json = resp.json()
                error_message = error_json.get('message', error_detail)
                print(f"GitHub API error message: {error_message}")
                return {"success": False, "error": f"Failed to create PR (HTTP {resp.status_code}): {error_message}"}
            except:
                return {"success": False, "error": f"Failed to create PR (HTTP {resp.status_code}): {error_detail}"}
    
    def _generate_multi_repo_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Generate recommendations for multiple repositories"""
        recommendations = []
        
        # Group findings by severity
        critical = [f for f in findings if f['severity'] == 'CRITICAL']
        high = [f for f in findings if f['severity'] == 'HIGH']
        medium = [f for f in findings if f['severity'] == 'MEDIUM']
        
        if critical:
            recommendations.append({
                'priority': 'CRITICAL',
                'action': 'Replace direct GitHub URL installs in Jenkinsfiles',
                'affected_files': list(set([f['file'] for f in critical])),
                'affected_repos': list(set([f['repository'] for f in critical if 'repository' in f])),
                'implementation': 'Use packages from approved virtual repository instead'
            })
        
        if high:
            recommendations.append({
                'priority': 'HIGH',
                'action': 'Configure package manager proxies in Jenkins shared library',
                'affected_files': list(set([f['file'] for f in high])),
                'affected_repos': list(set([f['repository'] for f in high if 'repository' in f])),
                'implementation': 'Add GOPROXY, PIP_INDEX_URL, NPM_CONFIG_REGISTRY environment variables'
            })
        
        return recommendations
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")


class RemoteComplianceScanner:
    def __init__(self, repo_root: Path, virtual_repos: Dict, artifactory_base: str, jenkins_configs: Dict = None, whitelist_urls: List[str] = None):
        self.repo_root = repo_root
        self.virtual_repos = virtual_repos
        self.artifactory_base = artifactory_base
        self.jenkins_configs = jenkins_configs or {}
        self.whitelist_urls = whitelist_urls or []
        self.findings = []
        self.compliant_count = 0
        self.non_compliant_count = 0
        # New: Track individual OSS items for accurate compliance calculation
        self.total_items = 0
        self.compliant_items = 0
        self.non_compliant_items = 0
    
    def scan(self) -> Dict:
        """Scan downloaded repository files for compliance"""
        print(f"Scanning repository files in: {self.repo_root}")
        
        # Scan Go modules
        self.scan_go_modules()
        
        # Scan Python requirements
        self.scan_python_requirements()
        
        # Scan Node.js package.json
        self.scan_node_packages()
        
        # Scan Maven pom.xml
        self.scan_maven_poms()
        
        # Scan Jenkinsfiles (including remote configs)
        self.scan_jenkinsfiles()
        
        # Scan Makefiles
        self.scan_makefiles()
        
        return self.generate_report()
    
    def is_url_whitelisted(self, url: str) -> bool:
        """Check if a URL matches any whitelisted patterns"""
        if not self.whitelist_urls:
            # Check for default trusted organizations even if whitelist is empty
            trusted_organizations = ['isg-edge', 'ISG-Edge', 'fusion-e', 'eos2git.cec.lab.emc.com']
            url_lower = url.lower()
            for trusted_org in trusted_organizations:
                if trusted_org.lower() in url_lower:
                    return True
            return False
        
        url_lower = url.lower()
        for whitelist_pattern in self.whitelist_urls:
            if whitelist_pattern.lower() in url_lower:
                return True
        return False
    
    def scan_go_modules(self):
        """Scan go.mod files for Go proxy configuration and count individual dependencies"""
        go_mod_files = list(self.repo_root.rglob('go.mod'))
        
        for go_mod in go_mod_files:
            relative_path = go_mod.relative_to(self.repo_root)
            content = go_mod.read_text()
            
            # Parse individual go modules
            go_deps = []
            in_require = False
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('require ('):
                    in_require = True
                elif line == ')':
                    in_require = False
                elif in_require and line and not line.startswith('//'):
                    # Parse dependency line: "github.com/package v1.0.0"
                    parts = line.split()
                    if len(parts) >= 2 and not parts[0].startswith('//'):
                        go_deps.append(parts[0])
                elif line.startswith('require ') and not line.startswith('//'):
                    # Single line require: "require github.com/package v1.0.0"
                    parts = line[7:].strip().split()
                    if len(parts) >= 2:
                        go_deps.append(parts[0])
            
            # Determine if GOPROXY is configured for Artifactory
            goproxy_configured = False
            jenkins_goproxy_configured = self._check_jenkins_goproxy_config()  # Check Jenkins configuration
            if f'{self.artifactory_base}' in content and 'go' in content.lower():
                goproxy_configured = True
            
            # Count each Go dependency
            for dep in go_deps:
                self.total_items += 1
                # Check if dependency URL is whitelisted
                if self.is_url_whitelisted(dep):
                    self.compliant_items += 1
                    continue
                    
                if goproxy_configured or jenkins_goproxy_configured:
                    self.compliant_items += 1
                else:
                    self.non_compliant_items += 1
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'go_module',
                        'issue': f'Go dependency {dep} not using approved proxy',
                        'severity': 'HIGH',
                        'recommended_action': f'Configure GOPROXY=https://{self.artifactory_base}/artifactory/api/go/{self.virtual_repos.get("go", "go-virtual")},direct',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
            
            # Keep file-level check for backward compatibility
            if 'github.com/' in content and not goproxy_configured and not jenkins_goproxy_configured:
                self.findings.append({
                    'file': str(relative_path),
                    'type': 'go_module',
                    'issue': 'Go dependencies from github.com (requires GOPROXY configuration)',
                    'severity': 'HIGH',
                    'recommended_action': f'Configure GOPROXY=https://{self.artifactory_base}/artifactory/api/go/{self.virtual_repos.get("go", "go-virtual")},direct',
                    'compliant': False,
                    'repository': self.repo_root.name
                })
                self.non_compliant_count += 1
            elif goproxy_configured:
                self.compliant_count += 1
    
    def scan_python_requirements(self):
        """Scan requirements.txt files for PyPI configuration and count individual packages"""
        req_files = list(self.repo_root.rglob('requirements.txt'))
        
        for req_file in req_files:
            relative_path = req_file.relative_to(self.repo_root)
            content = req_file.read_text()
            
            # Parse individual requirements
            requirements = []
            for line in content.split('\n'):
                line = line.strip()
                # Skip comments, empty lines, and options
                if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('#'):
                    # Extract package name (before version specifiers)
                    pkg_name = re.split(r'[<>=!~]', line)[0].strip()
                    if pkg_name and not pkg_name.startswith('#'):
                        requirements.append(pkg_name)
            
            # Check for direct GitHub URLs
            github_urls = re.findall(r'https://github\.com/[^\s]+', content)
            if github_urls:
                for url in github_urls:
                    # Check if URL is whitelisted
                    if self.is_url_whitelisted(url):
                        self.compliant_items += 1
                        self.total_items += 1
                        continue
                        
                    self.non_compliant_items += 1
                    self.total_items += 1
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'python_requirements',
                        'issue': f'Direct GitHub URL: {url}',
                        'severity': 'CRITICAL',
                        'recommended_action': f'Replace with package from {self.virtual_repos.get("pypi", "pypi-virtual")}',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
                    self.non_compliant_count += 1
            
            # Check if file has index-url configuration
            has_index_url = '--index-url' in content or 'index-url' in content
            is_compliant_registry = has_index_url and f'{self.artifactory_base}' in content and self.virtual_repos.get('pypi', 'pypi-virtual') in content
            
            # Count each requirement
            for req in requirements:
                self.total_items += 1
                if is_compliant_registry:
                    self.compliant_items += 1
                else:
                    self.non_compliant_items += 1
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'python_requirements',
                        'issue': f'Python package {req} not using approved PyPI virtual repository',
                        'severity': 'HIGH',
                        'recommended_action': f'Add: --index-url https://{self.artifactory_base}/artifactory/api/pypi/{self.virtual_repos.get("pypi", "pypi-virtual")}/simple',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
            
            # Keep file-level check for backward compatibility
            if not has_index_url:
                self.findings.append({
                    'file': str(relative_path),
                    'type': 'python_requirements',
                    'issue': 'No pip index-url configured (defaults to PyPI)',
                    'severity': 'HIGH',
                    'recommended_action': f'Add: --index-url https://{self.artifactory_base}/artifactory/api/pypi/{self.virtual_repos.get("pypi", "pypi-virtual")}/simple',
                    'compliant': False,
                    'repository': self.repo_root.name
                })
                self.non_compliant_count += 1
            elif is_compliant_registry:
                self.compliant_count += 1
    
    def scan_node_packages(self):
        """Scan package.json files for NPM registry configuration and count individual dependencies"""
        package_files = list(self.repo_root.rglob('package.json'))
        
        for pkg_file in package_files:
            relative_path = pkg_file.relative_to(self.repo_root)
            try:
                content = json.loads(pkg_file.read_text())
                
                # Collect all dependencies
                dependencies = {}
                if 'dependencies' in content:
                    dependencies.update(content['dependencies'])
                if 'devDependencies' in content:
                    dependencies.update(content['devDependencies'])
                if 'peerDependencies' in content:
                    dependencies.update(content['peerDependencies'])
                
                # Check for publishConfig or registry configuration
                registry_configured = False
                if 'publishConfig' in content and 'registry' in content['publishConfig']:
                    if self.artifactory_base in content['publishConfig']['registry']:
                        registry_configured = True
                
                # Count each npm dependency
                for dep_name in dependencies.keys():
                    self.total_items += 1
                    if registry_configured:
                        self.compliant_items += 1
                    else:
                        self.non_compliant_items += 1
                        self.findings.append({
                            'file': str(relative_path),
                            'type': 'node_package',
                            'issue': f'NPM package {dep_name} not using approved registry',
                            'severity': 'HIGH',
                            'recommended_action': f'Configure NPM registry: {self.virtual_repos.get("npm", "npm-virtual")}',
                            'compliant': False,
                            'repository': self.repo_root.name
                        })
                
                # Keep file-level check for backward compatibility
                if not registry_configured:
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'node_package',
                        'issue': 'No NPM registry configured (defaults to npmjs.org)',
                        'severity': 'HIGH',
                        'recommended_action': f'Configure NPM registry: {self.virtual_repos.get("npm", "npm-virtual")}',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
                    self.non_compliant_count += 1
                else:
                    self.compliant_count += 1
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    
    def scan_maven_poms(self):
        """Scan pom.xml files for Maven repository configuration and count individual dependencies"""
        pom_files = list(self.repo_root.rglob('pom.xml'))
        
        for pom_file in pom_files:
            relative_path = pom_file.relative_to(self.repo_root)
            content = pom_file.read_text()
            
            # Parse Maven dependencies
            maven_deps = []
            # Simple regex to find dependency entries
            dep_pattern = re.compile(r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>', re.IGNORECASE)
            matches = dep_pattern.findall(content)
            for group_id, artifact_id in matches:
                maven_deps.append(f"{group_id}:{artifact_id}")
            
            # Check for repository/mirror configuration
            has_artifactory_config = self.artifactory_base in content and self.virtual_repos.get('maven', 'maven-virtual') in content
            
            # Count each Maven dependency
            for dep in maven_deps:
                self.total_items += 1
                
                # Check if this is an internal Maven dependency
                internal_maven_patterns = [
                    'com.dell',
                    'com.emc', 
                    'com.delltechnologies',
                    'com.isgedge',
                    'com.vmware'
                ]
                
                is_internal_maven = False
                if ':' in dep:
                    group_id = dep.split(':')[0].lower()
                    for internal_pattern in internal_maven_patterns:
                        if group_id.startswith(internal_pattern):
                            is_internal_maven = True
                            break
                
                # Consider compliant if: has Artifactory config OR is internal Maven dependency
                if has_artifactory_config or is_internal_maven:
                    self.compliant_items += 1
                else:
                    self.non_compliant_items += 1
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'maven_pom',
                        'issue': f'Maven dependency {dep} not using approved repository',
                        'severity': 'HIGH',
                        'recommended_action': f'Add mirror to {self.virtual_repos.get("maven", "maven-virtual")}',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
            
            # Keep file-level check for backward compatibility
            # Consider compliant if: has Artifactory config OR all deps are internal Maven
            has_internal_deps = any(':' in dep and dep.split(':')[0].lower().startswith(pattern) 
                                   for dep in maven_deps 
                                   for pattern in ['com.dell', 'com.emc', 'com.delltechnologies', 'com.isgedge', 'com.vmware'])
            
            if has_artifactory_config or (maven_deps and has_internal_deps):
                self.compliant_count += 1
            else:
                self.findings.append({
                    'file': str(relative_path),
                    'type': 'maven_pom',
                    'issue': 'No Artifactory Maven repository configured (defaults to Maven Central)',
                    'severity': 'HIGH',
                    'recommended_action': f'Add mirror to {self.virtual_repos.get("maven", "maven-virtual")}',
                    'compliant': False,
                    'repository': self.repo_root.name
                })
                self.non_compliant_count += 1
    
    def scan_jenkinsfiles(self):
        """Scan Jenkinsfiles for repository configurations"""
        jenkinsfiles = list(self.repo_root.rglob('Jenkinsfile'))
        
        for jenkinsfile in jenkinsfiles:
            relative_path = jenkinsfile.relative_to(self.repo_root)
            content = jenkinsfile.read_text()
            
            # Check for direct GitHub installs
            github_installs = re.findall(r'pip install https://github\.com/[^\s]+', content)
            if github_installs:
                for install in github_installs:
                    # Extract URL from the install command
                    url_match = re.search(r'https://github\.com/[^\s]+', install)
                    if url_match:
                        url = url_match.group(0)
                        # Check if URL is whitelisted
                        if self.is_url_whitelisted(url):
                            continue
                            
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'jenkinsfile',
                        'issue': f'Direct GitHub install: {install}',
                        'severity': 'CRITICAL',
                        'recommended_action': f'Replace with package from {self.virtual_repos.get("pypi", "pypi-virtual")}',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
                    self.non_compliant_count += 1
        
        # Also scan Jenkins configurations from API
        for job_name, job_config in self.jenkins_configs.items():
            config_content = job_config.get('config', '')
            
            # Check for direct GitHub installs in Jenkins config
            github_installs = re.findall(r'pip install https://github\.com/[^\s]+', config_content)
            if github_installs:
                for install in github_installs:
                    # Extract URL from the install command
                    url_match = re.search(r'https://github\.com/[^\s]+', install)
                    if url_match:
                        url = url_match.group(0)
                        # Check if URL is whitelisted
                        if self.is_url_whitelisted(url):
                            continue
                            
                    self.findings.append({
                        'file': f"Jenkins Job: {job_name}",
                        'type': 'jenkinsfile',
                        'issue': f'Direct GitHub install in Jenkins config: {install}',
                        'severity': 'CRITICAL',
                        'recommended_action': f'Replace with package from {self.virtual_repos.get("pypi", "pypi-virtual")}',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
                    self.non_compliant_count += 1
    
    def scan_makefiles(self):
        """Scan Makefiles for repository configurations"""
        makefiles = list(self.repo_root.rglob('Makefile'))
        
        for makefile in makefiles:
            relative_path = makefile.relative_to(self.repo_root)
            content = makefile.read_text()
            
            # Check for Artifactory references
            if self.artifactory_base in content:
                # Check if using approved virtual repos
                uses_approved = False
                for repo_name in self.virtual_repos.values():
                    if repo_name in content:
                        uses_approved = True
                        break
                
                if uses_approved:
                    self.compliant_count += 1
                else:
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'makefile',
                        'issue': 'Uses Artifactory but not approved virtual repository',
                        'severity': 'MEDIUM',
                        'recommended_action': 'Update to use approved virtual repository from list',
                        'compliant': False,
                        'repository': self.repo_root.name
                    })
                    self.non_compliant_count += 1
    
    def generate_report(self) -> Dict:
        """Generate compliance report with per-dependency compliance calculation"""
        compliance_percentage = 100 if self.total_items == 0 else round((self.compliant_items / self.total_items) * 100, 2)
        
        return {
            'scan_summary': {
                'total_findings': len(self.findings),
                'total_items': self.total_items,
                'compliant_items': self.compliant_items,
                'non_compliant_items': self.non_compliant_items,
                'compliant_checks': self.compliant_count,
                'non_compliant_checks': self.non_compliant_count,
                'compliance_percentage': compliance_percentage,
                'repository_name': self.repo_root.name
            },
            'approved_virtual_repositories': self.virtual_repos,
            'findings': self.findings,
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        # Group findings by severity
        critical = [f for f in self.findings if f['severity'] == 'CRITICAL']
        high = [f for f in self.findings if f['severity'] == 'HIGH']
        medium = [f for f in self.findings if f['severity'] == 'MEDIUM']
        
        if critical:
            recommendations.append({
                'priority': 'CRITICAL',
                'action': 'Replace direct GitHub URL installs in Jenkinsfiles',
                'affected_files': [f['file'] for f in critical],
                'implementation': 'Use packages from approved virtual repository instead'
            })
        
        if high:
            recommendations.append({
                'priority': 'HIGH',
                'action': 'Configure package manager proxies in Jenkins shared library',
                'affected_files': [f['file'] for f in high],
                'implementation': 'Add GOPROXY, PIP_INDEX_URL, NPM_CONFIG_REGISTRY environment variables'
            })
        
        if medium:
            recommendations.append({
                'priority': 'MEDIUM',
                'action': 'Review and update dependency configurations',
                'affected_files': [f['file'] for f in medium],
                'implementation': 'Update configuration files to use approved repositories'
            })
        
        return recommendations
    
    def _check_jenkins_goproxy_config(self) -> bool:
        """Check if Jenkins has GOPROXY configured globally."""
        try:
            jenkins_user = os.getenv('JENKINS_USER', '')
            jenkins_token = os.getenv('JENKINS_API_TOKEN', '')
            jenkins_urls = [url.strip() for url in os.getenv('JENKINS_URLS', '').split(',') if url.strip()]
            
            debug_log(f"Checking Jenkins GOPROXY config with {len(jenkins_urls)} URLs")
            
            for jenkins_url in jenkins_urls:
                try:
                    jobs_url = f"{jenkins_url}/api/json"
                    auth = (jenkins_user, jenkins_token) if jenkins_user and jenkins_token else None
                    response = requests.get(jobs_url, auth=auth, verify=False)
                    response.raise_for_status()
                    jobs_data = response.json()
                    
                    debug_log(f"Successfully connected to Jenkins at {jenkins_url}, found {len(jobs_data.get('jobs', []))} jobs")
                    
                    for job in jobs_data.get('jobs', []):
                        job_name = job.get('name', '')
                        if 'hzp' in job_name.lower():
                            try:
                                job_url = job.get('url', '')
                                config_url = f"{job_url}config.xml"
                                response = requests.get(config_url, auth=auth, verify=False)
                                response.raise_for_status()
                                config_xml = response.text
                                
                                if 'GOPROXY' in config_xml.upper():
                                    debug_log(f"Found GOPROXY in Jenkins job {job_name}")
                                    return True
                            except Exception as e:
                                debug_log(f"Error checking job {job_name}: {e}")
                                continue
                except requests.exceptions.HTTPError as e:
                    debug_log(f"HTTP error checking Jenkins at {jenkins_url}: {e}")
                    continue  # Try next Jenkins URL
                except Exception as e:
                    debug_log(f"Error checking Jenkins at {jenkins_url}: {e}")
                    continue  # Try next Jenkins URL
        except Exception as e:
            debug_log(f"ERROR: Error checking Jenkins GOPROXY config: {e}")
        return False
