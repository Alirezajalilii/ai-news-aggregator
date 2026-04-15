"""
AI News Aggregator - Scrapers Module
Web scrapers for various AI news sources
"""

from src.scrapers.base import BaseScraper, ArticleData, ScraperResult
from src.scrapers.openai_scraper import OpenAIScraper
from src.scrapers.anthropic_scraper import AnthropicScraper
from src.scrapers.google_ai_scraper import GoogleAIScraper
from src.scrapers.huggingface_scraper import HuggingFaceScraper
from src.scrapers.marktechpost_scraper import MarkTechPostScraper
from src.scrapers.techcrunch_scraper import TechCrunchScraper
from src.scrapers.venturebeat_scraper import VentureBeatScraper
from src.scrapers.mit_news_scraper import MITNewsScraper
from src.scrapers.unite_ai_scraper import UniteAIScraper
from src.scrapers.ainews_scraper import AINewsScraper
from src.scrapers.theverge_scraper import TheVergeScraper
from src.scrapers.registry import ScraperRegistry

__all__ = [
    "BaseScraper",
    "ArticleData", 
    "ScraperResult",
    "OpenAIScraper",
    "AnthropicScraper",
    "GoogleAIScraper",
    "HuggingFaceScraper",
    "MarkTechPostScraper",
    "TechCrunchScraper",
    "VentureBeatScraper",
    "MITNewsScraper",
    "UniteAIScraper",
    "AINewsScraper",
    "TheVergeScraper",
    "ScraperRegistry",
]
