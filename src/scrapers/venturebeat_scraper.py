"""
AI News Aggregator - VentureBeat Scraper
Scraper for VentureBeat AI section
"""

import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData

logger = logging.getLogger(__name__)


class VentureBeatScraper(BaseScraper):
    """Scraper for VentureBeat AI section"""
    
    name = "venturebeat_ai"
    base_url = "https://venturebeat.com/category/ai/"
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from VentureBeat"""
        articles = []
        
        article_cards = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and "post" in str(x).lower())
        
        for card in article_cards[:20]:
            try:
                article = self._extract_article(card, url)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing VentureBeat article: {e}")
                continue
        
        return articles
    
    def _extract_article(self, card, base_url: str) -> ArticleData:
        """Extract article data from card element"""
        
        title_elem = card.find(["h2", "h3"]) or card.find("a")
        title = self.clean_text(title_elem.get_text()) if title_elem else None
        
        link = card.find("a", href=True)
        article_url = link["href"] if link else None
        
        if article_url and not article_url.startswith("http"):
            article_url = f"https://venturebeat.com{article_url}"
        
        summary_elem = card.find("p")
        summary = self.clean_text(summary_elem.get_text()) if summary_elem else None
        
        date_elem = card.find(["time", "span"])
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
            tags=["AI", "VentureBeat", "Business"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("venturebeat_ai", VentureBeatScraper)
