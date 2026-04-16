"""Reset all articles to unsent so they can be re-processed with Persian summaries"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.database.models import Article, SentMessage

DB_URL = "postgresql+asyncpg://planchin:dev_password@localhost:5432/ai_news"

async def reset_sent():
    engine = create_async_engine(DB_URL, pool_size=5)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Reset all articles to unsent
        result = await session.execute(
            select(Article)
        )
        all_articles = result.scalars().all()
        
        count = 0
        for article in all_articles:
            if article.is_sent or article.summary is None or article.summary == '':
                article.is_sent = False
                article.sent_count = 0
                count += 1
        
        await session.commit()
        
        # Count remaining
        result = await session.execute(
            select(func.count(Article.id)).where(Article.is_sent == False)
        )
        unsent = result.scalar()
        total = len(all_articles)
        
        print(f'Reset {count} articles to unsent status')
        print(f'Total articles: {total}')
        print(f'Ready to send: {unsent}')
    
    await engine.dispose()

asyncio.run(reset_sent())