"""
Document model for storing document metadata
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    """Document model for tracking versions"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=True)
    total_nodes = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Document(version={self.version}, filename={self.filename})>"