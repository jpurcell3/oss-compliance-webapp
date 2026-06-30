#!/usr/bin/env python3
import requests
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def trigger_scan_async(repo_name, github_instance='eos2git', use_enhanced=False):
    """Trigger scan via web application asynchronously"""
    print(f"[START] Initiating background scan for: {repo_name}")
    print(f"[CONFIG] GitHub instance: {github_instance}")
    print(f"[CONFIG] Scan type: {'enhanced' if use_enhanced else 'basic'}")
    
    scan_url = "http://localhost:5001/scan"
    data = {
        'scan_type': 'remote',
        'repo_input': repo_name,
        'use_enhanced': str(use_enhanced).lower(),
        'github_instance': github_instance
    }
    
    try:
        print("[PROGRESS] Submitting scan request to web application...")
        # Use curl to trigger scan in background (fire-and-forget)
        curl_cmd = [
            'curl', '-X', 'POST', '-d',
            f"scan_type=remote&repo_input={repo_name}&use_enhanced={str(use_enhanced).lower()}&github_instance={github_instance}",
            'http://localhost:5001/scan',
            '--max-time', '3'  # Only wait 3 seconds for connection
        ]
        
        # Start process in background
        process = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[PROGRESS] Scan request submitted (background process: {process.pid})")
        print(f"[INFO] Web application is generating report...")
        return True
            
    except Exception as e:
        print(f"[ERROR] Error triggering scan: {e}")
        return False

def monitor_reports_directory(repo_name, timeout=300):
    """Monitor reports directory for new scan completion"""
    print(f"[MONITOR] Watching for scan completion...")
    print(f"[MONITOR] Timeout: {timeout} seconds")
    
    reports_dir = Path('reports')
    if not reports_dir.exists():
        print(f"[ERROR] Reports directory not found: {reports_dir}")
        return None
    
    # Get current report count
    initial_reports = list(reports_dir.glob(f"*{repo_name}*.json"))
    initial_count = len(initial_reports)
    
    print(f"[MONITOR] Initial report count: {initial_count}")
    
    start_time = time.time()
    check_interval = 5  # Check every 5 seconds
    
    while time.time() - start_time < timeout:
        current_reports = list(reports_dir.glob(f"*{repo_name}*.json"))
        current_count = len(current_reports)
        
        if current_count > initial_count:
            # Find the newest report
            latest_report = max(current_reports, key=lambda p: p.stat().st_mtime)
            print(f"[MONITOR] New report detected: {latest_report.name}")
            print(f"[SUCCESS] Scan completed successfully")
            return latest_report
        
        print(f"[MONITOR] Waiting... (elapsed: {int(time.time() - start_time)}s)")
        time.sleep(check_interval)
    
    print(f"[ERROR] Timeout waiting for scan completion")
    return None

def load_report(report_path):
    """Load and parse report JSON"""
    print(f"[PROGRESS] Loading report: {report_path.name}")
    
    try:
        with open(report_path, 'r') as f:
            report = json.load(f)
        print(f"[SUCCESS] Report loaded successfully")
        return report
    except Exception as e:
        print(f"[ERROR] Error loading report: {e}")
        return None

