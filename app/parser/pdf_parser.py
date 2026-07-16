"""
PDF Parser using PyMuPDF (fitz) for the CT-200 manual
"""

import fitz
import re
import hashlib
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """Parse PDF and extract hierarchical structure"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = None
        self.nodes = []
        self._heading_patterns = [
            r'^(\d+\.\d+\.\d+)\s+(.+)',  # 1.2.3 Heading
            r'^(\d+\.\d+)\s+(.+)',        # 1.2 Heading
            r'^(\d+)\s+(.+)',             # 1 Heading
        ]
    
    def parse_structure(self) -> List[Dict]:
        """Parse PDF and return hierarchical structure"""
        try:
            self.doc = fitz.open(self.file_path)
            logger.info(f"Opened PDF with {len(self.doc)} pages")
            
            # Try TOC first
            toc = self.doc.get_toc()
            if toc and len(toc) > 0:
                logger.info(f"Found TOC with {len(toc)} entries")
                return self._parse_toc(toc)
            else:
                logger.info("No TOC found, falling back to heading detection")
                return self._parse_headings_by_font()
                
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise
        finally:
            if self.doc:
                self.doc.close()
    
    def _parse_toc(self, toc: List[Tuple[int, str, int]]) -> List[Dict]:
        """Parse Table of Contents structure"""
        nodes = []
        parent_stack = []
        
        for level, title, page_num in toc:
            # Generate content hash
            content_hash = self._generate_hash(title, "", level)
            
            # Find parent based on level
            parent_id = None
            while parent_stack and parent_stack[-1]['level'] >= level:
                parent_stack.pop()
            
            if parent_stack:
                parent_id = parent_stack[-1]['id']
            
            node = {
                'id': len(nodes) + 1,
                'heading': title,
                'level': level,
                'body_text': self._extract_body_text(page_num, title),
                'content_hash': content_hash,
                'parent_id': parent_id,
                'logical_id': str(hashlib.md5(f"{title}_{level}".encode()).hexdigest()),
                'page_number': page_num,
                'position': len(nodes)
            }
            
            nodes.append(node)
            parent_stack.append(node)
        
        return nodes
    
    def _parse_headings_by_font(self) -> List[Dict]:
        """Fallback: Detect headings by font size and formatting"""
        nodes = []
        current_level = 0
        parent_stack = []
        heading_count = 0
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            blocks = page.get_text("dict")['blocks']
            
            for block in blocks:
                if 'lines' in block:
                    for line in block['lines']:
                        text = ""
                        font_size = 0
                        
                        for span in line['spans']:
                            text += span['text']
                            font_size = max(font_size, span['size'])
                        
                        text = text.strip()
                        if not text:
                            continue
                        
                        # Determine if this is a heading based on font size
                        level = self._detect_heading_level(font_size, text)
                        
                        if level > 0:
                            heading_count += 1
                            # Generate content hash
                            content_hash = self._generate_hash(text, "", level)
                            
                            # Find parent
                            parent_id = None
                            while parent_stack and parent_stack[-1]['level'] >= level:
                                parent_stack.pop()
                            
                            if parent_stack:
                                parent_id = parent_stack[-1]['id']
                            
                            node = {
                                'id': heading_count,
                                'heading': text,
                                'level': level,
                                'body_text': self._extract_body_text_after_heading(page_num, text),
                                'content_hash': content_hash,
                                'parent_id': parent_id,
                                'logical_id': str(hashlib.md5(f"{text}_{level}".encode()).hexdigest()),
                                'page_number': page_num + 1,
                                'position': heading_count - 1
                            }
                            
                            nodes.append(node)
                            parent_stack.append(node)
        
        return nodes
    
    def _detect_heading_level(self, font_size: float, text: str) -> int:
        """Detect heading level based on font size and numbering"""
        # Check if text has numbering pattern
        for pattern in self._heading_patterns:
            match = re.match(pattern, text)
            if match:
                # Count dots to determine level
                numbering = match.group(1)
                level = numbering.count('.') + 1
                return level
        
        # Fallback to font size heuristics
        if font_size >= 18:
            return 1
        elif font_size >= 14:
            return 2
        elif font_size >= 12:
            return 3
        else:
            return 0  # Not a heading
    
    def _extract_body_text(self, page_num: int, heading: str) -> str:
        """Extract body text following a heading"""
        # Get page content
        page = self.doc[page_num - 1]
        text = page.get_text()
        
        # Find heading in text and extract following content
        lines = text.split('\n')
        body = []
        found = False
        
        for i, line in enumerate(lines):
            if heading in line and not found:
                found = True
                continue
            if found:
                # Stop at next heading (detected by number pattern or all caps)
                if re.match(r'^(\d+\.\d+\.\d+|\d+\.\d+|\d+)\s+', line):
                    break
                if line.strip():
                    body.append(line.strip())
        
        return '\n'.join(body[:10])  # Limit to 10 lines for initial extraction
    
    def _extract_body_text_after_heading(self, page_num: int, heading: str) -> str:
        """Extract body text after a heading on the same page"""
        # Similar to above but handles the case where heading is detected by font
        return ""  # Simplified for now
    
    def _generate_hash(self, heading: str, body: str, level: int) -> str:
        """Generate SHA256 hash for content"""
        content = f"{heading}{body}{level}"
        return hashlib.sha256(content.encode()).hexdigest()