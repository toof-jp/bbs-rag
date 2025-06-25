# BBS RAG Backend

FastAPI backend for the BBS RAG application.

## Configuration

### OpenAI Model Selection

Configure the AI models in your `.env` file:

```env
# Choose your model based on cost/quality tradeoff:
OPENAI_MODEL=gpt-4o-mini       # Default: $0.0005/query (recommended)
# OPENAI_MODEL=gpt-3.5-turbo   # $0.0015/query (budget option)
# OPENAI_MODEL=gpt-4o          # $0.0081/query (highest quality)

OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # Default embedding model
```

## Setup with uv

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

## Development

```bash
# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run linting
ruff check .
black --check .

# Run type checking
mypy .

# Format code
black .
ruff check --fix .
```