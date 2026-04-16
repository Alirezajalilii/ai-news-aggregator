"""Mark already-sent articles as is_sent = True to prevent re-sending"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.database.models import Article, SentMessage

DB_URL = "postgresql+asyncpg://planchin:dev_password@localhost:5432/ai_news"

async def mark_sent():
    engine = create_async_engine(DB_URL, pool_size=5)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Find all article IDs that have been sent (have SentMessage records)
        result = await session.execute(
            select(SentMessage.article_id).distinct()
        )
        sent_article_ids = [row[0] for row in result.all()]
        
        print(f"Found {len(sent_article_ids)} articles with sent message records")
        
        # Mark those articles as sent
        for article_id in sent_article_ids:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if article and not article.is_sent:
                article.is_sent = True
                print(f"  Marked as sent: {article.title[:60]}...")
        
        await session.commit()
        
        # Show stats
        result = await session.execute(
            select(func.count(Article.id)).where(Article.is_sent == True)
        )
        sent_count = result.scalar()
        
        result = await session.execute(
            select(func.count(Article.id))
        )
        total = result.scalar()
        
        result = await session.execute(
            select(func.count(Article.id)).where(Article.is_sent == False)
        )
        unsent = result.scalar()
        
        print(f"\n📊 Stats:")
        print(f"  Total articles: {total}")
        print(f"  Marked as sent: {sent_count}")
        print(f"  Unsent (ready to send): {unsent}")
    
    await engine.dispose()

asyncio.run(mark_sent())