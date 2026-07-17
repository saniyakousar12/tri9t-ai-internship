"""
Unit tests for versioning system
"""

import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.versioning.matcher import VersionMatcher


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
            {'id': 20, 'heading': 'Safety Warnings', 'level': 1, 'parent_id': None},
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
    
    def test_path_generation(self):
        """Test hierarchical path generation"""
        nodes = [
            {'id': 1, 'heading': 'Introduction', 'level': 1, 'parent_id': None},
            {'id': 2, 'heading': 'Safety', 'level': 1, 'parent_id': None},
            {'id': 3, 'heading': 'Warnings', 'level': 2, 'parent_id': 2},
            {'id': 4, 'heading': 'Fire Hazards', 'level': 3, 'parent_id': 3},
        ]
        
        matcher = VersionMatcher()
        
        path1 = matcher._get_path(nodes[0], nodes)  # Introduction
        path2 = matcher._get_path(nodes[2], nodes)  # Warnings
        path3 = matcher._get_path(nodes[3], nodes)  # Fire Hazards
        
        assert path1 == "Introduction"
        assert path2 == "Safety/Warnings"
        assert path3 == "Safety/Warnings/Fire Hazards"