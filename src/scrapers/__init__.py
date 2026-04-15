"""
AI News Aggregator - Scrapers Module
Web scrapers for various AI news sources
"""

from src.scrapers.base import BaseScraper, ArticleData, ScraperResult, ScraperRegistry

# Import all scrapers to trigger registration
from src.scrapers import openai_scraper
from src.scrapers import anthropic_scraper
from src.scrapers import google_ai_scraper
from src.scrapers import huggingface_scraper
from src.scrapers import marktechpost_scraper
from src.scrapers import techcrunch_scraper
from src.scrapers import venturebeat_scraper
from src.scrapers import mit_news_scraper
from src.scrapers import unite_ai_scraper
from src.scrapers import ainews_scraper
from src.scrapers import theverge_scraper

__all__ = [
    "BaseScraper",
    "ArticleData", 
    "ScraperResult",
    "ScraperRegistry",
]