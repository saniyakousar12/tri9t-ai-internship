"""
Unit tests for PDF parser
"""

import sys
import os
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parser.pdf_parser import PDFParser


class TestPDFParser:
    """Test cases for PDF parser"""
    
    def test_parser_initialization(self):
        """Test that parser can be initialized"""
        parser = PDFParser("test.pdf")
        assert parser is not None
        assert parser.file_path is not None
    
    def test_heading_detection_patterns(self):
        """Test heading detection with various patterns"""
        parser = PDFParser("test.pdf")
        
        # Test numbered headings - these should be detected
        assert parser._detect_heading_level("1. Introduction") == 1
        assert parser._detect_heading_level("1.2 Safety") == 2
        assert parser._detect_heading_level("1.2.3 Warnings") == 3
        
        # Test ALL CAPS headings
        assert parser._detect_heading_level("SAFETY WARNINGS") == 1
        
        # Test Roman numerals
        assert parser._detect_heading_level("I. Introduction") == 1
        assert parser._detect_heading_level("II. Safety") == 1
        
        # Test title case with keywords
        assert parser._detect_heading_level("Safety Introduction") == 2
        
        # Test non-headings - should return 0
        assert parser._detect_heading_level("This is a paragraph.") == 0
        assert parser._detect_heading_level("") == 0
        assert parser._detect_heading_level("abc") == 0
    
    def test_hash_generation(self):
        """Test content hash generation"""
        parser = PDFParser("test.pdf")
        
        hash1 = parser._generate_hash("Safety", "Warning content", 2)
        hash2 = parser._generate_hash("Safety", "Warning content", 2)
        hash3 = parser._generate_hash("Safety", "Different content", 2)
        
        # Same content should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        assert hash1 != hash3
        
        # Hash should be 64 characters (SHA256)
        assert len(hash1) == 64
    
    def test_parse_pdf_file_not_found(self):
        """Test parsing when file doesn't exist"""
        parser = PDFParser("nonexistent.pdf")
        
        with pytest.raises(Exception):
            parser.parse_structure()