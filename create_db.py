"""
Database initialization script
Run this once to create the database tables
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, engine
from app.models import Document, Node, Selection, GeneratedTest

def create_database():
    """Create all database tables"""
    print("🔄 Creating database tables...")
    init_db()
    print(f"✅ Database created successfully!")
    print(f"📁 Database: {engine.url}")

if __name__ == "__main__":
    create_database()