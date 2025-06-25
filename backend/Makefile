.PHONY: help install install-dev run format lint type-check test clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install all dependencies including dev"
	@echo "  make run          - Run the development server"
	@echo "  make format       - Format code with black and ruff"
	@echo "  make lint         - Run linting checks"
	@echo "  make type-check   - Run type checking with mypy"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Clean up cache files"

install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

format:
	black .
	ruff check --fix .

lint:
	ruff check .
	black --check .

type-check:
	mypy .

test:
	pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +