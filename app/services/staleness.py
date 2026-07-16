"""
Staleness detection service for generated test cases
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import logging

from app.models.node import Node
from app.models.document import Document
from app.models.generated_test import GeneratedTest

logger = logging.getLogger(__name__)


class StalenessChecker:
    """Check if generated test cases are still valid"""
    
    def check_staleness(self, generated_test: GeneratedTest, db: Session) -> Dict:
        """
        Check staleness of generated test cases
        
        Returns:
            Dict with staleness information
        """
        selection_id = generated_test.selection_id
        version_at_generation = generated_test.version_at_generation
        
        # Get current version
        current_doc = db.query(Document).order_by(Document.version.desc()).first()
        if not current_doc:
            return {
                "is_stale": True,
                "message": "No current document version found",
                "stale_nodes": [],
                "changed_nodes": []
            }
        
        current_version = current_doc.version
        
        # Get nodes in selection at generation time
        result = db.execute(
            "SELECT node_id FROM selection_nodes WHERE selection_id = ?",
            (selection_id,)
        )
        node_ids = [row[0] for row in result]
        
        if not node_ids:
            return {
                "is_stale": False,
                "message": "No nodes in selection",
                "stale_nodes": [],
                "changed_nodes": []
            }
        
        stale_nodes = []
        changed_nodes = []
        
        for node_id in node_ids:
            # Get the node at generation time
            gen_doc = db.query(Document).filter(
                Document.version == version_at_generation
            ).first()
            
            if not gen_doc:
                stale_nodes.append({
                    "node_id": node_id,
                    "reason": f"Version {version_at_generation} not found",
                    "severity": "critical"
                })
                continue
            
            old_node = db.query(Node).filter(
                Node.id == node_id,
                Node.document_id == gen_doc.id
            ).first()
            
            if not old_node:
                stale_nodes.append({
                    "node_id": node_id,
                    "reason": "Node not found in generation version",
                    "severity": "critical"
                })
                continue
            
            # Find current version of this logical node
            current_node = None
            if old_node.logical_id:
                current_node = db.query(Node).filter(
                    Node.logical_id == old_node.logical_id,
                    Node.document_id == current_doc.id
                ).first()
            
            if not current_node:
                # Try to find by heading
                current_node = db.query(Node).filter(
                    Node.heading == old_node.heading,
                    Node.document_id == current_doc.id
                ).first()
            
            if not current_node:
                stale_nodes.append({
                    "node_id": node_id,
                    "reason": "Node no longer exists in current version",
                    "severity": "critical"
                })
                continue
            
            # Check if content changed
            if old_node.content_hash != current_node.content_hash:
                changed_nodes.append({
                    "node_id": node_id,
                    "old_hash": old_node.content_hash,
                    "new_hash": current_node.content_hash,
                    "reason": "Content has changed",
                    "severity": "warning"
                })
        
        # Determine overall staleness
        is_stale = len(stale_nodes) > 0 or len(changed_nodes) > 0
        
        # Generate message
        message = self._generate_message(stale_nodes, changed_nodes)
        
        return {
            "is_stale": is_stale,
            "stale_nodes": stale_nodes,
            "changed_nodes": changed_nodes,
            "version_at_generation": version_at_generation,
            "current_version": current_version,
            "message": message
        }
    
    def _generate_message(self, stale_nodes: List, changed_nodes: List) -> str:
        """Generate human-readable staleness message"""
        if not stale_nodes and not changed_nodes:
            return "✅ Test cases are up-to-date with current document"
        
        messages = []
        
        if stale_nodes:
            messages.append(f"⚠️ {len(stale_nodes)} node(s) no longer exist in current version")
        
        if changed_nodes:
            messages.append(f"⚠️ {len(changed_nodes)} node(s) have changed content")
        
        return " | ".join(messages) + " - Manual review recommended"