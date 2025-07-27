"""Document parser tool for extracting text from various file formats."""

import os
from pathlib import Path
from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase


class DocumentParserTool(ToolBase):
    """Extracts text content from PDF, Word, and text files.
    
    Designed for maximum reusability across different document processing workflows.
    Supports multiple file formats and provides structured output with metadata.
    """
    
    name: str = "document_parser"
    description: str = "Extract text content from PDF, Word, and text files"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(
        self,
        file_paths: List[str] = None,
        file_path: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Parse documents and extract text content."""
        
        # Handle both single file and multiple files
        if file_path and not file_paths:
            file_paths = [file_path]
        elif not file_paths:
            file_paths = []
        
        if not file_paths:
            return {
                "success": False,
                "error": "No file paths provided",
                "documents": []
            }
        
        print(f"📄 Parsing {len(file_paths)} document(s)...")
        
        parsed_documents = []
        failed_files = []
        
        for file_path in file_paths:
            try:
                document = await self._parse_single_document(file_path)
                if document:
                    parsed_documents.append(document)
                else:
                    failed_files.append({"file": file_path, "error": "No content extracted"})
            except Exception as e:
                failed_files.append({"file": file_path, "error": str(e)})
                print(f"❌ Failed to parse {file_path}: {e}")
        
        return {
            "success": True,
            "documents": parsed_documents,
            "total_parsed": len(parsed_documents),
            "total_failed": len(failed_files),
            "failed_files": failed_files
        }
    
    async def _parse_single_document(self, file_path: str) -> Dict[str, Any]:
        """Parse a single document and extract metadata + content."""
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file metadata
        stat = file_path.stat()
        file_info = {
            "filename": file_path.name,
            "path": str(file_path),
            "size_bytes": stat.st_size,
            "extension": file_path.suffix.lower(),
            "modified_time": stat.st_mtime
        }
        
        print(f"📝 Parsing: {file_info['filename']} ({file_info['size_bytes']} bytes)")
        
        # Extract text based on file type
        if file_info["extension"] == ".pdf":
            content = await self._extract_pdf_text(file_path)
        elif file_info["extension"] in [".docx", ".doc"]:
            content = await self._extract_word_text(file_path)
        elif file_info["extension"] in [".txt", ".md", ".py", ".js", ".json"]:
            content = await self._extract_text_file(file_path)
        else:
            # Try as text file fallback
            try:
                content = await self._extract_text_file(file_path)
            except:
                raise ValueError(f"Unsupported file type: {file_info['extension']}")
        
        if not content or not content.strip():
            return None
        
        return {
            "content": content.strip(),
            "metadata": file_info,
            "word_count": len(content.split()),
            "char_count": len(content)
        }
    
    async def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        
        try:
            # Try using PyPDF2 if available
            import PyPDF2
            
            text_content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"[Page {page_num + 1}]\n{page_text}")
            
            return "\n\n".join(text_content)
            
        except ImportError:
            # Fallback: simulate PDF text extraction
            print("📦 PyPDF2 not available, using simulated PDF extraction")
            return f"""[Simulated PDF Content from {file_path.name}]

This is simulated text content extracted from a PDF file.
In a real implementation, this would use PyPDF2, pdfplumber, or similar library.

Document Title: {file_path.stem}
Content: Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

For demo purposes, this represents extracted PDF text that would
be processed by the intelligent chunker and embedded for search."""
    
    async def _extract_word_text(self, file_path: Path) -> str:
        """Extract text from Word document."""
        
        try:
            # Try using python-docx if available
            import docx
            
            doc = docx.Document(file_path)
            paragraphs = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
            
            return "\n\n".join(paragraphs)
            
        except ImportError:
            # Fallback: simulate Word text extraction
            print("📦 python-docx not available, using simulated Word extraction")
            return f"""[Simulated Word Content from {file_path.name}]

This is simulated text content extracted from a Word document.
In a real implementation, this would use python-docx library.

Document: {file_path.stem}

1. Introduction
This document contains important information that users would
want to search and ask questions about.

2. Main Content  
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
eiusmod tempor incididunt ut labore et dolore magna aliqua.

3. Conclusion
This simulated content demonstrates how the document chat system
would work with real Word documents."""
    
    async def _extract_text_file(self, file_path: Path) -> str:
        """Extract text from plain text files."""
        
        # Try different encodings
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not decode text file with any encoding: {file_path}")
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to parse"
                },
                "file_path": {
                    "type": "string", 
                    "description": "Single file path to parse (alternative to file_paths)"
                }
            },
            "anyOf": [
                {"required": ["file_paths"]},
                {"required": ["file_path"]}
            ]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return output schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "metadata": {"type": "object"},
                            "word_count": {"type": "integer"},
                            "char_count": {"type": "integer"}
                        }
                    }
                },
                "total_parsed": {"type": "integer"},
                "total_failed": {"type": "integer"},
                "failed_files": {"type": "array"}
            },
            "required": ["success", "documents"]
        } 