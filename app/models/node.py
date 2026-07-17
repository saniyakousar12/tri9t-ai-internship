"""
Node model for document hierarchy
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Node(Base):
    """Node representing a section/heading in the document"""
    __tablename__ = "nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    # Node content
    heading = Column(String(500), nullable=False)
    level = Column(Integer, nullable=False)
    body_text = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey("nodes.id"), nullable=True, index=True)
    
    # Logical ID for cross-version matching
    logical_id = Column(String(36), nullable=True, index=True)
    
    # Position in document
    page_number = Column(Integer, nullable=True)
    position = Column(Integer, nullable=True)
    
    # Relationships
    parent = relationship("Node", remote_side=[id], backref="children")
    
    # Indexes for faster queries
    __table_args__ = (
        Index('idx_node_document_parent', 'document_id', 'parent_id'),
        Index('idx_node_logical_id_version', 'logical_id', 'document_id'),
    )
    
    def __repr__(self):
        return f"<Node(id={self.id}, heading='{self.heading[:30]}...', level={self.level})>"