"""
AI News Aggregator - HuggingFace Scraper
Scraper for Hugging Face Blog
"""

import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData

logger = logging.getLogger(__name__)


class HuggingFaceScraper(BaseScraper):
    """Scraper for Hugging Face Blog"""
    
    name = "huggingface"
    base_url = "https://huggingface.co/blog"
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from HuggingFace blog"""
        articles = []
        
        article_cards = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and "card" in str(x).lower())
        
        for card in article_cards[:20]:
            try:
                article = self._extract_article(card, url)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing HuggingFace article: {e}")
                continue
        
        return articles
    
    def _extract_article(self, card, base_url: str) -> ArticleData:
        """Extract article data from card element"""
        
        title_elem = card.find(["h1", "h2", "h3"]) or card.find("a")
        title = self.clean_text(title_elem.get_text()) if title_elem else None
        
        link = card.find("a", href=True)
        article_url = link["href"] if link else None
        
        if article_url and not article_url.startswith("http"):
            article_url = f"https://huggingface.co{article_url}"
        
        summary_elem = card.find("p")
        summary = self.clean_text(summary_elem.get_text()) if summary_elem else None
        
        # Extract metadata (author, date) from span elements
        meta_spans = card.find_all("span")
        published_at = None
        author = None
        for span in meta_spans:
            text = span.get_text()
            date = self.extract_date(text)
            if date and not published_at:
                published_at = date
            if "ago" in text.lower() or any(month in text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                if not published_at:
                    published_at = self.extract_date(text)
        
        img_elem = card.find("img")
        image_url = img_elem.get("src") if img_elem else None
        
        return ArticleData(
            title=title or "No title",
            url=article_url or "",
            summary=summary,
            image_url=image_url,
            published_at=published_at or datetime.utcnow(),
            tags=["AI", "HuggingFace", "Open Source"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("huggingface", HuggingFaceScraper)
