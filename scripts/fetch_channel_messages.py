"""
AI News Aggregator - Fetch Channel Messages Utility
Fetches recent messages from the Telegram channel for analysis/debugging
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime

# Config
BOT_TOKEN = "7856786987:AAF6ikQ_C_VXDYO78CKW6V_X-US-PKS7w3U"
CHANNEL = "@ainews_ramzbank"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def fetch_channel_messages(limit: int = 20):
    """Fetch recent messages from the channel"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, try to get channel info
        me = await client.get(f"{BASE_URL}/getMe")
        me_data = me.json()
        print(f"Bot: @{me_data['result']['username']}")
        print()
        
        # Try to get updates (may not work for channels)
        # Instead, use getChat to check access
        chat_info = await client.get(f"{BASE_URL}/getChat", params={"chat_id": CHANNEL})
        chat_data = chat_info.json()
        
        if not chat_data.get("ok"):
            print(f"Error accessing channel: {chat_data}")
            return
        
        chat = chat_data["result"]
        print(f"Channel: {chat.get('title', CHANNEL)}")
        print(f"Type: {chat.get('type', 'unknown')}")
        print()
        
        # Fetch messages via getChat + forwardMessages trick
        # Actually, bots can't read channel history directly via API
        # We need to use getUpdates or the channel posts approach
        
        # Method: Check if bot is admin in channel, then try to get messages
        # Actually Telegram Bot API doesn't have a method to read channel messages
        
        # Alternative: Use the database to check sent articles
        print("=" * 80)
        print("NOTE: Telegram Bot API doesn't support reading channel history.")
        print("Checking database for sent articles instead...")
        print("=" * 80)
        print()
        
        # Connect to database and check recent articles
        from sqlalchemy import select, desc
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        
        DB_URL = "postgresql+asyncpg://planchin:dev_password@localhost:5432/ai_news"
        
        engine = create_async_engine(DB_URL, pool_size=5)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            from src.database.models import Article, SentMessage
            
            # Get recent sent articles
            query = (
                select(Article)
                .where(Article.is_sent == True)
                .order_by(Article.scraped_at.desc())
                .limit(30)
            )
            result = await session.execute(query)
            articles = result.scalars().all()
            
            print(f"Last {len(articles)} sent articles:")
            print("=" * 80)
            
            for i, article in enumerate(articles, 1):
                print(f"\n--- Article #{i} ---")
                print(f"Title: {article.title}")
                print(f"Source: {article.source_name}")
                print(f"Category: {article.category}")
                print(f"URL: {article.url}")
                print(f"Published: {article.published_at}")
                print(f"Scraped: {article.scraped_at}")
                print(f"Sent count: {article.sent_count}")
                print(f"Is duplicate: {article.is_duplicate}")
                print(f"Summary length: {len(article.summary) if article.summary else 0}")
                if article.summary:
                    # Show first 200 chars of summary
                    print(f"Summary preview: {article.summary[:200]}")
                
                # Check sent messages for this article
                sent_query = select(SentMessage).where(SentMessage.article_id == article.id)
                sent_result = await session.execute(sent_query)
                sent_msgs = sent_result.scalars().all()
                print(f"Sent messages: {len(sent_msgs)}")
                for sm in sent_msgs:
                    print(f"  - Channel: {sm.channel_id}, Delivered: {sm.delivered}, Sent at: {sm.sent_at}")
            
            # Check for duplicate issues - same URL appearing multiple times
            print("\n\n" + "=" * 80)
            print("DUPLICATE ANALYSIS")
            print("=" * 80)
            
            # Check for same URLs
            from sqlalchemy import func
            dup_query = (
                select(Article.url, func.count(Article.id).label("count"))
                .group_by(Article.url)
                .having(func.count(Article.id) > 1)
                .order_by(desc(func.count(Article.id)))
                .limit(20)
            )
            dup_result = await session.execute(dup_query)
            duplicates = dup_result.all()
            
            if duplicates:
                print(f"\nFound {len(duplicates)} URLs with duplicates:")
                for url, count in duplicates:
                    print(f"  [{count}x] {url}")
            else:
                print("\nNo URL duplicates found!")
            
            # Check for similar titles
            print("\n\n" + "=" * 80)
            print("TITLE SIMILARITY CHECK")
            print("=" * 80)
            
            recent_query = (
                select(Article)
                .order_by(Article.scraped_at.desc())
                .limit(50)
            )
            recent_result = await session.execute(recent_query)
            recent_articles = recent_result.scalars().all()
            
            # Simple check: same title appearing
            title_counts = {}
            for a in recent_articles:
                title_lower = a.title.lower().strip()
                if title_lower in title_counts:
                    title_counts[title_lower].append(a)
                else:
                    title_counts[title_lower] = [a]
            
            found_similar = False
            for title, articles_list in title_counts.items():
                if len(articles_list) > 1:
                    found_similar = True
                    print(f"\nDUPLICATE TITLE ({len(articles_list)}x): {title[:80]}")
                    for a in articles_list:
                        print(f"  - ID: {a.id}, Source: {a.source_name}, Sent: {a.is_sent}, Dup: {a.is_duplicate}")
            
            if not found_similar:
                print("\nNo duplicate titles found in recent articles!")
            
            # Check summary quality
            print("\n\n" + "=" * 80)
            print("SUMMARY QUALITY CHECK")
            print("=" * 80)
            
            for article in recent_articles[:10]:
                has_persian = False
                if article.summary:
                    # Check if summary contains Persian characters
                    for char in article.summary:
                        if '\u0600' <= char <= '\u06FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
                            has_persian = True
                            break
                
                print(f"\nTitle: {article.title[:60]}")
                print(f"  Has Persian: {has_persian}")
                print(f"  Summary length: {len(article.summary) if article.summary else 0}")
                if article.summary:
                    print(f"  Summary: {article.summary[:150]}...")
                else:
                    print(f"  Summary: NONE!")
        
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fetch_channel_messages(limit=20))