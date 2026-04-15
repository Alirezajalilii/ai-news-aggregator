"""
AI News Aggregator - Unite.AI Scraper
Scraper for Unite.AI
"""

import logging
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ArticleData

logger = logging.getLogger(__name__)


class UniteAIScraper(BaseScraper):
    """Scraper for Unite.AI"""
    
    name = "unite_ai"
    base_url = "https://www.unite.ai/"
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from Unite.AI"""
        articles = []
        
        # Find all links pointing to article pages
        all_links = soup.find_all("a", href=lambda x: x and "unite.ai" in str(x))
        
        seen_urls = set()
        for link in all_links:
            try:
                href = link.get("href", "")
                
                # Skip non-article URLs
                if any(skip in href for skip in ["/wp-", "/author/", "/category/", "/tag/", "/page/",
                                                   "/ar/", "/fr/", "/es/", "/de/", "/ja/", "/ko/",
                                                   "/pt/", "/tr/", "/ru/", "/uk/", "/zh-", "/da/",
                                                   "/no/", "/he/", "/cs/", "/el/", "/hi/", "/it/",
                                                   "/id/", "/vi/", "/pl/", "/nl/", "/th/", "/ro/",
                                                   "/sv/", "/fi/", "favicon", "comment", "login"]):
                    continue
                
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                text = link.get_text(strip=True)
                # Skip short texts (nav items) - article titles usually have more content
                if len(text.split()) < 5:
                    continue
                
                article = self._extract_article_from_link(link, href, text)
                if article and len(article.title) > 15:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing Unite.AI article: {e}")
                continue
        
        return articles
    
    def _extract_article_from_link(self, link, href, link_text) -> ArticleData:
        """Extract article data from link element"""
        
        # Clean title - remove date and author prefixes like "ReportsApril 15, 2026By Alex"
        title = link_text
        
        # Remove date patterns: "April 15, 2026" or "Apr 15, 2026"
        title = re.sub(r'[A-Za-z]+\s+\d{1,2},\s*\d{4}', '', title)
        
        # Remove author patterns: "By Alex McFarland" or "By Alex"
        title = re.sub(r'By\s+[A-Za-z]+\s+[A-Za-z]+', '', title)
        
        # Clean up extra whitespace
        title = ' '.join(title.split())
        title = self.clean_text(title)
        
        # Extract date if present
        published_at = None
        date_match = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})', link_text)
        if date_match:
            date_str = f"{date_match.group(1)} {date_match.group(2)}, {date_match.group(3)}"
            published_at = self.extract_date(date_str)
        
        # URL
        article_url = href
        
        # Summary - try to get from parent element
        summary = None
        parent = link.parent
        if parent:
            excerpt = parent.find(class_=lambda x: x and "excerpt" in str(x).lower())
            if excerpt:
                summary = self.clean_text(excerpt.get_text())
        
        # Image
        img = None
        parent = link.parent
        while parent and parent.name not in ["li", "div", "article", "section", "main"]:
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
            tags=["AI", "Unite.AI", "News"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("unite_ai", UniteAIScraper)