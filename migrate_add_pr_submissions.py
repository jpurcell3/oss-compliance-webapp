#!/usr/bin/env python3
"""
Migration script to add the pr_submissions table to the existing database
"""
import sqlite3
import os

def migrate():
    """Add pr_submissions table to the database"""
    # Check both possible locations
    db_path = 'instance/reports.db' if os.path.exists('instance/reports.db') else 'reports.db'
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. No migration needed.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if pr_submissions table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pr_submissions'")
    if cursor.fetchone():
        print("pr_submissions table already exists. No migration needed.")
        conn.close()
        return
    
    # Create pr_submissions table
    cursor.execute('''
        CREATE TABLE pr_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            pr_url VARCHAR(500),
            pr_number INTEGER,
            submitter_username VARCHAR(100),
            submitter_email VARCHAR(255),
            github_instance VARCHAR(100),
            submission_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'pending',
            FOREIGN KEY (report_id) REFERENCES reports (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Successfully added pr_submissions table to database.")

if __name__ == '__main__':
    migrate()
