#!/usr/bin/env python3

import logging
from pathlib import Path
from google import genai
from google.genai import types
import time
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Optional, Tuple
import re
import unicodedata
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# XML elements the model is asked for, in order. The parser below reads these exact tags.
ANALYSIS_FIELDS = [
    ("title", "Title"),
    ("authors", "Authors (in format: 'Last1, First1; Last2, First2')"),
    ("publication_year", "Publication year (four digits)"),
    ("abstract", "Abstract"),
    ("key_findings_contributions", "Key findings/contributions"),
    ("methodology", "Methodology"),
    ("results", "Results"),
    ("limitations", "Limitations"),
    ("research_gap", "Research gap"),
    ("thematic_analysis", "Thematic analysis"),
]

ANALYSIS_FORMAT = (
    "Respond with XML only, no Markdown code fences and no JSON. Use a single root element "
    "<analysis> containing exactly these child elements, in this order: "
    + ", ".join(f"<{tag}>" for tag, _ in ANALYSIS_FIELDS)
    + ". Escape &, < and > inside element text."
)


class PDFAnalyzer:
    """Analyze PDFs using Google's Gemini API and rename based on analysis."""

    def __init__(self, api_key: str):
        """Initialize the analyzer with API key."""
        self.source_dir = Path('sources_pdf')
        self.analysis_dir = Path('sources_analysis')

        # Configure Gemini (10 minute timeout for long PDFs)
        self.api_key = api_key
        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=600_000),
        )

        # Get model name from environment
        self.model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-3.8-flash')

        # System instructions sent with every request
        self.generation_config = types.GenerateContentConfig(
            system_instruction=[
                "You are an expert research assistant analyzing academic papers.",
                "Extract the following information:",
                *[f"<{tag}>: {label}" for tag, label in ANALYSIS_FIELDS],
                ANALYSIS_FORMAT,
            ]
        )

        # Create analysis directory if it doesn't exist
        self.analysis_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, text: str) -> str:
        """Convert text to a valid filename component."""
        # Convert to ASCII and remove invalid chars
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')

        # Replace invalid characters with underscore
        text = re.sub(r'[^\w\s-]', '_', text)

        # Replace spaces with underscores and collapse multiple underscores
        text = re.sub(r'[-\s]+', '_', text).strip('_')

        return text.lower()

    def extract_first_author_lastname(self, authors: str) -> str:
        """Extract the last name of the first author."""
        # Handle different author formats
        if ',' in authors:  # "Last, First" format
            first_author = authors.split(',')[0].strip()
            return first_author.split()[-1]
        else:  # "First Last" format
            first_author = authors.split(';')[0].split('and')[0].strip()
            return first_author.split()[-1]

    def create_ieee_filename(self, analysis_xml: str, original_name: str) -> str:
        """Create an IEEE-style filename (firstauthor_short_title_year.pdf) from the XML analysis."""
        try:
            root = ET.fromstring(analysis_xml)

            def field(tag: str) -> str:
                element = root.find(tag)
                return element.text.strip() if element is not None and element.text else ""

            title = field('title')
            authors = field('authors')
            year_match = re.search(r'\d{4}', field('publication_year'))
            year = year_match.group(0) if year_match else ""

            components = []
            if authors:
                first_author = self.extract_first_author_lastname(authors)
                if first_author:
                    components.append(self.sanitize_filename(first_author))
            if title:
                title_words = [w for w in re.findall(r'\w+', title.lower())
                               if len(w) > 3 and w not in {'with', 'using', 'from', 'through', 'based'}]
                if title_words:
                    components.append(self.sanitize_filename('_'.join(title_words[:3])))
            if year:
                components.append(year)

            if not components:
                return original_name
            return '_'.join(components) + '.pdf'

        except Exception as e:
            logger.error(f"Error creating filename from analysis: {e}")
            return original_name

    def generate_upload_name(self, original_name: str) -> str:
        """Generate a unique name for file upload that meets Gemini API requirements."""
        # Remove extension and special characters
        base_name = self.sanitize_filename(original_name.rsplit('.', 1)[0])

        # Replace underscores with dashes
        base_name = base_name.replace('_', '-')

        # Limit to 30 chars to leave room for unique identifier
        if len(base_name) > 30:
            base_name = base_name[:30]

        # Remove any trailing dashes
        base_name = base_name.rstrip('-')

        # Add a timestamp-based unique identifier
        unique_id = str(int(time.time()))[-8:]

        # Combine with a dash
        result = f"{base_name}-{unique_id}"

        # Ensure the name starts with a letter (Gemini requirement)
        if not result[0].isalpha():
            result = f"doc-{result}"

        return result

    def clean_xml_response(self, text: str) -> str:
        """Clean and extract valid XML from Gemini's response."""
        try:
            # Try to find XML content between tags
            xml_match = re.search(r'(<\?xml.*?</analysis>)', text, re.DOTALL)
            if xml_match:
                return xml_match.group(1)

            # If no XML declaration, try to find just the analysis tags
            xml_match = re.search(r'(<analysis>.*?</analysis>)', text, re.DOTALL | re.IGNORECASE)
            if xml_match:
                return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_match.group(1)}'

            # If still no match, try to extract structured data
            patterns = {
                tag: rf'<{tag.replace("_", "[_-]")}>(.*?)</{tag.replace("_", "[_-]")}>'
                for tag, _ in ANALYSIS_FIELDS
            }

            # Build XML structure from found elements
            root = ET.Element("analysis")
            found_any = False

            for tag, pattern in patterns.items():
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    value = match.group(1).strip()
                    if value:
                        element = ET.SubElement(root, tag)
                        element.text = value
                        found_any = True

            if found_any:
                return ET.tostring(root, encoding='unicode', method='xml')

            raise ValueError("No valid XML content found")

        except Exception as e:
            logger.error(f"Error cleaning XML response: {e}")
            # Create error XML
            root = ET.Element("analysis")
            error = ET.SubElement(root, "error")
            error.text = str(e)
            raw = ET.SubElement(root, "raw_text")
            raw.text = text[:1000]  # Limit raw text to first 1000 chars
            return ET.tostring(root, encoding='unicode', method='xml')

    def analyze_single_pdf(self, pdf_path: Path) -> Optional[Tuple[str, str]]:
        """Analyze a single PDF using Gemini API and rename it. Returns (analysis_result, new_filename)."""
        try:
            logger.info(f"Analyzing {pdf_path.name}...")

            # Generate a unique name for the file (under 40 chars)
            file_name = self.generate_upload_name(pdf_path.stem)
            logger.info(f"Using upload name: {file_name}")

            # Upload file to Gemini
            try:
                pdf_file = self.client.files.get(name=f"files/{file_name}")
                logger.info(f"File already exists: {pdf_file.uri}")
            except Exception:
                logger.info(f"Uploading file...")
                pdf_file = self.client.files.upload(
                    file=str(pdf_path),
                    config=types.UploadFileConfig(name=file_name, mime_type="application/pdf"),
                )
                logger.info(f"Completed upload: {pdf_file.uri}")

            # Wait for processing
            while pdf_file.state == types.FileState.PROCESSING:
                logger.info("Processing...")
                time.sleep(10)
                pdf_file = self.client.files.get(name=pdf_file.name)

            if pdf_file.state == types.FileState.FAILED:
                raise ValueError(f"File processing failed: {pdf_file.state}")

            # Generate analysis
            logger.info("Generating analysis...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[pdf_file, "Please analyze this academic paper and extract the requested information. "
                          "Use clear, descriptive text. " + ANALYSIS_FORMAT],
                config=self.generation_config,
            )
            if not response.text:
                raise ValueError("Gemini returned an empty response")

            # Clean and format XML response
            analysis_result = self.clean_xml_response(response.text)

            # Pretty print the XML
            try:
                parsed = minidom.parseString(analysis_result)
                analysis_result = parsed.toprettyxml(indent="  ")
                # Remove empty lines while preserving whitespace
                analysis_result = '\n'.join(line for line in analysis_result.split('\n') if line.strip())
            except Exception as e:
                logger.error(f"Error pretty printing XML: {e}")

            # Build the new filename from the XML fields
            new_name = self.create_ieee_filename(analysis_result, pdf_path.name)

            # Generate new filename based on the XML analysis
            new_path = pdf_path.parent / new_name

            # Ensure we don't overwrite existing files
            counter = 1
            while new_path.exists() and new_path != pdf_path:
                stem = new_name.rsplit('.', 1)[0]
                new_path = pdf_path.parent / f"{stem}_{counter}.pdf"
                counter += 1

            # Rename the PDF file
            if new_path != pdf_path:
                pdf_path.rename(new_path)
                logger.info(f"Renamed file to: {new_path.name}")

            # Save analysis with matching name
            analysis_filename = new_path.stem + "_analysis.xml"
            output_path = self.analysis_dir / analysis_filename

            # Save XML analysis
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(analysis_result)

            logger.info(f"Analysis saved to {output_path}")

            return analysis_result, new_path.name

        except Exception as e:
            logger.error(f"Error analyzing {pdf_path.name}: {e}")
            return None

    def analyze_all(self):
        """Analyze all PDFs in the source directory."""
        pdf_files = list(self.source_dir.glob('*.pdf'))
        if not pdf_files:
            logger.warning("No PDF files found in sources_pdf directory")
            return

        logger.info(f"Found {len(pdf_files)} PDF files to analyze")

        for i, pdf_path in enumerate(pdf_files):
            if pdf_path.name != '.gitkeep':  # Skip .gitkeep file
                try:
                    # Add delay between files to avoid rate limiting
                    if i > 0:
                        delay = 15  # 15 seconds delay between files
                        logger.info(f"Waiting {delay} seconds before processing next file...")
                        time.sleep(delay)

                    self.analyze_single_pdf(pdf_path)
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        wait_time = 300  # 5 minutes if we hit quota limit
                        logger.warning(f"Hit API quota limit. Waiting {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        # Retry this file
                        self.analyze_single_pdf(pdf_path)
                    else:
                        logger.error(f"Error processing {pdf_path.name}: {e}")
                        continue

    def analyze_specific(self, pdf_name: str):
        """Analyze a specific PDF file."""
        pdf_path = self.source_dir / pdf_name
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return

        logger.info(f"Analyzing specific file: {pdf_name}")
        self.analyze_single_pdf(pdf_path)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Analyze and rename PDF files using Gemini API')
    parser.add_argument('--file', '-f', help='Specific PDF file to analyze (must be in sources_pdf/)')
    parser.add_argument('--list', '-l', action='store_true', help='List available PDF files')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set. Please check your .env file.")
        return

    analyzer = PDFAnalyzer(api_key)

    if args.list:
        # List available PDFs
        pdf_files = list(Path('sources_pdf').glob('*.pdf'))
        if not pdf_files:
            print("No PDF files found in sources_pdf directory")
        else:
            print("\nAvailable PDF files:")
            for i, pdf in enumerate(pdf_files, 1):
                print(f"{i}. {pdf.name}")
        return

    if args.file:
        # Process single file
        analyzer.analyze_specific(args.file)
    else:
        # Process all files
        analyzer.analyze_all()

if __name__ == "__main__":
    main()
