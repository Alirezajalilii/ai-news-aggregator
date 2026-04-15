"""
AI News Aggregator - Base Scraper
Abstract base class for all news scrapers
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup

from src.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class ArticleData:
    """Structured data for a scraped article"""
    title: str
    url: str
    summary: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def generate_hash(self) -> str:
        """Generate content hash for deduplication"""
        content = f"{self.title}|{self.url}|{self.summary or ''}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def generate_title_hash(self) -> str:
        """Generate title-only hash for similarity comparison"""
        return hashlib.sha256(self.title.encode()).hexdigest()


@dataclass
class ScraperResult:
    """Result of a scraping operation"""
    source_name: str
    success: bool
    articles: List[ArticleData] = field(default_factory=list)
    error: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0
    
    @property
    def article_count(self) -> int:
        return len(self.articles)


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers
    
    Each scraper implements site-specific logic for extracting articles
    while following a common interface.
    """
    
    name: str = "base"
    base_url: str = ""
    
    def __init__(self):
        self.config = get_config()
        self.scraper_config = self.config.scraper
        self.logger = logging.getLogger(f"scraper.{self.name}")
        
    @abstractmethod
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """
        Parse articles from BeautifulSoup object
        
        Args:
            soup: BeautifulSoup parsed HTML
            url: Source URL
            
        Returns:
            List of ArticleData objects
        """
        pass
    
    async def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a webpage
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if failed
        """
        headers = {
            "User-Agent": self.scraper_config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        for attempt in range(self.scraper_config.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.scraper_config.request_timeout),
                    follow_redirects=True,
                    headers=headers,
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    # Try to detect encoding
                    content = response.text
                    
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(content, "html.parser")
                    return soup
                    
            except httpx.TimeoutException:
                self.logger.warning(f"Timeout fetching {url}, attempt {attempt + 1}/{self.scraper_config.max_retries}")
                
            except httpx.HTTPStatusError as e:
                self.logger.warning(f"HTTP error {e.response.status_code} for {url}, attempt {attempt + 1}/{self.scraper_config.max_retries}")
                
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {e}")
                break
                
            # Wait before retry
            if attempt < self.scraper_config.max_retries - 1:
                await asyncio.sleep(self.scraper_config.retry_delay)
        
        return None
    
    async def scrape(self) -> ScraperResult:
        """
        Main scraping method
        
        Returns:
            ScraperResult with all scraped articles
        """
        start_time = datetime.utcnow()
        result = ScraperResult(source_name=self.name, success=False)
        
        try:
            self.logger.info(f"Starting scrape for {self.name}")
            
            soup = await self.fetch_page(self.base_url)
            if soup is None:
                result.error = "Failed to fetch page"
                return result
            
            articles = await self.parse_articles(soup, self.base_url)
            result.articles = articles
            result.success = True
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = duration
            
            self.logger.info(f"Scraped {len(articles)} articles from {self.name} in {duration:.2f}s")
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Error scraping {self.name}: {e}")
            
        return result
    
    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean extracted text"""
        if not text:
            return None
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Remove common noise patterns
        text = text.replace("\n", " ").replace("\r", "")
        
        return text.strip() if text.strip() else None
    
    def extract_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        
        date_str = self.clean_text(date_str)
        if not date_str:
            return None
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None


class ScraperRegistry:
    """Registry for managing multiple scrapers"""
    
    _scrapers: Dict[str, BaseScraper] = {}
    
    @classmethod
    def register(cls, name: str, scraper_class: type):
        """Register a scraper class"""
        cls._scrapers[name] = scraper_class
        logger.debug(f"Registered scraper: {name}")
    
    @classmethod
    def get_scraper(cls, name: str) -> Optional[BaseScraper]:
        """Get scraper instance by name"""
        scraper_class = cls._scrapers.get(name)
        if scraper_class:
            return scraper_class()
        return None
    
    @classmethod
    def get_all_scrapers(cls) -> Dict[str, BaseScraper]:
        """Get all registered scraper instances"""
        return {
            name: scraper_class() 
            for name, scraper_class in cls._scrapers.items()
        }
    
    @classmethod
    def list_scrapers(cls) -> List[str]:
        """List all registered scraper names"""
        return list(cls._scrapers.keys())
