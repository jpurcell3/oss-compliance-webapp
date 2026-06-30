#!/usr/bin/env python3
"""
OSS Compliance Scanner
Provides comprehensive OSS compliance reporting with detailed endpoint enumeration
and runtime configuration analysis.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List
from endpoint_analyzer import EndpointAnalyzer
from config_enumerator import ConfigurationEnumerator, RuntimeConfiguration


class ComplianceScanner:
    """
    Comprehensive scanner that combines basic compliance checking with
    detailed endpoint analysis and proxy/translation detection.
    """
    
    def __init__(self, repo_root: str, virtual_repos: Dict = None, 
                 artifactory_base: str = None, whitelist_urls: List[str] = None,
                 repo_name: str = None, jenkins_urls: List[str] = None,
                 jenkins_user: str = None, jenkins_token: str = None):
        self.repo_root = Path(repo_root)
        self.repo_name = repo_name or self.repo_root.name
        self.virtual_repos = virtual_repos or {}
        self.artifactory_base = artifactory_base or 'isgedge.artifactory.cec.lab.emc.com'
        self.whitelist_urls = whitelist_urls or []
        
        # Basic compliance scanning state
        self.findings = []
        self.compliant_count = 0
        self.non_compliant_count = 0
        self.total_items = 0
        self.compliant_items = 0
        self.non_compliant_items = 0
        
        # Initialize endpoint analyzer
        self.endpoint_analyzer = EndpointAnalyzer(
            repo_root=repo_root,
            artifactory_base=artifactory_base
        )
        
        # Initialize configuration enumerator
        # SSL verification - default to False for internal Jenkins servers with self-signed certs
        ssl_verify_env = os.getenv('SSL_VERIFY', 'false').lower()
        ssl_verify = ssl_verify_env == 'true'
        
        self.config_enumerator = ConfigurationEnumerator(
            jenkins_urls=jenkins_urls,
            jenkins_user=jenkins_user,
            jenkins_token=jenkins_token,
            ssl_verify=ssl_verify
        )
    
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
    
    def scan_basic(self) -> Dict:
        """Basic compliance scan of build configuration files"""
        print(f"Basic compliance scan: {self.repo_root}")
        
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
        
        return self.generate_basic_report()
    
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
                
                # Check for npm workspaces configuration
                is_workspace_root = 'workspaces' in content
                
                # Check for publishConfig or registry configuration
                registry_configured = False
                registry_source = None
                
                # Check publishConfig.registry
                if 'publishConfig' in content and 'registry' in content['publishConfig']:
                    if self.artifactory_base in content['publishConfig']['registry']:
                        registry_configured = True
                        registry_source = 'publishConfig.registry'
                
                # Check config.registry (additional npm configuration field)
                if not registry_configured and 'config' in content and 'registry' in content['config']:
                    if self.artifactory_base in content['config']['registry']:
                        registry_configured = True
                        registry_source = 'config.registry'
                
                # Check for scope-specific registry configurations
                if not registry_configured:
                    package_name = content.get('name', '')
                    if package_name.startswith('@'):
                        # Extract scope from package name (e.g., @fusion -> fusion)
                        scope = package_name.split('/')[0][1:]  # Remove @
                        scope_registry_key = f"@{scope}:registry"
                        if 'config' in content and scope_registry_key in content['config']:
                            if self.artifactory_base in content['config'][scope_registry_key]:
                                registry_configured = True
                                registry_source = f'config.{scope_registry_key}'
                
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
                
                # Check package-lock.json for actual registry usage evidence
                lockfile_registry_evidence = None
                lockfile_path = pkg_file.parent / 'package-lock.json'
                if lockfile_path.exists():
                    try:
                        lockfile_content = json.loads(lockfile_path.read_text())
                        lockfile_registry_evidence = self._analyze_package_lock_registry(lockfile_content)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
                
                # Keep file-level check for backward compatibility
                if not registry_configured:
                    # Check if package-lock.json provides evidence
                    if lockfile_registry_evidence:
                        # Package-lock.json shows actual registry usage
                        if lockfile_registry_evidence['is_compliant']:
                            self.compliant_count += 1
                            self.findings.append({
                                'file': str(relative_path),
                                'type': 'node_package',
                                'issue': f'NPM registry detected from package-lock.json: {lockfile_registry_evidence["registry"]}',
                                'severity': 'INFO',
                                'recommended_action': None,
                                'compliant': True
                            })
                        else:
                            self.non_compliant_count += 1
                            self.findings.append({
                                'file': str(relative_path),
                                'type': 'node_package',
                                'issue': f'No NPM registry configured (package-lock.json uses {lockfile_registry_evidence["registry"]})',
                                'severity': 'HIGH',
                                'recommended_action': f'Configure NPM registry: {self.virtual_repos.get("npm", "npm-virtual")}',
                                'compliant': False
                            })
                    else:
                        # No package-lock.json or unable to parse
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
                    # Add info finding about registry configuration source
                    self.findings.append({
                        'file': str(relative_path),
                        'type': 'node_package',
                        'issue': f'NPM registry configured via {registry_source}',
                        'severity': 'INFO',
                        'recommended_action': None,
                        'compliant': True
                    })
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    
    def _analyze_package_lock_registry(self, lockfile_content: Dict) -> Dict:
        """
        Analyze package-lock.json to detect actual registry usage.
        Returns dict with registry info and compliance status.
        """
        try:
            packages = lockfile_content.get('packages', {})
            if not packages:
                return None
            
            # Sample resolved URLs to detect registry
            registries = set()
            sample_count = 0
            
            for pkg_name, pkg_data in packages.items():
                if sample_count >= 10:  # Sample first 10 packages
                    break
                
                resolved = pkg_data.get('resolved', '')
                if resolved:
                    sample_count += 1
                    
                    # Detect registry from URL
                    if 'registry.npmjs.org' in resolved:
                        registries.add('npmjs.org')
                    elif 'artifactory' in resolved.lower():
                        registries.add('artifactory')
                        # Check if it's our approved Artifactory
                        if self.artifactory_base in resolved:
                            registries.add('approved-artifactory')
                    elif 'npm.pkg.github.com' in resolved:
                        registries.add('github-npm')
                    else:
                        import re
                        match = re.search(r'https?://([^/]+)/', resolved)
                        if match:
                            registries.add(match.group(1))
            
            if not registries:
                return None
            
            # Determine compliance
            is_compliant = 'approved-artifactory' in registries
            primary_registry = list(registries)[0] if registries else 'unknown'
            
            return {
                'registry': primary_registry,
                'registries': list(registries),
                'is_compliant': is_compliant,
                'sample_size': sample_count
            }
        except Exception as e:
            print(f"Error analyzing package-lock.json: {e}")
            return None
    
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
    
    def generate_basic_report(self) -> Dict:
        """Generate basic compliance report with per-dependency compliance calculation"""
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
                'count': len(critical)
            })
        
        if high:
            recommendations.append({
                'priority': 'HIGH', 
                'action': 'Configure approved package repositories (Artifactory virtual repos)',
                'count': len(high)
            })
        
        if medium:
            recommendations.append({
                'priority': 'MEDIUM',
                'action': 'Update Artifactory virtual repository references',
                'count': len(medium)
            })
        
        return recommendations
    
    def scan_comprehensive(self) -> Dict:
        """
        Perform comprehensive scan combining basic compliance checks
        with detailed endpoint analysis and runtime configuration enumeration.
        """
        print(f"Starting comprehensive scan of: {self.repo_root}")
        
        # Run basic compliance scan
        print("\n=== Phase 1: Basic Compliance Scan ===")
        basic_report = self.scan_basic()
        
        # Run detailed endpoint analysis
        print("\n=== Phase 2: Detailed Endpoint Analysis ===")
        endpoint_report = self.endpoint_analyzer.analyze_repository()
        
        # Enumerate runtime configurations
        print("\n=== Phase 3: Runtime Configuration Enumeration ===")
        runtime_configs = self.config_enumerator.enumerate_all_configs(
            repo_name=self.repo_name,
            repo_path=self.repo_root
        )
        
        # Merge and enhance reports
        print("\n=== Phase 4: Merging Reports and Eliminating False Positives ===")
        comprehensive_report = self._merge_reports(basic_report, endpoint_report, runtime_configs)
        
        return comprehensive_report
    
    def _merge_reports(self, basic_report: Dict, endpoint_report: Dict, 
                      runtime_configs: Dict[str, List[RuntimeConfiguration]]) -> Dict:
        """Merge basic compliance report with detailed endpoint analysis and runtime configs"""
        
        # Create comprehensive summary
        comprehensive_summary = {
            'repository_name': basic_report['scan_summary']['repository_name'],
            'scan_timestamp': self._get_timestamp(),
            
            # Basic compliance metrics
            'basic_compliance': {
                'total_findings': basic_report['scan_summary']['total_findings'],
                'compliant_checks': basic_report['scan_summary']['compliant_checks'],
                'non_compliant_checks': basic_report['scan_summary']['non_compliant_checks'],
                'compliance_percentage': basic_report['scan_summary']['compliance_percentage']
            },
            
            # Detailed component metrics
            'component_analysis': {
                'total_components': endpoint_report['summary']['total_components'],
                'compliant_components': endpoint_report['summary']['compliant_components'],
                'non_compliant_components': endpoint_report['summary']['non_compliant_components'],
                'warning_components': endpoint_report['summary']['warning_components'],
                'component_compliance_percentage': endpoint_report['summary']['compliance_percentage']
            },
            
            # Endpoint configuration summary
            'endpoint_summary': {
                'total_configurations': endpoint_report['summary']['total_endpoint_configs'],
                'by_type': endpoint_report['by_endpoint_type'],
                'by_ecosystem': endpoint_report['by_ecosystem']
            }
        }
        
        # Reconcile findings between both scans
        reconciled_findings = self._reconcile_findings(
            basic_report['findings'],
            endpoint_report['critical_findings']
        )
        
        # Eliminate false positives using runtime configurations
        validated_findings = self._eliminate_false_positives(
            reconciled_findings,
            runtime_configs
        )
        
        # Separate INFO-level findings (compliant via runtime) from actual issues
        compliant_findings = [f for f in validated_findings if f.get('severity') == 'INFO' and f.get('status') == 'compliant_via_runtime_config']
        actual_issues = [f for f in validated_findings if not (f.get('severity') == 'INFO' and f.get('status') == 'compliant_via_runtime_config')]
        
        # Count findings by compliance status
        # For grouped findings, count the actual number of components, not the number of groups
        runtime_compliant_component_count = sum(f.get('component_count', 1) for f in compliant_findings)
        runtime_compliant_count = len(compliant_findings)  # Number of grouped findings for display
        non_compliant_count = len(actual_issues)
        total_findings_count = len(validated_findings)
        
        # Move runtime-validated findings from non-compliant/warning to compliant
        original_compliant = comprehensive_summary['component_analysis']['compliant_components']
        original_non_compliant = comprehensive_summary['component_analysis']['non_compliant_components']
        original_warning = comprehensive_summary['component_analysis']['warning_components']
        
        moved_from_non_compliant = min(runtime_compliant_component_count, original_non_compliant)
        remaining_to_move = max(0, runtime_compliant_component_count - moved_from_non_compliant)
        moved_from_warning = min(remaining_to_move, original_warning)
        
        updated_compliant = original_compliant + moved_from_non_compliant + moved_from_warning
        updated_non_compliant = max(0, original_non_compliant - moved_from_non_compliant)
        updated_warning = max(0, original_warning - moved_from_warning)
        
        comprehensive_summary['component_analysis']['compliant_components'] = updated_compliant
        comprehensive_summary['component_analysis']['non_compliant_components'] = updated_non_compliant
        comprehensive_summary['component_analysis']['warning_components'] = updated_warning
        comprehensive_summary['component_analysis']['component_compliance_percentage'] = round(
            (updated_compliant / comprehensive_summary['component_analysis']['total_components'] * 100)
            if comprehensive_summary['component_analysis']['total_components'] > 0 else 100, 2
        )
        
        # Update ecosystem breakdown to reflect runtime evidence
        # Count compliant components by ecosystem (not just grouped findings)
        # Map finding types to ecosystem names used by endpoint analyzer
        compliant_by_ecosystem = {}
        for finding in compliant_findings:
            ftype = finding.get('type', '')
            if 'python' in ftype.lower() or 'pip' in ftype.lower():
                ecosystem = 'python'
            elif 'node' in ftype.lower() or 'npm' in ftype.lower():
                ecosystem = 'npm'  # Changed from 'node' to match endpoint analyzer
            elif 'go' in ftype.lower():
                ecosystem = 'go'
            elif 'maven' in ftype.lower() or 'java' in ftype.lower():
                ecosystem = 'maven'
            elif 'docker' in ftype.lower():
                ecosystem = 'docker'
            else:
                ecosystem = 'other'
            
            # Count the actual number of components in this grouped finding
            component_count = finding.get('component_count', 1)
            compliant_by_ecosystem[ecosystem] = compliant_by_ecosystem.get(ecosystem, 0) + component_count
        
        # Update each ecosystem's stats
        moved_by_ecosystem = {}
        for ecosystem, stats in comprehensive_summary['endpoint_summary']['by_ecosystem'].items():
            ecosystem_compliant_count = compliant_by_ecosystem.get(ecosystem, 0)
            if ecosystem_compliant_count > 0:
                # Move non-compliant first, then warning, to compliant for this ecosystem
                ecosystem_non_compliant = stats.get('non_compliant', 0)
                ecosystem_warnings = stats.get('warning', 0)
                moved_nc = min(ecosystem_compliant_count, ecosystem_non_compliant)
                remaining = max(0, ecosystem_compliant_count - moved_nc)
                moved_warn = min(remaining, ecosystem_warnings)
                moved_by_ecosystem[ecosystem] = moved_nc + moved_warn
                stats['compliant'] = stats.get('compliant', 0) + moved_nc + moved_warn
                stats['non_compliant'] = max(0, ecosystem_non_compliant - moved_nc)
                stats['warning'] = max(0, ecosystem_warnings - moved_warn)
        
        # Reflect runtime translation in endpoint type summary:
        # runtime-validated components represent effectively translated/proxied behavior
        by_type = comprehensive_summary['endpoint_summary'].get('by_type', {})
        direct_public_count = by_type.get('direct_public', 0)
        translated_moved = min(runtime_compliant_component_count, direct_public_count)
        if translated_moved > 0:
            by_type['direct_public'] = direct_public_count - translated_moved
            by_type['translated'] = by_type.get('translated', 0) + translated_moved
        
        # Calculate reliability metrics using total components from endpoint analysis
        reliability_metrics = self._calculate_reliability_metrics(
            runtime_configs,
            endpoint_report['summary']['total_components']
        )
        
        # Get Artifactory servers detected
        artifactory_servers = self.config_enumerator.get_artifactory_servers_from_configs(runtime_configs)
        
        # Get current proxy configurations
        current_proxy_configs = self.endpoint_analyzer.get_current_proxy_configurations()
        
        # Generate enhanced recommendations with current vs desired config
        enhanced_recommendations = self._generate_enhanced_recommendations(
            basic_report,
            endpoint_report,
            actual_issues,
            current_proxy_configs
        )
        
        # Build comprehensive report
        comprehensive_report = {
            # Enhanced summary for display
            'summary': comprehensive_summary,
            
            # Template compatibility - add scan_summary and scan_metadata
            'scan_summary': {
                'scan_type': 'enhanced',
                'total_items': comprehensive_summary['component_analysis']['total_components'],
                'compliant_items': comprehensive_summary['component_analysis']['compliant_components'],
                'non_compliant_items': comprehensive_summary['component_analysis']['non_compliant_components'],
                'compliance_percentage': comprehensive_summary['component_analysis']['component_compliance_percentage'],
                'total_findings': total_findings_count,
                'compliant_checks': runtime_compliant_count,
                'non_compliant_checks': non_compliant_count,
                'repository_name': comprehensive_summary['repository_name']
            },
            'scan_metadata': basic_report.get('scan_metadata', {
                'repository_name': comprehensive_summary['repository_name'],
                'repository_path': str(self.repo_root),
                'scanned_at': comprehensive_summary['scan_timestamp'],
                'repository_type': 'local'
            }),
            
            'approved_virtual_repositories': basic_report['approved_virtual_repositories'],
            
            # Detailed endpoint configurations
            'endpoint_configurations': endpoint_report['endpoint_configurations'],
            
            # Component-to-endpoint mappings
            'component_mappings': endpoint_report['component_mappings'],
            
            # All findings (both compliant and non-compliant)
            # Compliant findings are marked with status='compliant_via_runtime_config' and severity='INFO'
            'findings': validated_findings,
            
            # Deprecated: kept for backward compatibility
            # Use 'findings' array and filter by status='compliant_via_runtime_config' instead
            'compliant_findings': compliant_findings,
            
            # Runtime configurations discovered
            'runtime_configurations': self._serialize_runtime_configs(runtime_configs),
            
            # Reliability metrics
            'reliability_metrics': reliability_metrics,
            
            # Artifactory servers detected
            'artifactory_servers_detected': artifactory_servers,
            
            # Enhanced recommendations
            'recommendations': enhanced_recommendations,
            
            # Critical issues requiring immediate attention (use post-validation component stats)
            'critical_issues': self._identify_critical_issues(
                endpoint_report,
                runtime_configs,
                comprehensive_summary.get('component_analysis')
            ),
            
            # Detailed breakdown by ecosystem (post-validation aligned)
            'ecosystem_breakdown': self._generate_ecosystem_breakdown(
                endpoint_report,
                comprehensive_summary['endpoint_summary']['by_ecosystem'],
                compliant_by_ecosystem
            ),
            
            # Proxy/translation analysis (adjusted for runtime validation)
            'proxy_analysis': self._analyze_proxy_usage(endpoint_report, runtime_compliant_component_count),
            
            # Current proxy configurations
            'current_proxy_configurations': current_proxy_configs
        }
        
        # Keep ecosystem endpoint type breakdown consistent with runtime validation:
        # if components were validated via runtime config, treat corresponding direct_public
        # counts as translated in the displayed ecosystem breakdown.
        eco_breakdown = comprehensive_report.get('ecosystem_breakdown', {}) or {}
        for ecosystem, moved_count in moved_by_ecosystem.items():
            if moved_count <= 0:
                continue
            eco_entry = eco_breakdown.get(ecosystem)
            if not eco_entry:
                continue
            endpoint_types = eco_entry.get('endpoint_types', {}) or {}
            direct_public = endpoint_types.get('direct_public', 0)
            translated_move = min(moved_count, direct_public)
            if translated_move > 0:
                endpoint_types['direct_public'] = direct_public - translated_move
                endpoint_types['translated'] = endpoint_types.get('translated', 0) + translated_move
                eco_entry['endpoint_types'] = endpoint_types
                eco_breakdown[ecosystem] = eco_entry
        comprehensive_report['ecosystem_breakdown'] = eco_breakdown
        
        # Final safety reconciliation: ensure critical issue messaging is consistent
        # with the same post-validation component analysis shown in the summary.
        ca = comprehensive_report.get('summary', {}).get('component_analysis', {})
        total_components = ca.get('total_components', 0) or 0
        non_compliant_components = ca.get('non_compliant_components', 0) or 0
        non_compliant_pct = (non_compliant_components / total_components * 100) if total_components > 0 else 0.0
        critical_issues = comprehensive_report.get('critical_issues', []) or []
        filtered_issues = []
        for issue in critical_issues:
            if issue.get('issue') == 'High Non-Compliance Rate':
                if non_compliant_pct > 50:
                    issue['description'] = f'{non_compliant_pct:.1f}% of components are non-compliant'
                    filtered_issues.append(issue)
            else:
                filtered_issues.append(issue)
        comprehensive_report['critical_issues'] = filtered_issues
        
        return comprehensive_report
    
    def _reconcile_findings(self, basic_findings: List[Dict], 
                           critical_findings: List[Dict]) -> List[Dict]:
        """Reconcile findings from both scans, grouping identical issues by type"""
        reconciled = []
        
        # Group endpoint analyzer findings by issue type
        endpoint_findings_by_issue = {}
        for finding in critical_findings:
            issue = finding['issue']
            severity = finding['severity']
            key = f"{severity}:{issue}"
            
            if key not in endpoint_findings_by_issue:
                endpoint_findings_by_issue[key] = {
                    'severity': severity,
                    'type': 'endpoint_configuration',
                    'issue': issue,
                    'file': finding.get('file', 'N/A'),
                    'recommended_action': finding['recommendation'],
                    'impact': finding['impact'],
                    'component_count': 0,
                    'components': [],
                    'source': 'endpoint_analyzer'
                }
            
            endpoint_findings_by_issue[key]['component_count'] += 1
            if finding.get('component'):
                endpoint_findings_by_issue[key]['components'].append(finding['component'])
        
        # Add grouped endpoint findings
        for finding in endpoint_findings_by_issue.values():
            # Update impact to show component count
            finding['impact'] = f"{finding['component_count']} components affected"
            reconciled.append(finding)
        
        # Add basic findings, avoiding duplicates
        for finding in basic_findings:
            # Check if this is already covered by a critical finding
            is_duplicate = False
            for critical in critical_findings:
                if (finding['file'] == critical.get('file') and 
                    finding['type'] in critical.get('issue', '')):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                reconciled.append({
                    **finding,
                    'source': 'basic_scanner'
                })
        
        # Sort by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        reconciled.sort(key=lambda x: severity_order.get(x['severity'], 4))
        
        return reconciled
    
    def _get_desired_proxy_configs(self, ecosystems_needing_proxy: List[Dict]) -> str:
        """Generate desired proxy configuration string for ecosystems"""
        desired_configs = []
        for eco in ecosystems_needing_proxy:
            ecosystem = eco['ecosystem']
            if ecosystem == 'go':
                desired_configs.append(
                    f"GO: GOPROXY=https://{self.artifactory_base}/artifactory/api/go/isgedge-maven-virtual,direct"
                )
            elif ecosystem == 'python':
                desired_configs.append(
                    f"Python: PIP_INDEX_URL=https://{self.artifactory_base}/artifactory/api/pypi/pypi-virtual/simple"
                )
            elif ecosystem == 'npm':
                desired_configs.append(
                    f"NPM: npm_config_registry=https://{self.artifactory_base}/artifactory/api/npm/npm-virtual"
                )
            elif ecosystem == 'maven':
                desired_configs.append(
                    f"Maven: settings.xml with {self.artifactory_base} mirror"
                )
            else:
                desired_configs.append(f"{ecosystem.upper()}: Configure with {self.artifactory_base}")
        return '; '.join(desired_configs)
    
    def _generate_enhanced_recommendations(self, basic_report: Dict, 
                                          endpoint_report: Dict,
                                          findings: List[Dict],
                                          current_proxy_configs: Dict) -> List[Dict]:
        """Generate prioritized, actionable recommendations with current vs desired config"""
        recommendations = []
        
        # Critical: GOPRIVATE misconfiguration
        goprivate_issues = [f for f in findings if 'GOPRIVATE' in f.get('issue', '')]
        if goprivate_issues:
            current_goprivate = current_proxy_configs.get('go', {}).get('private', 'Not configured')
            current_goproxy = current_proxy_configs.get('go', {}).get('proxy', 'Not configured')
            
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Go Module Configuration',
                'issue': 'GOPRIVATE includes github.com - bypassing Artifactory for public modules',
                'current_config': f'GOPRIVATE: {current_goprivate}, GOPROXY: {current_goproxy}',
                'desired_config': f'GOPRIVATE: eos2git.cec.lab.emc.com, GOPROXY: https://{self.artifactory_base}/artifactory/api/go/isgedge-maven-virtual,direct',
                'impact': f'{endpoint_report["by_ecosystem"].get("go", {}).get("total", 0)} Go modules affected',
                'action': 'Update Dockerfile GOPRIVATE configuration',
                'implementation': [
                    f'Current: GOPRIVATE={current_goprivate}',
                    f'Current: GOPROXY={current_goproxy}',
                    'Remove "github.com" from GOPRIVATE environment variable',
                    'Keep only "eos2git.cec.lab.emc.com" in GOPRIVATE',
                    f'Add GOPROXY=https://{self.artifactory_base}/artifactory/api/go/isgedge-maven-virtual,direct',
                    'This will proxy public GitHub modules through Artifactory while keeping internal modules direct'
                ],
                'affected_files': [f['file'] for f in goprivate_issues],
                'estimated_impact': f'~{endpoint_report["by_ecosystem"].get("go", {}).get("non_compliant", 0)} modules will become compliant'
            })
        
        # High: Missing proxy configurations
        ecosystems_needing_proxy = []
        for ecosystem, stats in endpoint_report['by_ecosystem'].items():
            if stats.get('non_compliant', 0) > 0:
                current_config = current_proxy_configs.get(ecosystem, {})
                ecosystems_needing_proxy.append({
                    'ecosystem': ecosystem,
                    'count': stats['non_compliant'],
                    'total': stats['total'],
                    'current_config': current_config
                })
        
        if ecosystems_needing_proxy:
            ecosystem_details = []
            for eco in ecosystems_needing_proxy:
                ecosystem_details.append(
                    f"{eco['ecosystem'].upper()}: {eco['count']}/{eco['total']} non-compliant, "
                    f"Current config: {eco['current_config'] or 'None configured'}"
                )
            
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Package Manager Proxy Configuration',
                'issue': f'{len(ecosystems_needing_proxy)} package ecosystems not using Artifactory proxy',
                'current_config': '; '.join(ecosystem_details),
                'desired_config': self._get_desired_proxy_configs(ecosystems_needing_proxy),
                'impact': f'{sum(e["count"] for e in ecosystems_needing_proxy)} components affected',
                'action': 'Configure package manager proxies in build pipeline',
                'implementation': self._generate_proxy_config_steps(ecosystems_needing_proxy),
                'affected_ecosystems': [e['ecosystem'] for e in ecosystems_needing_proxy]
            })
        
        # Medium: Optimize proxy usage
        proxy_count = endpoint_report['by_endpoint_type'].get('proxied', 0)
        direct_count = endpoint_report['by_endpoint_type'].get('direct_public', 0)
        
        if direct_count > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Proxy Optimization',
                'issue': f'{direct_count} components using direct public endpoints',
                'impact': 'Missing benefits of caching, security scanning, and compliance tracking',
                'action': 'Route all public dependencies through Artifactory',
                'implementation': [
                    'Ensure all package managers are configured to use Artifactory virtual repositories',
                    'Update Jenkins shared library to set proxy environment variables',
                    'Add proxy configuration to Dockerfiles and Makefiles'
                ],
                'current_state': f'{proxy_count} proxied, {direct_count} direct',
                'target_state': f'{proxy_count + direct_count} proxied, 0 direct'
            })
        
        return recommendations
    
    def _generate_proxy_config_steps(self, ecosystems: List[Dict]) -> List[str]:
        """Generate specific configuration steps for each ecosystem"""
        steps = []
        
        for eco in ecosystems:
            ecosystem = eco['ecosystem']
            
            if ecosystem == 'go':
                steps.append(f'Go ({eco["count"]} modules): Add GOPROXY=https://{self.artifactory_base}/artifactory/api/go/isgedge-maven-virtual,direct')
            elif ecosystem == 'python':
                steps.append(f'Python ({eco["count"]} packages): Add PIP_INDEX_URL=https://{self.artifactory_base}/artifactory/api/pypi/isgedge-pypi-virtual/simple')
            elif ecosystem == 'npm':
                steps.append(f'NPM ({eco["count"]} packages): Add NPM_CONFIG_REGISTRY=https://{self.artifactory_base}/artifactory/api/npm/isgedge-npm-virtual')
            elif ecosystem == 'maven':
                steps.append(f'Maven ({eco["count"]} dependencies): Configure mirror to https://{self.artifactory_base}/artifactory/isgedge-maven-virtual')
            elif ecosystem == 'docker':
                steps.append(f'Docker ({eco["count"]} images): Use DOCKER_ARTIFACTORY={self.artifactory_base}/isgedge-docker-virtual')
        
        return steps
    
    def _identify_critical_issues(
        self,
        endpoint_report: Dict,
        runtime_configs: Dict[str, List[RuntimeConfiguration]] = None,
        component_analysis: Dict = None
    ) -> List[Dict]:
        """Identify critical issues requiring immediate attention"""
        critical_issues = []
        
        # Issue 1: High percentage of non-compliant components
        summary_for_critical = component_analysis or endpoint_report.get('summary', {})
        total_components = summary_for_critical.get('total_components', 0)
        non_compliant_components = summary_for_critical.get('non_compliant_components', 0)
        non_compliant_pct = (
            non_compliant_components / total_components * 100
            if total_components > 0 else 0
        )
        
        if non_compliant_pct > 50:
            critical_issues.append({
                'issue': 'High Non-Compliance Rate',
                'description': f'{non_compliant_pct:.1f}% of components are non-compliant',
                'severity': 'CRITICAL',
                'recommendation': 'Immediate action required to configure package manager proxies'
            })
        
        # Issue 2: GOPRIVATE misconfiguration
        for config in endpoint_report['endpoint_configurations']:
            if 'GOPRIVATE' in config.get('snippet', ''):
                if 'github.com' in config['url']:
                    critical_issues.append({
                        'issue': 'GOPRIVATE Misconfiguration',
                        'description': 'github.com in GOPRIVATE bypasses Artifactory for all public Go modules',
                        'severity': 'CRITICAL',
                        'file': config['file'],
                        'recommendation': 'Remove github.com from GOPRIVATE immediately'
                    })
        
        # Issue 3: No proxy configuration found
        # Check both static configs AND runtime configs before flagging
        has_static_proxy = any(config['type'] == 'proxied' for config in endpoint_report['endpoint_configurations'])
        has_runtime_proxy = False
        
        if runtime_configs:
            # Check if any runtime configs exist with compliant Artifactory URLs
            for pm, config_list in runtime_configs.items():
                if config_list:
                    compliant_configs = [c for c in config_list if self.config_enumerator.is_compliant_artifactory(c.config_value)]
                    if compliant_configs:
                        has_runtime_proxy = True
                        break
        
        # Only flag if BOTH static and runtime checks fail
        if not has_static_proxy and not has_runtime_proxy and endpoint_report['summary']['total_components'] > 0:
            critical_issues.append({
                'issue': 'No Proxy Configuration Detected',
                'description': 'Repository has dependencies but no Artifactory proxy configuration',
                'severity': 'HIGH',
                'recommendation': 'Configure Artifactory proxy for all package managers'
            })
        
        return critical_issues
    
    def _generate_ecosystem_breakdown(
        self,
        endpoint_report: Dict,
        validated_by_ecosystem: Dict = None,
        compliant_by_ecosystem: Dict = None
    ) -> Dict:
        """Generate detailed breakdown by ecosystem aligned with post-validation stats"""
        breakdown = {}
        
        # Map ecosystems to their typical dependency files
        ecosystem_files = {
            'python': ['requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py'],
            'npm': ['package.json', 'package-lock.json'],
            'go': ['go.mod', 'go.sum'],
            'maven': ['pom.xml'],
            'docker': ['Dockerfile', 'docker-compose.yml']
        }
        
        source_by_ecosystem = validated_by_ecosystem or endpoint_report.get('by_ecosystem', {})
        compliant_by_ecosystem = compliant_by_ecosystem or {}
        
        for ecosystem, stats in source_by_ecosystem.items():
            # Get components for this ecosystem
            ecosystem_components = [
                m for m in endpoint_report['component_mappings']
                if m['component']['ecosystem'] == ecosystem
            ]
            
            # Analyze endpoint types
            endpoint_types = {}
            for comp in ecosystem_components:
                endpoint_type = comp['actual_endpoint']['type']
                endpoint_types[endpoint_type] = endpoint_types.get(endpoint_type, 0) + 1
            
            # Align endpoint type display with runtime validation:
            # runtime-compliant components are shown as translated, not direct_public.
            moved_count = compliant_by_ecosystem.get(ecosystem, 0)
            if moved_count > 0:
                direct_public = endpoint_types.get('direct_public', 0)
                translated_move = min(moved_count, direct_public)
                if translated_move > 0:
                    endpoint_types['direct_public'] = direct_public - translated_move
                    endpoint_types['translated'] = endpoint_types.get('translated', 0) + translated_move
                    if endpoint_types['direct_public'] == 0:
                        endpoint_types.pop('direct_public', None)
            
            # Get primary dependency file for this ecosystem
            primary_file = None
            
            # First, try to find the file from actual components
            for comp in ecosystem_components:
                # Try both 'file' and 'source_file' fields
                file_path = comp['component'].get('file', '') or comp['component'].get('source_file', '')
                if file_path:
                    # Convert Windows backslashes to forward slashes for GitHub URLs
                    primary_file = file_path.replace('\\', '/')
                    break
            
            # If no file found from components, use the first default for ecosystem
            if not primary_file and ecosystem in ecosystem_files:
                primary_file = ecosystem_files[ecosystem][0].replace('\\', '/')
            
            # Update sample component status based on runtime validation
            # If this ecosystem had components validated via runtime config, mark them as compliant
            runtime_validated_count = compliant_by_ecosystem.get(ecosystem, 0)
            sample_components = []
            for i, c in enumerate(ecosystem_components[:5]):
                # If we still have runtime-validated components to account for and this was non_compliant/warning,
                # mark it as compliant
                original_status = c['compliance_status']
                if runtime_validated_count > 0 and original_status in ['non_compliant', 'warning']:
                    status = 'compliant'
                    runtime_validated_count -= 1
                else:
                    status = original_status
                
                sample_components.append({
                    'name': c['component']['name'],
                    'endpoint': c['actual_endpoint']['url'],
                    'status': status
                })
            
            breakdown[ecosystem] = {
                'total_components': stats['total'],
                'compliant': stats['compliant'],
                'non_compliant': stats['non_compliant'],
                'warning': stats.get('warning', 0),
                'compliance_rate': round((stats['compliant'] / stats['total'] * 100) if stats['total'] > 0 else 0, 2),
                'endpoint_types': endpoint_types,
                'primary_file': primary_file,
                'sample_components': sample_components
            }
        
        return breakdown
    
    def _analyze_proxy_usage(self, endpoint_report: Dict, runtime_compliant_count: int = 0) -> Dict:
        """
        Analyze proxy and translation usage patterns.
        Adjusts counts based on runtime validation - components validated via runtime config
        are counted as translated, not direct_public.
        """
        analysis = {
            'total_components': endpoint_report['summary']['total_components'],
            'proxied_components': 0,
            'direct_public_components': 0,
            'direct_private_components': 0,
            'translated_components': 0,
            'proxy_configurations': [],
            'translation_rules': []
        }
        
        # Count components by endpoint type (pre-validation)
        for mapping in endpoint_report['component_mappings']:
            endpoint_type = mapping['actual_endpoint']['type']
            
            if endpoint_type in ['proxied', 'runtime_configured']:
                analysis['proxied_components'] += 1
            elif endpoint_type == 'direct_public':
                analysis['direct_public_components'] += 1
            elif endpoint_type == 'direct_private':
                analysis['direct_private_components'] += 1
            elif endpoint_type == 'translated':
                analysis['translated_components'] += 1
        
        # Adjust for runtime validation: move runtime-compliant components from direct_public to translated
        if runtime_compliant_count > 0:
            moved = min(runtime_compliant_count, analysis['direct_public_components'])
            analysis['direct_public_components'] -= moved
            analysis['translated_components'] += moved
        
        # Extract proxy configurations
        for config in endpoint_report['endpoint_configurations']:
            if config['type'] == 'proxied':
                analysis['proxy_configurations'].append({
                    'url': config['url'],
                    'location': config['location'],
                    'file': config['file']
                })
            elif config['type'] == 'translated':
                analysis['translation_rules'].append({
                    'rule': config['notes'],
                    'file': config['file'],
                    'line': config['line']
                })
        
        # Calculate proxy effectiveness (including runtime-validated as proxied)
        total = analysis['total_components']
        proxied = analysis['proxied_components'] + analysis['translated_components']
        analysis['proxy_effectiveness'] = round((proxied / total * 100) if total > 0 else 0, 2)
        
        return analysis
    
    def _eliminate_false_positives(self, findings: List[Dict], 
                                   runtime_configs: Dict[str, List[RuntimeConfiguration]]) -> List[Dict]:
        """
        Cross-reference findings with runtime configurations.
        Remove or downgrade findings when runtime config proves compliance.
        Groups identical runtime-validated findings to avoid duplicates.
        """
        validated_findings = []
        runtime_validated_groups = {}  # Track grouped runtime-validated findings
        
        print(f"Eliminating false positives from {len(findings)} findings...")
        
        for finding in findings:
            finding_type = finding.get('type', '')
            file_path = finding.get('file', '')
            ecosystem = None
            compliant_configs = []
            
            # Check Python requirements
            if finding_type == 'python_requirements' or 'pip' in finding_type.lower():
                ecosystem = 'python'
                pip_configs = runtime_configs.get('pip', [])
                
                if pip_configs:
                    # Check if any config is compliant
                    compliant_configs = [c for c in pip_configs if self.config_enumerator.is_compliant_artifactory(c.config_value)]
                    
                    if not compliant_configs:
                        # Runtime config exists but non-compliant
                        finding['runtime_evidence'] = [
                            {
                                'source': c.source_type,
                                'location': c.source_location,
                                'value': c.config_value,
                                'evidence': c.evidence[:500] if len(c.evidence) > 500 else c.evidence,
                                'confidence': c.confidence,
                                'timestamp': c.timestamp.isoformat()
                            }
                            for c in pip_configs
                        ]
                        finding['issue'] += f" (Runtime config found but non-compliant: {pip_configs[0].config_value})"
            
            # Check Go modules
            elif finding_type == 'go_module' or 'go' in finding_type.lower():
                ecosystem = 'go'
                go_configs = runtime_configs.get('go', [])
                
                if go_configs:
                    compliant_configs = [c for c in go_configs if self.config_enumerator.is_compliant_artifactory(c.config_value)]
            
            # Check NPM packages
            elif finding_type == 'node_package' or 'npm' in finding_type.lower():
                ecosystem = 'npm'
                npm_configs = runtime_configs.get('npm', [])
                
                if npm_configs:
                    compliant_configs = [c for c in npm_configs if self.config_enumerator.is_compliant_artifactory(c.config_value)]
            
            # Check Maven dependencies
            elif finding_type == 'maven_pom' or 'maven' in finding_type.lower():
                ecosystem = 'maven'
                maven_configs = runtime_configs.get('maven', [])
                
                if maven_configs:
                    compliant_configs = [c for c in maven_configs if self.config_enumerator.is_compliant_artifactory(c.config_value)]
            
            # If we found compliant runtime config, group this finding
            if compliant_configs and ecosystem:
                group_key = f"{ecosystem}:{file_path}:{compliant_configs[0].config_value}"
                
                # Extract component name from finding
                component_name = 'unknown'
                if 'component' in finding:
                    component_name = finding['component']
                else:
                    # Try to extract from issue text (e.g., "Python package requests not using...")
                    issue_text = finding.get('issue', '')
                    if 'package ' in issue_text:
                        parts = issue_text.split('package ')
                        if len(parts) > 1:
                            component_name = parts[1].split(' ')[0]
                
                if group_key not in runtime_validated_groups:
                    # Create a new grouped finding
                    ecosystem_label = {
                        'python': 'Python',
                        'go': 'Go',
                        'npm': 'NPM',
                        'maven': 'Maven'
                    }.get(ecosystem, ecosystem.upper())
                    
                    config_type = {
                        'python': 'PyPI index',
                        'go': 'GOPROXY',
                        'npm': 'NPM registry',
                        'maven': 'Maven mirror'
                    }.get(ecosystem, 'configuration')
                    
                    # Generate proper recommended action based on ecosystem
                    if ecosystem == 'python':
                        recommended_action = f"Add --index-url http://{self.artifactory_base}/{self.virtual_repos.get('pypi', 'isgedge-pypi-virtual')}/simple to pip install commands or add to pip.conf"
                    elif ecosystem == 'npm':
                        recommended_action = f"Add registry=http://{self.artifactory_base}/{self.virtual_repos.get('npm', 'isgedge-npm-virtual')}/ to .npmrc"
                    elif ecosystem == 'go':
                        recommended_action = f"Set GOPROXY=http://{self.artifactory_base}/{self.virtual_repos.get('go', 'isgedge-go-virtual')}"
                    elif ecosystem == 'maven':
                        recommended_action = f"Add mirror configuration for http://{self.artifactory_base}/{self.virtual_repos.get('maven', 'isgedge-maven-virtual')} to settings.xml"
                    else:
                        recommended_action = f"{ecosystem_label} components validated as compliant via runtime configuration"
                    
                    runtime_validated_groups[group_key] = {
                        'status': 'compliant_via_runtime_config',
                        'severity': 'INFO',
                        'type': finding_type,
                        'file': file_path,
                        'issue': f"Runtime {config_type} found: {compliant_configs[0].config_value}",
                        'original_severity': finding.get('severity', 'HIGH'),
                        'original_issue': finding.get('issue', ''),
                        'recommended_action': recommended_action,
                        'impact': f"1 component validated",
                        'component_count': 1,
                        'components': [component_name],
                        'runtime_evidence': [
                            {
                                'source': c.source_type,
                                'location': c.source_location,
                                'value': c.config_value,
                                'evidence': c.evidence[:500] if len(c.evidence) > 500 else c.evidence,
                                'confidence': c.confidence,
                                'timestamp': c.timestamp.isoformat()
                            }
                            for c in compliant_configs
                        ],
                        'validation_instructions': self._generate_validation_instructions(compliant_configs[0]),
                        'source': finding.get('source', 'basic_scanner')
                    }
                else:
                    # Add to existing group
                    group = runtime_validated_groups[group_key]
                    group['component_count'] += 1
                    group['components'].append(component_name)
                    group['impact'] = f"{group['component_count']} components validated"
            else:
                # No runtime validation or non-compliant - keep original finding
                validated_findings.append(finding)
        
        # Add all grouped runtime-validated findings
        for group in runtime_validated_groups.values():
            validated_findings.append(group)
        
        # Count how many were downgraded
        downgraded_count = sum(g['component_count'] for g in runtime_validated_groups.values())
        print(f"Downgraded {downgraded_count} findings to INFO based on runtime configuration evidence")
        print(f"Consolidated into {len(runtime_validated_groups)} grouped finding(s)")
        
        return validated_findings
    
    def _generate_validation_instructions(self, config: RuntimeConfiguration) -> str:
        """Generate validation instructions for a runtime configuration"""
        if config.source_type == 'jenkins_log':
            return f"To validate: Check Jenkins build log at {config.source_location}. Look for pip install output showing 'Looking in indexes:' with the Artifactory URL."
        elif config.source_type == 'jenkins_job':
            return f"To validate: Review Jenkins job configuration for {config.source_location}. Check environment variables section."
        elif config.source_type == 'dockerfile':
            return f"To validate: View {config.source_location} in the repository. Check for ENV or ARG declarations."
        elif config.source_type == 'repo_file':
            return f"To validate: View {config.source_location} in the repository."
        else:
            return f"To validate: Check {config.source_type} at {config.source_location}"
    
    def _calculate_reliability_metrics(self, runtime_configs: Dict[str, List[RuntimeConfiguration]], 
                                       total_packages: int) -> Dict:
        """Calculate reliability metrics for the scan"""
        
        # Count configurations by confidence level
        # When runtime config evidence exists for a package manager, all packages in that ecosystem get credit
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0
        
        for pm, config_list in runtime_configs.items():
            if not config_list:
                continue
            
            # Get the highest confidence level for this package manager
            max_confidence = 'low'
            for config in config_list:
                if config.confidence == 'high':
                    max_confidence = 'high'
                    break
                elif config.confidence == 'medium' and max_confidence != 'high':
                    max_confidence = 'medium'
            
            # Count all packages for this package manager at its highest confidence level
            # This assumes if we have runtime config for pip, all Python packages benefit
            if max_confidence == 'high':
                high_confidence = total_packages  # All packages get high confidence
            elif max_confidence == 'medium' and high_confidence == 0:
                medium_confidence = total_packages
            elif low_confidence == 0 and medium_confidence == 0:
                low_confidence = total_packages
        
        packages_with_evidence = min(total_packages, high_confidence + medium_confidence + low_confidence)
        no_evidence = max(0, total_packages - packages_with_evidence)
        
        # Calculate weighted reliability score (capped at 100%)
        if total_packages == 0:
            reliability_score = 0.0
        else:
            weighted_score = (
                (high_confidence * 1.0) +
                (medium_confidence * 0.7) +
                (low_confidence * 0.4)
            ) / total_packages
            
            reliability_score = min(100.0, round(weighted_score * 100, 2))
        
        # Generate recommendation
        if reliability_score >= 80:
            recommendation = f"High reliability. {reliability_score}% of packages have traceable configuration evidence."
        elif reliability_score >= 50:
            recommendation = f"Medium reliability. {reliability_score}% of packages have configuration evidence. Consider enabling Jenkins log analysis for higher confidence."
        else:
            recommendation = f"Low reliability. Only {reliability_score}% of packages have configuration evidence. Enable Jenkins integration and build log analysis for better results."
        
        return {
            'reliability_score': reliability_score,
            'total_packages': total_packages,
            'packages_with_evidence': packages_with_evidence,
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': low_confidence,
            'no_evidence': no_evidence,
            'recommendation': recommendation
        }
    
    def _serialize_runtime_configs(self, runtime_configs: Dict[str, List[RuntimeConfiguration]]) -> Dict:
        """Serialize runtime configurations for JSON output"""
        serialized = {}
        
        for pm, config_list in runtime_configs.items():
            serialized[pm] = [config.to_dict() for config in config_list]
        
        return serialized
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def export_report(self, report: Dict, output_file: str):
        """Export comprehensive report to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report exported to: {output_path}")
    
    def generate_summary_text(self, report: Dict) -> str:
        """Generate human-readable summary text"""
        summary = f"""
OSS COMPLIANCE SCAN REPORT
Repository: {report['summary']['repository_name']}
Scan Date: {report['summary']['scan_timestamp']}

=== OVERALL COMPLIANCE ===
Total Components: {report['summary']['component_analysis']['total_components']}
Compliant: {report['summary']['component_analysis']['compliant_components']} ({report['summary']['component_analysis']['component_compliance_percentage']}%)
Non-Compliant: {report['summary']['component_analysis']['non_compliant_components']}
Warnings: {report['summary']['component_analysis']['warning_components']}

=== ENDPOINT ANALYSIS ===
Total Endpoint Configurations: {report['summary']['endpoint_summary']['total_configurations']}
Proxied Components: {report['proxy_analysis']['proxied_components']}
Direct Public: {report['proxy_analysis']['direct_public_components']}
Direct Private: {report['proxy_analysis']['direct_private_components']}
Proxy Effectiveness: {report['proxy_analysis']['proxy_effectiveness']}%

=== RELIABILITY METRICS ===
Reliability Score: {report.get('reliability_metrics', {}).get('reliability_score', 0)}%
Packages with Evidence: {report.get('reliability_metrics', {}).get('packages_with_evidence', 0)}/{report.get('reliability_metrics', {}).get('total_packages', 0)}
High Confidence: {report.get('reliability_metrics', {}).get('high_confidence', 0)}
Medium Confidence: {report.get('reliability_metrics', {}).get('medium_confidence', 0)}
Low Confidence: {report.get('reliability_metrics', {}).get('low_confidence', 0)}
{report.get('reliability_metrics', {}).get('recommendation', '')}

=== ARTIFACTORY SERVERS DETECTED ===
"""
        
        for server in report.get('artifactory_servers_detected', []):
            summary += f"\n{server['server']}\n"
            summary += f"  Package Managers: {', '.join(server['package_managers'])}\n"
            summary += f"  Repositories: {', '.join(server['repositories'])}\n"
            summary += f"  Evidence Count: {server['evidence_count']}\n"
        
        summary += "\n=== CRITICAL ISSUES ===\n"
        
        if report['critical_issues']:
            for issue in report['critical_issues']:
                summary += f"\n[{issue['severity']}] {issue['issue']}\n"
                summary += f"  {issue['description']}\n"
                summary += f"  Recommendation: {issue['recommendation']}\n"
        else:
            summary += "No critical issues found.\n"
        
        summary += "\n=== TOP RECOMMENDATIONS ===\n"
        for i, rec in enumerate(report['recommendations'][:3], 1):
            summary += f"\n{i}. [{rec['priority']}] {rec['category']}\n"
            summary += f"   Issue: {rec['issue']}\n"
            summary += f"   Action: {rec['action']}\n"
        
        return summary
    
    def _generate_optimization_opportunities(self, endpoint_report: Dict, runtime_configs: Dict) -> Dict:
        """
        Generate optimization opportunities summary for suboptimal configurations
        
        Identifies components that are compliant but using suboptimal configurations
        (e.g., wrong Artifactory server or non-virtual repositories)
        """
        opportunities = {
            'total_suboptimal': 0,
            'by_issue_type': {},
            'by_ecosystem': {}
        }
        
        # Analyze each ecosystem's runtime configs
        for ecosystem, configs in runtime_configs.items():
            if not configs:
                continue
            
            ecosystem_opportunities = {
                'optimal_count': 0,
                'suboptimal_count': 0,
                'issues': []
            }
            
            for config in configs:
                evaluation = self.config_enumerator.evaluate_compliance_level(
                    config.config_value,
                    ecosystem
                )
                
                if evaluation['level'] == 'compliant_optimal':
                    ecosystem_opportunities['optimal_count'] += 1
                elif evaluation['level'] == 'compliant_warn':
                    ecosystem_opportunities['suboptimal_count'] += 1
                    opportunities['total_suboptimal'] += 1
                    
                    # Categorize the issue
                    for note in evaluation['improvement_notes']:
                        if 'artifactory instead of approved' in note:
                            issue_type = 'wrong_artifactory_server'
                            if issue_type not in opportunities['by_issue_type']:
                                opportunities['by_issue_type'][issue_type] = {
                                    'count': 0,
                                    'affected_ecosystems': set(),
                                    'current_server': evaluation['server'],
                                    'recommended_server': self.artifactory_base.split('.')[0],
                                    'impact': 'Standardize on approved Artifactory server'
                                }
                            opportunities['by_issue_type'][issue_type]['count'] += 1
                            opportunities['by_issue_type'][issue_type]['affected_ecosystems'].add(ecosystem)
                        
                        elif 'instead of approved virtual repo' in note:
                            issue_type = 'non_virtual_repository'
                            if issue_type not in opportunities['by_issue_type']:
                                opportunities['by_issue_type'][issue_type] = {
                                    'count': 0,
                                    'affected_ecosystems': set(),
                                    'examples': []
                                }
                            opportunities['by_issue_type'][issue_type]['count'] += 1
                            opportunities['by_issue_type'][issue_type]['affected_ecosystems'].add(ecosystem)
                            opportunities['by_issue_type'][issue_type]['examples'].append({
                                'ecosystem': ecosystem,
                                'current': evaluation['repository'],
                                'recommended': self.virtual_repos.get(ecosystem, f'isgedge-{ecosystem}-virtual'),
                                'benefit': 'Use virtual repository for better caching and control'
                            })
            
            if ecosystem_opportunities['suboptimal_count'] > 0:
                opportunities['by_ecosystem'][ecosystem] = ecosystem_opportunities
        
        # Convert sets to lists for JSON serialization
        for issue_type, data in opportunities['by_issue_type'].items():
            if 'affected_ecosystems' in data:
                data['affected_ecosystems'] = list(data['affected_ecosystems'])
        
        # Add estimated improvement message
        if opportunities['total_suboptimal'] > 0:
            opportunities['estimated_improvement'] = f"{opportunities['total_suboptimal']} components can be upgraded to best practice"
        
        return opportunities


def main():
    """Main entry point for standalone execution"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python enhanced_scanner.py <repo_path> [output_file]")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'compliance_report.json'
    
    # Initialize scanner
    scanner = ComplianceScanner(repo_path)
    
    # Run comprehensive scan
    report = scanner.scan_comprehensive()
    
    # Export report
    scanner.export_report(report, output_file)
    
    # Print summary
    print("\n" + "="*80)
    print(scanner.generate_summary_text(report))
    print("="*80)


if __name__ == '__main__':
    main()
