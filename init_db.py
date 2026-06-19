"""
Initialize the database for OSS Compliance Web Application
Run this script once to create the database tables.
"""
from app import app, db

if __name__ == '__main__':
    with app.application_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        print(f"Database location: {app.config['SQLALCHEMY_DATABASE_URI']}")
