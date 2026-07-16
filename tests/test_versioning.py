"""
Unit tests for versioning system
"""

import pytest
from app.versioning.matcher import VersionMatcher
from app.versioning.manager import VersionManager


class TestVersioning:
    """Test cases for versioning system"""
    
    def test_path_based_matching(self):
        """Test path-based matching logic"""
        v1_nodes = [
            {'id': 1, 'heading': 'Introduction', 'level': 1, 'parent_id': None},
            {'id': 2, 'heading': 'Safety', 'level': 1, 'parent_id': None},
            {'id': 3, 'heading': 'Warnings', 'level': 2, 'parent_id': 2},
        ]
        
        v2_nodes = [
            {'id': 10, 'heading': 'Introduction', 'level': 1, 'parent_id': None},
            {'id': 20, 'heading': 'Safety', 'level': 1, 'parent_id': None},
            {'id': 30, 'heading': 'Warnings', 'level': 2, 'parent_id': 20},
        ]
        
        matcher = VersionMatcher()
        matches = matcher.match_nodes(v1_nodes, v2_nodes)
        
        # Check matches
        assert matches.get(1) == 10
        assert matches.get(2) == 20
        assert matches.get(3) == 30
    
    def test_fuzzy_matching_moved_sections(self):
        """Test fuzzy matching when sections are moved"""
        v1_nodes = [
            {'id': 1, 'heading': 'Introduction', 'level': 1, 'parent_id': None},
            {'id': 2, 'heading': 'Safety Warnings', 'level': 2, 'parent_id': 1},
        ]
        
        v2_nodes = [
            {'id': 10, 'heading': 'Introduction', 'level': 1, 'parent_id': None},
            {'id': 20, 'heading': 'Safety Warnings', 'level': 1, 'parent_id': None},  # Moved to level 1
        ]
        
        matcher = VersionMatcher(threshold=80)
        matches = matcher.match_nodes(v1_nodes, v2_nodes)
        
        # Should still match despite different level
        assert matches.get(2) == 20
    
    def test_hash_based_matching(self):
        """Test hash-based matching for identical content"""
        v1_nodes = [
            {'id': 1, 'heading': 'Test', 'level': 1, 'content_hash': 'abc123', 'parent_id': None},
        ]
        
        v2_nodes = [
            {'id': 10, 'heading': 'Test', 'level': 1, 'content_hash': 'abc123', 'parent_id': None},
        ]
        
        matcher = VersionMatcher()
        matches = matcher.match_nodes(v1_nodes, v2_nodes)
        
        assert matches.get(1) == 10