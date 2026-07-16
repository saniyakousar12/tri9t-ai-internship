"""
Unit tests for PDF parser
"""

import pytest
from pathlib import Path
from app.parser.pdf_parser import PDFParser


class TestPDFParser:
    """Test cases for PDF parser"""
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Path to sample PDF"""
        # This should point to a small test PDF
        return "data/ct200_manual.pdf"
    
    def test_duplicate_headings_get_unique_ids(self, sample_pdf_path):
        """Test that duplicate headings become distinct nodes"""
        parser = PDFParser(sample_pdf_path)
        nodes = parser.parse_structure()
        
        # Find duplicate headings
        headings = {}
        for node in nodes:
            if node['heading'] in headings:
                headings[node['heading']].append(node)
            else:
                headings[node['heading']] = [node]
        
        # For each duplicate heading, ensure unique IDs
        for heading, duplicates in headings.items():
            if len(duplicates) > 1:
                ids = [d['id'] for d in duplicates]
                assert len(set(ids)) == len(ids), f"Duplicate heading '{heading}' has duplicate IDs"
                
                # Ensure each has different parent (if applicable)
                for i, dup in enumerate(duplicates):
                    for j, other in enumerate(duplicates):
                        if i != j:
                            # They should have different parent or different position
                            if dup.get('parent_id') == other.get('parent_id'):
                                assert dup.get('position') != other.get('position'), \
                                    f"Duplicate headings with same parent: {heading}"
    
    def test_parent_child_relationships(self, sample_pdf_path):
        """Test that parent-child relationships are preserved"""
        parser = PDFParser(sample_pdf_path)
        nodes = parser.parse_structure()
        
        # Create lookup
        node_map = {n['id']: n for n in nodes}
        
        for node in nodes:
            if node.get('parent_id'):
                parent = node_map.get(node['parent_id'])
                assert parent is not None, f"Parent {node['parent_id']} not found"
                assert node['level'] > parent['level'], \
                    f"Child level ({node['level']}) should be greater than parent level ({parent['level']})"
    
    def test_heading_detection_with_inconsistent_formatting(self, sample_pdf_path):
        """Test that heading detection works with inconsistent formatting"""
        parser = PDFParser(sample_pdf_path)
        nodes = parser.parse_structure()
        
        # Check that we have some structure
        assert len(nodes) > 0, "No nodes parsed"
        
        # Check that levels are reasonable (1-5)
        for node in nodes:
            assert 1 <= node['level'] <= 5, f"Invalid level {node['level']}"
        
        # Check that each node has a content hash
        for node in nodes:
            assert 'content_hash' in node, "Missing content_hash"
            assert len(node['content_hash']) == 64, "Invalid hash length"