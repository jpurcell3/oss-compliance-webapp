#!/usr/bin/env python3
"""
OSS Repository Compliance Scanner
Adapted for web application use
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

class ComplianceScanner:
    def __init__(self, repo_root: str, virtual_repos: Dict = None, artifactory_base: str = None, whitelist_urls: List[str] = None):
        self.repo_root = Path(repo_root)
        self.virtual_repos = virtual_repos or {}
        self.artifactory_base = artifactory_base or 'isgedge.artifactory.cec.lab.emc.com'
        self.whitelist_urls = whitelist_urls or []
        self.findings = []
        self.compliant_count = 0
        self.non_compliant_count = 0
        # New: Track individual OSS items for accurate compliance calculation
        self.total_items = 0
        self.compliant_items = 0
        self.non_compliant_items = 0
    
    def is_url_whitelisted(self, url: str) -> bool:
        """Check if a URL matches any whitelisted patterns (trusted Dell/EMC sources)"""
        url_lower = url.lower()
        
        # Always check Dell/EMC internal domains
        trusted_domains = [
            'cec.lab.emc.com',
            '.emc.com',
            '.dell.com',
            self.artifactory_base
        ]
        
        for domain in trusted_domains:
            if domain.lower() in url_lower:
                return True
        
        # Check Dell GitHub organizations
        trusted_orgs = [
            'github.com/fusion-e',
            'github.com/isg-edge'
        ]
        
        for org in trusted_orgs:
            if org.lower() in url_lower:
                return True
        
        # Check configured whitelist patterns
        if self.whitelist_urls:
            for whitelist_pattern in self.whitelist_urls:
                if whitelist_pattern.lower() in url_lower:
                    return True
        
        return False
    
    def scan(self) -> Dict:
        """Scan all build configuration files"""
        print(f"Scanning repository: {self.repo_root}")
        
        # Scan Go modules
        self.scan_go_modules()
        
        # Scan Python requirements
        self.scan_python_requirements()
        
        # Scan Node.js package.json
        self.scan_node_packages()
        
        # Scan Maven pom.xml
        self.scan_maven_poms()
        
        # Scan Jenkinsfiles
        self.scan_jenkinsfiles()
        
        # Scan Makefiles
        self.scan_makefiles()
        
        return self.generate_report()
    
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
            if f'{self.artifactory_base}' in content and 'go' in content.lower():
                goproxy_configured = True
            
            # Count each Go dependency
            for dep in go_deps:
                self.total_items += 1
                # Check if dependency URL is whitelisted
                if self.is_url_whitelisted(dep):
                    self.compliant_items += 1
                    continue
                    
                if goproxy_configured:
                    self.compliant_items += 1
                else:
                    self.non_compliant_items += 1
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'go_module',
                        'issue': f'Go dependency {dep} not using approved proxy',
                        'severity': 'HIGH',
                        'recommended_action': f'Configure GOPROXY=https://{self.artifactory_base}/artifactory/api/go/{self.virtual_repos.get("go", "go-virtual")},direct',
                        'compliant': False
                    })
            
            # Keep file-level check for backward compatibility
            if 'github.com/' in content and not goproxy_configured:
                self.findings.append({
                    'file': str(relative_path),
                    'type': 'go_module',
                    'issue': 'Go dependencies from github.com (requires GOPROXY configuration)',
                    'severity': 'HIGH',
                    'recommended_action': f'Configure GOPROXY=https://{self.artifactory_base}/artifactory/api/go/{self.virtual_repos.get("go", "go-virtual")},direct',
                    'compliant': False
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
                        'compliant': False
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
                        'compliant': False
                    })
            
            # Keep file-level check for backward compatibility
            if not has_index_url:
                self.findings.append({
                    'file': str(relative_path),
                    'type': 'python_requirements',
                    'issue': 'No pip index-url configured (defaults to PyPI)',
                    'severity': 'HIGH',
                    'recommended_action': f'Add: --index-url https://{self.artifactory_base}/artifactory/api/pypi/{self.virtual_repos.get("pypi", "pypi-virtual")}/simple',
                    'compliant': False
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
                            'compliant': False
                        })
                
                # Keep file-level check for backward compatibility
                if not registry_configured:
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'node_package',
                        'issue': 'No NPM registry configured (defaults to npmjs.org)',
                        'severity': 'HIGH',
                        'recommended_action': f'Configure NPM registry: {self.virtual_repos.get("npm", "npm-virtual")}',
                        'compliant': False
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
                        'compliant': False
                    })
            
            # Keep file-level check for backward compatibility
            if has_artifactory_config:
                self.compliant_count += 1
            else:
                self.findings.append({
                    'file': str(relative_path),
                    'type': 'maven_pom',
                    'issue': 'No Artifactory Maven repository configured (defaults to Maven Central)',
                    'severity': 'HIGH',
                    'recommended_action': f'Add mirror to {self.virtual_repos.get("maven", "maven-virtual")}',
                    'compliant': False
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
                        'compliant': False
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
                        'compliant': False
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
            'recommendations': self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[Dict]:
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
        
        return recommendations
