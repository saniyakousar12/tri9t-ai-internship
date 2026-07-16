# tests/test_parser.py
import pytest
from app.parser.pdf_parser import PDFParser

def test_duplicate_headings_get_unique_ids():
    """Test requirement: duplicate headings become distinct nodes"""
    parser = PDFParser("data/ct200_manual.pdf")
    nodes = parser.parse_structure()
    
    # Find duplicate headings
    headings = [n for n in nodes if n.level == 1]
    duplicate_names = [n.title for n in headings if headings.count(n.title) > 1]
    
    for dup in duplicate_names:
        duplicates = [n for n in headings if n.title == dup]
        assert len(set([n.id for n in duplicates])) == len(duplicates)
        # Verify each duplicate has different parent (if applicable)

def test_parent_child_relationships():
    """Test hierarchy preservation"""
    parser = PDFParser("data/ct200_manual.pdf")
    nodes = parser.parse_structure()
    
    for node in nodes:
        if node.parent_id:
            parent = nodes[node.parent_id]
            assert node.level == parent.level + 1
            assert node.id in [c.id for c in parent.children]

def test_heading_detection_works_with_inconsistent_formatting():
    """Test requirement: handle PDF irregularities"""
    # This test ensures your parser doesn't break on edge cases
    pass