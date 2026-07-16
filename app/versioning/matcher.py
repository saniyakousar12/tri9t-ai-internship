"""
Version matcher for linking nodes across document versions
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from rapidfuzz import fuzz
import hashlib
import logging

logger = logging.getLogger(__name__)


class VersionMatcher:
    """Match nodes across document versions"""
    
    def __init__(self, threshold: int = 85):
        self.threshold = threshold
    
    def match_nodes(
        self,
        v1_nodes: List[Dict],
        v2_nodes: List[Dict]
    ) -> Dict[int, int]:
        """
        Match nodes from version 1 to version 2
        
        Returns: dict mapping v1_node_id -> v2_node_id
        """
        matches = {}
        unmatched_v1 = [node for node in v1_nodes]
        unmatched_v2 = [node for node in v2_nodes]
        
        # Strategy 1: Path-based matching
        logger.info("Attempting path-based matching...")
        for v1_node in unmatched_v1[:]:
            v1_path = self._get_path(v1_node, v1_nodes)
            
            # Find best match in v2
            best_match = None
            best_score = 0
            
            for v2_node in unmatched_v2:
                v2_path = self._get_path(v2_node, v2_nodes)
                
                if v1_path == v2_path:
                    score = 100
                else:
                    # Calculate path similarity
                    score = fuzz.ratio(v1_path, v2_path)
                
                if score > best_score:
                    best_score = score
                    best_match = v2_node
            
            if best_match and best_score >= self.threshold:
                matches[v1_node['id']] = best_match['id']
                unmatched_v1.remove(v1_node)
                unmatched_v2.remove(best_match)
                logger.debug(f"Matched: {v1_node['heading']} -> {best_match['heading']} (score: {best_score})")
        
        # Strategy 2: Fuzzy title matching for remaining nodes
        logger.info(f"Attempting fuzzy matching for {len(unmatched_v1)} remaining nodes...")
        for v1_node in unmatched_v1[:]:
            best_match = None
            best_score = 0
            
            for v2_node in unmatched_v2:
                score = fuzz.ratio(
                    v1_node['heading'].lower(),
                    v2_node['heading'].lower()
                )
                
                if score > best_score:
                    best_score = score
                    best_match = v2_node
            
            if best_match and best_score >= self.threshold:
                matches[v1_node['id']] = best_match['id']
                unmatched_v1.remove(v1_node)
                unmatched_v2.remove(best_match)
                logger.debug(f"Fuzzy matched: {v1_node['heading']} -> {best_match['heading']} (score: {best_score})")
        
        # Strategy 3: Content hash matching for remaining
        logger.info(f"Attempting hash matching for {len(unmatched_v1)} remaining nodes...")
        for v1_node in unmatched_v1[:]:
            for v2_node in unmatched_v2:
                if v1_node['content_hash'] == v2_node['content_hash']:
                    matches[v1_node['id']] = v2_node['id']
                    unmatched_v1.remove(v1_node)
                    unmatched_v2.remove(v2_node)
                    logger.debug(f"Hash matched: {v1_node['heading']} -> {v2_node['heading']}")
                    break
        
        logger.info(f"Matched {len(matches)} nodes. Unmatched: v1={len(unmatched_v1)}, v2={len(unmatched_v2)}")
        return matches
    
    def _get_path(self, node: Dict, all_nodes: List[Dict]) -> str:
        """Generate hierarchical path for a node"""
        path_parts = [node['heading']]
        current = node
        
        while current.get('parent_id'):
            parent = self._find_node_by_id(current['parent_id'], all_nodes)
            if parent:
                path_parts.insert(0, parent['heading'])
                current = parent
            else:
                break
        
        return '/'.join(path_parts)
    
    def _find_node_by_id(self, node_id: int, nodes: List[Dict]) -> Optional[Dict]:
        """Find node by ID in a list"""
        for node in nodes:
            if node['id'] == node_id:
                return node
        return None