#!/usr/bin/env python3
"""Initialize RAG database tables."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import init_rag_db


def main() -> None:
    """Initialize RAG database."""
    print("🔧 Initializing RAG database tables...")

    try:
        init_rag_db()
        print("✅ RAG database initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
