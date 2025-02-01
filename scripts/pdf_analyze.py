#!/usr/bin/env python3

import logging
from pathlib import Path
import google.generativeai as genai
import time
import os
from dotenv import load_dotenv
import json
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

class PDFAnalyzer:
    """Analyze PDFs using Google's Gemini API and rename based on analysis."""

    def __init__(self, api_key: str):
        """Initialize the analyzer with API key."""
        self.source_dir = Path('sources_pdf')
        self.analysis_dir = Path('sources_analysis')

        # Configure Gemini
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        # Get model name from environment
        self.model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash-exp')

        # Initialize model with system instructions
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=[
                "You are an expert research assistant analyzing academic papers.",
                "Extract the following information in XML format:",
                "1. Title",
                "2. Authors (in format: 'Last1, First1; Last2, First2')",
                "3. Publication year",
                "4. Abstract",
                "5. Key findings/contributions",
                "6. Methodology",
                "7. Results",
                "8. Limitations",
                "9. Research gap",
                "10. Thematic analysis",
                "Format the response as a valid XML document with these fields as elements."
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

    def create_ieee_filename(self, analysis_text: str, original_name: str) -> str:
        """Create IEEE-style filename from analysis results."""
        try:
            # Try to parse the analysis text as JSON
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If not valid JSON, try to extract information using regex
                title_match = re.search(r'"Title":\s*"([^"]+)"', analysis_text)
                authors_match = re.search(r'"Authors":\s*"([^"]+)"', analysis_text)
                year_match = re.search(r'"Publication year":\s*"?(\d{4})"?', analysis_text)

                analysis = {
                    "Title": title_match.group(1) if title_match else "",
                    "Authors": authors_match.group(1) if authors_match else "",
                    "Publication year": year_match.group(1) if year_match else ""
                }

            # Extract components
            title = analysis.get("Title", "")
            authors = analysis.get("Authors", "")
            year = analysis.get("Publication year", "")

            # Clean up year
            year = re.search(r'\d{4}', str(year)).group(0) if re.search(r'\d{4}', str(year)) else ""

            # Get first author's last name
            first_author = self.extract_first_author_lastname(authors) if authors else ""

            # Get shortened title (first 3-4 significant words)
            title_words = [w for w in re.findall(r'\w+', title.lower())
                         if len(w) > 3 and w not in {'with', 'using', 'from', 'through', 'based'}]
            short_title = '_'.join(title_words[:3])

            # Combine components
            components = []
            if first_author:
                components.append(self.sanitize_filename(first_author))
            if short_title:
                components.append(self.sanitize_filename(short_title))
            if year:
                components.append(year)

            # If we couldn't extract meaningful components, use original name
            if not components:
                return original_name

            new_name = '_'.join(components) + '.pdf'
            return new_name

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

    def clean_json_response(self, text: str) -> str:
        """Clean and extract valid JSON from Gemini's response."""
        try:
            # First try to find a complete JSON object with balanced braces
            def find_json_object(text):
                stack = []
                start = -1
                for i, char in enumerate(text):
                    if char == '{':
                        if not stack:
                            start = i
                        stack.append(char)
                    elif char == '}':
                        if stack:
                            stack.pop()
                            if not stack and start != -1:
                                return text[start:i+1]
                return None

            json_str = find_json_object(text)
            if not json_str:
                raise ValueError("No valid JSON object found")

            # Clean up the JSON string
            json_str = re.sub(r'\\n\s+', ' ', json_str)  # Replace newlines with spaces
            json_str = re.sub(r'\s+', ' ', json_str)  # Normalize whitespace
            json_str = json_str.replace('\\"', '"')  # Fix escaped quotes
            json_str = re.sub(r'(?<!\\)"([^"]*?)\\(?!["\\])', r'"\1', json_str)  # Fix invalid escapes

            # Try to parse it
            try:
                return json.dumps(json.loads(json_str), ensure_ascii=False)
            except:
                # If that fails, try more aggressive cleaning
                json_str = re.sub(r'\\(?!["\\/bfnrt])', '', json_str)  # Remove invalid escapes
                return json.dumps(json.loads(json_str), ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error cleaning JSON response: {e}")
            # If cleaning fails, try to create a structured JSON from the text
            try:
                # Extract information using regex patterns with more flexible matching
                patterns = {
                    "Title": r'Title["\']?\s*:?\s*["\']?([^"}{\n]+)["\']?',
                    "Authors": r'Authors["\']?\s*:?\s*["\']?([^"}{\n]+)["\']?',
                    "Publication year": r'Publication year["\']?\s*:?\s*["\']?(\d{4})["\']?',
                    "Abstract": r'Abstract["\']?\s*:?\s*["\']?([^"}{\n]+)["\']?',
                    "Key findings/contributions": r'Key findings[^:]*:?\s*["\']?([^"}{\n]+)["\']?',
                    "Methodology": r'Methodology["\']?\s*:?\s*["\']?([^"}{\n]+)["\']?'
                }

                result = {}
                for key, pattern in patterns.items():
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        value = match.group(1).strip()
                        value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
                        if value and (key not in result or len(value) > len(result[key])):
                            result[key] = value

                # If we found any data, return it
                if any(result.values()):
                    return json.dumps(result, ensure_ascii=False)

                # If no data found, raise exception to trigger error XML
                raise ValueError("No data could be extracted from response")

            except Exception as e2:
                logger.error(f"Error extracting structured data: {e2}")
                return json.dumps({
                    "error": str(e2),
                    "raw_text": text[:1000]  # Limit raw text to first 1000 chars
                })

    def clean_text_content(self, text: str) -> str:
        """Clean text content for XML by removing unwanted escape sequences."""
        if not text:
            return ""

        # Convert escaped quotes back to regular quotes
        text = text.replace('\\"', '"')
        text = text.replace('&quot;', '"')

        # Remove any remaining escape sequences except for newlines
        text = text.replace('\\n', '\n')  # Preserve newlines
        text = re.sub(r'\\[^n]', '', text)  # Remove other escape sequences

        # Clean up any HTML/XML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')

        return text.strip()

    def json_to_xml(self, json_str: str) -> str:
        """Convert JSON analysis to pretty XML format."""
        try:
            # Clean and parse JSON
            cleaned_json = self.clean_json_response(json_str)
            data = json.loads(cleaned_json)

            # Create XML structure
            root = ET.Element("analysis")

            # Add each field
            for key, value in data.items():
                element = ET.SubElement(root, key.lower().replace(' ', '_').replace('/', '_'))
                # Clean and handle multiline text
                if isinstance(value, str):
                    element.text = self.clean_text_content(value)
                else:
                    element.text = str(value)

            # Convert to string and pretty print with proper encoding
            rough_string = ET.tostring(root, encoding='unicode', method='xml')
            parsed = minidom.parseString(rough_string)
            # Remove extra blank lines while preserving intended whitespace
            xml_str = '\n'.join(line for line in parsed.toprettyxml(indent='  ').split('\n') if line.strip())
            return xml_str

        except Exception as e:
            logger.error(f"Error converting to XML: {e}")
            # Create error XML
            root = ET.Element("analysis")
            error = ET.SubElement(root, "error")
            error.text = str(e)
            raw = ET.SubElement(root, "raw_text")
            raw.text = self.clean_text_content(json_str)
            return minidom.parseString(ET.tostring(root, encoding='unicode')).toprettyxml(indent="  ")

    def clean_xml_response(self, text: str) -> str:
        """Clean and extract valid XML from Gemini's response."""
        try:
            # Try to find XML content between tags
            xml_match = re.search(r'(<\?xml.*?</analysis>)', text, re.DOTALL)
            if xml_match:
                return xml_match.group(1)

            # If no XML declaration, try to find just the analysis tags
            xml_match = re.search(r'(<analysis>.*?</analysis>)', text, re.DOTALL)
            if xml_match:
                return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_match.group(1)}'

            # If still no match, try to extract structured data
            patterns = {
                "title": r'<title>(.*?)</title>',
                "authors": r'<authors>(.*?)</authors>',
                "publication_year": r'<publication[_-]year>(\d{4})</publication[_-]year>',
                "abstract": r'<abstract>(.*?)</abstract>',
                "key_findings_contributions": r'<key[_-]findings[_-]contributions>(.*?)</key[_-]findings[_-]contributions>',
                "methodology": r'<methodology>(.*?)</methodology>',
                "results": r'<results>(.*?)</results>',
                "limitations": r'<limitations>(.*?)</limitations>',
                "research_gap": r'<research[_-]gap>(.*?)</research[_-]gap>',
                "thematic_analysis": r'<thematic[_-]analysis>(.*?)</thematic[_-]analysis>'
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
                pdf_file = genai.get_file(f"files/{file_name}")
                logger.info(f"File already exists: {pdf_file.uri}")
            except:
                logger.info(f"Uploading file...")
                pdf_file = genai.upload_file(path=str(pdf_path), name=file_name, resumable=True)
                logger.info(f"Completed upload: {pdf_file.uri}")

            # Wait for processing
            while pdf_file.state.name == "PROCESSING":
                logger.info("Processing...")
                time.sleep(10)
                pdf_file = genai.get_file(pdf_file.name)

            if pdf_file.state.name == "FAILED":
                raise ValueError(f"File processing failed: {pdf_file.state.name}")

            # Generate analysis
            logger.info("Generating analysis...")
            response = self.model.generate_content(
                [pdf_file, """Please analyze this academic paper and extract the requested information in XML format.
                Format your response as a valid XML document with root element <analysis> containing the specified fields as child elements.
                Use clear, descriptive text and preserve any important formatting or structure in the content.
                Ensure all XML tags are properly closed and nested."""],
                request_options={"timeout": 600}
            )

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

            # Extract title and authors for filename from XML
            try:
                root = ET.fromstring(analysis_result)
                title = root.find('title').text if root.find('title') is not None else ""
                authors = root.find('authors').text if root.find('authors') is not None else ""
                year = root.find('publication_year').text if root.find('publication_year') is not None else ""

                # Generate filename components
                components = []
                if authors:
                    first_author = self.extract_first_author_lastname(authors)
                    if first_author:
                        components.append(self.sanitize_filename(first_author))

                if title:
                    title_words = [w for w in re.findall(r'\w+', title.lower())
                                 if len(w) > 3 and w not in {'with', 'using', 'from', 'through', 'based'}]
                    if title_words:
                        components.append('_'.join(title_words[:3]))

                if year and re.match(r'\d{4}', year):
                    components.append(year)

                new_name = '_'.join(components) + '.pdf' if components else pdf_path.name
            except Exception as e:
                logger.error(f"Error extracting filename components from XML: {e}")
                new_name = pdf_path.name

            # Generate new filename based on JSON response
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
