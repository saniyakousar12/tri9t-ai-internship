"""
Database initialization script
Run this once to create the database tables
"""

from app.database import init_db, engine
from app.models import document, node, selection, generated_test
from app.models.document import Document
from app.models.node import Node
from app.models.selection import Selection
from app.models.generated_test import GeneratedTest

def create_database():
    """Create all database tables"""
    print("🔄 Creating database tables...")
    init_db()
    print("✅ Database tables created successfully!")
    print(f"📁 Database: {engine.url}")

if __name__ == "__main__":
    create_database()