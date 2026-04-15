"""
AI News Aggregator - Base Scraper
Each scraper is fully self-contained with its own fetch strategy.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from bs4 import BeautifulSoup

from src.core.config import get_config


@dataclass
class ArticleData:
    """Single article data"""
    title: str
    url: str
    summary: Optional[str] = None
    image_url: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScraperResult:
    """Result from a scraper run"""
    source_name: str
    success: bool
    articles: List[ArticleData] = field(default_factory=list)
    error: Optional[str] = None
    article_count: int = 0
    
    def __post_init__(self):
        self.article_count = len(self.articles)


class BaseScraper(ABC):
    """
    Base class for web scrapers.
    
    Each scraper is fully self-contained and specifies:
    - fetch_strategy: How to get the HTML (httpx, curl, ollama, playwright, brave)
    - Each scraper implements its own parse logic
    """
    
    # Override these in each scraper
    name: str = "base"
    base_url: str = ""
    fetch_strategy: str = "httpx"  # httpx, curl, ollama, playwright, brave
    
    def __init__(self):
        self.config = get_config()
        self.scraper_config = self.config.scraper
        self.logger = logging.getLogger(f"scraper.{self.name}")
    
    @abstractmethod
    async def parse_articles(self, content: str | BeautifulSoup, url: str) -> List[ArticleData]:
        """
        Parse articles from HTML content or BeautifulSoup
        
        Args:
            content: HTML string or BeautifulSoup object
            url: Source URL (for context)
            
        Returns:
            List of ArticleData objects
        """
        pass
    
    def _html_to_soup(self, content: str | BeautifulSoup) -> BeautifulSoup:
        """Convert HTML string to BeautifulSoup if needed"""
        if isinstance(content, str):
            return BeautifulSoup(content, "html.parser")
        return content
    
    async def scrape(self) -> ScraperResult:
        """
        Main entry point: fetch and parse articles
        
        Returns:
            ScraperResult with articles or error
        """
        try:
            html_content = await self._fetch()
            
            if not html_content:
                return ScraperResult(
                    source_name=self.name,
                    success=False,
                    error="Failed to fetch content"
                )
            
            # Convert to BeautifulSoup for parsing
            soup = self._html_to_soup(html_content)
            articles = await self.parse_articles(soup, self.base_url)
            
            return ScraperResult(
                source_name=self.name,
                success=True,
                articles=articles
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping {self.name}: {e}")
            return ScraperResult(
                source_name=self.name,
                success=False,
                error=str(e)
            )
    
    async def _fetch(self) -> Optional[str]:
        """
        Fetch content using the scraper's designated strategy
        
        Returns:
            HTML content as string, or None if failed
        """
        from src.scrapers.fetch_strategies import get_fetch_strategy
        
        strategy = get_fetch_strategy(
            self.fetch_strategy,
            timeout=self.scraper_config.request_timeout
        )
        
        return await strategy.fetch(self.base_url)
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        # Remove extra whitespace
        text = " ".join(text.split())
        return text.strip()
    
    def extract_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        try:
            # Try common formats
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        return None


class ScraperRegistry:
    """Registry to get scraper by name"""
    _scrapers: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, scraper_class: type):
        cls._scrapers[name] = scraper_class
    
    @classmethod
    def get_scraper(cls, name: str) -> Optional[BaseScraper]:
        if name in cls._scrapers:
            return cls._scrapers[name]()
        return None
    
    @classmethod
    def list_scrapers(cls) -> List[str]:
        return list(cls._scrapers.keys())