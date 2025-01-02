#!/bin/bash

# Script to convert draft.md to draft.docx using Pandoc
# Ensures proper academic formatting and table handling

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "Error: pandoc is not installed. Please install it using:"
    echo "brew install pandoc"
    exit 1
fi

# Set paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
INPUT_FILE="$ROOT_DIR/draft.md"
OUTPUT_FILE="$ROOT_DIR/draft.docx"
REFERENCE_FILE="$ROOT_DIR/reference.docx"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: draft.md not found in $ROOT_DIR"
    exit 1
fi

# Remove existing reference.docx if it exists
if [ -f "$REFERENCE_FILE" ]; then
    echo "Removing existing reference.docx..."
    rm "$REFERENCE_FILE"
fi

# Create reference.docx with proper styles
echo "Creating reference.docx template..."
pandoc -o "$REFERENCE_FILE" --print-default-data-file reference.docx

# Configure styles in reference document
python3 - << EOF
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='docx')

from docx import Document
from docx.shared import Pt, Inches, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

# Open the reference document
doc = Document("$REFERENCE_FILE")

# Set page dimensions and margins first
sections = doc.sections
for section in sections:
    section.page_width = Inches(8.5)  # Standard letter width
    section.page_height = Inches(11)  # Standard letter height
    section.top_margin = Inches(0.25)
    section.bottom_margin = Inches(0.25)
    section.left_margin = Inches(0.25)
    section.right_margin = Inches(0.25)

# First, create all required styles
required_styles = [
    ('Normal', WD_STYLE_TYPE.PARAGRAPH),
    ('Title', WD_STYLE_TYPE.PARAGRAPH),
    ('Heading 1', WD_STYLE_TYPE.PARAGRAPH),
    ('Heading 2', WD_STYLE_TYPE.PARAGRAPH),
    ('Heading 3', WD_STYLE_TYPE.PARAGRAPH),
    ('List Bullet', WD_STYLE_TYPE.PARAGRAPH),
    ('List Number', WD_STYLE_TYPE.PARAGRAPH),
    ('Caption', WD_STYLE_TYPE.PARAGRAPH),
    ('Figure', WD_STYLE_TYPE.PARAGRAPH),
    ('Table Grid', WD_STYLE_TYPE.TABLE),
    ('Table Paragraph', WD_STYLE_TYPE.PARAGRAPH)
]

# Create styles if they don't exist
existing_style_names = [s.name for s in doc.styles]
for style_name, style_type in required_styles:
    if style_name not in existing_style_names:
        try:
            doc.styles.add_style(style_name, style_type)
        except ValueError:
            # Style might exist but not be visible
            pass

# Now configure all styles
for style in doc.styles:
    if style.type == WD_STYLE_TYPE.PARAGRAPH:
        if hasattr(style, 'font'):
            style.font.name = 'Times New Roman'

            if style.name == 'Normal':
                style.font.size = Pt(12)
                if hasattr(style, 'paragraph_format'):
                    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            elif style.name == 'Title':
                style.font.size = Pt(12)
                if hasattr(style, 'paragraph_format'):
                    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif style.name in ['Author', 'Subtitle']:
                style.font.size = Pt(12)
                if hasattr(style, 'paragraph_format'):
                    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            elif style.name == 'Heading 1':
                style.font.size = Pt(16)
            elif style.name == 'Heading 2':
                style.font.size = Pt(14)
            elif style.name == 'Heading 3':
                style.font.size = Pt(12)
            elif style.name in ['List Bullet', 'List Number']:
                style.font.size = Pt(12)
            elif style.name in ['Caption', 'Figure']:
                style.font.size = Pt(12)
                if hasattr(style, 'paragraph_format'):
                    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    style.paragraph_format.space_before = Pt(12)
                    style.paragraph_format.space_after = Pt(12)
            elif 'Table' in style.name:
                style.font.size = Pt(8)
                if hasattr(style, 'paragraph_format'):
                    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# Add a dummy paragraph and table to ensure styles exist
