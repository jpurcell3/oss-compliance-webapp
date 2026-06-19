#!/usr/bin/env python3
"""
Enhanced Endpoint Analyzer for OSS Compliance Scanner
Provides detailed enumeration of OSS components, their configured endpoints,
and proxy/translation mechanisms in both repository files and Jenkins pipelines.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class EndpointType(Enum):
    """Types of endpoints that can be configured"""
    DIRECT_PUBLIC = "direct_public"  # Direct to public registry (github.com, npmjs.org, etc.)
    INTERNAL = "internal"  # Internal trusted sources (eos2git, etc.)
    PROXIED = "proxied"  # Through Artifactory or other proxy
    TRANSLATED = "translated"  # URL rewriting/translation configured
    RUNTIME_CONFIGURED = "runtime_configured"  # Environment variable or runtime configuration
    UNKNOWN = "unknown"


class ConfigurationLocation(Enum):
    """Where the configuration is defined"""
    REPO_FILE = "repository_file"  # In go.mod, requirements.txt, etc.
    DOCKERFILE = "dockerfile"  # In Dockerfile
    MAKEFILE = "makefile"  # In Makefile
    JENKINSFILE = "jenkinsfile"  # In Jenkinsfile
    JENKINS_SHARED_LIB = "jenkins_shared_library"  # In Jenkins shared library
    ENV_VAR = "environment_variable"  # Environment variable
    GIT_CONFIG = "git_config"  # Git URL rewriting
    UNKNOWN = "unknown"


@dataclass
class OSSComponent:
    """Represents a single OSS component/dependency"""
    name: str
    version: Optional[str]
    ecosystem: str  # go, python, npm, maven, docker, etc.
    source_file: str
    line_number: Optional[int] = None


@dataclass
class EndpointConfiguration:
    """Represents how an endpoint is configured"""
    endpoint_url: str
    endpoint_type: EndpointType
    config_location: ConfigurationLocation
    config_file: str
    config_line: Optional[int] = None
    config_snippet: Optional[str] = None
    is_compliant: bool = False
    notes: Optional[str] = None


@dataclass
class ComponentEndpointMapping:
    """Maps an OSS component to its endpoint configuration"""
    component: OSSComponent
    declared_endpoint: Optional[str]  # What's in the dependency file
    actual_endpoint: EndpointConfiguration  # How it's actually resolved
    proxy_chain: List[EndpointConfiguration]  # Chain of proxies/translations
    compliance_status: str  # "compliant", "non_compliant", "warning"
    recommendations: List[str]


class EndpointAnalyzer:
    """
    Analyzes OSS components and their endpoint configurations across
    repository files, Dockerfiles, Makefiles, and Jenkins pipelines.
    """
    
    def __init__(self, repo_root: str, artifactory_base: str = None):
        self.repo_root = Path(repo_root)
        self.artifactory_base = artifactory_base or 'isgedge.artifactory.cec.lab.emc.com'
        self.components: List[OSSComponent] = []
        self.endpoint_configs: List[EndpointConfiguration] = []
        self.mappings: List[ComponentEndpointMapping] = []
        
    def analyze_repository(self) -> Dict:
        """
        Perform comprehensive endpoint analysis of the repository.
        Returns detailed mapping of components to endpoints.
        """
        print(f"Starting endpoint analysis for: {self.repo_root}")
        
        # Step 1: Enumerate all OSS components
        self._enumerate_oss_components()
        
        # Step 2: Discover all endpoint configurations
        self._discover_endpoint_configurations()
        
        # Step 3: Map components to their actual endpoints
        self._map_components_to_endpoints()
        
        # Step 4: Analyze proxy/translation chains
        self._analyze_proxy_chains()
        
        # Step 5: Generate detailed report
        return self._generate_detailed_report()
    
    def _enumerate_oss_components(self):
        """Enumerate all OSS components from dependency files"""
        print("Enumerating OSS components...")
        
        # Go modules
        self._enumerate_go_modules()
        
        # Python packages
        self._enumerate_python_packages()
        
        # NPM packages
        self._enumerate_npm_packages()
        
        # Maven dependencies
        self._enumerate_maven_dependencies()
        
        # Docker images
        self._enumerate_docker_images()
        
        print(f"Found {len(self.components)} OSS components")
    
    def _enumerate_go_modules(self):
        """Enumerate Go modules from go.mod files"""
        for go_mod in self.repo_root.rglob('go.mod'):
            try:
                content = go_mod.read_text()
                lines = content.split('\n')
                
                in_require = False
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    if line.startswith('require ('):
                        in_require = True
                        continue
                    elif line == ')':
                        in_require = False
                        continue
                    
                    # Parse require block or single require
                    if (in_require or line.startswith('require ')) and line and not line.startswith('//'):
                        # Extract module name and version
                        parts = line.replace('require ', '').strip().split()
                        if len(parts) >= 2:
                            module_name = parts[0]
                            version = parts[1]
                            
                            self.components.append(OSSComponent(
                                name=module_name,
                                version=version,
                                ecosystem='go',
                                source_file=str(go_mod.relative_to(self.repo_root)),
                                line_number=line_num
                            ))
            except Exception as e:
                print(f"Error parsing {go_mod}: {e}")
    
    def _enumerate_python_packages(self):
        """Enumerate Python packages from requirements.txt files"""
        for req_file in self.repo_root.rglob('requirements.txt'):
            try:
                content = req_file.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    # Skip comments, empty lines, and pip options
                    if not line or line.startswith('#') or line.startswith('-'):
                        continue
                    
                    # Parse package name and version
                    # Handle various formats: package==1.0.0, package>=1.0.0, package, git+https://...
                    if line.startswith('git+') or line.startswith('https://'):
                        # Direct URL install
                        self.components.append(OSSComponent(
                            name=line,
                            version=None,
                            ecosystem='python',
                            source_file=str(req_file.relative_to(self.repo_root)),
                            line_number=line_num
                        ))
                    else:
                        # Regular package
                        match = re.match(r'^([a-zA-Z0-9_\-\.]+)([<>=!~]+.*)?$', line)
                        if match:
                            pkg_name = match.group(1)
                            version_spec = match.group(2) if match.group(2) else None
                            
                            self.components.append(OSSComponent(
                                name=pkg_name,
                                version=version_spec,
                                ecosystem='python',
                                source_file=str(req_file.relative_to(self.repo_root)),
                                line_number=line_num
                            ))
            except Exception as e:
                print(f"Error parsing {req_file}: {e}")
    
    def _enumerate_npm_packages(self):
        """Enumerate NPM packages from package.json files"""
        for pkg_file in self.repo_root.rglob('package.json'):
            try:
                content = json.loads(pkg_file.read_text())
                
                # Collect all dependency types
                dep_types = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']
                
                for dep_type in dep_types:
                    if dep_type in content:
                        for pkg_name, version in content[dep_type].items():
                            self.components.append(OSSComponent(
                                name=pkg_name,
                                version=version,
                                ecosystem='npm',
                                source_file=str(pkg_file.relative_to(self.repo_root)),
                                line_number=None  # JSON doesn't have line numbers easily
                            ))
            except Exception as e:
                print(f"Error parsing {pkg_file}: {e}")
    
    def _enumerate_maven_dependencies(self):
        """Enumerate Maven dependencies from pom.xml files"""
        for pom_file in self.repo_root.rglob('pom.xml'):
            try:
                content = pom_file.read_text()
                
                # Parse Maven dependencies using regex
                dep_pattern = re.compile(
                    r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*(?:<version>([^<]+)</version>)?',
                    re.IGNORECASE | re.DOTALL
                )
                
                for match in dep_pattern.finditer(content):
                    group_id = match.group(1).strip()
                    artifact_id = match.group(2).strip()
                    version = match.group(3).strip() if match.group(3) else None
                    
                    self.components.append(OSSComponent(
                        name=f"{group_id}:{artifact_id}",
                        version=version,
                        ecosystem='maven',
                        source_file=str(pom_file.relative_to(self.repo_root)),
                        line_number=None
                    ))
            except Exception as e:
                print(f"Error parsing {pom_file}: {e}")
    
    def _enumerate_docker_images(self):
        """Enumerate Docker images from Dockerfiles"""
        for dockerfile in self.repo_root.rglob('Dockerfile*'):
            try:
                content = dockerfile.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Look for FROM statements
                    if line.strip().startswith('FROM'):
                        match = re.match(r'FROM\s+(?:\$\{[^}]+\}/)?([^\s]+)', line.strip())
                        if match:
                            image = match.group(1)
                            
                            # Parse image name and tag
                            if ':' in image:
                                image_name, tag = image.rsplit(':', 1)
                            else:
                                image_name, tag = image, 'latest'
                            
                            self.components.append(OSSComponent(
                                name=image_name,
                                version=tag,
                                ecosystem='docker',
                                source_file=str(dockerfile.relative_to(self.repo_root)),
                                line_number=line_num
                            ))
            except Exception as e:
                print(f"Error parsing {dockerfile}: {e}")
    
    def _discover_endpoint_configurations(self):
        """Discover all endpoint configurations in the repository"""
        print("Discovering endpoint configurations...")
        
        # Check Dockerfiles for GOPROXY, pip index, npm registry, etc.
        self._discover_dockerfile_configs()
        
        # Check Makefiles for repository URLs
        self._discover_makefile_configs()
        
        # Check Jenkinsfiles for environment variables and configurations
        self._discover_jenkinsfile_configs()
        
        # Check for .npmrc, .pypirc, etc.
        self._discover_config_files()
        
        # Check go.mod for replace directives
        self._discover_go_replace_directives()
        
        print(f"Found {len(self.endpoint_configs)} endpoint configurations")
    
    def get_current_proxy_configurations(self) -> Dict[str, Dict]:
        """
        Summarize current proxy configurations for each ecosystem
        Returns dict with ecosystem -> current config details
        """
        current_configs = {
            'go': {'proxy': None, 'private': None, 'config_files': []},
            'python': {'proxy': None, 'index_url': None, 'config_files': []},
            'npm': {'registry': None, 'config_files': []},
            'maven': {'proxy': None, 'config_files': []},
            'docker': {'registry': None, 'config_files': []}
        }
        
        for config in self.endpoint_configs:
            # Extract ecosystem-specific configurations
            if 'GOPROXY' in config.config_snippet or config.endpoint_type == EndpointType.PROXIED:
                if config.endpoint_url and 'go' in config.endpoint_url.lower():
                    current_configs['go']['proxy'] = config.endpoint_url
                    current_configs['go']['config_files'].append(config.config_file)
            
            if 'GOPRIVATE' in config.config_snippet:
                current_configs['go']['private'] = config.endpoint_url
                current_configs['go']['config_files'].append(config.config_file)
            
            if 'PIP_INDEX_URL' in config.config_snippet or 'index-url' in config.config_snippet:
                current_configs['python']['index_url'] = config.endpoint_url
                current_configs['python']['config_files'].append(config.config_file)
            
            if 'NPM_CONFIG_REGISTRY' in config.config_snippet or 'npm_config_registry' in config.config_snippet:
                current_configs['npm']['registry'] = config.endpoint_url
                current_configs['npm']['config_files'].append(config.config_file)
        
        return current_configs
    
    def _discover_dockerfile_configs(self):
        """Discover endpoint configurations in Dockerfiles"""
        for dockerfile in self.repo_root.rglob('Dockerfile*'):
            try:
                content = dockerfile.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Look for GOPROXY configuration
                    if 'GOPROXY' in line_stripped:
                        match = re.search(r'GOPROXY[=\s]+["\']?([^"\'\s]+)["\']?', line_stripped)
                        if match:
                            goproxy_url = match.group(1)
                            
                            endpoint_type = self._classify_endpoint(goproxy_url)
                            
                            self.endpoint_configs.append(EndpointConfiguration(
                                endpoint_url=goproxy_url,
                                endpoint_type=endpoint_type,
                                config_location=ConfigurationLocation.DOCKERFILE,
                                config_file=str(dockerfile.relative_to(self.repo_root)),
                                config_line=line_num,
                                config_snippet=line_stripped,
                                is_compliant=self.artifactory_base in goproxy_url
                            ))
                    
                    # Look for GOPRIVATE configuration
                    if 'GOPRIVATE' in line_stripped:
                        match = re.search(r'GOPRIVATE[=\s]+["\']?([^"\'\s]+)["\']?', line_stripped)
                        if match:
                            goprivate = match.group(1)
                            
                            # GOPRIVATE indicates direct access (bypass proxy)
                            for domain in goprivate.split(','):
                                domain = domain.strip()
                                self.endpoint_configs.append(EndpointConfiguration(
                                    endpoint_url=domain,
                                    endpoint_type=EndpointType.INTERNAL if 'eos2git' in domain or 'internal' in domain else EndpointType.DIRECT_PUBLIC,
                                    config_location=ConfigurationLocation.DOCKERFILE,
                                    config_file=str(dockerfile.relative_to(self.repo_root)),
                                    config_line=line_num,
                                    config_snippet=line_stripped,
                                    is_compliant='github.com' not in domain,  # github.com in GOPRIVATE is non-compliant
                                    notes=f"GOPRIVATE bypasses proxy for {domain}"
                                ))
                    
                    # Look for git config URL rewriting
                    if 'git config' in line_stripped and 'url.' in line_stripped:
                        match = re.search(r'url\."([^"]+)"\s*\.insteadOf\s*"([^"]+)"', line_stripped)
                        if match:
                            new_url = match.group(1)
                            old_url = match.group(2)
                            
                            self.endpoint_configs.append(EndpointConfiguration(
                                endpoint_url=new_url,
                                endpoint_type=EndpointType.TRANSLATED,
                                config_location=ConfigurationLocation.GIT_CONFIG,
                                config_file=str(dockerfile.relative_to(self.repo_root)),
                                config_line=line_num,
                                config_snippet=line_stripped,
                                is_compliant=True,
                                notes=f"Translates {old_url} -> {new_url}"
                            ))
                    
                    # Look for pip index-url
                    if 'PIP_INDEX_URL' in line_stripped or 'index-url' in line_stripped:
                        match = re.search(r'(?:PIP_INDEX_URL|index-url)[=\s]+["\']?([^"\'\s]+)["\']?', line_stripped)
                        if match:
                            pip_url = match.group(1)
                            
                            endpoint_type = self._classify_endpoint(pip_url)
                            
                            self.endpoint_configs.append(EndpointConfiguration(
                                endpoint_url=pip_url,
                                endpoint_type=endpoint_type,
                                config_location=ConfigurationLocation.DOCKERFILE,
                                config_file=str(dockerfile.relative_to(self.repo_root)),
                                config_line=line_num,
                                config_snippet=line_stripped,
                                is_compliant=self.artifactory_base in pip_url
                            ))
                    
                    # Look for npm registry
                    if 'NPM_CONFIG_REGISTRY' in line_stripped or 'npm_config_registry' in line_stripped:
                        match = re.search(r'(?:NPM_CONFIG_REGISTRY|npm_config_registry)[=\s]+["\']?([^"\'\s]+)["\']?', line_stripped)
                        if match:
                            npm_url = match.group(1)
                            
                            endpoint_type = self._classify_endpoint(npm_url)
                            
                            self.endpoint_configs.append(EndpointConfiguration(
                                endpoint_url=npm_url,
                                endpoint_type=endpoint_type,
                                config_location=ConfigurationLocation.DOCKERFILE,
                                config_file=str(dockerfile.relative_to(self.repo_root)),
                                config_line=line_num,
                                config_snippet=line_stripped,
                                is_compliant=self.artifactory_base in npm_url
                            ))
                    
            except Exception as e:
                print(f"Error analyzing {dockerfile}: {e}")
    
    def _discover_makefile_configs(self):
        """Discover endpoint configurations in Makefiles"""
        for makefile in self.repo_root.rglob('Makefile*'):
            try:
                content = makefile.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Look for curl/wget commands with URLs
                    url_match = re.search(r'(?:curl|wget)[^;]*?(https?://[^\s\'"]+)', line)
                    if url_match:
                        url = url_match.group(1)
                        
                        endpoint_type = self._classify_endpoint(url)
                        
                        self.endpoint_configs.append(EndpointConfiguration(
                            endpoint_url=url,
                            endpoint_type=endpoint_type,
                            config_location=ConfigurationLocation.MAKEFILE,
                            config_file=str(makefile.relative_to(self.repo_root)),
                            config_line=line_num,
                            config_snippet=line.strip(),
                            is_compliant=self.artifactory_base in url
                        ))
            except Exception as e:
                print(f"Error analyzing {makefile}: {e}")
    
    def _discover_jenkinsfile_configs(self):
        """Discover endpoint configurations in Jenkinsfiles"""
        for jenkinsfile in self.repo_root.rglob('Jenkinsfile*'):
            try:
                content = jenkinsfile.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Look for environment blocks with repository configurations
                    if any(keyword in line_stripped for keyword in ['GOPROXY', 'PIP_INDEX_URL', 'NPM_CONFIG_REGISTRY', 'ARTIFACTORY']):
                        # Extract the configuration
                        match = re.search(r'(\w+)\s*=\s*["\']([^"\']+)["\']', line_stripped)
                        if match:
                            var_name = match.group(1)
                            var_value = match.group(2)
                            
                            endpoint_type = self._classify_endpoint(var_value)
                            
                            self.endpoint_configs.append(EndpointConfiguration(
                                endpoint_url=var_value,
                                endpoint_type=endpoint_type,
                                config_location=ConfigurationLocation.JENKINSFILE,
                                config_file=str(jenkinsfile.relative_to(self.repo_root)),
                                config_line=line_num,
                                config_snippet=line_stripped,
                                is_compliant=self.artifactory_base in var_value,
                                notes=f"Jenkins environment variable: {var_name}"
                            ))
            except Exception as e:
                print(f"Error analyzing {jenkinsfile}: {e}")
    
    def _discover_config_files(self):
        """Discover endpoint configurations in config files like .npmrc, .pypirc, etc."""
        config_files = [
            ('.npmrc', 'npm'),
            ('.pypirc', 'python'),
            ('.pip/pip.conf', 'python'),
            ('pip.conf', 'python'),
        ]
        
        for config_pattern, ecosystem in config_files:
            for config_file in self.repo_root.rglob(config_pattern):
                try:
                    content = config_file.read_text()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        # Look for registry/index URLs
                        url_match = re.search(r'(?:registry|index-url)\s*[=:]\s*([^\s]+)', line)
                        if url_match:
                            url = url_match.group(1)
                            
                            endpoint_type = self._classify_endpoint(url)
                            
                            self.endpoint_configs.append(EndpointConfiguration(
                                endpoint_url=url,
                                endpoint_type=endpoint_type,
                                config_location=ConfigurationLocation.REPO_FILE,
                                config_file=str(config_file.relative_to(self.repo_root)),
                                config_line=line_num,
                                config_snippet=line.strip(),
                                is_compliant=self.artifactory_base in url
                            ))
                except Exception as e:
                    print(f"Error analyzing {config_file}: {e}")
    
    def _discover_go_replace_directives(self):
        """Discover Go module replace directives that redirect dependencies"""
        for go_mod in self.repo_root.rglob('go.mod'):
            try:
                content = go_mod.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith('replace '):
                        # Parse replace directive: replace old => new version
                        match = re.match(r'replace\s+([^\s]+)\s+=>\s+([^\s]+)', line.strip())
                        if match:
                            old_module = match.group(1)
                            new_module = match.group(2)
                            
                            self.endpoint_configs.append(EndpointConfiguration(
                                endpoint_url=new_module,
                                endpoint_type=EndpointType.TRANSLATED,
                                config_location=ConfigurationLocation.REPO_FILE,
                                config_file=str(go_mod.relative_to(self.repo_root)),
                                config_line=line_num,
                                config_snippet=line.strip(),
                                is_compliant=True,
                                notes=f"Replaces {old_module} with {new_module}"
                            ))
            except Exception as e:
                print(f"Error analyzing {go_mod}: {e}")
    
    def _classify_endpoint(self, url: str) -> EndpointType:
        """Classify an endpoint URL by type"""
        url_lower = url.lower()
        
        # Check if it's an environment variable or runtime configuration
        if any(pattern in url for pattern in ['${', '$', '%', '__']):
            return EndpointType.RUNTIME_CONFIGURED
        
        # Check if it's the configured Artifactory
        if self.artifactory_base.lower() in url_lower:
            return EndpointType.PROXIED
        
        # Check if it's another artifactory/proxy
        if 'artifactory' in url_lower or 'nexus' in url_lower or 'jfrog' in url_lower:
            return EndpointType.PROXIED
        
        # Check if it's internal/private
        if any(keyword in url_lower for keyword in ['eos2git', 'internal', 'corp', 'enterprise']):
            return EndpointType.INTERNAL
        
        # Check if it's public
        if any(keyword in url_lower for keyword in ['github.com', 'npmjs.org', 'pypi.org', 'maven.org', 'golang.org']):
            return EndpointType.DIRECT_PUBLIC
        
        return EndpointType.UNKNOWN
    
    def _map_components_to_endpoints(self):
        """Map each OSS component to its actual endpoint configuration"""
        print("Mapping components to endpoints...")
        
        for component in self.components:
            # Determine the declared endpoint (from the component name/source)
            declared_endpoint = self._get_declared_endpoint(component)
            
            # Find the actual endpoint configuration that applies
            actual_endpoint = self._find_applicable_endpoint(component)
            
            # Determine compliance status
            compliance_status = self._determine_compliance(component, actual_endpoint)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(component, actual_endpoint, compliance_status)
            
            mapping = ComponentEndpointMapping(
                component=component,
                declared_endpoint=declared_endpoint,
                actual_endpoint=actual_endpoint,
                proxy_chain=[],  # Will be filled in next step
                compliance_status=compliance_status,
                recommendations=recommendations
            )
            
            self.mappings.append(mapping)
    
    def _get_declared_endpoint(self, component: OSSComponent) -> Optional[str]:
        """Extract the declared endpoint from the component name"""
        if component.ecosystem == 'go':
            # Go modules have the domain in the module name
            parts = component.name.split('/')
            if len(parts) > 0:
                return parts[0]
        elif component.ecosystem == 'python':
            if component.name.startswith('git+') or component.name.startswith('https://'):
                return component.name
            else:
                return 'pypi.org'  # Default PyPI
        elif component.ecosystem == 'npm':
            return 'npmjs.org'  # Default npm registry
        elif component.ecosystem == 'maven':
            return 'maven.org'  # Default Maven Central
        elif component.ecosystem == 'docker':
            if '/' in component.name:
                return component.name.split('/')[0]
            else:
                return 'docker.io'  # Default Docker Hub
        
        return None
    
    def _find_applicable_endpoint(self, component: OSSComponent) -> EndpointConfiguration:
        """Find the endpoint configuration that applies to this component"""
        # Special case: If component is from trusted internal source (eos2git),
        # use the declared endpoint regardless of any general ecosystem config
        if self._is_trusted_source(component):
            declared_endpoint = self._get_declared_endpoint(component) or 'unknown'
            endpoint_type = self._classify_endpoint(declared_endpoint)
            
            return EndpointConfiguration(
                endpoint_url=declared_endpoint,
                endpoint_type=endpoint_type,
                config_location=ConfigurationLocation.REPO_FILE,
                config_file=component.source_file or 'unknown',
                is_compliant=True,
                notes=f'Internal trusted source: {declared_endpoint}'
            )
        
        # Look for ecosystem-specific configurations
        ecosystem_configs = {
            'go': ['GOPROXY', 'GOPRIVATE'],
            'python': ['PIP_INDEX_URL', 'index-url'],
            'npm': ['NPM_CONFIG_REGISTRY', 'npm_config_registry'],
            'maven': ['maven'],
            'docker': ['DOCKER', 'docker']
        }
        
        keywords = ecosystem_configs.get(component.ecosystem, [])
        
        # Find matching endpoint configurations
        for config in self.endpoint_configs:
            # Check if this config applies to this ecosystem
            if any(keyword.lower() in config.config_snippet.lower() for keyword in keywords):
                return config
        
        # No specific config found - return default based on declared endpoint
        declared_endpoint = self._get_declared_endpoint(component) or 'unknown'
        
        # Determine endpoint type based on the declared endpoint
        endpoint_type = self._classify_endpoint(declared_endpoint)
        
        # Check if this is a trusted internal source
        is_compliant = self._is_trusted_source(component)
        
        return EndpointConfiguration(
            endpoint_url=declared_endpoint,
            endpoint_type=endpoint_type,
            config_location=ConfigurationLocation.UNKNOWN,
            config_file='none',
            is_compliant=is_compliant,
            notes='No explicit endpoint configuration found - using defaults'
        )
    
    def _determine_compliance(self, component: OSSComponent, endpoint: EndpointConfiguration) -> str:
        """Determine if the component's endpoint configuration is compliant"""
        # Priority 1: Check if endpoint is explicitly compliant (Artifactory)
        if endpoint.is_compliant:
            return 'compliant'
        
        # Priority 2: Check if component is from trusted Dell sources
        if self._is_trusted_source(component):
            return 'compliant'
        
        # Priority 3: Check for GOPRIVATE misconfiguration FIRST (overrides proxy check)
        if component.ecosystem == 'go' and 'github.com' in component.name:
            if self._is_goprivate_misconfigured():
                return 'non_compliant'
        
        # Priority 4: Check if proxy is configured for this ecosystem
        if self._has_proxy_configured(component.ecosystem):
            return 'compliant'
        
        # Priority 5: Check for git URL rewriting to internal sources
        if self._has_url_rewriting_to_internal(component):
            return 'compliant'
        
        # Priority 6: Public endpoints without explicit proxy configuration are non-compliant
        if endpoint.endpoint_type == EndpointType.DIRECT_PUBLIC:
            return 'non_compliant'
        
        return 'warning'
    
    def _is_trusted_source(self, component: OSSComponent) -> bool:
        """Check if component is from a trusted Dell/EMC internal source"""
        component_name_lower = component.name.lower()
        
        # Check for Dell/EMC internal domains (any subdomain)
        trusted_domains = [
            'cec.lab.emc.com',
            '.emc.com',
            '.dell.com'
        ]
        
        for domain in trusted_domains:
            if domain in component_name_lower:
                return True
        
        # Check for Dell Artifactory
        if self.artifactory_base.lower() in component_name_lower:
            return True
        
        # Check for Dell GitHub organizations (must match org exactly, not just github.com)
        trusted_orgs = [
            'github.com/fusion-e/',
            'github.com/isg-edge/'
        ]
        
        for org in trusted_orgs:
            if component_name_lower.startswith(org):
                return True
        
        return False
    
    def _has_proxy_configured(self, ecosystem: str) -> bool:
        """Check if a proxy is configured for the given ecosystem"""
        proxy_indicators = {
            'go': ['GOPROXY'],
            'python': ['PIP_INDEX_URL', 'index-url'],
            'npm': ['NPM_CONFIG_REGISTRY', 'npm_config_registry'],
            'maven': ['maven'],
            'docker': ['DOCKER_REGISTRY']
        }
        
        keywords = proxy_indicators.get(ecosystem, [])
        
        for config in self.endpoint_configs:
            # Check if this config is a proxy (contains artifactory)
            if self.artifactory_base in config.endpoint_url:
                # Check if it applies to this ecosystem
                if any(keyword.lower() in config.config_snippet.lower() for keyword in keywords):
                    return True
        
        return False
    
    def _has_url_rewriting_to_internal(self, component: OSSComponent) -> bool:
        """Check if git URL rewriting redirects to Dell internal sources (eos2git)"""
        for config in self.endpoint_configs:
            if config.endpoint_type == EndpointType.TRANSLATED:
                # Only compliant if rewriting to eos2git (Dell internal)
                # Rewriting github.com -> github.com with token is NOT compliant
                if 'eos2git.cec.lab.emc.com' in config.endpoint_url.lower():
                    # Check if this rewriting applies to the component's source
                    if 'github.com' in component.name.lower():
                        return True
        
        return False
    
    def _is_goprivate_misconfigured(self) -> bool:
        """Check if GOPRIVATE includes github.com (misconfiguration)"""
        for config in self.endpoint_configs:
            if 'GOPRIVATE' in config.config_snippet:
                if 'github.com' in config.endpoint_url:
                    return True
        
        return False
    
    def _generate_recommendations(self, component: OSSComponent, endpoint: EndpointConfiguration, status: str) -> List[str]:
        """Generate recommendations for non-compliant configurations"""
        recommendations = []
        
        if status == 'non_compliant':
            if component.ecosystem == 'go':
                recommendations.append(f"Configure GOPROXY=https://{self.artifactory_base}/artifactory/api/go/isgedge-maven-virtual,direct")
                recommendations.append(f"Remove 'github.com' from GOPRIVATE (only include eos2git.cec.lab.emc.com)")
            elif component.ecosystem == 'python':
                recommendations.append(f"Add --index-url https://{self.artifactory_base}/artifactory/api/pypi/isgedge-pypi-virtual/simple")
            elif component.ecosystem == 'npm':
                recommendations.append(f"Configure npm registry: https://{self.artifactory_base}/artifactory/api/npm/isgedge-npm-virtual")
            elif component.ecosystem == 'maven':
                recommendations.append(f"Add mirror to https://{self.artifactory_base}/artifactory/isgedge-maven-virtual")
        
        return recommendations
    
    def _analyze_proxy_chains(self):
        """Analyze proxy/translation chains for each component"""
        print("Analyzing proxy chains...")
        
        for mapping in self.mappings:
            proxy_chain = []
            
            # Find all configurations that affect this component
            for config in self.endpoint_configs:
                # Check if this config is in the translation/proxy chain
                if config.endpoint_type in [EndpointType.TRANSLATED, EndpointType.PROXIED]:
                    # Check if it applies to this component
                    if self._config_applies_to_component(config, mapping.component):
                        proxy_chain.append(config)
            
            mapping.proxy_chain = proxy_chain
    
    def _config_applies_to_component(self, config: EndpointConfiguration, component: OSSComponent) -> bool:
        """Check if a configuration applies to a specific component"""
        # Simple heuristic: check if the config is for the same ecosystem
        ecosystem_keywords = {
            'go': ['GOPROXY', 'GOPRIVATE', 'go'],
            'python': ['pip', 'pypi', 'PIP_INDEX_URL'],
            'npm': ['npm', 'NPM_CONFIG_REGISTRY'],
            'maven': ['maven'],
            'docker': ['docker', 'DOCKER']
        }
        
        keywords = ecosystem_keywords.get(component.ecosystem, [])
        config_text = (config.config_snippet or '').lower()
        
        return any(keyword.lower() in config_text for keyword in keywords)
    
    def _generate_detailed_report(self) -> Dict:
        """Generate comprehensive endpoint analysis report"""
        print("Generating detailed report...")
        
        # Calculate statistics
        total_components = len(self.components)
        compliant_components = sum(1 for m in self.mappings if m.compliance_status == 'compliant')
        non_compliant_components = sum(1 for m in self.mappings if m.compliance_status == 'non_compliant')
        warning_components = sum(1 for m in self.mappings if m.compliance_status == 'warning')
        
        # Group by ecosystem
        by_ecosystem = {}
        for component in self.components:
            if component.ecosystem not in by_ecosystem:
                by_ecosystem[component.ecosystem] = {
                    'total': 0,
                    'compliant': 0,
                    'non_compliant': 0,
                    'warning': 0
                }
            by_ecosystem[component.ecosystem]['total'] += 1
        
        for mapping in self.mappings:
            ecosystem = mapping.component.ecosystem
            by_ecosystem[ecosystem][mapping.compliance_status] += 1
        
        # Group by endpoint type
        by_endpoint_type = {}
        for mapping in self.mappings:
            endpoint_type = mapping.actual_endpoint.endpoint_type.value
            if endpoint_type not in by_endpoint_type:
                by_endpoint_type[endpoint_type] = 0
            by_endpoint_type[endpoint_type] += 1
        
        # Generate summary
        report = {
            'summary': {
                'repository': str(self.repo_root.name),
                'total_components': total_components,
                'compliant_components': compliant_components,
                'non_compliant_components': non_compliant_components,
                'warning_components': warning_components,
                'compliance_percentage': round((compliant_components / total_components * 100) if total_components > 0 else 0, 2),
                'total_endpoint_configs': len(self.endpoint_configs)
            },
            'by_ecosystem': by_ecosystem,
            'by_endpoint_type': by_endpoint_type,
            'endpoint_configurations': [
                {
                    'url': config.endpoint_url,
                    'type': config.endpoint_type.value,
                    'location': config.config_location.value,
                    'file': config.config_file,
                    'line': config.config_line,
                    'snippet': config.config_snippet,
                    'compliant': config.is_compliant,
                    'notes': config.notes
                }
                for config in self.endpoint_configs
            ],
            'component_mappings': [
                {
                    'component': {
                        'name': mapping.component.name,
                        'version': mapping.component.version,
                        'ecosystem': mapping.component.ecosystem,
                        'source_file': mapping.component.source_file,
                        'line_number': mapping.component.line_number
                    },
                    'declared_endpoint': mapping.declared_endpoint,
                    'actual_endpoint': {
                        'url': mapping.actual_endpoint.endpoint_url,
                        'type': mapping.actual_endpoint.endpoint_type.value,
                        'location': mapping.actual_endpoint.config_location.value,
                        'file': mapping.actual_endpoint.config_file,
                        'compliant': mapping.actual_endpoint.is_compliant
                    },
                    'proxy_chain': [
                        {
                            'url': proxy.endpoint_url,
                            'type': proxy.endpoint_type.value,
                            'notes': proxy.notes
                        }
                        for proxy in mapping.proxy_chain
                    ],
                    'compliance_status': mapping.compliance_status,
                    'recommendations': mapping.recommendations
                }
                for mapping in self.mappings
            ],
            'critical_findings': self._generate_critical_findings()
        }
        
        return report
    
    def _generate_critical_findings(self) -> List[Dict]:
        """Generate list of critical findings that need immediate attention"""
        findings = []
        
        # Find GOPRIVATE misconfiguration
        for config in self.endpoint_configs:
            if 'GOPRIVATE' in (config.config_snippet or ''):
                if 'github.com' in config.endpoint_url:
                    findings.append({
                        'severity': 'CRITICAL',
                        'issue': 'GOPRIVATE includes github.com - bypassing proxy for public modules',
                        'file': config.config_file,
                        'line': config.config_line,
                        'recommendation': 'Remove github.com from GOPRIVATE. Only include eos2git.cec.lab.emc.com',
                        'impact': f'All GitHub modules are bypassing Artifactory proxy'
                    })
        
        # Find direct public endpoints
        for mapping in self.mappings:
            if mapping.compliance_status == 'non_compliant':
                if mapping.actual_endpoint.endpoint_type == EndpointType.DIRECT_PUBLIC:
                    findings.append({
                        'severity': 'HIGH',
                        'issue': f'{mapping.component.ecosystem} component using direct public endpoint',
                        'component': mapping.component.name,
                        'file': mapping.component.source_file,
                        'recommendation': mapping.recommendations[0] if mapping.recommendations else 'Configure proxy',
                        'impact': 'Component not using approved Artifactory proxy'
                    })
        
        return findings


def main():
    """Main entry point for standalone execution"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python endpoint_analyzer.py <repo_path>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    analyzer = EndpointAnalyzer(repo_path)
    report = analyzer.analyze_repository()
    
    # Print report as JSON
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
