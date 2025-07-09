#!/usr/bin/env python3
"""Run data synchronization pipeline."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.sync.pipeline import DataSyncPipeline


def main() -> None:
    """Run data sync pipeline."""
    parser = argparse.ArgumentParser(description="Sync data from source DB to GraphRAG DB")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of posts to process in each batch (default: 100)",
    )
    parser.add_argument(
        "--initial",
        action="store_true",
        help="Run initial full sync (sync all posts) and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval between sync runs in seconds (default: 60)",
    )

    args = parser.parse_args()

    pipeline = DataSyncPipeline()

    if args.initial:
        print(f"🔄 Running initial full sync with batch size {args.batch_size}...")
        count = pipeline.sync_all(args.batch_size)
        print(f"✅ Initial sync completed! Total posts synced: {count}")
    else:
        print(
            f"🔄 Starting continuous sync "
            f"(batch_size={args.batch_size}, interval={args.interval}s)"
        )
        pipeline.run_continuous_sync(args.batch_size, args.interval)


if __name__ == "__main__":
    main()
