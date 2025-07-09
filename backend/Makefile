.PHONY: install dev lint test create-index update-index

# Install dependencies using uv
install:
	uv venv
	uv pip install -e .

# Install dev dependencies
install-dev:
	uv venv
	uv pip install -e ".[dev]"

# Run development server
dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run linting
lint:
	uv run ruff check .
	uv run black --check .
	uv run mypy .

# Format code
format:
	uv run ruff check --fix .
	uv run black .

# Run tests
test:
	uv run pytest

# Create vector index (old sliding window approach)
create-index:
	uv run python scripts/create_index.py

# Create GraphRAG vector index
create-graphrag-index:
	uv run python scripts/create_graphrag_index.py

# Update vector index (incremental)
update-index:
	uv run python scripts/update_index.py

# Initialize RAG database
init-db:
	uv run python scripts/init_rag_db.py

# Run data sync pipeline (once)
sync-once:
	uv run python scripts/sync_data.py --once

# Run continuous data sync
sync:
	uv run python scripts/sync_data.py