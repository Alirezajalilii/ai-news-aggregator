"""
AI News Aggregator - OpenAI Scraper
Scraper for OpenAI RSS Feed
"""

import logging
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData, ScraperResult

logger = logging.getLogger(__name__)


class OpenAIScraper(BaseScraper):
    """Scraper for OpenAI RSS Feed"""
    
    name = "openai"
    base_url = "https://openai.com/news/rss.xml"
    
    async def parse_articles(self, content: str | BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from OpenAI RSS feed"""
        soup = self._html_to_soup(content)
        articles = []
        
        # Find all item elements in RSS
        items = soup.find_all("item")
        
        for item in items[:15]:  # Limit to 15 most recent
            try:
                article = self._extract_article(item)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing OpenAI RSS item: {e}")
                continue
        
        return articles
    
    def _extract_article(self, item) -> ArticleData:
        """Extract article data from RSS item element"""
        
        # Title
        title_elem = item.find("title")
        title = self.clean_text(title_elem.get_text()) if title_elem else "No title"
        
        # Link
        link_elem = item.find("link")
        article_url = link_elem.get_text() if link_elem else ""
        
        # Remove CDATA wrapper if present
        if article_url.startswith("<![CDATA[") and article_url.endswith("]]>"):
            article_url = article_url[9:-3]
        
        article_url = article_url.strip()
        
        # Description/Summary
        desc_elem = item.find("description")
        summary = ""
        if desc_elem:
            desc_text = desc_elem.get_text()
            # Remove CDATA if present
            if desc_text.startswith("<![CDATA[") and desc_text.endswith("]]>"):
                desc_text = desc_text[9:-3]
            summary = self.clean_text(desc_text)
        
        # Published date
        pubdate_elem = item.find("pubdate")
        published_at = datetime.utcnow()
        if pubdate_elem:
            published_at = self.extract_date(pubdate_elem.get_text()) or datetime.utcnow()
        
        # Category
        cat_elem = item.find("category")
        tags = ["AI", "OpenAI"]
        if cat_elem:
            tags.append(self.clean_text(cat_elem.get_text()))
        
        # Image - try enclosure or media:content
        image_url = None
        enclosure = item.find("enclosure")
        if enclosure and enclosure.get("url"):
            image_url = enclosure["url"]
        
        return ArticleData(
            title=title,
            url=article_url,
            summary=summary,
            image_url=image_url,
            published_at=published_at,
            tags=tags
        )


# Register scraper
from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("openai", OpenAIScraper)