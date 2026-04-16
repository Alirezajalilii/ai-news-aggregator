#!/usr/bin/env python3
"""Regenerate Persian summaries for articles that don't have one"""
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
    """Check if text contains Persian characters"""
    if not text:
        return False
    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
            return True
    return False

async def regenerate():
    engine = create_async_engine(DB_URL, pool_size=5)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    summarizer = get_summarization_service()
    
    async with async_session() as session:
        # Find articles without Persian summaries
        result = await session.execute(
            select(Article).order_by(Article.scraped_at.desc())
        )
        all_articles = result.scalars().all()
        
        needs_summary = []
        for a in all_articles:
            if not a.summary or not has_persian(a.summary):
                needs_summary.append(a)
        
        print(f"Total articles: {len(all_articles)}")
        print(f"Articles needing Persian summary: {len(needs_summary)}")
        print()
        
        success = 0
        failed = 0
        skipped = 0
        
        for i, article in enumerate(needs_summary, 1):
            # Use content first (longer), then summary, then title
            content = article.content or article.summary or article.title or ""
            if not content or len(content) < 30:
                print(f"  [{i}/{len(needs_summary)}] SKIP (too short): {article.title[:60]}...")
                skipped += 1
                continue
            
            print(f"  [{i}/{len(needs_summary)}] Summarizing: {article.title[:60]}...")
            print(f"    Content length: {len(content)} chars")
            
            try:
                summary = await summarizer.summarize(content, article.url)
                
                if summary and has_persian(summary):
                    article.summary = summary
                    success += 1
                    print(f"    ✅ Generated Persian summary ({len(summary)} chars)")
                elif summary:
                    article.summary = summary
                    success += 1
                    print(f"    ⚠️ Generated non-Persian summary ({len(summary)} chars)")
                else:
                    failed += 1
                    print(f"    ❌ No summary generated")
                
                # Commit every 3 articles
                if i % 3 == 0:
                    await session.commit()
                    print(f"    💾 Committed progress ({success} summaries so far)")
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                failed += 1
            
            # Rate limit - wait between API calls
            await asyncio.sleep(3)
        
        # Final commit
        await session.commit()
        
        print()
        print(f"✅ Done! Success: {success}, Failed: {failed}, Skipped: {skipped}")
        
        # Verify
        result = await session.execute(
            select(func.count(Article.id)).where(
                (Article.summary == None) | (Article.summary == '')
            )
        )
        no_summary = result.scalar()
        
        result = await session.execute(
            select(func.count(Article.id))
        )
        total = result.scalar()
        
        result = await session.execute(
            select(func.count(Article.id))
        )
        all_articles = result.scalars().all()
        with_persian = sum(1 for a in all_articles if has_persian(a.summary or ''))
        
        print(f"Total: {total}, Without summary: {no_summary}, With Persian: {with_persian}")
    
    await summarizer.close()
    await engine.dispose()

asyncio.run(regenerate())