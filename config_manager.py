"""
Configuration Manager for OSS Compliance Web Application
Provides centralized configuration management with validation
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class GitHubUser:
    """GitHub user configuration"""
    username: str
    token_encrypted: str = ""  # Encrypted token stored directly in YAML
    email: str = ""
    
    @property
    def token(self) -> str:
        """Get decrypted token"""
        if self.token_encrypted:
            from app import decrypt_token
            return decrypt_token(self.token_encrypted)
        return ""
    
    def validate(self):
        """Validate user configuration"""
        if not self.username:
            raise ValueError("GitHub user must have a username")
        # Token is optional - can be added later via UI


@dataclass
class GitHubInstance:
    """GitHub instance configuration"""
    name: str
    api_url: str
    org: str
    users: List[GitHubUser] = field(default_factory=list)
    
    def validate(self):
        """Validate GitHub instance configuration"""
        if not self.name:
            raise ValueError("GitHub instance must have a name")
        if not self.api_url:
            raise ValueError(f"GitHub instance '{self.name}' missing API URL")
        if not self.org:
            raise ValueError(f"GitHub instance '{self.name}' missing organization")
        if not self.users:
            raise ValueError(f"GitHub instance '{self.name}' has no users configured")
        
        # Validate each user
        for user in self.users:
            user.validate()
    
    def get_user(self, username: str) -> Optional[GitHubUser]:
        """Get a specific user by username"""
        for user in self.users:
            if user.username == username:
                return user
        return None
    
    def get_default_user(self) -> Optional[GitHubUser]:
        """Get the default user (first user or user named 'default_user')"""
        # Try to find user named 'default_user'
        default = self.get_user('default_user')
        if default:
            return default
        # Fall back to first user
        return self.users[0] if self.users else None


@dataclass
class ArtifactoryConfig:
    """Artifactory configuration"""
    base_url: str
    virtual_repos: Dict[str, str] = field(default_factory=dict)
    user: str = ""
    token_encrypted: str = ""  # Encrypted token stored directly in YAML
    
    @property
    def token(self) -> str:
        """Get decrypted token"""
        if self.token_encrypted:
            from app import decrypt_token
            return decrypt_token(self.token_encrypted)
        return ""
    
    def validate(self):
        """Validate Artifactory configuration"""
        if not self.base_url:
            raise ValueError("Artifactory base URL is required")
        if not self.virtual_repos:
            raise ValueError("At least one virtual repository must be configured")


@dataclass
class JenkinsConfig:
    """Jenkins configuration"""
    user: str
    token_encrypted: str = ""  # Encrypted token stored directly in YAML
    urls: List[str] = field(default_factory=list)
    pr_validation_job: str = "oss-compliance-validation"
    
    @property
    def token(self) -> str:
        """Get decrypted token"""
        if self.token_encrypted:
            from app import decrypt_token
            return decrypt_token(self.token_encrypted)
        return ""
    
    def validate(self):
        """Validate Jenkins configuration"""
        if not self.user:
            raise ValueError("Jenkins user is required")
        # Token is optional - can be added later via UI
        if not self.urls:
            raise ValueError("At least one Jenkins URL must be configured")


@dataclass
class AppSettings:
    """Application settings"""
    max_scan_threads: int = 4
    cache_ttl_hours: int = 1
    report_retention_days: int = 90
    debug_logging: bool = True


class ConfigManager:
    """Centralized configuration management with validation"""
    
    def __init__(self, config_file: str = "config/app_config.yaml"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        if not self.config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_file}\n"
                f"Please copy config/app_config.example.yaml to config/app_config.yaml and customize it."
            )
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError("Configuration file is empty")
            
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    def _validate_config(self):
        """Validate entire configuration"""
        try:
            # Validate Artifactory
            artifactory = self.get_artifactory_config()
            artifactory.validate()
            
            # Validate GitHub instances
            instances = self.get_github_instances()
            if not instances:
                raise ValueError("At least one GitHub instance must be configured")
            
            for instance_id, instance in instances.items():
                instance.validate()
            
            # Validate Jenkins
            jenkins = self.get_jenkins_config()
            jenkins.validate()
            
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def get_artifactory_config(self) -> ArtifactoryConfig:
        """Get Artifactory configuration"""
        artifactory_data = self.config.get('artifactory', {})
        return ArtifactoryConfig(
            base_url=artifactory_data.get('base_url', ''),
            virtual_repos=artifactory_data.get('virtual_repos', {}),
            user=artifactory_data.get('user', ''),
            token_encrypted=artifactory_data.get('token_encrypted', '')
        )
    
    def get_github_instances(self) -> Dict[str, GitHubInstance]:
        """Get all GitHub instances"""
        instances = {}
        github_instances_data = self.config.get('github_instances', {})
        
        for instance_id, instance_data in github_instances_data.items():
            users_data = instance_data.get('users', [])
            users = [
                GitHubUser(
                    username=user.get('username', ''),
                    token_encrypted=user.get('token_encrypted', ''),
                    email=user.get('email', '')
                )
                for user in users_data
            ]
            
            instances[instance_id] = GitHubInstance(
                name=instance_data.get('name', instance_id),
                api_url=instance_data.get('api_url', ''),
                org=instance_data.get('org', ''),
                users=users
            )
        
        return instances
    
    def get_github_instance(self, instance_id: str) -> Optional[GitHubInstance]:
        """Get specific GitHub instance"""
        return self.get_github_instances().get(instance_id)
    
    def get_jenkins_config(self) -> JenkinsConfig:
        """Get Jenkins configuration"""
        jenkins_data = self.config.get('jenkins', {})
        return JenkinsConfig(
            user=jenkins_data.get('user', ''),
            token_encrypted=jenkins_data.get('token_encrypted', ''),
            urls=jenkins_data.get('urls', []),
            pr_validation_job=jenkins_data.get('pr_validation_job', 'oss-compliance-validation')
        )
    
    def get_whitelist_urls(self) -> List[str]:
        """Get whitelist URLs"""
        return self.config.get('whitelist_urls', [])
    
    def get_app_settings(self) -> AppSettings:
        """Get application settings"""
        settings_data = self.config.get('app_settings', {})
        return AppSettings(
            max_scan_threads=settings_data.get('max_scan_threads', 4),
            cache_ttl_hours=settings_data.get('cache_ttl_hours', 1),
            report_retention_days=settings_data.get('report_retention_days', 90),
            debug_logging=settings_data.get('debug_logging', True)
        )
    
    def update_config(self, updates: dict, validate: bool = True):
        """
        Update configuration and save to file
        
        Args:
            updates: Dictionary of updates to merge into configuration
            validate: Whether to validate configuration after update
        """
        # Deep merge updates
        self._deep_merge(self.config, updates)
        
        # Validate if requested
        if validate:
            self._validate_config()
        
        # Save to file
        self._save_config()
    
    def _deep_merge(self, base: dict, updates: dict):
        """Deep merge updates into base dictionary"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise IOError(f"Failed to save configuration: {e}")
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        self._validate_config()
    
    def get_config_summary(self) -> dict:
        """Get a summary of the current configuration (without sensitive data)"""
        artifactory = self.get_artifactory_config()
        github_instances = self.get_github_instances()
        jenkins = self.get_jenkins_config()
        
        return {
            'artifactory': {
                'base_url': artifactory.base_url,
                'virtual_repo_count': len(artifactory.virtual_repos),
                'virtual_repos': list(artifactory.virtual_repos.keys())
            },
            'github_instances': {
                instance_id: {
                    'name': instance.name,
                    'api_url': instance.api_url,
                    'org': instance.org,
                    'user_count': len(instance.users),
                    'users': [user.username for user in instance.users]
                }
                for instance_id, instance in github_instances.items()
            },
            'jenkins': {
                'user': jenkins.user,
                'url_count': len(jenkins.urls),
                'urls': jenkins.urls,
                'pr_validation_job': jenkins.pr_validation_job
            },
            'whitelist_url_count': len(self.get_whitelist_urls()),
            'app_settings': {
                'max_scan_threads': self.get_app_settings().max_scan_threads,
                'cache_ttl_hours': self.get_app_settings().cache_ttl_hours,
                'report_retention_days': self.get_app_settings().report_retention_days,
                'debug_logging': self.get_app_settings().debug_logging
            }
        }


# Singleton instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get or create singleton ConfigManager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config():
    """Reload configuration from file"""
    global _config_manager
    if _config_manager is not None:
        _config_manager.reload()
    else:
        _config_manager = ConfigManager()
