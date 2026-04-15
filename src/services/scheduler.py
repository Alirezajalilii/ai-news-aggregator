"""
AI News Aggregator - Scheduler
APScheduler-based job scheduler for periodic tasks
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.core.config import get_config

logger = logging.getLogger(__name__)


class NewsScheduler:
    """
    Scheduler for running periodic news aggregation tasks
    """
    
    def __init__(self):
        self.config = get_config()
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._scraper_worker = None
        self._digest_worker = None
    
    @property
    def scraper_worker(self):
        if self._scraper_worker is None:
            from src.workers.scraper_worker import ScraperWorker
            self._scraper_worker = ScraperWorker()
        return self._scraper_worker
    
    @property
    def digest_worker(self):
        if self._digest_worker is None:
            from src.workers.digest_worker import DigestWorker
            self._digest_worker = DigestWorker()
        return self._digest_worker
    
    def start(self):
        """Start the scheduler"""
        if self.scheduler is not None:
            logger.warning("Scheduler already started")
            return
        
        self.scheduler = AsyncIOScheduler(timezone=self.config.scheduler.timezone)
        
        # Add jobs from config
        for job_config in self.config.scheduler.jobs:
            if not job_config.enabled:
                continue
            
            if job_config.name == "fetch_all_sources":
                self._add_fetch_job(job_config)
            elif job_config.name == "cleanup_old_news":
                self._add_cleanup_job(job_config)
            elif job_config.name == "send_digest":
                self._add_digest_job(job_config)
        
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            logger.info("Scheduler stopped")
    
    def _add_fetch_job(self, job_config):
        """Add job for fetching news from all sources"""
        trigger = CronTrigger.from_crontab(job_config.schedule)
        
        self.scheduler.add_job(
            self._run_fetcher,
            trigger=trigger,
            id=job_config.name,
            name=job_config.description,
            replace_existing=True,
            max_instances=1,
        )
        
        logger.info(f"Added fetch job: {job_config.schedule}")
    
    def _add_cleanup_job(self, job_config):
        """Add job for cleaning up old news"""
        trigger = CronTrigger.from_crontab(job_config.schedule)
        
        self.scheduler.add_job(
            self._run_cleanup,
            trigger=trigger,
            id=job_config.name,
            name=job_config.description,
            replace_existing=True,
            max_instances=1,
        )
        
        logger.info(f"Added cleanup job: {job_config.schedule}")
    
    def _add_digest_job(self, job_config):
        """Add job for sending digests"""
        trigger = CronTrigger.from_crontab(job_config.schedule)
        
        self.scheduler.add_job(
            self._run_digest,
            trigger=trigger,
            id=job_config.name,
            name=job_config.description,
            replace_existing=True,
            max_instances=1,
        )
        
        logger.info(f"Added digest job: {job_config.schedule}")
    
    async def _run_fetcher(self):
        """Run the scraper worker"""
        logger.info("Running scheduled fetch job")
        try:
            stats = await self.scraper_worker.run()
            logger.info(f"Fetch job completed: {stats}")
        except Exception as e:
            logger.error(f"Error in fetch job: {e}")
    
    async def _run_cleanup(self):
        """Run cleanup of old articles"""
        logger.info("Running scheduled cleanup job")
        # TODO: Implement cleanup logic
        pass
    
    async def _run_digest(self):
        """Run the digest worker"""
        logger.info("Running scheduled digest job")
        try:
            stats = await self.digest_worker.run()
            logger.info(f"Digest job completed: {stats}")
        except Exception as e:
            logger.error(f"Error in digest job: {e}")
    
    async def run_now(self, job_name: str):
        """Manually trigger a job"""
        logger.info(f"Manually triggering job: {job_name}")
        
        if job_name == "fetch_all_sources":
            await self._run_fetcher()
        elif job_name == "cleanup_old_news":
            await self._run_cleanup()
        elif job_name == "send_digest":
            await self._run_digest()
        else:
            logger.warning(f"Unknown job: {job_name}")


# Singleton scheduler
_scheduler: Optional[NewsScheduler] = None


def get_scheduler() -> NewsScheduler:
    """Get singleton scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = NewsScheduler()
    return _scheduler
