"""
AI News Aggregator - Google AI Scraper
Scraper for Google AI Blog
"""

import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData

logger = logging.getLogger(__name__)


class GoogleAIScraper(BaseScraper):
    """Scraper for Google AI Blog"""
    
    name = "google_ai"
    base_url = "https://blog.google/technology/ai/"
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from Google AI blog"""
        articles = []
        seen_urls = set()
        
        # Google AI uses div.card class for news items
        # The actual articles are inside these cards
        cards = soup.find_all("div", class_=lambda x: x and "card" in str(x).lower())
        
        for card in cards[:20]:
            try:
                article = self._extract_article(card, url)
                if article and len(article.title) > 10 and article.url:
                    if article.url in seen_urls:
                        continue
                    seen_urls.add(article.url)
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing Google AI article: {e}")
                continue
        
        return articles
    
    def _extract_article(self, card, base_url: str) -> ArticleData:
        """Extract article data from card element"""
        
        # Title - look for h1, h2, h3 or link with title
        title_elem = (
            card.find("h1") or 
            card.find("h2") or 
            card.find("h3") or
            card.find("a", class_=lambda x: x and "title" in str(x).lower())
        )
        title = self.clean_text(title_elem.get_text()) if title_elem else None
        
        # If no title found, try to get from any link
        if not title:
            link = card.find("a", href=True)
            if link:
                title = self.clean_text(link.get_text())
        
        # URL - find first link with href
        link = card.find("a", href=True)
        article_url = None
        if link:
            article_url = link.get("href")
        
        if article_url and not article_url.startswith("http"):
            article_url = f"https://blog.google{article_url}"
        
        # Summary - look for p tag or text content
        summary_elem = card.find("p")
        if summary_elem:
            summary = self.clean_text(summary_elem.get_text())
        else:
            # Try to get text directly from card
            text = card.get_text(strip=True)
            if text and len(text) > 50:
                summary = text[:300]
            else:
                summary = None
        
        # Date
        date_elem = card.find(["time", "span", "div"], class_=lambda x: x and "date" in str(x).lower())
        published_at = None
        if date_elem:
            if date_elem.name == "time":
                published_at = self.extract_date(date_elem.get("datetime"))
            else:
                published_at = self.extract_date(date_elem.get_text())
        
        # Image
        img_elem = card.find("img")
        image_url = None
        if img_elem:
            image_url = img_elem.get("src") or img_elem.get("data-src")
        
        return ArticleData(
            title=title or "No title",
            url=article_url or "",
            summary=summary,
            image_url=image_url,
            published_at=published_at or datetime.utcnow(),
            tags=["AI", "Google", "Gemini"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("google_ai", GoogleAIScraper)