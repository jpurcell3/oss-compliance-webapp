#!/usr/bin/env python3
"""
Create a distributable zip archive of the OSS Compliance Web Application.
Simple version that includes essential files only.
"""

import os
import zipfile
from pathlib import Path
from datetime import datetime

def create_distribution():
    """Create a zip archive of the application."""
    base_dir = Path(__file__).parent
    
    # Files and directories to include
    include_files = [
        'app.py',
        'models.py',
        'config_manager.py',
        'compliance_scanner.py',
        'remote_scanner.py',
        'enhanced_scanner.py',
        'endpoint_analyzer.py',
        'markdown_generator.py',
        'init_db.py',
        'migrate_add_pr_submissions.py',
        'requirements.txt',
        'Dockerfile',
        'docker-compose.yml',
        'docker-helper.bat',
        '.gitignore',
    ]
    
    include_dirs = [
        'templates',
        'static',
        'config',
        'docs',
    ]
    
    # Create output filename
    version = "1.0"
    date_str = datetime.now().strftime('%Y%m%d')
    output_filename = base_dir / f"oss-compliance-webapp-v{version}-{date_str}.zip"
    
    print(f"Creating distribution: {output_filename}")
    print(f"Base directory: {base_dir}")
    print()
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        files_included = 0
        
        # Include individual files
        for file in include_files:
            file_path = base_dir / file
            if file_path.exists():
                zipf.write(file_path, file)
                files_included += 1
                print(f"  Included: {file}")
            else:
                print(f"  Skipped (not found): {file}")
        
        # Include directories
        for dir_name in include_dirs:
            dir_path = base_dir / dir_name
            if dir_path.exists():
                for root, dirs, files in os.walk(dir_path):
                    # Skip __pycache__ and hidden files
                    dirs[:] = [d for d in dirs if d != '__pycache__' and not d.startswith('.')]
                    
                    for file in files:
                        file_path = Path(root) / file
                        # Skip hidden files and compiled Python files
                        if file.startswith('.') or file.endswith('.pyc') or file.endswith('.pyo'):
                            continue
                        # Skip app_config.yaml (contains encrypted tokens)
                        if file == 'app_config.yaml':
                            continue
                        # Skip backup files
                        if '.backup.' in file:
                            continue
                        # Skip .env files
                        if file.startswith('.env'):
                            continue
                        
                        relative_path = file_path.relative_to(base_dir)
                        zipf.write(file_path, relative_path)
                        files_included += 1
                        print(f"  Included: {relative_path}")
            else:
                print(f"  Skipped directory (not found): {dir_name}")
        
        print()
        print(f"Total files included: {files_included}")
        print(f"Archive size: {os.path.getsize(output_filename) / 1024 / 1024:.2f} MB")
    
    return output_filename

def create_readme(base_dir):
    """Create a README file for the distribution."""
    readme_content = """# OSS Compliance Web Application - Distribution

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Git (for remote scanning)
- SQLite 3 (default) or PostgreSQL 14+ (optional)

### Installation

1. **Extract the archive**
   ```bash
   unzip oss-compliance-webapp-v1.0-*.zip
   cd oss-compliance-webapp
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Create configuration**
   ```bash
   mkdir -p config
   cp config/app_config.example.yaml config/app_config.yaml
   nano config/app_config.yaml  # Edit with your configuration
   ```

5. **Generate encryption key**
   ```bash
   export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   # On Windows PowerShell:
   # $env:ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

6. **Initialize database**
   ```bash
   python init_db.py
   ```

7. **Run the application**
   ```bash
   python app.py
   ```

8. **Access the application**
   Open your browser to: http://localhost:5001

### Docker Deployment

1. **Build and run with Docker**
   ```bash
   docker build -t oss-compliance-webapp:latest .
   docker run -d -p 5001:5001 -e ENCRYPTION_KEY=your-key -v $(pwd)/config:/app/config -v $(pwd)/reports:/app/reports -v $(pwd)/uploads:/app/uploads -v $(pwd)/cache:/app/cache -v $(pwd)/instance:/app/instance --name oss-compliance-webapp oss-compliance-webapp:latest
   ```

2. **Or use docker-compose**
   ```bash
   export ENCRYPTION_KEY=your-key
   docker-compose up -d
   ```

### Adding Tokens

Tokens are added via the web UI:

1. Navigate to http://localhost:5001/config
2. Click "Users" on a GitHub instance
3. Click "Edit" on a user
4. Paste your token
5. Click "Save User"
6. Token is encrypted and saved to YAML

### Documentation

Full documentation is available in the `docs/` directory:
- `DEPLOYMENT_GUIDE.md` - Complete deployment instructions
- `DOCKER_DEPLOYMENT.md` - Docker-specific deployment
- `CONFIGURATION_QUICK_START.md` - Configuration guide
- `API_REFERENCE.md` - API documentation

### Support

For issues or questions, please refer to the documentation or contact the support team.

## Version Information

- Application Version: 1.0
- Distribution Date: {date}
- Python Required: 3.9+

## Security Notes

- The `ENCRYPTION_KEY` environment variable is required for token encryption/decryption
- Never commit `config/app_config.yaml` to version control (contains encrypted tokens)
- Add `config/app_config.yaml` to `.gitignore`
- Rotate encryption keys and tokens regularly (every 90 days recommended)
"""
    
    readme_path = base_dir / "DISTRIBUTION_README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content.format(date=datetime.now().strftime('%Y-%m-%d')))
    
    print(f"Created distribution README: {readme_path}")
    return readme_path

def main():
    """Main entry point."""
    print("=" * 60)
    print("OSS Compliance Web Application - Distribution Creator")
    print("=" * 60)
    print()
    
    # Create the zip archive
    zip_file = create_distribution()
    
    # Create distribution README
    readme_file = create_readme(zip_file.parent)
    
    print()
    print("=" * 60)
    print(f"[SUCCESS] Distribution created successfully!")
    print("=" * 60)
    print(f"   Zip file: {zip_file}")
    print(f"   README: {readme_file}")
    print()
    print("Next steps for recipients:")
    print("  1. Extract the zip archive")
    print("  2. Read DISTRIBUTION_README.md for installation instructions")
    print("  3. Follow the Quick Start guide to deploy")
    print()

if __name__ == "__main__":
    main()
