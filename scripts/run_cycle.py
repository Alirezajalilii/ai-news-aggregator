"""Run a manual fetch+digest cycle to test the fixed summarizer and deduplication"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.workers.scraper_worker import ScraperWorker
from src.workers.digest_worker import DigestWorker
from src.database.models import init_db, close_db

async def main():
    print("🔧 Running manual fetch+digest cycle...")
    print()
    
    # 1. Scrape
    print("📡 Step 1: Fetching news from sources...")
    worker = ScraperWorker()
    stats = await worker.run()
    print(f"   Sources processed: {stats.get('sources_processed', 0)}")
    print(f"   Articles scraped: {stats.get('articles_scraped', 0)}")
    print(f"   Articles saved: {stats.get('articles_saved', 0)}")
    print(f"   Articles duplicate: {stats.get('articles_duplicate', 0)}")
    print(f"   Errors: {len(stats.get('errors', []))}")
    if stats.get('errors'):
        for e in stats['errors'][:5]:
            print(f"     - {e}")
    print()
    
    # 2. Send digest
    print("📤 Step 2: Sending digest to channel...")
    digest = DigestWorker()
    digest_stats = await digest.run()
    print(f"   Subscribers notified: {digest_stats.get('subscribers_notified', 0)}")
    print(f"   Messages sent: {digest_stats.get('messages_sent', 0)}")
    print(f"   Articles included: {digest_stats.get('articles_included', 0)}")
    if digest_stats.get('errors'):
        for e in digest_stats['errors'][:5]:
            print(f"     - {e}")
    print()
    
    # 3. Close
    await close_db()
    
    print("✅ Manual cycle complete!")

asyncio.run(main())