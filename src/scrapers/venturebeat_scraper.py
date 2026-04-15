"""
AI News Aggregator - VentureBeat Scraper
Scraper for VentureBeat RSS Feed
"""

import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData

logger = logging.getLogger(__name__)


class VentureBeatScraper(BaseScraper):
    """Scraper for VentureBeat RSS Feed"""
    
    name = "venturebeat_ai"
    base_url = "https://venturebeat.com/feed/"
    
    async def parse_articles(self, content: str | BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from VentureBeat RSS feed"""
        soup = self._html_to_soup(content)
        articles = []
        
        # Find all item elements in RSS
        items = soup.find_all("item")
        
        for item in items[:20]:  # Limit to 20 most recent
            try:
                article = self._extract_article(item)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing VentureBeat RSS item: {e}")
                continue
        
        return articles
    
    def _extract_article(self, item) -> ArticleData:
        """Extract article data from RSS item element"""
        
        # Title
        title_elem = item.find("title")
        title = self.clean_text(title_elem.get_text()) if title_elem else "No title"
        
        # Remove CDATA wrapper if present
        title_text = title
        if title_text.startswith("<![CDATA[") and title_text.endswith("]]>"):
            title_text = title_text[9:-3]
        
        # Link
        link_elem = item.find("link")
        article_url = ""
        if link_elem:
            article_url = link_elem.get_text()
            if article_url.startswith("<![CDATA[") and article_url.endswith("]]>"):
                article_url = article_url[9:-3]
            article_url = article_url.strip()
        
        # Description/Summary - extract from HTML content
        desc_elem = item.find("description")
        summary = ""
        if desc_elem:
            desc_text = desc_elem.get_text()
            if desc_text.startswith("<![CDATA[") and desc_text.endswith("]]>"):
                desc_text = desc_text[9:-3]
            # Clean HTML tags from description
            desc_soup = BeautifulSoup(desc_text, "html.parser")
            summary = self.clean_text(desc_soup.get_text())
            # Truncate if too long
            if len(summary) > 500:
                summary = summary[:500] + "..."
        
        # Published date
        pubdate_elem = item.find("pubdate")
        published_at = datetime.utcnow()
        if pubdate_elem:
            published_at = self.extract_date(pubdate_elem.get_text()) or datetime.utcnow()
        
        # Category
        cat_elem = item.find("category")
        tags = ["AI", "VentureBeat", "Business"]
        if cat_elem:
            tags.append(self.clean_text(cat_elem.get_text()))
        
        # Author
        author_elem = item.find("author")
        if author_elem:
            tags.append(self.clean_text(author_elem.get_text()))
        
        # Image - try enclosure
        image_url = None
        enclosure = item.find("enclosure")
        if enclosure and enclosure.get("url"):
            image_url = enclosure["url"]
        
        return ArticleData(
            title=title_text,
            url=article_url,
            summary=summary,
            image_url=image_url,
            published_at=published_at,
            tags=tags
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("venturebeat_ai", VentureBeatScraper)