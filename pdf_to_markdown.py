#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import pypdf
import re

def clean_text(text):
    """Clean extracted text to make it more readable."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove multiple newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Add proper spacing after periods
    text = re.sub(r'\.(?=[A-Z])', '. ', text)
    return text.strip()

def extract_pdf_metadata(pdf_reader):
    """Extract PDF metadata if available."""
    metadata = pdf_reader.metadata
    md_metadata = []
    
    if metadata:
        if metadata.get('/Title'):
            md_metadata.append(f"# {metadata['/Title']}\n")
        if metadata.get('/Author'):
            md_metadata.append(f"**Author(s):** {metadata['/Author']}\n")
        if metadata.get('/Subject'):
            md_metadata.append(f"**Subject:** {metadata['/Subject']}\n")
        if metadata.get('/Keywords'):
            md_metadata.append(f"**Keywords:** {metadata['/Keywords']}\n")
    
    return '\n'.join(md_metadata)

def pdf_to_markdown(pdf_path, output_dir):
    """Convert PDF to markdown format."""
    try:
        # Create output directory if it doesn't exist
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        pdf_name = Path(pdf_path).stem
        output_path = output_dir / f"{pdf_name}.md"
        
        # Open PDF file
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            
            # Start with metadata
            content = extract_pdf_metadata(pdf_reader)
            content += "\n## Content\n\n"
            
            # Extract text from each page
            total_pages = len(pdf_reader.pages)
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    cleaned_text = clean_text(text)
                    # Add page number header
                    content += f"### Page {page_num + 1} of {total_pages}\n\n"
                    content += f"{cleaned_text}\n\n"
                    # Add a horizontal rule between pages
                    if page_num < total_pages - 1:
                        content += "---\n\n"
            
            # Write to markdown file
            with open(output_path, 'w', encoding='utf-8') as md_file:
                md_file.write(content)
            
            print(f"Successfully converted {pdf_path.name} ({total_pages} pages)")
            return output_path
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_markdown.py <pdf_directory>")
        sys.exit(1)
    
    pdf_dir = sys.argv[1]
    output_dir = os.path.join(os.path.dirname(pdf_dir), "markdown_sources")
    
    # Process all PDFs in the directory
    pdf_files = Path(pdf_dir).glob('*.pdf')
    for pdf_path in pdf_files:
        print(f"Converting {pdf_path.name}...")
        output_path = pdf_to_markdown(pdf_path, output_dir)
        if output_path:
            print(f"Created {output_path}")
        else:
            print(f"Failed to convert {pdf_path.name}")

if __name__ == "__main__":
    main()
