from __future__ import annotations

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import logfire
from openai import AsyncOpenAI
import asyncpg
from typing import List

from agents.document_processor import DocumentProcessor
from agents.knowledge_ingester import KnowledgeIngester, Section
from agents.query_agent import QueryAgent

logfire.configure(
    service_name="research-assistant",
    service_version="1.0.0",
    environment="development",
    send_to_logfire='if-token-present',
    console={"span_style": "simple"}
)

async def main():
    """Run the complete research assistant workflow."""
    load_dotenv()
    
    # Initialize OpenAI client
    openai = AsyncOpenAI()
    logfire.info("OpenAI client initialized")
    
    # Initialize database connection
    pool = await asyncpg.create_pool(
        'postgresql://postgres:postgres@localhost:5432/knowledge_base'
    )
    logfire.info("Database connection established")
    
    try:
        # 1. Process Documents
        processor = DocumentProcessor()
        await processor.initialize(openai)
        
        input_dir = Path("sources_pdf")
        results = await processor.process_directory(input_dir)
        if results:
            logfire.info(f"Processed {len(results)} PDF files")
        
        # 2. Ingest Knowledge
        ingester = KnowledgeIngester()
        await ingester.initialize(pool, openai)
        
        # Process all markdown files
        markdown_dir = Path("sources_markdown")
        markdown_files = list(markdown_dir.glob("*.md"))
        logfire.info(f"Found {len(markdown_files)} markdown files")
        
        for md_file in markdown_files:
            with open(md_file, 'r') as f:
                content = f.read()
                
            section = Section(
                file_path=str(md_file),
                title=md_file.stem,
                content=content
            )
            result = await ingester.ingest_section(section)
            logfire.info(f"Processed {md_file.name}: {result}")
        
        # 3. Initialize Query Agent
        query_agent = QueryAgent()
        await query_agent.initialize(pool, openai)
        
        # Example query
        question = "What is the main topic of the documents?"
        answer = await query_agent.answer_question(question)
        print(f"\nQuestion: {question}")
        print(f"Answer: {answer.answer}")
        print("Sources:")
        for source in answer.sources:
            print(f"- {source}")
            
    finally:
        await pool.close()
        logfire.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())