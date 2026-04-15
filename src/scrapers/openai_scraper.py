"""
AI News Aggregator - OpenAI Scraper
Scraper for OpenAI Blog
"""

import asyncio
import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData, ScraperResult

logger = logging.getLogger(__name__)


class OpenAIScraper(BaseScraper):
    """Scraper for OpenAI Blog"""
    
    name = "openai"
    base_url = "https://openai.com/blog"
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from OpenAI blog page"""
        articles = []
        
        # Find article cards
        article_cards = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and "card" in x.lower())
        
        for card in article_cards[:15]:  # Limit to 15 most recent
            try:
                article = self._extract_article(card, url)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing OpenAI article card: {e}")
                continue
        
        return articles
    
    def _extract_article(self, card, base_url: str) -> ArticleData:
        """Extract article data from card element"""
        
        # Try different selectors for title
        title_elem = (
            card.find("h1") or 
            card.find("h2") or 
            card.find("h3") or
            card.find("a", class_=lambda x: x and "title" in x.lower())
        )
        
        title = self.clean_text(title_elem.get_text()) if title_elem else None
        
        # Extract URL
        link = card.find("a", href=True)
        article_url = link["href"] if link else None
        
        if article_url and not article_url.startswith("http"):
            article_url = f"https://openai.com{article_url}"
        
        # Extract summary/description
        summary_elem = card.find("p") or card.find("div", class_=lambda x: x and "desc" in x.lower())
        summary = self.clean_text(summary_elem.get_text()) if summary_elem else None
        
        # Extract date
        date_elem = card.find(["time", "span", "div"], class_=lambda x: x and "date" in x.lower())
        published_at = self.extract_date(date_elem.get("datetime") if date_elem and date_elem.name == "time" else date_elem.get_text() if date_elem else None)
        
        # Extract image
        img_elem = card.find("img")
        image_url = img_elem["src"] if img_elem and img_elem.get("src") else None
        
        return ArticleData(
            title=title or "No title",
            url=article_url or "",
            summary=summary,
            image_url=image_url,
            published_at=published_at or datetime.utcnow(),
            tags=["AI", "OpenAI", "GPT"]
        )


# Register scraper
from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("openai", OpenAIScraper)
