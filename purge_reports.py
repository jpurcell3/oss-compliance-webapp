"""
Purge all reports from the database
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Report
from flask import Flask

# Create a minimal Flask app for database operations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/reports.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

if __name__ == '__main__':
    with app.app_context():
        # Count existing reports
        count = Report.query.count()
        print(f"Found {count} reports in database")
        
        if count > 0:
            # Delete all reports
            Report.query.delete()
            db.session.commit()
            print(f"Successfully deleted all {count} reports")
        else:
            print("No reports to delete")
        
        # Verify deletion
        remaining = Report.query.count()
        print(f"Reports remaining: {remaining}")