try:
    # Add and remove a paragraph with each style to ensure they're saved
    for style_name, _ in required_styles:
        if style_name != 'Table Grid':
            p = doc.add_paragraph('Dummy', style=style_name)
            p._element.getparent().remove(p._element)

    # Add and configure a table to ensure Table Grid style exists with proper borders
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    table = doc.add_table(rows=1, cols=1)
    table.style = 'Table Grid'

    # Configure table borders in the reference document
    for cell in table._cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        for border_name in ['top', 'left', 'bottom', 'right']:
            border = OxmlElement(f'w:{border_name}')
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), '2')  # 1/4 point
            border.set(qn('w:color'), '000000')  # Black
            tcBorders.append(border)
        tcPr.append(tcBorders)

    # Remove the dummy table after style is configured
    table._element.getparent().remove(table._element)
except Exception as e:
    print(f"Warning: Could not create dummy elements: {str(e)}")

# Save the reference document
doc.save("$REFERENCE_FILE")
EOF

# Convert markdown to docx using the reference document
echo "Converting draft.md to draft.docx..."
pandoc "$INPUT_FILE" \
    -f markdown+pipe_tables+grid_tables+multiline_tables+simple_tables \
    -t docx \
    --reference-doc="$REFERENCE_FILE" \
    --wrap=preserve \
    --standalone \
    -o "$OUTPUT_FILE"

# Apply final formatting
python3 - << EOF
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='docx')

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

# Open the document
doc = Document("$OUTPUT_FILE")

# Set margins
sections = doc.sections
for section in sections:
    section.top_margin = Inches(0.25)
    section.bottom_margin = Inches(0.25)
    section.left_margin = Inches(0.25)
    section.right_margin = Inches(0.25)

# Process paragraphs
abstract_found = False
for paragraph in doc.paragraphs:
    # Check if we've reached the Abstract section
    if paragraph.text.strip().lower().startswith('abstract'):
        abstract_found = True

    # Apply justification after Abstract
    if abstract_found and not any(paragraph.text.strip().lower().startswith(x) for x in ['#', 'author', 'email']):
        if not paragraph.text.strip().startswith('-'):  # Don't justify bullet points
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Handle bullet points
    if paragraph.text.strip().startswith('-'):
        try:
            paragraph.style = doc.styles['List Bullet']
        except KeyError:
            # If style doesn't exist, keep normal style
            pass

    # Center images and their captions
    if 'Figure' in paragraph.text or any('![' in run.text for run in paragraph.runs):
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(12)
        paragraph.paragraph_format.space_after = Pt(12)
        try:
            if 'Figure' in paragraph.text:
                paragraph.style = doc.styles['Caption']
            else:
                paragraph.style = doc.styles['Figure']
        except KeyError:
            pass

# Process tables - ensure all table content is 8pt
for table in doc.tables:
    # Set table border properties
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    table.style = 'Table Grid'
    for cell in table._cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        for border_name in ['top', 'left', 'bottom', 'right']:
            border = OxmlElement(f'w:{border_name}')
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), '2')  # 1/4 point
            border.set(qn('w:color'), '000000')  # Black
            tcBorders.append(border)
        tcPr.append(tcBorders)

        for paragraph in cell.paragraphs:
            # Apply direct formatting
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(8)
            # Apply style-based formatting
            try:
                paragraph.style = doc.styles['Table Paragraph']
            except KeyError:
                # Fallback to direct formatting if style doesn't exist
                paragraph.style.font.size = Pt(8)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# Save the document
doc.save("$OUTPUT_FILE")
EOF

# Check if conversion was successful
if [ $? -eq 0 ]; then
    echo "Successfully converted $INPUT_FILE to $OUTPUT_FILE"
else
    echo "Error: Conversion failed"
    exit 1
fi
