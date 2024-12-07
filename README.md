# Research Assistant

A tool for managing academic research materials, including PDF processing, knowledge ingestion, and semantic search capabilities using AI agents.

## Project Structure

```
research-assistant/
├── agents/             # AI agents for processing and querying
│   ├── document_processor.py  # Handles PDF conversion
│   ├── knowledge_ingester.py  # Manages vector database ingestion
│   └── query_agent.py        # Handles semantic search queries
├── scripts/           # Utility scripts
│   ├── pdf_to_markdown.py
│   └── pdf_to_png.py
├── sources_pdf/       # Store original PDF papers
├── sources_markdown/  # Converted markdown versions of papers
└── sources_png/       # Extracted images from PDFs
```

## Features

- PDF to Markdown conversion with OpenAI-enhanced processing
- Image extraction from PDFs (300 DPI)
- Vector database storage for semantic search
- RAG (Retrieval-Augmented Generation) based querying
- Organized storage of research materials

## Requirements

- Python 3.8+
- PostgreSQL with pgvector extension
- OpenAI API key
- Required Python packages (install via `pip install -r requirements.txt`)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/parthchandak02/research-assistant.git
cd research-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL with pgvector:
```bash
docker run --name postgres-vector \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=knowledge_base \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16
```

5. Create a `.env` file with your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Process PDF documents:
```bash
python agents/document_processor.py --input-dir sources_pdf
```

2. Ingest knowledge into vector database:
```bash
python agents/knowledge_ingester.py
```

3. Query your research materials:
```bash
python agents/query_agent.py "Your research question here"
```

You can also use the agents programmatically in your Python code:

```python
from agents.document_processor import DocumentProcessor
from agents.knowledge_ingester import KnowledgeIngester
from agents.query_agent import QueryAgent

# Initialize and use the agents as needed
```

## Agent Descriptions

### Document Processor
- Converts PDFs to markdown format
- Extracts images from PDFs
- Uses OpenAI for enhanced text processing (optional)

### Knowledge Ingester
- Processes markdown files into embeddings
- Stores content in vector database
- Handles large documents by chunking

### Query Agent
- Performs semantic search on stored knowledge
- Uses RAG for intelligent responses
- Provides source references for answers

## Contributing

Feel free to:
- Submit issues for suggestions
- Create pull requests with improvements
- Share your customized versions
- Report any bugs or unclear documentation

## License

This project is licensed under MIT License - see the LICENSE file for details.
