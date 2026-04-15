"""
AI News Aggregator - Anthropic Scraper
Scraper for Anthropic News
"""

import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData

logger = logging.getLogger(__name__)


class AnthropicScraper(BaseScraper):
    """Scraper for Anthropic News"""
    
    name = "anthropic"
    base_url = "https://www.anthropic.com/news"
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from Anthropic news page"""
        articles = []
        
        # Find article sections
        article_sections = soup.find_all("article") or soup.find_all("section") or soup.find_all("div", class_=lambda x: x and "article" in str(x).lower())
        
        for section in article_sections[:15]:
            try:
                article = self._extract_article(section, url)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing Anthropic article: {e}")
                continue
        
        return articles
    
    def _extract_article(self, section, base_url: str) -> ArticleData:
        """Extract article data from section element"""
        
        # Title
        title_elem = (
            section.find("h1") or 
            section.find("h2") or 
            section.find("h3")
        )
        title = self.clean_text(title_elem.get_text()) if title_elem else None
        
        # URL
        link = section.find("a", href=True)
        article_url = link["href"] if link else None
        
        if article_url and not article_url.startswith("http"):
            article_url = f"https://www.anthropic.com{article_url}"
        
        # Summary
        summary_elem = section.find("p")
        summary = self.clean_text(summary_elem.get_text()) if summary_elem else None
        
        # Date
        date_elem = section.find(["time", "span"], class_=lambda x: x and "date" in str(x).lower())
        published_at = None
        if date_elem:
            if date_elem.name == "time":
                published_at = self.extract_date(date_elem.get("datetime"))
            else:
                published_at = self.extract_date(date_elem.get_text())
        
        # Image
        img_elem = section.find("img")
        image_url = img_elem["src"] if img_elem and img_elem.get("src") else None
        
        return ArticleData(
            title=title or "No title",
            url=article_url or "",
            summary=summary,
            image_url=image_url,
            published_at=published_at or datetime.utcnow(),
            tags=["AI", "Anthropic", "Claude"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("anthropic", AnthropicScraper)
