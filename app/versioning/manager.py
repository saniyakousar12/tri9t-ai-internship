"""
Version management service
"""

from typing import Optional, Dict, List
from sqlalchemy.orm import Session
import hashlib
import logging

from app.models.node import Node
from app.models.document import Document
from app.versioning.matcher import VersionMatcher

logger = logging.getLogger(__name__)


class VersionManager:
    """Manage document versions and detect changes"""
    
    def __init__(self):
        self.matcher = VersionMatcher()
    
    def link_with_previous_version(self, doc_id: int, db: Session):
        """
        Link nodes in new version with previous version
        """
        # Get current document
        current_doc = db.query(Document).filter(Document.id == doc_id).first()
        if not current_doc:
            raise ValueError(f"Document {doc_id} not found")
        
        # Get previous version
        prev_doc = db.query(Document).filter(
            Document.version == current_doc.version - 1
        ).first()
        
        if not prev_doc:
            logger.info(f"No previous version found for version {current_doc.version}")
            return
        
        # Get nodes from both versions
        current_nodes = db.query(Node).filter(Node.document_id == doc_id).all()
        prev_nodes = db.query(Node).filter(Node.document_id == prev_doc.id).all()
        
        # Convert to dict for matcher
        current_dict = [
            {
                'id': n.id,
                'heading': n.heading,
                'body_text': n.body_text,
                'level': n.level,
                'content_hash': n.content_hash,
                'parent_id': n.parent_id
            }
            for n in current_nodes
        ]
        
        prev_dict = [
            {
                'id': n.id,
                'heading': n.heading,
                'body_text': n.body_text,
                'level': n.level,
                'content_hash': n.content_hash,
                'parent_id': n.parent_id
            }
            for n in prev_nodes
        ]
        
        # Match nodes
        matches = self.matcher.match_nodes(prev_dict, current_dict)
        
        # Update logical_id for matched nodes
        for prev_id, current_id in matches.items():
            prev_node = db.query(Node).filter(Node.id == prev_id).first()
            current_node = db.query(Node).filter(Node.id == current_id).first()
            
            if prev_node and current_node:
                # Use prev_node's logical_id if it exists, otherwise create new
                if prev_node.logical_id:
                    current_node.logical_id = prev_node.logical_id
                else:
                    # Generate logical_id if not exists
                    logical_id = hashlib.md5(
                        f"{prev_node.heading}_{prev_node.level}".encode()
                    ).hexdigest()
                    prev_node.logical_id = logical_id
                    current_node.logical_id = logical_id
        
        db.commit()
        logger.info(f"Linked {len(matches)} nodes between versions")
    
    def has_node_changed(self, logical_id: str, version: int, db: Session) -> bool:
        """
        Check if a node has changed across versions
        """
        if not logical_id:
            return False
        
        # Get current version node
        current_doc = db.query(Document).filter(Document.version == version).first()
        if not current_doc:
            return False
        
        current_node = db.query(Node).filter(
            Node.logical_id == logical_id,
            Node.document_id == current_doc.id
        ).first()
        
        if not current_node:
            return True  # Node not found, considered changed
        
        # Get previous version
        if version <= 1:
            return False
        
        prev_doc = db.query(Document).filter(
            Document.version == version - 1
        ).first()
        
        if not prev_doc:
            return False
        
        prev_node = db.query(Node).filter(
            Node.logical_id == logical_id,
            Node.document_id == prev_doc.id
        ).first()
        
        if not prev_node:
            return True  # Node didn't exist in previous version
        
        # Compare hashes
        return prev_node.content_hash != current_node.content_hash
    
    def generate_diff(
        self,
        old_text: str,
        new_text: str,
        old_hash: str,
        new_hash: str
    ) -> Dict:
        """
        Generate a simple diff between two texts
        """
        if old_hash == new_hash:
            return {
                'changed': False,
                'summary': 'No changes detected'
            }
        
        # Simple diff - count words changed
        old_words = set(old_text.split())
        new_words = set(new_text.split())
        
        added = new_words - old_words
        removed = old_words - new_words
        
        return {
            'changed': True,
            'summary': f'Changed: +{len(added)} words, -{len(removed)} words',
            'added_words': list(added)[:5],  # Show first 5
            'removed_words': list(removed)[:5]
        }