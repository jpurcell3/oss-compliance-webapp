# Database Guide
## OSS Compliance Web Application

**Version:** 1.0  
**Last Updated:** 2026-06-12  
**Application Version:** 0.5.0

---

## Table of Contents
1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [Initialization](#initialization)
4. [Migration Scripts](#migration-scripts)
5. [Recent Improvements (v0.5.0)](#recent-improvements-v050)
6. [Database Operations](#database-operations)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The OSS Compliance Web Application uses SQLAlchemy ORM for database operations, supporting both SQLite (development) and PostgreSQL (production) databases. The database stores compliance scan reports and tracks pull request submissions for remediation workflows.

### Database Technology Stack

- **Development**: SQLite 3 (default, zero configuration)
- **Production**: PostgreSQL 14+ (recommended for scalability)
- **ORM**: SQLAlchemy 2.x
- **Migration**: Custom migration scripts (Alembic recommended for future)

### Database Location

- **Development**: `instance/reports.db` (relative to application root)
- **Docker**: `/app/instance/reports.db` (persistent volume)
- **Production**: PostgreSQL database server

---

## Database Schema

### Tables

#### 1. reports Table

Stores compliance scan results and metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique report identifier |
| filename | VARCHAR(255) | UNIQUE, NOT NULL, INDEXED | Report filename |
| repository_name | VARCHAR(255) | NOT NULL, INDEXED | Repository name |
| scan_type | VARCHAR(50) | NULL | Scan type (basic/enhanced) |
| compliance_percentage | FLOAT | NULL | Compliance score (0-100) |
| total_findings | INTEGER | NULL | Total compliance findings |
| critical_issues | INTEGER | NULL | Critical severity count |
| high_issues | INTEGER | NULL | High severity count |
| compliant_items | INTEGER | NULL | Compliant component count |
| non_compliant_items | INTEGER | NULL | Non-compliant component count |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | Report creation timestamp |
| file_path | TEXT | NULL | Path to JSON report file |
| markdown_path | TEXT | NULL | Path to markdown summary file |
| github_org | VARCHAR(255) | INDEXED | GitHub organization |
| github_instance | VARCHAR(100) | NULL | GitHub instance identifier |
| scan_metadata | TEXT | NULL | JSON scan metadata |

**Indexes:**
- `filename` (unique)
- `repository_name`
- `github_org`

#### 2. pr_submissions Table

Tracks pull request submissions for compliance fixes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique submission identifier |
| report_id | INTEGER | FOREIGN KEY → reports.id, NOT NULL | Related report ID |
| pr_url | VARCHAR(500) | NULL | Pull request URL |
| pr_number | INTEGER | NULL | Pull request number |
| submitter_username | VARCHAR(100) | NULL | Submitter GitHub username |
| submitter_email | VARCHAR(255) | NULL | Submitter email address |
| github_instance | VARCHAR(100) | NULL | GitHub instance identifier |
| submission_timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | Submission timestamp |
| status | VARCHAR(50) | DEFAULT 'pending' | Submission status |

**Status Values:**
- `pending` - Submission in progress
- `created` - PR successfully created
- `failed` - PR creation failed
- `merged` - PR has been merged
- `closed` - PR has been closed

**Foreign Key Relationship:**
- `report_id` → `reports.id` (CASCADE delete not enabled)

### Entity Relationship Diagram

```
┌─────────────────┐         ┌──────────────────┐
│     reports      │         │ pr_submissions   │
├─────────────────┤         ├──────────────────┤
│ id (PK)         │◄────────│ report_id (FK)   │
│ filename        │         │ pr_url           │
│ repository_name │         │ pr_number        │
│ scan_type       │         │ submitter_username│
│ compliance_%    │         │ submitter_email  │
│ total_findings  │         │ github_instance  │
│ critical_issues │         │ submission_ts    │
│ high_issues     │         │ status           │
│ created_at      │         └──────────────────┘
│ file_path       │
│ markdown_path   │
│ github_org      │
│ github_instance │
│ scan_metadata   │
└─────────────────┘
```

---

## Initialization

### Initial Database Setup

Run the initialization script to create all required tables:

```bash
python init_db.py
```

**Output:**
```
Database tables created successfully!
Database location: sqlite:///instance/reports.db
```

### What Initialization Does

1. **Creates Instance Directory**: Ensures `instance/` directory exists
2. **Creates Database File**: Initializes SQLite database if it doesn't exist
3. **Creates Tables**: Creates `reports` and `pr_submissions` tables
4. **Sets Up Relationships**: Configures foreign key relationships
5. **Creates Indexes**: Sets up performance indexes on frequently queried fields

### Manual Initialization (Alternative)

```python
from app import app, db

with app.app_context():
    db.create_all()
    print("Database initialized successfully!")
```

---

## Migration Scripts

### Current Migration: PR Submissions Table

**Script:** `migrate_add_pr_submissions.py`

**Purpose:** Adds the `pr_submissions` table to existing databases for PR tracking functionality.

**When to Run:**
- Upgrading from v0.4.0 to v0.5.0
- When PR submission features are first enabled
- If `pr_submissions` table is missing

**Usage:**

```bash
python migrate_add_pr_submissions.py
```

**Output Examples:**

**Success:**
```
Successfully added pr_submissions table to database.
```

**Already Exists:**
```
pr_submissions table already exists. No migration needed.
```

**Database Not Found:**
```
Database instance/reports.db does not exist. No migration needed.
```

### Migration Script Details

The migration script:

1. **Checks Multiple Locations**: Looks for database in both `instance/reports.db` and `reports.db`
2. **Validates Existence**: Confirms database file exists before attempting migration
3. **Checks for Existing Table**: Prevents duplicate table creation
4. **Creates Table with Schema**: Uses SQL DDL to create `pr_submissions` table
5. **Sets Up Foreign Key**: Establishes relationship to `reports` table
6. **Commits Changes**: Ensures data integrity

### Future Migrations

For production deployments, consider using **Alembic** for database migrations:

#### Install Alembic

```bash
pip install alembic
```

#### Initialize Alembic

```bash
alembic init alembic
```

#### Configure Alembic

Edit `alembic.ini`:

```ini
sqlalchemy.url = postgresql://oss_user:password@localhost/oss_compliance
```

#### Create Migration

```bash
alembic revision --autogenerate -m "Add new feature"
```

#### Apply Migration

```bash
alembic upgrade head
```

---

## Recent Improvements (v0.5.0)

### Database Path Configuration

**Improvement:** Enhanced database path configuration for Docker compatibility

**Changes:**
- Standardized database location to `instance/reports.db`
- Added automatic directory creation for `instance/` folder
- Improved path handling for both local and Docker environments
- Fixed relative path issues in containerized deployments

**Benefit:** Consistent database location across development and production environments

### Orphaned Record Cleanup

**Improvement:** Added cleanup functionality for orphaned database records

**Changes:**
- Implemented data integrity checks
- Added cleanup routines for orphaned PR submissions
- Enhanced error handling for database operations
- Improved referential integrity validation

**Benefit:** Maintains data integrity and prevents database bloat

### Enhanced Error Handling

**Improvement:** Comprehensive error handling in database operations

**Changes:**
- Added try-catch blocks for all database operations
- Improved error messages for troubleshooting
- Added logging for database operations
- Enhanced connection error handling

**Benefit:** Better debugging and more reliable database operations

### Docker Database Support

**Improvement:** Full Docker support with persistent database storage

**Changes:**
- Added `instance/` directory to Docker volumes
- Configured persistent storage for SQLite database
- Added PostgreSQL support for production deployments
- Updated docker-compose.yml with database service

**Benefit:** Production-ready database configuration with containerization

### Multi-User Support

**Improvement:** Database schema enhanced for multi-user GitHub support

**Changes:**
- Enhanced `pr_submissions` table for user tracking
- Added support for multiple GitHub users per instance
- Improved user attribution in PR submissions
- Enhanced credential encryption support

**Benefit:** Supports enterprise multi-user workflows

---

## Database Operations

### Common Database Operations

#### Query All Reports

```python
from app import app, db, Report

with app.app_context():
    reports = Report.query.all()
    for report in reports:
        print(f"{report.filename}: {report.repository_name}")
```

#### Query Report by ID

```python
from app import app, db, Report

with app.app_context():
    report = Report.query.get(1)
    print(f"Repository: {report.repository_name}")
    print(f"Compliance: {report.compliance_percentage}%")
```

#### Query PR Submissions for a Report

```python
from app import app, db, PRSubmission

with app.app_context():
    submissions = PRSubmission.query.filter_by(report_id=1).all()
    for sub in submissions:
        print(f"PR: {sub.pr_url} - Status: {sub.status}")
```

#### Update PR Status

```python
from app import app, db, PRSubmission

with app.app_context():
    submission = PRSubmission.query.get(1)
    submission.status = 'merged'
    db.session.commit()
```

#### Delete Old Reports

```python
from app import app, db, Report
from datetime import datetime, timedelta

with app.app_context():
    # Delete reports older than 90 days
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    old_reports = Report.query.filter(Report.created_at < cutoff_date).all()
    
    for report in old_reports:
        db.session.delete(report)
    
    db.session.commit()
    print(f"Deleted {len(old_reports)} old reports")
```

### Database Maintenance

#### Vacuum SQLite Database

```bash
sqlite3 instance/reports.db "VACUUM;"
```

#### Analyze PostgreSQL Database

```bash
psql -U oss_user -d oss_compliance -c "ANALYZE;"
```

#### Reindex PostgreSQL Database

```bash
psql -U oss_user -d oss_compliance -c "REINDEX DATABASE oss_compliance;"
```

---

## Backup and Recovery

### SQLite Backup

#### Backup

```bash
# Create backup
cp instance/reports.db backups/reports_$(date +%Y%m%d_%H%M%S).db

# Or using sqlite3
sqlite3 instance/reports.db ".backup backups/reports_$(date +%Y%m%d_%H%M%S).db"
```

#### Restore

```bash
# Stop application
# Restore from backup
cp backups/reports_20260612_120000.db instance/reports.db
# Restart application
```

### PostgreSQL Backup

#### Backup

```bash
# Full database backup
pg_dump -U oss_user oss_compliance > backups/oss_compliance_$(date +%Y%m%d).sql

# Compressed backup
pg_dump -U oss_user oss_compliance | gzip > backups/oss_compliance_$(date +%Y%m%d).sql.gz
```

#### Restore

```bash
# Restore from backup
psql -U oss_user oss_compliance < backups/oss_compliance_20260612.sql

# Restore from compressed backup
gunzip -c backups/oss_compliance_20260612.sql.gz | psql -U oss_user oss_compliance
```

### Automated Backup Script

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -U oss_user oss_compliance | gzip > $BACKUP_DIR/oss_compliance_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "oss_compliance_*.sql.gz" -mtime +30 -delete

echo "Backup completed: oss_compliance_$DATE.sql.gz"
```

---

## Troubleshooting

### Common Issues

#### Database Locked Error

**Symptom:** `sqlite3.OperationalError: database is locked`

**Solutions:**
1. Check for other processes accessing the database
2. Close all database connections
3. Restart the application
4. Check for long-running transactions

#### Foreign Key Constraint Error

**Symptom:** `IntegrityError: FOREIGN KEY constraint failed`

**Solutions:**
1. Ensure referenced record exists in parent table
2. Check foreign key values are valid
3. Verify database relationship integrity
4. Use proper transaction handling

#### Migration Script Fails

**Symptom:** Migration script doesn't execute or errors

**Solutions:**
1. Verify database file exists
2. Check database permissions
3. Ensure no schema conflicts
4. Run with verbose error output

#### Database Connection Issues

**Symptom:** Cannot connect to database

**Solutions:**
1. Verify database server is running
2. Check connection string in `.env`
3. Test network connectivity
4. Verify credentials are correct

### Debug Mode

#### Enable SQLAlchemy Logging

Add to `.env`:

```env
SQLALCHEMY_ECHO=True
```

#### Database Query Inspection

```python
from app import app, db
import sqlalchemy as sa

with app.app_context():
    # Enable query logging
    sa.echo = True
    
    # Run your queries
    reports = Report.query.all()
```

#### Connection Pool Issues

Check connection pool status:

```python
from app import app, db

with app.app_context():
    pool = db.engine.pool
    print(f"Pool size: {pool.size()}")
    print(f"Checked out: {pool.checkedout()}")
```

---

## Performance Optimization

### SQLite Optimization

#### Enable WAL Mode

```bash
sqlite3 instance/reports.db "PRAGMA journal_mode=WAL;"
```

#### Set Cache Size

```bash
sqlite3 instance/reports.db "PRAGMA cache_size=-64000;"  # 64MB cache
```

### PostgreSQL Optimization

#### Configuration Tuning

Edit `postgresql.conf`:

```ini
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
```

#### Index Optimization

```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE tablename IN ('reports', 'pr_submissions');
```

---

## Security Considerations

### File Permissions

```bash
# Set restrictive permissions on database files
chmod 600 instance/reports.db
chmod 700 instance/
```

### Database Credentials

- Use strong passwords for PostgreSQL
- Store credentials in environment variables
- Rotate credentials regularly
- Never commit credentials to version control

### Encryption

- v0.5.0 uses Fernet encryption for sensitive data
- Encryption keys stored in `ENCRYPTION_KEY` environment variable
- Rotate encryption keys periodically (every 90 days)

---

## Best Practices

1. **Regular Backups**: Schedule automated daily backups
2. **Index Maintenance**: Rebuild indexes periodically for PostgreSQL
3. **Query Optimization**: Use `EXPLAIN QUERY PLAN` for slow queries
4. **Connection Pooling**: Configure appropriate pool sizes for production
5. **Monitoring**: Monitor database size and performance metrics
6. **Testing**: Test migrations in staging before production
7. **Documentation**: Document custom database procedures and triggers

---

**Document Status**: Complete  
**Last Updated**: 2026-06-12  
**Next Review**: 2026-09-12