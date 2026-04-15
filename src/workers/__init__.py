"""
AI News Aggregator - Workers Module
Background workers for scraping, processing, and publishing news
"""

from src.workers.scraper_worker import ScraperWorker
from src.workers.digest_worker import DigestWorker

__all__ = ["ScraperWorker", "DigestWorker"]
