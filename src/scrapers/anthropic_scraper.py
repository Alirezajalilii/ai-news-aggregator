"""
AI News Aggregator - Anthropic Scraper
Scraper for Anthropic News
"""

import logging
import re
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
        
        # Find all links that point to news articles
        news_links = soup.find_all("a", href=lambda x: x and "/news/" in str(x) and not x.endswith("/news"))
        
        seen_urls = set()
        for link in news_links:
            try:
                href = link.get("href", "")
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                article = self._extract_article_from_link(link, href)
                if article and len(article.title) > 10:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing Anthropic article: {e}")
                continue
        
        return articles
    
    def _extract_article_from_link(self, link, href) -> ArticleData:
        """Extract article data from link element"""
        
        # Title: link text contains "DateCategoryTitle" format - extract just the title
        full_text = self.clean_text(link.get_text())
        
        # Pattern: "Apr 14, 2026AnnouncementsActual Title Here"
        # Date pattern with optional comma after date
        date_pattern = r'^[A-Za-z]+\s+\d{1,2},\s*\d{4}'
        title = re.sub(date_pattern, '', full_text).strip()
        
        # Also remove category if present (Announcements, Research, etc)
        # Categories are: Announcements, Research, Policy, Product
        title = re.sub(r'^(Announcements|Research|Policy|Product)\s*', '', title, flags=re.IGNORECASE).strip()
        
        # URL
        article_url = href
        if not article_url.startswith("http"):
            article_url = f"https://www.anthropic.com{href}"
        
        # Date - try to extract from full text
        published_at = None
        date_match = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})', full_text)
        if date_match:
            date_str = f"{date_match.group(1)} {date_match.group(2)}, {date_match.group(3)}"
            published_at = self.extract_date(date_str)
        
        # Summary - try parent element
        summary = None
        parent = link.parent
        if parent:
            p = parent.find("p")
            if p:
                summary = self.clean_text(p.get_text())
        
        # Image
        img = None
        parent = link.parent
        while parent and parent.name != "article" and parent.name != "main":
            parent = parent.parent
        if parent:
            img_elem = parent.find("img")
            if img_elem:
                img = img_elem.get("src") or img_elem.get("data-src")
        
        return ArticleData(
            title=title or "No title",
            url=article_url or "",
            summary=summary,
            image_url=img,
            published_at=published_at or datetime.utcnow(),
            tags=["AI", "Anthropic", "Claude"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("anthropic", AnthropicScraper)