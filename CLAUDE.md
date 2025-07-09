# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a BBS (Bulletin Board System) GraphRAG (Graph-enhanced Retrieval Augmented Generation) application that uses LangChain and LangGraph to provide intelligent Q&A capabilities over bulletin board historical data. The system addresses the challenge of understanding conversation context in boards where anchor functionality (reply-to-post feature) is underutilized by building a knowledge graph of post relationships.

## Technology Stack

- **Backend**: Python with FastAPI, LangChain and LangGraph for GraphRAG pipeline
- **Frontend**: React with TypeScript, Vite as build tool
- **Databases**: 
  - PostgreSQL for source bulletin board data (read-only)
  - PostgreSQL for RAG knowledge graph (posts and relationships)
- **Vector Store**: Chroma (local file-based vector database)
- **AI/LLM**: OpenAI API (GPT-4o for Q&A, GPT-3.5-turbo for relationship inference)
- **API**: OpenAPI 3.0 specification with auto-generated TypeScript client
- **Python Package Management**: uv (fast Python package installer and resolver)

## Key Commands

### Backend Development
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Initialize RAG database
python scripts/init_rag_db.py

# Run data sync pipeline (ETL from source DB to GraphRAG)
python scripts/sync_data.py  # Continuous sync
python scripts/sync_data.py --initial  # Initial full sync (all posts)

# Create GraphRAG vector index
python scripts/create_graphrag_index.py

# Legacy: Create sliding window vector index (old approach)
python scripts/create_index.py

# Linting and formatting
ruff check .
black .
mypy .
```

### Frontend Development
```bash
# Install dependencies
cd frontend
npm install

# Generate API client from OpenAPI spec
npx openapi-generator-cli generate -i http://localhost:8000/openapi.json -g typescript-fetch -o src/api

# Run development server
npm run dev
```

### Database Setup
```bash
# The database schema is already defined in docs/DESIGN.md
# Ensure PostgreSQL with PGVector extension is installed
# Connection string: postgresql://user:password@localhost:5432/bbs2
```

## Architecture Overview

The system implements a GraphRAG pipeline with the following key components:

1. **Graph-based Knowledge Representation**:
   - **Nodes**: Individual posts stored in RAG PostgreSQL
   - **Edges**: Two types of relationships:
     - `IS_REPLY_TO`: Semantic reply relationships inferred by GPT-3.5-turbo
     - `IS_SEQUENTIAL_TO`: Structural relationships to subsequent 20 posts
   - Graph traversal for collecting rich conversation context

2. **Two-Database Architecture**:
   - **Source DB**: Read-only access to existing bulletin board data
   - **RAG DB**: Dedicated PostgreSQL for knowledge graph (posts and relationships)
   - Complete separation ensures no impact on existing system

3. **LangGraph Workflow**:
   - `vector_retriever`: Find relevant posts using Chroma similarity search
   - `graph_traverser`: Traverse knowledge graph from starting posts
   - `context_synthesizer`: Format graph context for LLM
   - `response_generator`: Generate answer with GPT-4o

4. **Data Sync Pipeline**:
   - ETL process from source DB to RAG DB
   - Batch processing with configurable intervals
   - LLM-based relationship inference during sync
   - Incremental updates support

5. **Streaming Response Architecture**:
   - Uses Server-Sent Events (SSE) for real-time token streaming
   - FastAPI StreamingResponse + LangChain AsyncIteratorCallbackHandler
   - Frontend handles ReadableStream with TextDecoder for typewriter effect

## Database Schema

### Source Database (Read-only)
The `public.res` table contains bulletin board posts:
- `no`: Post number (primary key)
- `name_and_trip`: Author identification
- `datetime`: Timestamp
- `id`: Post ID
- `main_text`: Plain text content (used for embeddings)
- `main_text_html`: HTML formatted content

### RAG Database (GraphRAG)
**posts** table (Knowledge graph nodes):
- `post_id`: UUID primary key
- `source_post_no`: Original post number from source DB
- `content`: Post text content
- `timestamp`: Post timestamp
- `created_at`, `updated_at`: Tracking fields

**relationships** table (Knowledge graph edges):
- `relationship_id`: UUID primary key
- `source_node_id`: Source post UUID (FK)
- `target_node_id`: Target post UUID (FK)
- `relationship_type`: Type of relationship (IS_REPLY_TO, IS_SEQUENTIAL_TO)
- `properties`: JSONB field for additional metadata
- `created_at`: Creation timestamp

## Project Structure

```
backend/
├── app/
│   ├── api/endpoints/    # API endpoints (chat.py for /ask)
│   ├── core/             # Configuration
│   ├── rag/              # RAG pipeline components
│   │   ├── chain.py      # RAG chain definition
│   │   ├── loader.py     # PostgresResLoader
│   │   └── retriever.py  # ParentDocumentRetriever setup
│   └── main.py           # FastAPI app entry
└── scripts/
    ├── create_index.py   # Full index creation script
    └── update_index.py   # Incremental update script

frontend/
├── src/
│   ├── api/              # Auto-generated from OpenAPI
│   ├── components/       # React components
│   │   ├── ChatInterface.tsx
│   │   ├── Message.tsx
│   │   └── InputForm.tsx
│   └── App.tsx
└── package.json
```

## Environment Variables

Create `.env` file in the project root directory (not in backend/):
```bash
# Copy from .env.example
cp .env.example .env
```

Edit `.env` with your values:
```
# PostgreSQL Databases
DATABASE_URL=postgresql://user:password@localhost:5432/bbs2  # Source DB (read-only)
RAG_DATABASE_URL=postgresql://user:password@localhost:5432/bbs_rag  # RAG DB for GraphRAG

# OpenAI API
OPENAI_API_KEY=sk-...

# Vector Store
COLLECTION_NAME=bbs_rag_collection

# Backend Settings
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Frontend Settings (for development)
VITE_API_URL=http://localhost:8000

# API CORS Origins (comma-separated)
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Important**: The `.env` file should be placed in the project root directory, not in the backend or frontend subdirectories. Both backend and frontend are configured to read from the root `.env` file.

## Development Workflow

1. Set up PostgreSQL databases:
   - Source database with bulletin board data (existing)
   - RAG database for GraphRAG (new, empty)
2. Configure environment variables in `.env`
3. Initialize RAG database: `python scripts/init_rag_db.py`
4. Run data sync pipeline: `python scripts/sync_data.py --initial` (or without --initial for continuous)
5. Create vector index: `python scripts/create_graphrag_index.py`
6. Start backend server: `make dev`
7. Generate TypeScript client from OpenAPI spec
8. Start frontend development server

## Key Implementation Details

- **GraphRAG Architecture**: Knowledge graph-based retrieval combining vector search with graph traversal
- **LangGraph Workflow**: State machine for orchestrating retrieval, traversal, and generation steps
- **Relationship Inference**: GPT-3.5-turbo analyzes post content to identify semantic reply relationships
- **Graph Traversal**: Recursive SQL queries traverse up to 3 hops in the knowledge graph
- **Dual Relationship Types**: IS_REPLY_TO (semantic) and IS_SEQUENTIAL_TO (structural)
- **Streaming**: AsyncIteratorCallbackHandler for real-time token streaming
- **Frontend TypeScript client**: Auto-generated from FastAPI's OpenAPI schema
- **Vector embeddings**: OpenAI's text-embedding-3-small model for cost efficiency