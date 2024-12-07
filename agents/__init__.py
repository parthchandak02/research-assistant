"""Research Assistant Agents.

This package contains the core agents for the research assistant system:
- DocumentProcessor: Converts PDFs to markdown and extracts images
"""

from .document_processor import DocumentProcessor

__all__ = [
    'DocumentProcessor',
]
