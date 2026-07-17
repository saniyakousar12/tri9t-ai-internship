"""
PDF Parser using pdfplumber (Pure Python - No compilation required)
"""

import re
import pdfplumber
import hashlib
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """Parse PDF and extract hierarchical structure using pdfplumber"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.nodes = []

    def parse_structure(self) -> List[Dict]:
        """Parse PDF and return hierarchical structure"""
        nodes = []
        heading_count = 0
        parent_stack = []

        try:
            with pdfplumber.open(self.file_path) as pdf:
                logger.info(f"Opened PDF with {len(pdf.pages)} pages")

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue

                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line or len(line) < 3:
                            continue

                        # Detect heading level
                        level = self._detect_heading_level(line)

                        if level > 0:
                            heading_count += 1
                            content_hash = self._generate_hash(line, "", level)

                            # Find parent based on level
                            parent_id = None
                            while parent_stack and parent_stack[-1]['level'] >= level:
                                parent_stack.pop()

                            if parent_stack:
                                parent_id = parent_stack[-1]['id']

                            node = {
                                'id': heading_count,
                                'heading': line,
                                'level': level,
                                'body_text': self._extract_body_text(page, line),
                                'content_hash': content_hash,
                                'parent_id': parent_id,
                                'logical_id': hashlib.md5(f"{line}_{level}".encode()).hexdigest(),
                                'page_number': page_num,
                                'position': heading_count - 1
                            }

                            nodes.append(node)
                            parent_stack.append(node)

                logger.info(f"Parsed {len(nodes)} nodes from PDF")
                return nodes

        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise

    def _detect_heading_level(self, text: str) -> int:
        """Detect heading level based on patterns"""

        # Pattern 1: Numbered headings (1.2.3 Heading, 1.2 Heading, 1. Heading)
        patterns = [
            (r'^(\d+\.\d+\.\d+)\s+', 3),  # 1.2.3
            (r'^(\d+\.\d+)\s+', 2),       # 1.2
            (r'^(\d+)\.\s+', 1),          # 1. (handles "1. Introduction")
            (r'^(\d+)\s+', 1),            # 1 (fallback)
        ]

        for pattern, level in patterns:
            if re.match(pattern, text):
                return level

        # Pattern 2: Roman numerals (I. Introduction, II. Safety)
        # CHECK THIS BEFORE title case (Pattern 3)
        if re.match(r'^[IVXLCDM]+\.\s+', text):
            return 1

        # Pattern 3: ALL CAPS headings (SAFETY WARNINGS)
        if text.isupper() and len(text) > 5 and len(text.split()) > 1:
            return 1

        # Pattern 4: Title Case with specific words
        title_keywords = [
            'Introduction',
            'Safety',
            'Warning',
            'Caution',
            'Operation',
            'Maintenance',
            'Specifications'
        ]

        if any(keyword in text for keyword in title_keywords) and text.istitle():
            return 2

        return 0

    def _extract_body_text(self, page, heading: str) -> str:
        """Extract body text following a heading on the same page"""
        try:
            text = page.extract_text()
            if not text:
                return ""

            lines = text.split('\n')
            body_lines = []
            found = False

            for i, line in enumerate(lines):
                if heading in line and not found:
                    found = True
                    continue
                if found:
                    # Stop at next heading
                    if self._detect_heading_level(line.strip()) > 0:
                        break
                    if line.strip():
                        body_lines.append(line.strip())

            return '\n'.join(body_lines[:10])

        except Exception:
            return ""

    def _generate_hash(self, heading: str, body: str, level: int) -> str:
        """Generate SHA256 hash for content"""
        content = f"{heading}{body}{level}"
        return hashlib.sha256(content.encode()).hexdigest()