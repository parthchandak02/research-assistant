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
TMP_FILE="$ROOT_DIR/tmp_draft.md"

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
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

# Open the reference document
doc = Document("$REFERENCE_FILE")

# Set page dimensions and margins
sections = doc.sections
for section in sections:
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.25)
    section.bottom_margin = Inches(0.25)
    section.left_margin = Inches(0.25)
    section.right_margin = Inches(0.25)

# Configure basic styles
for style in doc.styles:
    if style.type == WD_STYLE_TYPE.PARAGRAPH:
        if hasattr(style, 'font'):
            style.font.name = 'Times New Roman'

            # Configure heading sizes
            if style.name == 'Heading 1':
                style.font.size = Pt(16)
                style.font.bold = True
                style.paragraph_format.space_before = Pt(36)
                style.paragraph_format.space_after = Pt(18)
                style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif style.name == 'Heading 2':
                style.font.size = Pt(14)
                style.font.bold = True
                style.paragraph_format.space_before = Pt(30)
                style.paragraph_format.space_after = Pt(12)
            elif style.name == 'Heading 3':
                style.font.size = Pt(12)
                style.font.bold = True
                style.paragraph_format.space_before = Pt(24)
                style.paragraph_format.space_after = Pt(10)
            elif style.name == 'Normal':
                style.font.size = Pt(12)
                style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                style.paragraph_format.space_before = Pt(12)
                style.paragraph_format.space_after = Pt(12)
            elif style.name == 'List Bullet':
                style.font.size = Pt(12)
                style.paragraph_format.left_indent = Inches(0.15)
                style.paragraph_format.first_line_indent = Inches(-0.15)
                style.paragraph_format.space_before = Pt(0)
                style.paragraph_format.space_after = Pt(0)

            # Handle figure captions
            elif style.name == 'Caption':
                style.font.size = Pt(10)
                style.font.italic = True
                style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                style.paragraph_format.space_before = Pt(6)
                style.paragraph_format.space_after = Pt(12)

# Save the reference document
doc.save("$REFERENCE_FILE")
EOF

# Create a temporary file for processing
cp "$INPUT_FILE" "$TMP_FILE"

# Process the markdown file to ensure proper bullet point formatting
sed -i '' 's/^•/*/g' "$TMP_FILE"  # Convert bullet points to asterisks
sed -i '' 's/^  -/  */g' "$TMP_FILE"  # Convert sub-bullet dashes to asterisks

# Convert markdown to docx
echo "Converting draft.md to draft.docx..."

pandoc "$TMP_FILE" \
    -f markdown+raw_html+raw_tex+raw_attribute+pipe_tables+grid_tables+multiline_tables+simple_tables \
    -t docx \
    --reference-doc="$REFERENCE_FILE" \
    --wrap=preserve \
    --standalone \
    --resource-path=".:$ROOT_DIR:$ROOT_DIR/sources_png:$ROOT_DIR/user_illustrations" \
    --dpi=300 \
    --verbose \
    --lua-filter="$SCRIPT_DIR/filters/bullet_spacing.lua" \
    -o "$OUTPUT_FILE"

# Remove temporary file
rm "$TMP_FILE"

# Apply final formatting
python3 - << EOF
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='docx')

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.enum.table import WD_TABLE_ALIGNMENT

# Open the document
doc = Document("$OUTPUT_FILE")

# Process paragraphs
for paragraph in doc.paragraphs:
    # Handle bullet points
    if paragraph.text.strip().startswith('-'):
        paragraph.paragraph_format.left_indent = Inches(0.15)
        paragraph.paragraph_format.first_line_indent = Inches(-0.15)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)

    # Handle images and captions
    if 'Figure' in paragraph.text:
        paragraph.style = doc.styles['Caption']
    elif '![' in paragraph.text:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(12)
        paragraph.paragraph_format.space_after = Pt(6)

        # Resize inline shapes (images)
        for shape in doc.inline_shapes:
            # Set width to 6 inches while maintaining aspect ratio
            if shape.width > 0:  # Only process if width is valid
                desired_width = Inches(6)
                aspect_ratio = shape.height / shape.width
                shape.width = desired_width
                shape.height = int(desired_width * aspect_ratio)

# Process tables
for table in doc.tables:
    # Add borders to all cells
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in table.rows:
        for cell in row.cells:
            # Set cell borders
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tcBorders>')
            tcPr.append(tcBorders)

    # Make first row bold
    for cell in table.rows[0].cells:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(8)
                run.font.name = 'Times New Roman'

    # Process remaining rows
    for row in table.rows[1:]:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(8)
                    run.font.name = 'Times New Roman'

# Process images to ensure they're properly sized
for shape in doc.inline_shapes:
    # Set width to 6 inches while maintaining aspect ratio
    if shape.width > 0:  # Only process if width is valid
        desired_width = Inches(6)
        aspect_ratio = shape.height / shape.width
        shape.width = desired_width
        shape.height = int(desired_width * aspect_ratio)

# Process paragraphs containing images
for paragraph in doc.paragraphs:
    if '![' in paragraph.text or paragraph.text.strip().startswith('Figure'):
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(12)
        paragraph.paragraph_format.space_after = Pt(12)
        # Clear any existing text that was part of the markdown image syntax
        if '![' in paragraph.text:
            paragraph.clear()

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
