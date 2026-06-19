"""
Database models for OSS Compliance Web Application
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Report(db.Model):
    """Model for storing scan reports"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False, index=True)
    repository_name = db.Column(db.String(255), nullable=False, index=True)
    scan_type = db.Column(db.String(50))
    compliance_percentage = db.Column(db.Float)
    total_findings = db.Column(db.Integer)
    critical_issues = db.Column(db.Integer)
    high_issues = db.Column(db.Integer)
    compliant_items = db.Column(db.Integer)
    non_compliant_items = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.Text)
    markdown_path = db.Column(db.Text)
    github_org = db.Column(db.String(255), index=True)
    github_instance = db.Column(db.String(100))
    scan_metadata = db.Column(db.Text)
    
    @classmethod
    def from_report_data(cls, filename, report_data, file_path, markdown_path=None):
        """Create a Report instance from report data"""
        import json
        
        scan_metadata = report_data.get('scan_metadata', {})
        summary = report_data.get('summary', {})
        findings = report_data.get('findings', [])
        
        # Extract compliance data - prioritize scan_summary for enhanced scans
        scan_summary = report_data.get('scan_summary', {})
        if scan_summary and 'compliance_percentage' in scan_summary:
            compliance_percentage = scan_summary.get('compliance_percentage', 0.0)
        else:
            basic_compliance = summary.get('basic_compliance', {})
            compliance_percentage = basic_compliance.get('compliance_percentage', 0.0)
        
        # Extract component counts - prioritize scan_summary for enhanced scans
        total_findings = len(findings)
        if scan_summary:
            compliant_items = scan_summary.get('compliant_items', 0)
            non_compliant_items = scan_summary.get('non_compliant_items', 0)
        else:
            compliant_items = basic_compliance.get('compliant_components', 0)
            non_compliant_items = basic_compliance.get('non_compliant_components', 0)
        
        # Count critical and high issues
        critical_issues = sum(1 for f in findings if f.get('severity') == 'critical')
        high_issues = sum(1 for f in findings if f.get('severity') == 'high')
        
        # Determine scan type
        scan_type = 'enhanced' if 'component_analysis' in summary else 'basic'
        
        return cls(
            filename=filename,
            file_path=file_path,
            markdown_path=markdown_path,
            repository_name=scan_metadata.get('repository_name', ''),
            github_org=scan_metadata.get('github_org', ''),
            github_instance=scan_metadata.get('github_instance', ''),
            scan_type=scan_type,
            compliance_percentage=compliance_percentage,
            total_findings=total_findings,
            critical_issues=critical_issues,
            high_issues=high_issues,
            compliant_items=compliant_items,
            non_compliant_items=non_compliant_items,
            scan_metadata=json.dumps(scan_metadata),
            created_at=datetime.utcnow()
        )
    
    def to_dict(self):
        """Convert report to dictionary"""
        import json
        
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'markdown_path': self.markdown_path,
            'repository_name': self.repository_name,
            'github_org': self.github_org,
            'github_instance': self.github_instance,
            'scan_type': self.scan_type,
            'compliance_percentage': self.compliance_percentage,
            'total_findings': self.total_findings,
            'critical_issues': self.critical_issues,
            'high_issues': self.high_issues,
            'compliant_items': self.compliant_items,
            'non_compliant_items': self.non_compliant_items,
            'scan_metadata': json.loads(self.scan_metadata) if self.scan_metadata else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Report {self.filename}>'


class PRSubmission(db.Model):
    """Model for tracking pull request submissions"""
    __tablename__ = 'pr_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    pr_url = db.Column(db.String(500))
    pr_number = db.Column(db.Integer)
    submitter_username = db.Column(db.String(100))
    submitter_email = db.Column(db.String(255))
    github_instance = db.Column(db.String(100))
    submission_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')  # pending/merged/closed
    
    # Relationship
    report = db.relationship('Report', backref=db.backref('pr_submissions', lazy=True))
    
    def to_dict(self):
        """Convert PR submission to dictionary"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'pr_url': self.pr_url,
            'pr_number': self.pr_number,
            'submitter_username': self.submitter_username,
            'submitter_email': self.submitter_email,
            'github_instance': self.github_instance,
            'submission_timestamp': self.submission_timestamp.isoformat() if self.submission_timestamp else None,
            'status': self.status
        }
    
    def __repr__(self):
        return f'<PRSubmission {self.pr_url}>'
