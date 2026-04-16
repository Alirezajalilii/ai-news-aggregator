#!/usr/bin/env python3
"""Fetch and analyze last N messages from Telegram channel for debugging"""
import asyncio
import sys
import os
import json
from datetime import datetime

BOT_TOKEN = "7856786987:AAF6ikQ_C_VXDYO78CKW6V_X-US-PKS7w3U"
CHANNEL = "@ainews_ramzbank"

async def fetch_messages(limit=20):
    import httpx
    
    async with httpx.AsyncClient() as client:
        # Get channel chat ID first
        resp = await client.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
            params={"chat_id": CHANNEL}
        )
        chat_data = resp.json()
        if not chat_data.get("ok"):
            print(f"Error getting chat: {chat_data}")
            return
        
        chat_id = chat_data["result"]["id"]
        print(f"Channel: {chat_data['result'].get('title', CHANNEL)} (ID: {chat_id})")
        print(f"{'='*80}")
        
        # Get recent messages
        resp = await client.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"limit": 100, "offset": -100}
        )
        
        # Use forwardMessages to get channel posts
        # Actually, bots can't read channel history directly. Let's use a different approach.
        # We'll use the getChat method and look at linked_chat_id
        
        # Try to get messages via getUpdates (only works for messages bot receives)
        # For channels, we need to check sent messages via our DB
        
        print("\n⚠️  Telegram Bot API doesn't support reading channel history directly.")
        print("   Checking database for sent messages instead...\n")
        
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from sqlalchemy import select, func
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from src.database.models import Article, SentMessage
        
        DB_URL = "postgresql+asyncpg://planchin:dev_password@localhost:5432/ai_news"
        engine = create_async_engine(DB_URL, pool_size=5)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Get recent sent messages
            result = await session.execute(
                select(SentMessage)
                .order_by(SentMessage.sent_at.desc())
                .limit(limit)
            )
            messages = result.scalars().all()
            
            if not messages:
                print("No sent messages found in database.")
                return
            
            print(f"Last {len(messages)} sent messages:\n")
            
            for i, msg in enumerate(messages, 1):
                # Get article details
                result = await session.execute(
                    select(Article).where(Article.id == msg.article_id)
                )
                article = result.scalar_one_or_none()
                
                print(f"--- Message #{i} ---")
                print(f"  Sent at: {msg.sent_at}")
                print(f"  TG msg ID: {msg.message_id}")
                print(f"  Source: {article.source_name if article else 'N/A'}")
                print(f"  Title: {article.title[:80] if article and article.title else 'N/A'}...")
                print(f"  URL: {article.url if article else 'N/A'}")
                summary = article.summary or 'NO SUMMARY'
                print(f"  Summary: {summary[:150]}...")
                print(f"  Has Persian: {_has_persian(article.summary) if article else False}")
                print(f"  Hash: {article.content_hash[:16] if article and article.content_hash else 'N/A'}...")
                print()
            
            # Check for duplicates
            print(f"\n{'='*80}")
            print("DUPLICATE CHECK:")
            print(f"{'='*80}")
            
            result = await session.execute(
                select(Article.url, func.count(Article.id).label('count'))
                .where(Article.url != '', Article.url != None)
                .group_by(Article.url)
                .having(func.count(Article.id) > 1)
                .order_by(func.count(Article.id).desc())
            )
            dup_urls = result.all()
            
            if dup_urls:
                print(f"\n⚠️  Found {len(dup_urls)} URLs with duplicate articles:")
                for url, count in dup_urls[:10]:
                    print(f"  ({count}x) {url[:80]}...")
            else:
                print("\n✅ No duplicate URLs found in database!")
            
            # Check title duplicates
            result = await session.execute(
                select(Article.title, func.count(Article.id).label('count'))
                .group_by(Article.title)
                .having(func.count(Article.id) > 1)
                .order_by(func.count(Article.id).desc())
            )
            dup_titles = result.all()
            
            if dup_titles:
                print(f"\n⚠️  Found {len(dup_titles)} titles with duplicate articles:")
                for title, count in dup_titles[:10]:
                    print(f"  ({count}x) {title[:80]}...")
            
            # Articles without summaries
            result = await session.execute(
                select(func.count(Article.id))
                .where((Article.summary == None) | (Article.summary == ''))
            )
            no_summary = result.scalar()
            
            result = await session.execute(
                select(func.count(Article.id))
                .where(Article.is_sent == True)
            )
            sent_count = result.scalar()
            
            result = await session.execute(
                select(func.count(Article.id))
            )
            total = result.scalar()
            
            print(f"\n{'='*80}")
            print("DATABASE STATS:")
            print(f"{'='*80}")
            print(f"  Total articles: {total}")
            print(f"  Sent articles: {sent_count}")
            print(f"  Articles without summary: {no_summary}")
        
        await engine.dispose()

def _has_persian(text):
    if not text:
        return False
    persian_chars = set('ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی')
    return any(c in persian_chars for c in text)

asyncio.run(fetch_messages(20))