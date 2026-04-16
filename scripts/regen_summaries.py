#!/usr/bin/env python3
"""Regenerate Persian summaries - lightweight version that processes one article at a time"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.database.models import Article
from src.services.summarizer import get_summarization_service

DB_URL = "postgresql+asyncpg://planchin:dev_password@localhost:5432/ai_news"

def has_persian(text: str) -> bool:
    if not text:
        return False
    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
            return True
    return False

async def regenerate():
    engine = create_async_engine(DB_URL, pool_size=3)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    summarizer = get_summarization_service()
    
    async with async_session() as session:
        result = await session.execute(
            select(Article).order_by(Article.scraped_at.desc())
        )
        all_articles = result.scalars().all()
        
        needs_summary = [a for a in all_articles if not has_persian(a.summary or '')]
        
        print(f"Total: {len(all_articles)}, Need Persian summary: {len(needs_summary)}")
        
        success = 0
        failed = 0
        
        for i, article in enumerate(needs_summary, 1):
            content = article.content or article.summary or article.title or ""
            if not content or len(content) < 20:
                print(f"  [{i}/{len(needs_summary)}] SKIP: {article.title[:50]}")
                continue
            
            print(f"  [{i}/{len(needs_summary)}] {article.title[:50]}...", end=" ", flush=True)
            
            try:
                summary = await summarizer.summarize(content, article.url)
                if summary and (has_persian(summary) or len(summary) > 50):
                    article.summary = summary
                    success += 1
                    print(f"✅ ({len(summary)} chars)")
                else:
                    failed += 1
                    print("❌ (empty/short)")
                
                await session.commit()
                
            except Exception as e:
                failed += 1
                print(f"❌ ({e})")
            
            await asyncio.sleep(2)
        
        print(f"\nDone! Success: {success}, Failed: {failed}")
    
    await summarizer.close()
    await engine.dispose()

asyncio.run(regenerate())