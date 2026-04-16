"""Cleanup duplicate/invalid articles from the database"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.database.models import Article, SentMessage

DB_URL = "postgresql+asyncpg://planchin:dev_password@localhost:5432/ai_news"

async def cleanup():
    engine = create_async_engine(DB_URL, pool_size=5)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Delete articles with empty URLs
        result = await session.execute(
            select(Article).where(
                (Article.url == '') | (Article.url == None) | (func.length(Article.url) < 10)
            )
        )
        empty_url_articles = result.scalars().all()
        print(f'Deleting {len(empty_url_articles)} articles with empty/short URLs')
        for a in empty_url_articles:
            print(f'  - [{a.source_name}] {a.title[:60]} (URL: {repr(a.url)[:40]})')
            await session.delete(a)
        
        # 2. Delete articles with category page URLs
        bad_url_patterns = ['/category/', '/tag/', '/feed/', '/rss/', '/page/']
        for pattern in bad_url_patterns:
            result = await session.execute(
                select(Article).where(Article.url.contains(pattern))
            )
            bad_articles = result.scalars().all()
            if bad_articles:
                print(f'Deleting {len(bad_articles)} articles with "{pattern}" in URL')
                for a in bad_articles:
                    await session.delete(a)
        
        # 3. Delete duplicate articles (same URL, keep the oldest)
        result = await session.execute(
            select(Article.url, func.count(Article.id).label('count'))
            .where(Article.url != '')
            .group_by(Article.url)
            .having(func.count(Article.id) > 1)
        )
        dup_urls = result.all()
        
        total_deduped = 0
        for url, count in dup_urls:
            result = await session.execute(
                select(Article)
                .where(Article.url == url)
                .order_by(Article.scraped_at.asc())
            )
            articles = result.scalars().all()
            
            # Keep the first one, delete the rest
            for a in articles[1:]:
                total_deduped += 1
                await session.delete(a)
        
        print(f'Deleted {total_deduped} duplicate articles (same URL)')
        
        # 4. Delete articles with garbage titles (too short or starting with comma)
        import re
        result = await session.execute(
            select(Article).order_by(Article.scraped_at.desc()).limit(200)
        )
        all_articles = result.scalars().all()
        
        bad_title_count = 0
        for a in all_articles:
            # Remove articles with titles that start with comma (Unite.AI garbage)
            if a.title.strip().startswith(','):
                await session.delete(a)
                bad_title_count += 1
            # Remove articles with titles that are too short (less than 15 chars after cleanup)
            elif len(a.title.strip()) < 15:
                await session.delete(a)
                bad_title_count += 1
        
        print(f'Deleted {bad_title_count} articles with garbage titles')
        
        await session.commit()
        print('\n✅ Cleanup complete!')
        
        # Show remaining article count
        result = await session.execute(select(func.count(Article.id)))
        total = result.scalar()
        print(f'Total articles remaining: {total}')
        
        # Show unsent count
        result = await session.execute(
            select(func.count(Article.id)).where(Article.is_sent == False)
        )
        unsent = result.scalar()
        print(f'Unsent articles: {unsent}')
    
    await engine.dispose()

asyncio.run(cleanup())