"""
Selection models for storing user selections
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

# Junction table for Selection-Nodes many-to-many
selection_nodes = Table(
    "selection_nodes",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("selection_id", Integer, ForeignKey("selections.id")),
    Column("node_id", Integer, ForeignKey("nodes.id")),
    Column("node_version", Integer, nullable=False),
)


class Selection(Base):
    """User selection of document nodes"""
    __tablename__ = "selections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    nodes = relationship("Node", secondary=selection_nodes, backref="selections")
    
    def __repr__(self):
        return f"<Selection(id={self.id}, name='{self.name}', version={self.version})>"