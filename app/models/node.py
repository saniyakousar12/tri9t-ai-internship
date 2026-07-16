# app/models/node.py
class Node(Base):
    __tablename__ = "nodes"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    heading = Column(String(500))
    level = Column(Integer)
    body_text = Column(Text)
    content_hash = Column(String(64))
    parent_id = Column(Integer, ForeignKey("nodes.id"))
    
    # Relationships
    children = relationship("Node", backref="parent", remote_side=[id])
    # For versioning: logical_id links nodes across versions
    logical_id = Column(String(36))  # UUID for matching across versions