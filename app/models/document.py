# app/models/document.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    filename = Column(String(255))
    created_at = Column(DateTime)
    processed_at = Column(DateTime)
