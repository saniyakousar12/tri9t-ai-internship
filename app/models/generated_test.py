"""
Generated Test model for storing LLM outputs in MongoDB
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import JSON
from app.database import Base


class GeneratedTest(Base):
    """Generated test cases from LLM"""
    __tablename__ = "generated_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    selection_id = Column(Integer, ForeignKey("selections.id"), nullable=False, index=True)
    
    # Store LLM output as JSON
    output = Column(JSON, nullable=False)
    
    # Version tracking
    version_at_generation = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<GeneratedTest(selection_id={self.selection_id}, version={self.version_at_generation})>"