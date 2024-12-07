from __future__ import annotations

import asyncio
import argparse
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

import pydantic_core
import logfire
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv
import asyncpg

class SearchResult(BaseModel):
    title: str
    content: str
    similarity: float
    file_path: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]

@dataclass
class QueryDeps:
    pool: asyncpg.Pool
    openai: AsyncOpenAI

class QueryAgent:
    def __init__(self):
        self.agent = Agent(
            'openai:gpt-3.5-turbo',
            deps_type=QueryDeps,
            system_prompt=(
                "You are a helpful research assistant. Search through "
                "the knowledge base and provide accurate answers with sources."
            )
        )
        self.deps: Optional[QueryDeps] = None

    async def initialize(self, pool: asyncpg.Pool, openai: AsyncOpenAI):
        """Initialize the agent with dependencies."""
        self.deps = QueryDeps(pool=pool, openai=openai)

    @Agent.tool
    async def search(
        self,
        context: RunContext[QueryDeps],
        query: str,
        limit: int = 5
    ) -> List[SearchResult]:
        """Search for relevant content in the knowledge base."""
        embedding = await context.deps.openai.embeddings.create(
            input=query,
            model='text-embedding-3-small'
        )
        
        embedding_json = pydantic_core.to_json(embedding.data[0].embedding).decode()
        
        # Perform vector search
        results = await context.deps.pool.fetch('''
            SELECT 
                title,
                content,
                file_path,
                1 - (embedding <=> $1::vector) as similarity
            FROM markdown_sections
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        ''', embedding_json, limit)
        
        return [
            SearchResult(
                title=r['title'],
                content=r['content'],
                similarity=r['similarity'],
                file_path=r['file_path']
            )
            for r in results
        ]

async def main():
    """Run the query agent as a standalone script."""
    load_dotenv()  # Load environment variables
    
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="The query to answer")
    args = parser.parse_args()

    # Initialize OpenAI client
    openai = AsyncOpenAI()
    
    # Initialize database connection
    pool = await asyncpg.create_pool(
        'postgresql://postgres:postgres@localhost:5432/knowledge_base'
    )
    
    try:
        # Initialize agent
        agent = QueryAgent()
        await agent.initialize(pool, openai)
        
        # Run query
        result = await agent.search(args.query)
        
        # Print results
        print("\nSearch Results:")
        for r in result:
            print(f"\nTitle: {r.title}")
            print(f"Source: {r.file_path}")
            print(f"Similarity: {r.similarity:.2f}")
            print(f"Content: {r.content[:200]}...")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
