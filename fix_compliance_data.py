"""
Script to fix compliance percentage data in the database by re-parsing report files
"""
import json
import sys
from pathlib import Path
from app import app, db, Report

def fix_compliance_data():
    """Update all report records with correct compliance data from their JSON files"""
    with app.app_context():
        reports = Report.query.all()
        updated_count = 0
        error_count = 0
        
        print(f"Found {len(reports)} reports in database")
        
        for report in reports:
            try:
                # Read the report JSON file
                report_path = Path(report.file_path) if report.file_path else Path(app.config['REPORTS_FOLDER']) / report.filename
                
                if not report_path.exists():
                    print(f"Warning: Report file not found: {report_path}")
                    error_count += 1
                    continue
                
                with open(report_path, 'r') as f:
                    report_data = json.load(f)
                
                # Extract compliance data using the same logic as from_report_data
                summary = report_data.get('summary', {})
                scan_summary = report_data.get('scan_summary', {})
                
                # Extract compliance percentage - prioritize scan_summary for enhanced scans
                if scan_summary and 'compliance_percentage' in scan_summary:
                    compliance_percentage = scan_summary.get('compliance_percentage', 0.0)
                else:
                    basic_compliance = summary.get('basic_compliance', {})
                    compliance_percentage = basic_compliance.get('compliance_percentage', 0.0)
                
                # Extract component counts
                findings = report_data.get('findings', [])
                total_findings = len(findings)
                
                if scan_summary:
                    compliant_items = scan_summary.get('compliant_items', 0)
                    non_compliant_items = scan_summary.get('non_compliant_items', 0)
                else:
                    basic_compliance = summary.get('basic_compliance', {})
                    compliant_items = basic_compliance.get('compliant_components', 0)
                    non_compliant_items = basic_compliance.get('non_compliant_components', 0)
                
                # Count critical and high issues
                critical_issues = sum(1 for f in findings if f.get('severity') == 'critical')
                high_issues = sum(1 for f in findings if f.get('severity') == 'high')
                
                # Update the database record
                old_compliance = report.compliance_percentage
                report.compliance_percentage = compliance_percentage
                report.total_findings = total_findings
                report.critical_issues = critical_issues
                report.high_issues = high_issues
                report.compliant_items = compliant_items
                report.non_compliant_items = non_compliant_items
                
                # Only print if something changed
                if old_compliance != compliance_percentage:
                    print(f"Updated {report.filename}: {old_compliance}% -> {compliance_percentage}%")
                    updated_count += 1
                else:
                    print(f"No change needed for {report.filename}: {compliance_percentage}%")
                
            except Exception as e:
                print(f"Error processing {report.filename}: {str(e)}")
                error_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"\nSummary:")
        print(f"Total reports processed: {len(reports)}")
        print(f"Reports updated: {updated_count}")
        print(f"Reports unchanged: {len(reports) - updated_count - error_count}")
        print(f"Errors encountered: {error_count}")

if __name__ == '__main__':
    fix_compliance_data()