from __future__ import annotations

import asyncio
import asyncpg
from typing import List, Optional
from dataclasses import dataclass
import pydantic_core
import logfire
from pydantic_ai import Agent, RunContext
from openai import AsyncOpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pathlib import Path
import tiktoken

# Configure logfire
logfire.configure(
    service_name="research-assistant",
    service_version="1.0.0",
    environment="development",
    send_to_logfire='if-token-present',
    console={"span_style": "simple"}
)

class Section(BaseModel):
    file_path: str
    title: str
    content: str
    
    def embedding_content(self) -> str:
        return '\n\n'.join((
            f'file: {self.file_path}',
            f'title: {self.title}',
            self.content
        ))

@dataclass
class IngesterDeps:
    pool: asyncpg.Pool
    openai: AsyncOpenAI

class KnowledgeIngester:
    def __init__(self):
        self.agent = Agent(
            'openai:gpt-3.5-turbo',
            deps_type=Section,
            system_prompt=(
                "You are a knowledge ingestion agent. Your job is to process sections "
                "of text and store them in a vector database for later retrieval."
            )
        )
        self.pool: asyncpg.Pool | None = None
        self.openai: AsyncOpenAI | None = None
    
    async def initialize(self, pool: asyncpg.Pool, openai: AsyncOpenAI):
        """Initialize the agent with database pool and OpenAI client."""
        self.pool = pool
        self.openai = openai
        await self.setup_database_schema()
    
    async def setup_database_schema(self):
        """Setup the database schema for knowledge storage."""
        if not self.pool:
            raise ValueError("Database pool not initialized")
            
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE EXTENSION IF NOT EXISTS vector;
                
                CREATE TABLE IF NOT EXISTS markdown_sections (
                    id SERIAL PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1536) NOT NULL,
                    UNIQUE(file_path, title)
                );
                
                CREATE INDEX IF NOT EXISTS markdown_sections_embedding_idx 
                ON markdown_sections 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            ''')
    
    async def ingest_section(self, section: Section) -> str:
        """Ingest a section into the knowledge base."""
        if not self.openai or not self.pool:
            raise ValueError("Agent not properly initialized")
            
        # Split content into chunks if needed
        content_chunks = split_text(section.content)
        logfire.info(f"Split content into {len(content_chunks)} chunks")
        
        for i, chunk in enumerate(content_chunks):
            chunk_section = Section(
                file_path=section.file_path,
                title=f"{section.title}_chunk_{i+1}" if len(content_chunks) > 1 else section.title,
                content=chunk
            )
            
            with logfire.span('create embedding for section chunk', 
                          title=chunk_section.title):
                try:
                    embedding = await self.openai.embeddings.create(
                        input=chunk_section.embedding_content(),
                        model='text-embedding-3-small'
                    )
                    
                    assert len(embedding.data) == 1, \
                        f'Expected 1 embedding, got {len(embedding.data)}'
                    embedding_json = pydantic_core.to_json(
                        embedding.data[0].embedding).decode()
                    
                    async with self.pool.acquire() as conn:
                        await conn.execute('''
                            INSERT INTO markdown_sections (file_path, title, content, embedding)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (file_path, title) DO UPDATE
                            SET content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding
                        ''', chunk_section.file_path, chunk_section.title, 
                            chunk_section.content, embedding_json)
                    
                    logfire.info(f"Successfully processed chunk {i+1}/{len(content_chunks)}")
                    
                except Exception as e:
                    logfire.error(f"Failed to process chunk {i+1}/{len(content_chunks)}: {e}")
                    continue
        
        return f"Successfully ingested section: {section.title}"
    
    async def process_sections(self, sections: List[Section]):
        """Process multiple sections concurrently."""
        if not self.agent:
            raise ValueError("Agent not initialized")
            
        sem = asyncio.Semaphore(5)  # Limit concurrent operations
        
        async def process_with_semaphore(section: Section):
            async with sem:
                result = await self.agent.run(
                    f"Process section titled '{section.title}' from {section.file_path}",
                    deps=section
                )
                return result.data
        
        tasks = [process_with_semaphore(section) for section in sections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any errors
        for result, section in zip(results, sections):
            if isinstance(result, Exception):
                logfire.error(
                    "Failed to process section",
                    title=section.title,
                    error=str(result)
                )

def split_text(text: str, max_tokens: int = 8000) -> List[str]:
    """Split text into chunks that fit within token limit."""
    enc = tiktoken.encoding_for_model("text-embedding-3-small")
    tokens = enc.encode(text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for token in tokens:
        if current_size + 1 > max_tokens:
            chunk_text = enc.decode(current_chunk)
            chunks.append(chunk_text)
            current_chunk = [token]
            current_size = 1
        else:
            current_chunk.append(token)
            current_size += 1
    
    if current_chunk:
        chunk_text = enc.decode(current_chunk)
        chunks.append(chunk_text)
    
    return chunks

async def main():
    """Run the knowledge ingester as a standalone script."""
    load_dotenv()
    
    logfire.info("Starting knowledge ingester")
    
    # Initialize OpenAI client
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        logfire.error("OpenAI API key not found")
        return
    
    openai = AsyncOpenAI()
    logfire.info("OpenAI client initialized")
    
    # Initialize database connection
    try:
        pool = await asyncpg.create_pool(
            'postgresql://postgres:postgres@localhost:5432/knowledge_base'
        )
        logfire.info("Database connection established")
    except Exception as e:
        logfire.error(f"Failed to connect to database: {e}")
        logfire.info("Please make sure PostgreSQL is running with pgvector extension.")
        logfire.info("You can start it with Docker using:")
        logfire.info("docker run --name postgres-vector -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=knowledge_base -p 5432:5432 -d pgvector/pgvector:pg16")
        return
    
    try:
        # Initialize ingester
        ingester = KnowledgeIngester()
        await ingester.initialize(pool, openai)
        logfire.info("Knowledge ingester initialized")
        
        # Process markdown files
        markdown_dir = Path("sources_markdown")
        if not markdown_dir.exists():
            logfire.error(f"Markdown directory not found: {markdown_dir}")
            logfire.info("Please run document_processor.py first to generate markdown files")
            return
            
        markdown_files = list(markdown_dir.glob("*.md"))
        logfire.info(f"Found {len(markdown_files)} markdown files")
        
        for md_file in markdown_files:
            try:
                with open(md_file, 'r') as f:
                    content = f.read()
                
                section = Section(
                    file_path=str(md_file),
                    title=md_file.stem,
                    content=content
                )
                
                result = await ingester.ingest_section(section)
                logfire.info(f"Processed {md_file.name}: {result}")
            except Exception as e:
                logfire.error(f"Failed to process {md_file.name}: {e}")
                continue
            
    except Exception as e:
        logfire.error(f"Error during processing: {e}")
    finally:
        await pool.close()
        logfire.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())
