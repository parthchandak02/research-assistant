# Research Assistant Guidelines

## Project Structure
1. Source PDFs stored in `sources_pdf/`
2. Markdown conversions in `sources_markdown/`
3. PNG extractions in `sources_png/`
4. Draft documents in root directory
5. Scripts for file processing in `scripts/`

## Document Conversion
To convert the draft markdown to Word format:
1. Install Pandoc if not already installed:
   ```bash
   brew install pandoc
   ```
2. Run the conversion script:
   ```bash
   ./scripts/convert_to_docx.sh
   ```

## Information Accuracy & Citations
1. Verify all information against primary sources
2. Use requested citation format:
   ```markdown
   IEEE Example: [1] A. Author, B. Author, "Title of paper," Journal Name, vol. 1, no. 2, pp. 123-456, 2023.
   APA Example: Author, A., & Author, B. (2023). Title of paper. Journal Name, 1(2), 123-456.
   ```
3. Include DOI or permanent links:
   ```markdown
   DOI: 10.1234/journal.2023.1234
   arXiv: arXiv:2301.12345
   ```
4. Distinguish peer-reviewed vs non-peer-reviewed sources
5. Track citation networks and cross-references

## Document Management
1. Make changes file-by-file with verification
2. Preserve existing document structures
3. Use markdown for academic writing:
   ```markdown
   # Main Title
   ## Section Heading
   ### Subsection

   Key finding from [1] shows...
   ```
4. Maintain consistent formatting and hierarchy

## Image and Table Management
1. Center all images using markdown div syntax and set standard width:
   ```markdown
   <div style="width: 500px;">

   ![Description of Image](sources_png/paper_id/page_001.png)

   </div>

   *Note: Description of the content. Adapted from Author et al. (YEAR), Fig. X.*
   ```
2. Use standard image width:
   - All figures and diagrams: 500px
   - Add blank lines before and after the div and image for better readability
3. Format figure captions:
   - Start with "Figure N:" for numbering in the document
   - Follow with descriptive title
   - End with *Note: [Description]. Adapted from [Author] ([Year]), Fig. [X].* where X is the original figure number
4. Format tables with clear headers and citations:
   ```markdown
   **Table 1: Descriptive Title**
   | Column 1 | Column 2 | Column 3 |
   |----------|----------|----------|
   | Data     | Data     | Data     |

   *Note: Description of the table. Adapted from Author et al. (YEAR), Table X.*
   ```
5. For tables synthesized from multiple sources:
   ```markdown
   *Note: Framework synthesized from multiple sources: Author1 et al. (YEAR1), Author2 et al. (YEAR2), Author3 (YEAR3).*
   ```
