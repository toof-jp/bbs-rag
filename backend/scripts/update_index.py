#!/usr/bin/env python3
"""Update vector index with new bulletin board posts (incremental update)."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.create_index import create_index


async def main():
    """Run incremental index update."""
    print("🔄 Running incremental index update...")
    await create_index(incremental=True)


if __name__ == "__main__":
    asyncio.run(main())