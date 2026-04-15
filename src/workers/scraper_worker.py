"""
AI News Aggregator - Scraper Worker
Background worker that fetches news from all sources
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_config
from src.database.models import Article, Source, init_db, get_async_session
from src.scrapers import ScraperRegistry
from src.services.entity_extractor import EntityExtractor
from src.services.deduplication import DeduplicationService

logger = logging.getLogger(__name__)


class ScraperWorker:
    """
    Worker that scrapes all configured sources and saves articles to database
    """
    
    def __init__(self):
        self.config = get_config()
        self.entity_extractor = EntityExtractor()
        self.scraper_config = self.config.scraper
        self._session: Optional[AsyncSession] = None
    
    async def get_session(self) -> AsyncSession:
        """Get or create database session"""
        if self._session is None:
            self._session = await get_async_session()
        return self._session
    
    async def close_session(self):
        """Close database session"""
        if self._session is not None:
            await self._session.close()
            self._session = None
    
    async def run(self) -> Dict[str, any]:
        """
        Run the scraper worker
        
        Returns:
            Dict with scraping statistics
        """
        logger.info("Starting scraper worker")
        start_time = datetime.utcnow()
        
        stats = {
            "sources_processed": 0,
            "sources_failed": 0,
            "articles_scraped": 0,
            "articles_saved": 0,
            "articles_duplicate": 0,
            "errors": []
        }
        
        try:
            # Initialize database
            await init_db()
            session = await self.get_session()
            
            # Get all enabled sources from config
            source_configs = [s for s in self.scraper_config.sources if s.enabled]
            
            # Scrape in batches for concurrency control
            batch_size = self.scraper_config.batch_size
            all_results = []
            
            for i in range(0, len(source_configs), batch_size):
                batch = source_configs[i:i + batch_size]
                results = await self._scrape_batch(batch, session)
                all_results.extend(results)
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            # Process results
            for scraper_result in all_results:
                if scraper_result.success:
                    stats["sources_processed"] += 1
                    stats["articles_scraped"] += scraper_result.article_count
                    
                    # Save articles
                    saved, dupes = await self._save_articles(scraper_result, session)
                    stats["articles_saved"] += saved
                    stats["articles_duplicate"] += dupes
                else:
                    stats["sources_failed"] += 1
                    stats["errors"].append({
                        "source": scraper_result.source_name,
                        "error": scraper_result.error
                    })
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            stats["duration_seconds"] = duration
            
            logger.info(
                f"Scraper worker completed in {duration:.2f}s. "
                f"Processed {stats['sources_processed']} sources, "
                f"saved {stats['articles_saved']} articles, "
                f"skipped {stats['articles_duplicate']} duplicates"
            )
            
        except Exception as e:
            logger.error(f"Error in scraper worker: {e}")
            stats["errors"].append({"general": str(e)})
        
        finally:
            await self.close_session()
        
        return stats
    
    async def _scrape_batch(self, source_configs: List, session: AsyncSession) -> List:
        """Scrape a batch of sources concurrently"""
        tasks = []
        
        for source_config in source_configs:
            # Get or create source in database
            source = await self._get_or_create_source(source_config, session)
            
            # Create scraper
            scraper = ScraperRegistry.get_scraper(source_config.name)
            
            if scraper:
                tasks.append(self._scrape_source(scraper, source, session))
            else:
                logger.warning(f"No scraper found for source: {source_config.name}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [r for r in results if not isinstance(r, Exception)]
    
    async def _scrape_source(self, scraper, source: Source, session: AsyncSession):
        """Scrape a single source and update source metadata"""
        try:
            result = await scraper.scrape()
            
            # Update source metadata
            source.last_fetched_at = datetime.utcnow()
            source.fetch_count += 1
            
            if result.success:
                source.last_error = None
            else:
                source.error_count += 1
                source.last_error = result.error
            
            await session.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error scraping source {source.name}: {e}")
            source.error_count += 1
            source.last_error = str(e)
            await session.commit()
            raise
    
    async def _get_or_create_source(self, source_config, session: AsyncSession) -> Source:
        """Get or create source in database"""
        query = select(Source).where(Source.name == source_config.name)
        result = await session.execute(query)
        source = result.scalar_one_or_none()
        
        if source is None:
            source = Source(
                name=source_config.name,
                url=source_config.url,
                category=source_config.category,
                priority=source_config.priority,
                enabled=source_config.enabled,
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
        
        return source
    
    async def _save_articles(self, scraper_result, session: AsyncSession) -> tuple:
        """Save scraped articles to database"""
        saved = 0
        duplicates = 0
        
        dedup_service = DeduplicationService(session)
        
        for article_data in scraper_result.articles:
            try:
                # Extract entities
                entities = self.entity_extractor.extract_to_list(
                    f"{article_data.title} {article_data.summary or ''}"
                )
                
                # Check for duplicates
                is_dup, original, similarity_info = await dedup_service.is_duplicate(
                    title=article_data.title,
                    url=article_data.url,
                    entities=entities,
                    content=article_data.summary
                )
                
                if is_dup and original:
                    # Mark as duplicate
                    await dedup_service.mark_as_duplicate(
                        type('Article', (), {'id': None, 'title': article_data.title})(),
                        original
                    )
                    duplicates += 1
                    continue
                
                # Get source
                query = select(Source).where(Source.name == scraper_result.source_name)
                result = await session.execute(query)
                source = result.scalar_one_or_none()
                
                if not source:
                    continue
                
                # Create article
                article = Article(
                    source_id=source.id,
                    title=article_data.title,
                    summary=article_data.summary,
                    content=article_data.content,
                    url=article_data.url,
                    image_url=article_data.image_url,
                    published_at=article_data.published_at,
                    entities={"entities": entities, "tags": article_data.tags},
                    tags=article_data.tags,
                    content_hash=article_data.generate_hash(),
                    title_hash=article_data.generate_title_hash(),
                )
                
                session.add(article)
                saved += 1
                
            except Exception as e:
                logger.debug(f"Error saving article: {e}")
                continue
        
        await session.commit()
        return saved, duplicates


# Make Optional available
from typing import Optional
