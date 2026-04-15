"""
AI News Aggregator - TechCrunch Scraper
Scraper for TechCrunch AI section
"""

import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData

logger = logging.getLogger(__name__)


class TechCrunchScraper(BaseScraper):
    """Scraper for TechCrunch AI section"""
    
    name = "techcrunch_ai"
    base_url = "https://techcrunch.com/category/artificial-intelligence/"
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from TechCrunch"""
        articles = []
        
        article_cards = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and "post" in str(x).lower())
        
        for card in article_cards[:20]:
            try:
                article = self._extract_article(card, url)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing TechCrunch article: {e}")
                continue
        
        return articles
    
    def _extract_article(self, card, base_url: str) -> ArticleData:
        """Extract article data from card element"""
        
        title_elem = card.find(["h2", "h3"]) or card.find("a", class_=lambda x: x and "title" in str(x).lower())
        title = self.clean_text(title_elem.get_text()) if title_elem else None
        
        link = card.find("a", href=True)
        article_url = link["href"] if link else None
        
        summary_elem = card.find("p") or card.find("div", class_=lambda x: x and "excerpt" in str(x).lower())
        summary = self.clean_text(summary_elem.get_text()) if summary_elem else None
        
        date_elem = card.find(["time", "span"], class_=lambda x: x and "date" in str(x).lower())
        published_at = None
        if date_elem:
            if date_elem.name == "time":
                published_at = self.extract_date(date_elem.get("datetime"))
            else:
                published_at = self.extract_date(date_elem.get_text())
        
        img_elem = card.find("img")
        image_url = img_elem.get("src") if img_elem else None
        
        return ArticleData(
            title=title or "No title",
            url=article_url or "",
            summary=summary,
            image_url=image_url,
            published_at=published_at or datetime.utcnow(),
            tags=["AI", "TechCrunch", "Business", "Startup"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("techcrunch_ai", TechCrunchScraper)
