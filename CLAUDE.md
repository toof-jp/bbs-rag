# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a BBS (Bulletin Board System) RAG (Retrieval Augmented Generation) application that uses LangChain to provide intelligent Q&A capabilities over bulletin board historical data. The system addresses the challenge of understanding conversation context in boards where anchor functionality (reply-to-post feature) is underutilized.

## Technology Stack

- **Backend**: Python with FastAPI, LangChain for RAG pipeline
- **Frontend**: React with TypeScript, Vite as build tool
- **Database**: PostgreSQL for bulletin board data
- **Vector Store**: Chroma (local file-based vector database)
- **AI/LLM**: OpenAI API (GPT-4o or similar)
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

# Create/update vector index (with progress bar)
python scripts/create_index.py

# Update index with new posts (incremental update)
python scripts/update_index.py

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

The system implements a RAG pipeline with the following key components:

1. **Sliding Window Strategy with Citation Extraction**: 
   - Sliding windows: 50 posts per window with 20 posts overlap
   - Ensures context is preserved regardless of where the relevant information appears
   - Uses GPT-3.5-turbo to extract specific post numbers as citations
   - Displays exact post numbers (No.XXX) with author and timestamp

2. **Streaming Response Architecture**:
   - Uses Server-Sent Events (SSE) for real-time token streaming
   - FastAPI StreamingResponse + LangChain AsyncIteratorCallbackHandler
   - Frontend handles ReadableStream with TextDecoder for typewriter effect

3. **Index Management**:
   - Batch processing script (`scripts/create_index.py`) for initial/full indexing
   - Incremental update script (`scripts/update_index.py`) for adding new posts
   - Uses PostgresResLoader (custom BaseLoader) to read from `res` table
   - Embeddings stored in Chroma (local file at `backend/chroma_db/`) with metadata for filtering
   - Tracks last processed post number in `index_metadata.json`

## Database Schema

The `public.res` table contains bulletin board posts:
- `no`: Post number (primary key)
- `name_and_trip`: Author identification
- `datetime`: Timestamp
- `id`: Post ID
- `main_text`: Plain text content (used for embeddings)
- `main_text_html`: HTML formatted content

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
# PostgreSQL Database
DATABASE_URL=postgresql://user:password@localhost:5432/bbs2

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

1. Set up PostgreSQL with PGVector extension
2. Configure environment variables
3. Run index creation script to build vector store
4. Start backend server
5. Generate TypeScript client from OpenAPI spec
6. Start frontend development server

## Key Implementation Details

- The RAG pipeline uses LangChain's ParentDocumentRetriever for better context preservation
- Streaming is implemented using AsyncIteratorCallbackHandler for real-time responses
- Frontend TypeScript client is auto-generated from FastAPI's OpenAPI schema
- Vector embeddings use OpenAI's text-embedding-3-small model for cost efficiency