def generate_pdf_report(report, output_file):
    """Generate PDF report from scan results"""
    print(f"[PROGRESS] Generating PDF report: {output_file}")
    
    try:
        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph("OSS Compliance Scan Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Scan metadata - handle different report structures
        scan_metadata = report.get('scan_metadata', {})
        summary = report.get('summary', {})
        scan_summary = report.get('scan_summary', {})
        
        repo_name = scan_metadata.get('repository_name') or summary.get('repository_name') or scan_summary.get('repository_name') or 'Unknown'
        scan_time = scan_metadata.get('scanned_at') or summary.get('scan_timestamp') or str(datetime.now())
        scan_type = scan_metadata.get('scan_method') or scan_summary.get('scan_type') or 'Unknown'
        
        metadata_data = [
            ['Repository:', repo_name],
            ['Scan Time:', scan_time],
            ['Scan Type:', scan_type],
        ]
        
        metadata_table = Table(metadata_data, colWidths=[100, 300])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 12))
        
        # Summary section - use actual report structure
        summary_title = Paragraph("Scan Summary", styles['Heading2'])
        story.append(summary_title)
        
        # Get component analysis data
        component_analysis = summary.get('component_analysis', {})
        total_components = component_analysis.get('total_components', 0)
        compliant_components = component_analysis.get('compliant_components', 0)
        non_compliant_components = component_analysis.get('non_compliant_components', 0)
        compliance_percentage = component_analysis.get('component_compliance_percentage', 0)
        
        # Get scan summary data
        total_findings = scan_summary.get('total_findings', 0)
        compliant_checks = scan_summary.get('compliant_checks', 0)
        non_compliant_checks = scan_summary.get('non_compliant_checks', 0)
        
        summary_data = [
            ['Total Components:', str(total_components)],
            ['Compliant Components:', str(compliant_components)],
            ['Non-Compliant Components:', str(non_compliant_components)],
            ['Compliance Percentage:', f"{compliance_percentage}%"],
            ['Total Findings:', str(total_findings)],
            ['Compliant Checks:', str(compliant_checks)],
            ['Non-Compliant Checks:', str(non_compliant_checks)],
        ]
        
        summary_table = Table(summary_data, colWidths=[150, 100])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.beige),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWCOLORS', (0, 1), (0, 1), colors.lightgrey),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 12))
        
        # Findings section - use component mappings
        findings_title = Paragraph("Component Compliance Details", styles['Heading2'])
        story.append(findings_title)
        
        component_mappings = report.get('component_mappings', [])
        if component_mappings:
            findings_data = [['Component', 'Version', 'Ecosystem', 'Status', 'Recommendation']]
            for mapping in component_mappings[:50]:  # Limit to first 50 components
                component = mapping.get('component', {})
                component_name = component.get('name', 'N/A')[:25]
                version = component.get('version', 'N/A')[:15]
                ecosystem = component.get('ecosystem', 'N/A')
                compliance_status = mapping.get('compliance_status', 'N/A')
                recommendations = mapping.get('recommendations', [])
                recommendation = recommendations[0][:40] if recommendations else 'N/A'
                
                findings_data.append([component_name, version, ecosystem, compliance_status, recommendation])
            
            findings_table = Table(findings_data, colWidths=[70, 50, 50, 60, 120])
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWCOLORS', (0, 1), (0, -1), colors.beige),
            ]))
            story.append(findings_table)
            
            if len(component_mappings) > 50:
                more_info = Paragraph(f"... and {len(component_mappings) - 50} more components", styles['Normal'])
                story.append(more_info)
        else:
            no_findings = Paragraph("No component data available.", styles['Normal'])
            story.append(no_findings)
        
        # Build PDF
        doc.build(story)
        print(f"[SUCCESS] PDF report generated: {output_file}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error generating PDF: {e}")
        return False

def main():
    """Main execution function"""
    print("=" * 70)
    print("OSS Compliance Scan - fusion-stage-backend Repository")
    print("=" * 70)
    print()
    
    # Trigger the scan via web application
    scan_success = trigger_scan_async('fusion-stage-backend', 'eos2git', use_enhanced=True)
    
    if scan_success:
        # Monitor for completion
        report_file = monitor_reports_directory('fusion-stage-backend', timeout=300)
        
        if report_file:
            # Load the report
            report = load_report(report_file)
            
            if report:
                # Generate PDF report
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pdf_file = f"fusion_stage_backend_scan_{timestamp}.pdf"
                
                success = generate_pdf_report(report, pdf_file)
                
                if success:
                    print()
                    print("=" * 70)
                    print("SCAN COMPLETION SUMMARY")
                    print("=" * 70)
                    
                    # Get correct metrics from report
                    component_analysis = report.get('summary', {}).get('component_analysis', {})
                    scan_summary = report.get('scan_summary', {})
                    
                    print(f"[RESULT] Total Components: {component_analysis.get('total_components', 0)}")
                    print(f"[RESULT] Compliant Components: {component_analysis.get('compliant_components', 0)}")
                    print(f"[RESULT] Non-Compliant Components: {component_analysis.get('non_compliant_components', 0)}")
                    print(f"[RESULT] Compliance Percentage: {component_analysis.get('component_compliance_percentage', 0)}%")
                    print(f"[RESULT] Total Findings: {scan_summary.get('total_findings', 0)}")
                    print(f"[RESULT] PDF report: {pdf_file}")
                    print(f"[LOCATION] {Path.cwd() / pdf_file}")
                    print("=" * 70)
                else:
                    print("[ERROR] Failed to generate PDF report")
            else:
                print("[ERROR] Failed to load report")
        else:
            print("[ERROR] Scan did not complete within timeout period")
    else:
        print("[ERROR] Failed to trigger scan")

if __name__ == "__main__":
    main()