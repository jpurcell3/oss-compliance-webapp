#!/usr/bin/env python3
"""
Configuration Enumerator for OSS Compliance Scanner
Enumerates package manager configurations from multiple sources:
- Jenkins job configurations and build logs
- Dockerfiles and base images
- Repository configuration files
"""

import os
import re
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from dotenv import load_dotenv
import urllib3

# Suppress InsecureRequestWarning when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()


@dataclass
class RuntimeConfiguration:
    """Represents a runtime configuration discovered from various sources"""
    package_manager: str  # pip, go, npm, maven, docker
    config_type: str  # index_url, proxy, registry, mirror
    config_value: str  # The actual URL/value
    source_type: str  # jenkins_job, jenkins_log, dockerfile, base_image, repo_file
    source_location: str  # Job name, log URL, file path, image name
    evidence: str  # Log excerpt, file content snippet, API response
    timestamp: datetime  # When discovered
    confidence: str  # high (from logs), medium (from config), low (inferred)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class ConfigurationEnumerator:
    """
    Enumerates package manager configurations from all available sources
    to provide evidence-based compliance validation.
    """
    
    def __init__(self, jenkins_urls: List[str] = None, jenkins_user: str = None, 
                 jenkins_token: str = None, ssl_verify: bool = True):
        # Jenkins configuration
        self.jenkins_urls = jenkins_urls or [url.strip() for url in os.getenv('JENKINS_URLS', '').split(',') if url.strip()]
        self.jenkins_user = jenkins_user or os.getenv('JENKINS_USER')
        self.jenkins_token = jenkins_token or os.getenv('JENKINS_API_TOKEN')
        self.jenkins_max_builds = int(os.getenv('JENKINS_MAX_BUILDS_TO_CHECK', '5'))
        
        # SSL configuration
        self.ssl_verify = ssl_verify
        
        # Session for API calls
        self.session = requests.Session()
        self.session.verify = self.ssl_verify
        
        # Approved Artifactory servers
        self.approved_artifactory_servers = [
            'isgedge.artifactory.cec.lab.emc.com',
            'hopjpd.artifactory.cec.lab.emc.com'
        ]
        
        # Add custom servers from environment
        custom_servers = os.getenv('APPROVED_ARTIFACTORY_SERVERS', '')
        if custom_servers:
            self.approved_artifactory_servers.extend([s.strip() for s in custom_servers.split(',') if s.strip()])
        
        print(f"ConfigurationEnumerator initialized with {len(self.jenkins_urls)} Jenkins URLs")
    
    def enumerate_all_configs(self, repo_name: str, repo_path: Path = None) -> Dict[str, List[RuntimeConfiguration]]:
        """
        Enumerate all package manager configurations for a repository.
        
        Returns:
            Dict with keys: pip, go, npm, maven, docker
            Each containing a list of RuntimeConfiguration objects
        """
        print(f"\n=== Enumerating Runtime Configurations for {repo_name} ===")
        
        configs = {
            'pip': [],
            'go': [],
            'npm': [],
            'maven': [],
            'docker': []
        }
        
        # Enumerate from Jenkins
        jenkins_configs = self.enumerate_jenkins_configs(repo_name)
        for pm, config_list in jenkins_configs.items():
            configs[pm].extend(config_list)
        
        # Enumerate from repository files (if repo_path provided)
        if repo_path:
            repo_configs = self.enumerate_repo_file_configs(repo_path)
            for pm, config_list in repo_configs.items():
                configs[pm].extend(config_list)
            
            # Extract from Dockerfile
            dockerfile_configs = self.extract_dockerfile_configs(repo_path)
            for pm, config_list in dockerfile_configs.items():
                configs[pm].extend(config_list)
            
            # Extract from Makefile
            makefile_configs = self.extract_makefile_configs(repo_path)
            for pm, config_list in makefile_configs.items():
                configs[pm].extend(config_list)
            
            # Extract from GitHub Actions
            github_actions_configs = self.extract_github_actions_configs(repo_path)
            for pm, config_list in github_actions_configs.items():
                configs[pm].extend(config_list)
        
        # Print summary
        total_configs = sum(len(config_list) for config_list in configs.values())
        print(f"Total configurations found: {total_configs}")
        for pm, config_list in configs.items():
            if config_list:
                print(f"  {pm}: {len(config_list)} configurations")
        
        return configs
    
    def enumerate_jenkins_configs(self, repo_name: str) -> Dict[str, List[RuntimeConfiguration]]:
        """Enumerate configurations from Jenkins jobs and build logs"""
        print(f"Enumerating Jenkins configurations for {repo_name}...")
        
        configs = {
            'pip': [],
            'go': [],
            'npm': [],
            'maven': [],
            'docker': []
        }
        
        if not self.jenkins_urls or not self.jenkins_user or not self.jenkins_token:
            print("Jenkins credentials not configured, skipping Jenkins enumeration")
            return configs
        
        for jenkins_url in self.jenkins_urls:
            try:
                # Find jobs related to this repository
                jobs = self._find_related_jenkins_jobs(jenkins_url, repo_name)
                print(f"Found {len(jobs)} related jobs on {jenkins_url}")
                
                for job in jobs:
                    # Get job configuration
                    job_configs = self._extract_job_configs(jenkins_url, job)
                    for pm, config_list in job_configs.items():
                        configs[pm].extend(config_list)
                    
                    # Get build log configurations (high confidence)
                    build_configs = self._extract_build_log_configs(jenkins_url, job, repo_name)
                    for pm, config_list in build_configs.items():
                        configs[pm].extend(config_list)
                        
            except Exception as e:
                print(f"Error enumerating Jenkins configs from {jenkins_url}: {e}")
        
        return configs
    
    def _find_related_jenkins_jobs(self, jenkins_url: str, repo_name: str) -> List[Dict]:
        """Find Jenkins jobs related to a repository"""
        jobs = []
        
        try:
            api_url = f"{jenkins_url}/api/json?tree=jobs[name,url,jobs[name,url]]"
            auth = (self.jenkins_user, self.jenkins_token)
            
            response = self.session.get(api_url, auth=auth, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            jobs = self._search_jobs_recursive(data.get('jobs', []), repo_name)
            
        except Exception as e:
            print(f"Error finding Jenkins jobs: {e}")
        
        return jobs
    
    def _search_jobs_recursive(self, jobs: List[Dict], repo_name: str) -> List[Dict]:
        """Recursively search for jobs matching repository name"""
        matching_jobs = []
        
        for job in jobs:
            job_name = job.get('name', '')
            job_name_lower = job_name.lower()
            repo_name_lower = repo_name.lower()
            
            # Try multiple matching strategies
            match = False
            
            # 1. Exact substring match
            if repo_name_lower in job_name_lower:
                match = True
            
            # 2. Match individual words (e.g., "fusion-agent" matches "Agent-Multibranch")
            repo_words = repo_name_lower.replace('-', ' ').replace('_', ' ').split()
            job_words = job_name_lower.replace('-', ' ').replace('_', ' ').split()
            
            # If any significant word from repo name is in job name
            for word in repo_words:
                if len(word) > 3 and word in job_words:  # Only match words longer than 3 chars
                    match = True
                    break
            
            # 3. Reverse match: repo name contains job name (e.g., "fusion-agent" contains "agent")
            for word in job_words:
                if len(word) > 3 and word in repo_name_lower:
                    match = True
                    break
            
            if match:
                matching_jobs.append(job)
                print(f"Matched job: {job_name} for repo: {repo_name}")
            
            # Check nested jobs (folders)
            if 'jobs' in job:
                matching_jobs.extend(self._search_jobs_recursive(job['jobs'], repo_name))
        
        return matching_jobs
    
    def _extract_job_configs(self, jenkins_url: str, job: Dict) -> Dict[str, List[RuntimeConfiguration]]:
        """Extract configurations from Jenkins job XML config"""
        configs = {
            'pip': [],
            'go': [],
            'npm': [],
            'maven': [],
            'docker': []
        }
        
        try:
            job_url = job.get('url')
            config_url = f"{job_url}config.xml"
            auth = (self.jenkins_user, self.jenkins_token)
            
            response = self.session.get(config_url, auth=auth, timeout=30)
            response.raise_for_status()
            
            config_xml = response.text
            
            # Extract environment variables from job config
            env_vars = self._parse_env_vars_from_xml(config_xml)
            
            # Look for package manager configurations
            for var_name, var_value in env_vars.items():
                if 'PIP_INDEX_URL' in var_name or 'pip' in var_name.lower() and 'index' in var_name.lower():
                    configs['pip'].append(RuntimeConfiguration(
                        package_manager='pip',
                        config_type='index_url',
                        config_value=var_value,
                        source_type='jenkins_job',
                        source_location=f"{job.get('name')} (job config)",
                        evidence=f"Environment variable: {var_name}={var_value}",
                        timestamp=datetime.now(),
                        confidence='medium'
                    ))
                
                elif 'GOPROXY' in var_name:
                    configs['go'].append(RuntimeConfiguration(
                        package_manager='go',
                        config_type='proxy',
                        config_value=var_value,
                        source_type='jenkins_job',
                        source_location=f"{job.get('name')} (job config)",
                        evidence=f"Environment variable: {var_name}={var_value}",
                        timestamp=datetime.now(),
                        confidence='medium'
                    ))
                
                elif 'NPM_CONFIG_REGISTRY' in var_name or 'npm_config_registry' in var_name:
                    configs['npm'].append(RuntimeConfiguration(
                        package_manager='npm',
                        config_type='registry',
                        config_value=var_value,
                        source_type='jenkins_job',
                        source_location=f"{job.get('name')} (job config)",
                        evidence=f"Environment variable: {var_name}={var_value}",
                        timestamp=datetime.now(),
                        confidence='medium'
                    ))
        
        except Exception as e:
            print(f"Error extracting job configs: {e}")
        
        return configs
    
    def _parse_env_vars_from_xml(self, xml_content: str) -> Dict[str, str]:
        """Parse environment variables from Jenkins job XML"""
        env_vars = {}
        
        # Look for EnvInjectJobProperty or similar environment injection
        env_pattern = re.compile(r'<name>([^<]+)</name>\s*<value>([^<]*)</value>', re.IGNORECASE)
        matches = env_pattern.findall(xml_content)
        
        for name, value in matches:
            env_vars[name.strip()] = value.strip()
        
        # Also look for Kubernetes pod template environment variables
        kube_env_pattern = re.compile(r'<key>([^<]+)</key>\s*<value>([^<]*)</value>', re.IGNORECASE)
        kube_matches = kube_env_pattern.findall(xml_content)
        
        for name, value in kube_matches:
            if name.strip() not in env_vars:
                env_vars[name.strip()] = value.strip()
        
        return env_vars
    
    def _extract_build_log_configs(self, jenkins_url: str, job: Dict, repo_name: str) -> Dict[str, List[RuntimeConfiguration]]:
        """Extract configurations from recent build logs (HIGH confidence)"""
        configs = {
            'pip': [],
            'go': [],
            'npm': [],
            'maven': [],
            'docker': []
        }
        
        try:
            job_url = job.get('url')
            job_name = job.get('name')
            
            # Get recent builds
            builds_url = f"{job_url}api/json?tree=builds[number,url]{{0,{self.jenkins_max_builds}}}"
            auth = (self.jenkins_user, self.jenkins_token)
            
            response = self.session.get(builds_url, auth=auth, timeout=30)
            response.raise_for_status()
            
            builds_data = response.json()
            builds = builds_data.get('builds', [])
            
            print(f"Checking {len(builds)} recent builds for {job_name}")
            
            for build in builds:
                build_number = build.get('number')
                build_url = build.get('url')
                
                # Get console log
                console_url = f"{build_url}consoleText"
                
                try:
                    log_response = self.session.get(console_url, auth=auth, timeout=60)
                    log_response.raise_for_status()
                    
                    console_log = log_response.text
                    
                    # Parse pip configurations from log
                    pip_configs = self._parse_pip_from_log(console_log, job_name, build_number, build_url)
                    configs['pip'].extend(pip_configs)
                    
                    # Parse Go configurations from log
                    go_configs = self._parse_go_from_log(console_log, job_name, build_number, build_url)
                    configs['go'].extend(go_configs)
                    
                    # Parse NPM configurations from log
                    npm_configs = self._parse_npm_from_log(console_log, job_name, build_number, build_url)
                    configs['npm'].extend(npm_configs)
                    
                    # Only check first successful build with configs
                    if pip_configs or go_configs or npm_configs:
                        print(f"Found configurations in build #{build_number}")
                        break
                        
                except Exception as e:
                    print(f"Error fetching build log #{build_number}: {e}")
                    continue
        
        except Exception as e:
            print(f"Error extracting build log configs: {e}")
        
        return configs
    
    def _parse_pip_from_log(self, log_content: str, job_name: str, build_number: int, build_url: str) -> List[RuntimeConfiguration]:
        """Parse pip index URLs from build log"""
        configs = []
        
        # Look for "Looking in indexes:" lines from pip
        index_pattern = re.compile(r'Looking in indexes:\s+(.+)', re.IGNORECASE)
        matches = index_pattern.findall(log_content)
        
        for match in matches:
            # Extract URL (may have credentials masked)
            urls = [url.strip() for url in match.split(',')]
            
            for url in urls:
                # Clean up URL (remove credentials for display)
                clean_url = re.sub(r'://[^:]+:[^@]+@', '://<credentials>@', url)
                
                # Extract actual URL for validation
                actual_url = url
                
                # Get surrounding context for evidence
                context_lines = self._get_log_context(log_content, match, lines_before=2, lines_after=2)
                
                configs.append(RuntimeConfiguration(
                    package_manager='pip',
                    config_type='index_url',
                    config_value=actual_url,
                    source_type='jenkins_log',
                    source_location=f"{job_name} build #{build_number}",
                    evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
        
        return configs
    
    def _parse_go_from_log(self, log_content: str, job_name: str, build_number: int, build_url: str) -> List[RuntimeConfiguration]:
        """Parse Go proxy configurations from build log"""
        configs = []
        
        # Look for GOPROXY environment variable in log
        goproxy_pattern = re.compile(r'GOPROXY[=\s]+([^\s\n]+)', re.IGNORECASE)
        matches = goproxy_pattern.findall(log_content)
        
        for match in matches:
            context_lines = self._get_log_context(log_content, match, lines_before=1, lines_after=1)
            
            configs.append(RuntimeConfiguration(
                package_manager='go',
                config_type='proxy',
                config_value=match.strip(),
                source_type='jenkins_log',
                source_location=f"{job_name} build #{build_number}",
                evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                timestamp=datetime.now(),
                confidence='high'
            ))
        
        return configs
    
    def _parse_npm_from_log(self, log_content: str, job_name: str, build_number: int, build_url: str) -> List[RuntimeConfiguration]:
        """Parse NPM registry configurations from build log"""
        configs = []
        seen_registries = set()
        
        # Pattern 1: npm install/config with --registry flag
        # Example: npm install --registry https://registry.npmjs.org
        registry_flag_pattern = re.compile(r'npm\s+(?:install|i|ci|config)\s+.*--registry[=\s]+([^\s\n]+)', re.IGNORECASE)
        matches = registry_flag_pattern.findall(log_content)
        for match in matches:
            registry_url = match.strip()
            if registry_url not in seen_registries:
                seen_registries.add(registry_url)
                context_lines = self._get_log_context(log_content, registry_url, lines_before=2, lines_after=2)
                configs.append(RuntimeConfiguration(
                    package_manager='npm',
                    config_type='registry',
                    config_value=registry_url,
                    source_type='jenkins_log',
                    source_location=f"{job_name} build #{build_number}",
                    evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
        
        # Pattern 2: npm config get/set registry output
        # Example: npm config get registry -> https://registry.npmjs.org/
        config_pattern = re.compile(r'npm\s+config\s+(?:get|set)\s+registry\s*[:\s]+([^\s\n]+)', re.IGNORECASE)
        matches = config_pattern.findall(log_content)
        for match in matches:
            registry_url = match.strip()
            if registry_url not in seen_registries:
                seen_registries.add(registry_url)
                context_lines = self._get_log_context(log_content, registry_url, lines_before=2, lines_after=2)
                configs.append(RuntimeConfiguration(
                    package_manager='npm',
                    config_type='registry',
                    config_value=registry_url,
                    source_type='jenkins_log',
                    source_location=f"{job_name} build #{build_number}",
                    evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
        
        # Pattern 3: NPM_CONFIG_REGISTRY environment variable
        # Example: NPM_CONFIG_REGISTRY=https://registry.npmjs.org
        env_pattern = re.compile(r'NPM_CONFIG_REGISTRY[=\s]+([^\s\n]+)', re.IGNORECASE)
        matches = env_pattern.findall(log_content)
        for match in matches:
            registry_url = match.strip()
            if registry_url not in seen_registries:
                seen_registries.add(registry_url)
                context_lines = self._get_log_context(log_content, registry_url, lines_before=2, lines_after=2)
                configs.append(RuntimeConfiguration(
                    package_manager='npm',
                    config_type='registry',
                    config_value=registry_url,
                    source_type='jenkins_log',
                    source_location=f"{job_name} build #{build_number}",
                    evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
        
        # Pattern 4: npm notice output showing registry
        # Example: npm notice Using registry: https://registry.npmjs.org/
        notice_pattern = re.compile(r'npm\s+(?:notice|info|http)\s+.*(?:Using registry|registry)[:\s]+([^\s\n]+)', re.IGNORECASE)
        matches = notice_pattern.findall(log_content)
        for match in matches:
            registry_url = match.strip()
            if registry_url not in seen_registries:
                seen_registries.add(registry_url)
                context_lines = self._get_log_context(log_content, registry_url, lines_before=2, lines_after=2)
                configs.append(RuntimeConfiguration(
                    package_manager='npm',
                    config_type='registry',
                    config_value=registry_url,
                    source_type='jenkins_log',
                    source_location=f"{job_name} build #{build_number}",
                    evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
        
        # Pattern 5: .npmrc file creation (echo registry= or similar)
        # Example: echo registry=https://artifactory.example.com/npm/
        npmrc_creation_pattern = re.compile(r'(?:echo|cat|>)\s+registry=([^\s\n]+)', re.IGNORECASE)
        matches = npmrc_creation_pattern.findall(log_content)
        for match in matches:
            registry_url = match.strip()
            if registry_url not in seen_registries:
                seen_registries.add(registry_url)
                context_lines = self._get_log_context(log_content, registry_url, lines_before=2, lines_after=2)
                configs.append(RuntimeConfiguration(
                    package_manager='npm',
                    config_type='registry',
                    config_value=registry_url,
                    source_type='jenkins_log',
                    source_location=f"{job_name} build #{build_number}",
                    evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
        
        # Pattern 6: Generic npm registry pattern (fallback)
        # Example: npm registry=https://registry.npmjs.org
        generic_pattern = re.compile(r'npm.*registry[=:\s]+([^\s\n]+)', re.IGNORECASE)
        matches = generic_pattern.findall(log_content)
        for match in matches:
            registry_url = match.strip()
            # Filter out false positives from AWS ECR commands
            if 'aws ecr' not in match.lower() and registry_url not in seen_registries:
                seen_registries.add(registry_url)
                context_lines = self._get_log_context(log_content, registry_url, lines_before=2, lines_after=2)
                configs.append(RuntimeConfiguration(
                    package_manager='npm',
                    config_type='registry',
                    config_value=registry_url,
                    source_type='jenkins_log',
                    source_location=f"{job_name} build #{build_number}",
                    evidence=f"Build log excerpt:\n{context_lines}\n\nFull log: {build_url}console",
                    timestamp=datetime.now(),
                    confidence='medium'
                ))
        
        return configs
    
    def _get_log_context(self, log_content: str, search_text: str, lines_before: int = 2, lines_after: int = 2) -> str:
        """Get surrounding context from log for a search text"""
        lines = log_content.split('\n')
        
        for i, line in enumerate(lines):
            if search_text in line:
                start = max(0, i - lines_before)
                end = min(len(lines), i + lines_after + 1)
                context = lines[start:end]
                return '\n'.join(context)
        
        return search_text
    
    def enumerate_repo_file_configs(self, repo_path: Path) -> Dict[str, List[RuntimeConfiguration]]:
        """Enumerate configurations from repository files"""
        print(f"Enumerating repository file configurations from {repo_path}...")
        
        configs = {
            'pip': [],
            'go': [],
            'npm': [],
            'maven': [],
            'docker': []
        }
        
        # Check for pip configuration files
        pip_configs = self._find_pip_config_files(repo_path)
        configs['pip'].extend(pip_configs)
        
        # Check for npm configuration files
        npm_configs = self._find_npm_config_files(repo_path)
        configs['npm'].extend(npm_configs)
        
        # Check for Maven settings
        maven_configs = self._find_maven_config_files(repo_path)
        configs['maven'].extend(maven_configs)
        
        # Check Dockerfiles
        docker_configs = self._find_dockerfile_configs(repo_path)
        for pm, config_list in docker_configs.items():
            configs[pm].extend(config_list)
        
        return configs
    
    def _find_pip_config_files(self, repo_path: Path) -> List[RuntimeConfiguration]:
        """Find pip.conf and pip.ini files"""
        configs = []
        
        # Look for pip.conf, pip.ini
        for pattern in ['**/pip.conf', '**/pip.ini', '**/.pip/pip.conf']:
            for config_file in repo_path.rglob(pattern.split('/')[-1]):
                try:
                    content = config_file.read_text()
                    
                    # Parse index-url from config file
                    index_pattern = re.compile(r'index-url\s*=\s*(.+)', re.IGNORECASE)
                    matches = index_pattern.findall(content)
                    
                    for match in matches:
                        configs.append(RuntimeConfiguration(
                            package_manager='pip',
                            config_type='index_url',
                            config_value=match.strip(),
                            source_type='repo_file',
                            source_location=str(config_file.relative_to(repo_path)),
                            evidence=f"File content:\n{content[:500]}",
                            timestamp=datetime.now(),
                            confidence='medium'
                        ))
                except Exception as e:
                    print(f"Error reading {config_file}: {e}")
        
        return configs
    
    def _find_npm_config_files(self, repo_path: Path) -> List[RuntimeConfiguration]:
        """Find .npmrc files including parent directories and npm scripts"""
        configs = []
        
        # Check for .npmrc in repo and parent directories
        npmrc_locations = []
        
        # First, check current repo directory
        if (repo_path / '.npmrc').exists():
            npmrc_locations.append(repo_path / '.npmrc')
        
        # Then check parent directories up to 3 levels up
        current_path = repo_path
        for _ in range(3):
            parent = current_path.parent
            if parent != current_path:  # Not at root
                if (parent / '.npmrc').exists():
                    npmrc_locations.append(parent / '.npmrc')
                current_path = parent
            else:
                break
        
        # Also check recursively (existing behavior)
        for npmrc in repo_path.rglob('.npmrc'):
            if npmrc not in npmrc_locations:
                npmrc_locations.append(npmrc)
        
        # Check package.json for npm scripts with registry configuration
        for pkg_json in repo_path.rglob('package.json'):
            try:
                with open(pkg_json, 'r', encoding='utf-8') as f:
                    pkg_content = json.load(f)
                    
                    # Check scripts section for npm config set registry commands
                    scripts = pkg_content.get('scripts', {})
                    if isinstance(scripts, dict):
                        for script_name, script_cmd in scripts.items():
                            if isinstance(script_cmd, str):
                                # Look for npm config set registry commands
                                registry_match = re.search(
                                    r'npm\s+config\s+set\s+registry\s+([^\s&|;]+)',
                                    script_cmd,
                                    re.IGNORECASE
                                )
                                if registry_match:
                                    registry_url = registry_match.group(1).strip('\'"')
                                    configs.append(RuntimeConfiguration(
                                        package_manager='npm',
                                        config_type='registry',
                                        config_value=registry_url,
                                        source_type='repo_file',
                                        source_location=f"{pkg_json.relative_to(repo_path)}:scripts.{script_name}",
                                        evidence=f"npm script: {script_name}='{script_cmd}'",
                                        timestamp=datetime.now(),
                                        confidence='medium'
                                    ))
            except Exception as e:
                pass  # Skip if unable to parse
        
        for npmrc in npmrc_locations:
            try:
                content = npmrc.read_text()
                
                # Parse global registry from .npmrc
                registry_pattern = re.compile(r'registry\s*=\s*(.+)', re.IGNORECASE)
                matches = registry_pattern.findall(content)
                
                for match in matches:
                    configs.append(RuntimeConfiguration(
                        package_manager='npm',
                        config_type='registry',
                        config_value=match.strip(),
                        source_type='repo_file',
                        source_location=str(npmrc.relative_to(repo_path)),
                        evidence=f"File content:\n{content[:500]}",
                        timestamp=datetime.now(),
                        confidence='medium'
                    ))
                
                # Parse scope-specific registries from .npmrc
                # Pattern: @scope:registry=<url>
                scope_registry_pattern = re.compile(r'(@[\w-]+):registry\s*=\s*(.+)', re.IGNORECASE)
                scope_matches = scope_registry_pattern.findall(content)
                
                for scope, registry_url in scope_matches:
                    configs.append(RuntimeConfiguration(
                        package_manager='npm',
                        config_type=f'scope_registry_{scope}',
                        config_value=registry_url.strip(),
                        source_type='repo_file',
                        source_location=str(npmrc.relative_to(repo_path)),
                        evidence=f"Scope-specific registry: {scope}:registry={registry_url.strip()}",
                        timestamp=datetime.now(),
                        confidence='medium'
                    ))
            except Exception as e:
                print(f"Error reading {npmrc}: {e}")
        
        return configs
    
    def _find_maven_config_files(self, repo_path: Path) -> List[RuntimeConfiguration]:
        """Find Maven settings.xml files"""
        configs = []
        
        for settings_xml in repo_path.rglob('settings.xml'):
            try:
                content = settings_xml.read_text()
                
                # Parse mirror URLs from settings.xml
                mirror_pattern = re.compile(r'<url>([^<]+)</url>', re.IGNORECASE)
                matches = mirror_pattern.findall(content)
                
                for match in matches:
                    if 'artifactory' in match.lower() or 'maven' in match.lower():
                        configs.append(RuntimeConfiguration(
                            package_manager='maven',
                            config_type='mirror',
                            config_value=match.strip(),
                            source_type='repo_file',
                            source_location=str(settings_xml.relative_to(repo_path)),
                            evidence=f"File content:\n{content[:500]}",
                            timestamp=datetime.now(),
                            confidence='medium'
                        ))
            except Exception as e:
                print(f"Error reading {settings_xml}: {e}")
        
        return configs
    
    def _find_dockerfile_configs(self, repo_path: Path) -> Dict[str, List[RuntimeConfiguration]]:
        """Find configurations in Dockerfiles"""
        configs = {
            'pip': [],
            'go': [],
            'npm': [],
            'maven': [],
            'docker': []
        }
        
        for dockerfile in repo_path.rglob('Dockerfile*'):
            try:
                content = dockerfile.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Look for ENV or ARG declarations
                    if line_stripped.startswith('ENV ') or line_stripped.startswith('ARG '):
                        # PIP_INDEX_URL
                        if 'PIP_INDEX_URL' in line_stripped:
                            match = re.search(r'PIP_INDEX_URL[=\s]+([^\s]+)', line_stripped)
                            if match:
                                configs['pip'].append(RuntimeConfiguration(
                                    package_manager='pip',
                                    config_type='index_url',
                                    config_value=match.group(1).strip(),
                                    source_type='dockerfile',
                                    source_location=f"{dockerfile.relative_to(repo_path)}:line {line_num}",
                                    evidence=f"Dockerfile line: {line_stripped}",
                                    timestamp=datetime.now(),
                                    confidence='medium'
                                ))
                        
                        # GOPROXY
                        if 'GOPROXY' in line_stripped:
                            match = re.search(r'GOPROXY[=\s]+([^\s]+)', line_stripped)
                            if match:
                                configs['go'].append(RuntimeConfiguration(
                                    package_manager='go',
                                    config_type='proxy',
                                    config_value=match.group(1).strip(),
                                    source_type='dockerfile',
                                    source_location=f"{dockerfile.relative_to(repo_path)}:line {line_num}",
                                    evidence=f"Dockerfile line: {line_stripped}",
                                    timestamp=datetime.now(),
                                    confidence='medium'
                                ))
                        
                        # NPM_CONFIG_REGISTRY
                        if 'NPM_CONFIG_REGISTRY' in line_stripped or 'npm_config_registry' in line_stripped:
                            match = re.search(r'npm_config_registry[=\s]+([^\s]+)', line_stripped, re.IGNORECASE)
                            if match:
                                configs['npm'].append(RuntimeConfiguration(
                                    package_manager='npm',
                                    config_type='registry',
                                    config_value=match.group(1).strip(),
                                    source_type='dockerfile',
                                    source_location=f"{dockerfile.relative_to(repo_path)}:line {line_num}",
                                    evidence=f"Dockerfile line: {line_stripped}",
                                    timestamp=datetime.now(),
                                    confidence='medium'
                                ))
            
            except Exception as e:
                print(f"Error reading {dockerfile}: {e}")
        
        return configs
    
    def is_compliant_artifactory(self, url: str) -> bool:
        """Check if URL uses approved Artifactory server"""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Check exact matches
        for server in self.approved_artifactory_servers:
            if server.lower() in url_lower:
                return True
        
        # Check pattern: *.artifactory.cec.lab.emc.com
        if re.search(r'[\w-]+\.artifactory\.cec\.lab\.emc\.com', url_lower):
            return True
        
        return False
    
    def evaluate_compliance_level(self, url: str, ecosystem: str) -> Dict:
        """
        Evaluate compliance level with three-tier model
        
        Returns detailed compliance evaluation:
        - compliant_optimal: Approved server + approved virtual repo
        - compliant_warn: Any Artifactory server (suboptimal configuration)
        - non_compliant: Public/external sources
        
        Args:
            url: Configuration URL to evaluate
            ecosystem: Package manager ecosystem (go, python, npm, maven, docker)
            
        Returns:
            Dict with level, server, repository, and improvement notes
        """
        result = {
            'level': 'non_compliant',
            'server': None,
            'repository': None,
            'approved_server': False,
            'approved_virtual_repo': False,
            'current_config': url,
            'recommended_config': None,
            'improvement_notes': []
        }
        
        if not url:
            return result
        
        url_lower = url.lower()
        
        # Check if using any Artifactory
        if not re.search(r'\.artifactory\.cec\.lab\.emc\.com', url_lower):
            result['level'] = 'non_compliant'
            result['server'] = 'public'
            result['recommended_config'] = self._get_recommended_config(ecosystem)
            result['improvement_notes'].append('Not using Artifactory - direct public access')
            return result
        
        # Extract server name
        server_match = re.search(r'([\w-]+)\.artifactory\.cec\.lab\.emc\.com', url_lower)
        if server_match:
            result['server'] = server_match.group(1)
        
        # Check if using approved server (isgedge)
        approved_server = self.artifactory_base.lower() in url_lower
        result['approved_server'] = approved_server
        
        # Extract repository name
        repo_match = re.search(r'/artifactory/(?:api/(?:pypi|npm|go|maven)/)?([^/\s]+)', url_lower)
        if repo_match:
            repo_name = repo_match.group(1)
            result['repository'] = repo_name
            
            # Check if using approved virtual repository
            approved_virtual_repo = self.virtual_repos.get(ecosystem, '').lower()
            if approved_virtual_repo and approved_virtual_repo in repo_name:
                result['approved_virtual_repo'] = True
        
        # Determine compliance level
        if result['approved_server'] and result['approved_virtual_repo']:
            result['level'] = 'compliant_optimal'
        elif approved_server or re.search(r'\.artifactory\.cec\.lab\.emc\.com', url_lower):
            result['level'] = 'compliant_warn'
            result['recommended_config'] = self._get_recommended_config(ecosystem)
            
            # Add specific improvement notes
            if not result['approved_server']:
                result['improvement_notes'].append(
                    f"Using {result['server']}.artifactory instead of approved {self.artifactory_base}"
                )
            
            if not result['approved_virtual_repo']:
                expected_repo = self.virtual_repos.get(ecosystem, f'isgedge-{ecosystem}-virtual')
                result['improvement_notes'].append(
                    f"Using {result['repository']} instead of approved virtual repo {expected_repo}"
                )
        
        return result
    
    def _get_recommended_config(self, ecosystem: str) -> str:
        """Generate recommended configuration URL for ecosystem"""
        virtual_repo = self.virtual_repos.get(ecosystem, f'isgedge-{ecosystem}-virtual')
        
        if ecosystem == 'python':
            return f"https://{self.artifactory_base}/artifactory/api/pypi/{virtual_repo}/simple"
        elif ecosystem == 'go':
            return f"https://{self.artifactory_base}/artifactory/api/go/{virtual_repo},direct"
        elif ecosystem == 'npm':
            return f"https://{self.artifactory_base}/artifactory/api/npm/{virtual_repo}"
        elif ecosystem == 'maven':
            return f"https://{self.artifactory_base}/artifactory/{virtual_repo}"
        elif ecosystem == 'docker':
            return f"https://{self.artifactory_base}/artifactory/{virtual_repo}"
        else:
            return f"https://{self.artifactory_base}/artifactory/{virtual_repo}"
    
    def extract_dockerfile_configs(self, repo_path: Path) -> Dict[str, List[RuntimeConfiguration]]:
        """Extract proxy configurations from Dockerfile ENV statements"""
        configs = {
            'go': [],
            'pip': [],
            'npm': [],
            'docker': []
        }
        
        if not repo_path or not repo_path.exists():
            return configs
        
        # Find all Dockerfiles
        dockerfile_patterns = ['Dockerfile', 'Dockerfile.*', '*.dockerfile']
        dockerfiles = []
        for pattern in dockerfile_patterns:
            dockerfiles.extend(repo_path.rglob(pattern))
        
        for dockerfile in dockerfiles:
            try:
                with open(dockerfile, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Extract ENV statements
                    env_pattern = re.compile(r'ENV\s+(\w+)(?:=|\s+)(.+?)(?:\n|$)', re.MULTILINE)
                    for match in env_pattern.finditer(content):
                        var_name = match.group(1)
                        var_value = match.group(2).strip().strip('"').strip("'")
                        
                        # Check for Go proxy
                        if var_name == 'GOPROXY':
                            configs['go'].append(RuntimeConfiguration(
                                package_manager='go',
                                config_type='proxy',
                                config_value=var_value,
                                source_type='dockerfile',
                                source_location=str(dockerfile.relative_to(repo_path)),
                                evidence=f"ENV {var_name}={var_value}",
                                timestamp=datetime.now(),
                                confidence='high'
                            ))
                        
                        # Check for Python pip
                        elif var_name in ['PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL']:
                            configs['pip'].append(RuntimeConfiguration(
                                package_manager='pip',
                                config_type='index_url',
                                config_value=var_value,
                                source_type='dockerfile',
                                source_location=str(dockerfile.relative_to(repo_path)),
                                evidence=f"ENV {var_name}={var_value}",
                                timestamp=datetime.now(),
                                confidence='high'
                            ))
                        
                        # Check for NPM registry
                        elif var_name == 'NPM_CONFIG_REGISTRY':
                            configs['npm'].append(RuntimeConfiguration(
                                package_manager='npm',
                                config_type='registry',
                                config_value=var_value,
                                source_type='dockerfile',
                                source_location=str(dockerfile.relative_to(repo_path)),
                                evidence=f"ENV {var_name}={var_value}",
                                timestamp=datetime.now(),
                                confidence='high'
                            ))
            except Exception as e:
                print(f"Error reading Dockerfile {dockerfile}: {e}")
        
        return configs
    
    def extract_makefile_configs(self, repo_path: Path) -> Dict[str, List[RuntimeConfiguration]]:
        """Extract proxy configurations from Makefile export statements"""
        configs = {
            'go': [],
            'pip': [],
            'npm': []
        }
        
        if not repo_path or not repo_path.exists():
            return configs
        
        # Find all Makefiles
        makefile_patterns = ['Makefile', 'makefile', '*.mk', 'GNUmakefile']
        makefiles = []
        for pattern in makefile_patterns:
            makefiles.extend(repo_path.rglob(pattern))
        
        for makefile in makefiles:
            try:
                with open(makefile, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Extract export statements
                    export_pattern = re.compile(r'export\s+(\w+)\s*[:=]\s*(.+?)(?:\n|$)', re.MULTILINE)
                    for match in export_pattern.finditer(content):
                        var_name = match.group(1)
                        var_value = match.group(2).strip()
                        
                        # Check for Go proxy
                        if var_name == 'GOPROXY':
                            configs['go'].append(RuntimeConfiguration(
                                package_manager='go',
                                config_type='proxy',
                                config_value=var_value,
                                source_type='makefile',
                                source_location=str(makefile.relative_to(repo_path)),
                                evidence=f"export {var_name} := {var_value}",
                                timestamp=datetime.now(),
                                confidence='high'
                            ))
                        
                        # Check for Python pip
                        elif var_name in ['PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL']:
                            configs['pip'].append(RuntimeConfiguration(
                                package_manager='pip',
                                config_type='index_url',
                                config_value=var_value,
                                source_type='makefile',
                                source_location=str(makefile.relative_to(repo_path)),
                                evidence=f"export {var_name} := {var_value}",
                                timestamp=datetime.now(),
                                confidence='high'
                            ))
                        
                        # Check for NPM registry
                        elif var_name == 'NPM_CONFIG_REGISTRY':
                            configs['npm'].append(RuntimeConfiguration(
                                package_manager='npm',
                                config_type='registry',
                                config_value=var_value,
                                source_type='makefile',
                                source_location=str(makefile.relative_to(repo_path)),
                                evidence=f"export {var_name} := {var_value}",
                                timestamp=datetime.now(),
                                confidence='high'
                            ))
            except Exception as e:
                print(f"Error reading Makefile {makefile}: {e}")
        
        return configs
    
    def extract_github_actions_configs(self, repo_path: Path) -> Dict[str, List[RuntimeConfiguration]]:
        """Extract proxy configurations from GitHub Actions workflows"""
        configs = {
            'go': [],
            'pip': [],
            'npm': []
        }
        
        if not repo_path or not repo_path.exists():
            return configs
        
        # Find GitHub Actions workflows
        workflows_dir = repo_path / '.github' / 'workflows'
        if not workflows_dir.exists():
            return configs
        
        for workflow_file in workflows_dir.glob('*.yml'):
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow = yaml.safe_load(f)
                    
                    if not workflow:
                        continue
                    
                    workflow_name = workflow.get('name', workflow_file.name)
                    
                    # Check for workflow-level env variables
                    if 'env' in workflow:
                        self._extract_env_vars(workflow['env'], configs, workflow_file, repo_path, workflow_name)
                    
                    # Check for job-level env variables and step-level configs
                    if 'jobs' in workflow:
                        for job_name, job_config in workflow['jobs'].items():
                            if isinstance(job_config, dict):
                                # Check job-level env
                                if 'env' in job_config:
                                    self._extract_env_vars(job_config['env'], configs, workflow_file, repo_path, f"{workflow_name}/{job_name}")
                                
                                # Check steps for npm registry configurations
                                if 'steps' in job_config:
                                    for step_idx, step in enumerate(job_config['steps']):
                                        if isinstance(step, dict):
                                            # Check step-level env
                                            if 'env' in step:
                                                self._extract_env_vars(step['env'], configs, workflow_file, repo_path, f"{workflow_name}/{job_name}/step-{step_idx}")
                                            
                                            # Check for npm registry in run commands
                                            if 'run' in step:
                                                run_cmd = step['run']
                                                npm_registry_match = re.search(r'npm\s+config\s+set\s+registry\s+([^\s\n]+)', run_cmd, re.IGNORECASE)
                                                if npm_registry_match:
                                                    registry_url = npm_registry_match.group(1).strip('\'"')
                                                    configs['npm'].append(RuntimeConfiguration(
                                                        package_manager='npm',
                                                        config_type='registry',
                                                        config_value=registry_url,
                                                        source_type='github_actions',
                                                        source_location=str(workflow_file.relative_to(repo_path)),
                                                        evidence=f"Step run command: npm config set registry {registry_url}",
                                                        timestamp=datetime.now(),
                                                        confidence='high'
                                                    ))
            except Exception as e:
                print(f"Error reading GitHub Actions workflow {workflow_file}: {e}")
        
        return configs
    
    def _extract_env_vars(self, env_dict: Dict, configs: Dict[str, List[RuntimeConfiguration]], 
                         workflow_file: Path, repo_path: Path, location: str):
        """Extract environment variables and add to configs"""
        if not isinstance(env_dict, dict):
            return
        
        for key, value in env_dict.items():
            if key == 'GOPROXY':
                configs['go'].append(RuntimeConfiguration(
                    package_manager='go',
                    config_type='proxy',
                    config_value=str(value),
                    source_type='github_actions',
                    source_location=str(workflow_file.relative_to(repo_path)),
                    evidence=f"env.{key}: {value} (in {location})",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
            elif key in ['PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL']:
                configs['pip'].append(RuntimeConfiguration(
                    package_manager='pip',
                    config_type='index_url',
                    config_value=str(value),
                    source_type='github_actions',
                    source_location=str(workflow_file.relative_to(repo_path)),
                    evidence=f"env.{key}: {value} (in {location})",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
            elif key == 'NPM_CONFIG_REGISTRY':
                configs['npm'].append(RuntimeConfiguration(
                    package_manager='npm',
                    config_type='registry',
                    config_value=str(value),
                    source_type='github_actions',
                    source_location=str(workflow_file.relative_to(repo_path)),
                    evidence=f"env.{key}: {value} (in {location})",
                    timestamp=datetime.now(),
                    confidence='high'
                ))
    
    def get_artifactory_servers_from_configs(self, configs: Dict[str, List[RuntimeConfiguration]]) -> List[Dict]:
        """Extract unique Artifactory servers from configurations"""
        servers = {}
        
        for pm, config_list in configs.items():
            for config in config_list:
                if self.is_compliant_artifactory(config.config_value):
                    # Extract server domain
                    match = re.search(r'([\w-]+\.artifactory\.cec\.lab\.emc\.com)', config.config_value)
                    if match:
                        server = match.group(1)
                        
                        if server not in servers:
                            servers[server] = {
                                'server': server,
                                'package_managers': set(),
                                'repositories': set(),
                                'evidence_count': 0
                            }
                        
                        servers[server]['package_managers'].add(pm)
                        servers[server]['evidence_count'] += 1
                        
                        # Extract repository name if present
                        repo_match = re.search(r'/artifactory/(?:api/(?:pypi|npm|go|maven)/)?([^/\s]+)', config.config_value)
                        if repo_match:
                            servers[server]['repositories'].add(repo_match.group(1))
        
        # Convert sets to lists for JSON serialization
        result = []
        for server_data in servers.values():
            result.append({
                'server': server_data['server'],
                'package_managers': list(server_data['package_managers']),
                'repositories': list(server_data['repositories']),
                'evidence_count': server_data['evidence_count']
            })
        
        return result


def main():
    """Test the configuration enumerator"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python config_enumerator.py <repo_name> [repo_path]")
        sys.exit(1)
    
    repo_name = sys.argv[1]
    repo_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    enumerator = ConfigurationEnumerator()
    configs = enumerator.enumerate_all_configs(repo_name, repo_path)
    
    print("\n=== Configuration Summary ===")
    for pm, config_list in configs.items():
        if config_list:
            print(f"\n{pm.upper()}:")
            for config in config_list:
                print(f"  - {config.config_value}")
                print(f"    Source: {config.source_type} ({config.source_location})")
                print(f"    Confidence: {config.confidence}")
    
    # Show Artifactory servers
    servers = enumerator.get_artifactory_servers_from_configs(configs)
    if servers:
        print("\n=== Artifactory Servers Detected ===")
        for server in servers:
            print(f"  {server['server']}")
            print(f"    Package Managers: {', '.join(server['package_managers'])}")
            print(f"    Repositories: {', '.join(server['repositories'])}")
            print(f"    Evidence Count: {server['evidence_count']}")


if __name__ == '__main__':
    main()
