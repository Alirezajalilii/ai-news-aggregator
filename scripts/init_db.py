#!/usr/bin/env python3
"""
Database initialization script
Run this before starting the application
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import init_db, Source
from src.core.config import load_config, get_config


async def create_sources():
    """Create default news sources"""
    from src.database import get_async_session
    
    session = await get_async_session()
    
    # Check if sources already exist
    from sqlalchemy import select
    result = await session.execute(select(Source))
    existing = result.scalars().all()
    
    if existing:
        print(f"✓ Sources already exist ({len(existing)} sources)")
        await session.close()
        return
    
    # Create default sources from config
    config = get_config()
    
    for source_config in config.scraper.sources:
        source = Source(
            name=source_config.name,
            url=source_config.url,
            category=source_config.category,
            priority=source_config.priority,
            enabled=source_config.enabled,
        )
        session.add(source)
        print(f"  + Created source: {source_config.name}")
    
    await session.commit()
    await session.close()
    print(f"✓ Created {len(config.scraper.sources)} sources")


async def main():
    print("=" * 50)
    print("AI News Aggregator - Database Setup")
    print("=" * 50)
    
    # Load config
    try:
        load_config("config.yaml")
        print("✓ Config loaded")
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        sys.exit(1)
    
    # Initialize database
    print("\nInitializing database tables...")
    try:
        await init_db()
        print("✓ Database tables created")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)
    
    # Create sources
    print("\nCreating news sources...")
    await create_sources()
    
    print("\n" + "=" * 50)
    print("✓ Setup complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("  1. Start the scheduler: python -m src.main scheduler")
    print("  2. Or run a manual scrape: python -m src.main scrape")


if __name__ == "__main__":
    asyncio.run(main())
