"""
Environment File Manager for OSS Compliance Web Application
Provides safe manipulation of .env files
"""

from pathlib import Path
from typing import Dict, List, Optional


class EnvFileManager:
    """Helper for safely manipulating .env files"""
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize EnvFileManager
        
        Args:
            env_file: Path to .env file
        """
        self.env_file = Path(env_file)
    
    def read(self) -> Dict[str, str]:
        """
        Read .env file into dictionary
        
        Returns:
            Dictionary of environment variables
        """
        env_dict = {}
        
        if not self.env_file.exists():
            return env_dict
        
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_dict[key.strip()] = value.strip()
                    else:
                        print(f"Warning: Invalid line {line_num} in {self.env_file}: {line}")
        
        except Exception as e:
            print(f"Error reading {self.env_file}: {e}")
            raise
        
        return env_dict
    
    def write(self, env_dict: Dict[str, str], sort_keys: bool = True):
        """
        Write dictionary to .env file
        
        Args:
            env_dict: Dictionary of environment variables
            sort_keys: Whether to sort keys alphabetically
        """
        try:
            # Create backup before writing
            self._create_backup()
            
            with open(self.env_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write("# OSS Compliance Web Application Environment Configuration\n")
                f.write("# Auto-generated - Do not edit manually unless necessary\n\n")
                
                # Sort keys if requested
                keys = sorted(env_dict.keys()) if sort_keys else env_dict.keys()
                
                # Group keys by prefix for better organization
                grouped = self._group_keys(env_dict, keys)
                
                for group_name, group_keys in grouped.items():
                    if group_name:
                        f.write(f"\n# {group_name}\n")
                    for key in group_keys:
                        value = env_dict[key]
                        f.write(f"{key}={value}\n")
        
        except Exception as e:
            print(f"Error writing {self.env_file}: {e}")
            # Attempt to restore from backup
            self._restore_backup()
            raise
    
    def update(self, updates: Dict[str, str]):
        """
        Update specific keys in .env file
        
        Args:
            updates: Dictionary of keys to update
        """
        env_dict = self.read()
        env_dict.update(updates)
        self.write(env_dict)
    
    def remove(self, keys: List[str]):
        """
        Remove specific keys from .env file
        
        Args:
            keys: List of keys to remove
        """
        env_dict = self.read()
        for key in keys:
            env_dict.pop(key, None)
        self.write(env_dict)
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a specific value from .env file
        
        Args:
            key: Environment variable key
            default: Default value if key not found
            
        Returns:
            Value or default
        """
        env_dict = self.read()
        return env_dict.get(key, default)
    
    def set(self, key: str, value: str):
        """
        Set a specific key in .env file
        
        Args:
            key: Environment variable key
            value: Value to set
        """
        self.update({key: value})
    
    def exists(self) -> bool:
        """Check if .env file exists"""
        return self.env_file.exists()
    
    def _create_backup(self):
        """Create backup of .env file"""
        if self.env_file.exists():
            backup_file = self.env_file.with_suffix('.env.backup')
            try:
                import shutil
                shutil.copy2(self.env_file, backup_file)
            except Exception as e:
                print(f"Warning: Could not create backup: {e}")
    
    def _restore_backup(self):
        """Restore .env file from backup"""
        backup_file = self.env_file.with_suffix('.env.backup')
        if backup_file.exists():
            try:
                import shutil
                shutil.copy2(backup_file, self.env_file)
                print(f"Restored {self.env_file} from backup")
            except Exception as e:
                print(f"Error restoring backup: {e}")
    
    def _group_keys(self, env_dict: Dict[str, str], keys: List[str]) -> Dict[str, List[str]]:
        """
        Group keys by prefix for better organization
        
        Args:
            env_dict: Dictionary of environment variables
            keys: List of keys to group
            
        Returns:
            Dictionary of group names to list of keys
        """
        groups = {
            'Flask Configuration': [],
            'Encryption': [],
            'Database': [],
            'Artifactory': [],
            'GitHub Instances': [],
            'Jenkins': [],
            'Other': []
        }
        
        for key in keys:
            if key.startswith('FLASK_') or key == 'SECRET_KEY':
                groups['Flask Configuration'].append(key)
            elif key.startswith('ENCRYPTION_'):
                groups['Encryption'].append(key)
            elif key.startswith('DATABASE_'):
                groups['Database'].append(key)
            elif key.startswith('ARTIFACTORY_') or key.startswith('VIRTUAL_REPO_'):
                groups['Artifactory'].append(key)
            elif key.startswith('GITHUB_'):
                groups['GitHub Instances'].append(key)
            elif key.startswith('JENKINS_'):
                groups['Jenkins'].append(key)
            else:
                groups['Other'].append(key)
        
        # Remove empty groups
        return {name: keys for name, keys in groups.items() if keys}
    
    def validate(self) -> List[str]:
        """
        Validate .env file and return list of issues
        
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        if not self.exists():
            issues.append(f".env file not found at {self.env_file}")
            return issues
        
        env_dict = self.read()
        
        # Check for required keys
        required_keys = [
            'SECRET_KEY',
            'ENCRYPTION_KEY'
        ]
        
        for key in required_keys:
            if key not in env_dict or not env_dict[key]:
                issues.append(f"Required key '{key}' is missing or empty")
        
        # Check for suspicious values
        if env_dict.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
            issues.append("SECRET_KEY is still set to default development value")
        
        # Check for token environment variables referenced in config
        # This would require loading the config, so we'll skip for now
        
        return issues
    
    def print_summary(self):
        """Print a summary of the .env file"""
        if not self.exists():
            print(f".env file not found at {self.env_file}")
            return
        
        env_dict = self.read()
        
        print(f"\n.env File Summary ({self.env_file})")
        print("=" * 60)
        print(f"Total variables: {len(env_dict)}")
        
        grouped = self._group_keys(env_dict, env_dict.keys())
        for group_name, keys in grouped.items():
            print(f"\n{group_name}: {len(keys)} variables")
            for key in keys:
                # Mask sensitive values
                value = env_dict[key]
                if 'TOKEN' in key or 'KEY' in key or 'PASSWORD' in key:
                    display_value = value[:10] + '...' if len(value) > 10 else '***'
                else:
                    display_value = value[:50] + '...' if len(value) > 50 else value
                print(f"  {key}={display_value}")
        
        # Show validation issues
        issues = self.validate()
        if issues:
            print(f"\nValidation Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"\nNo validation issues found.")
