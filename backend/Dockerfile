FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY README.md ./
COPY app ./app
COPY scripts ./scripts

# Install dependencies using uv
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Expose port
EXPOSE 8000

# Set environment to use the virtual environment
ENV PATH="/app/.venv/bin:${PATH}"

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]