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
    
    # URLs to skip - category pages, not articles
    _SKIP_URL_PATTERNS = [
        "/category/",
        "/tag/",
        "/page/",
        "/author/",
        "/video/",
    ]
    
    async def parse_articles(self, soup: BeautifulSoup, url: str) -> List[ArticleData]:
        """Parse articles from TechCrunch"""
        articles = []
        seen_urls = set()
        
        # Find all article links on the page
        all_links = soup.find_all("a", href=True)
        
        for link in all_links:
            try:
                href = link.get("href", "")
                
                # Skip non-article URLs
                if not href or len(href) < 20:
                    continue
                
                # Skip category, tag, and other non-article pages
                skip = False
                for pattern in self._SKIP_URL_PATTERNS:
                    if pattern in href:
                        skip = True
                        break
                if skip:
                    continue
                
                # Only accept URLs that look like TechCrunch articles
                # Article URLs: https://techcrunch.com/2026/04/15/...
                # Not category pages or feeds
                if not href.startswith("https://techcrunch.com/20"):
                    continue
                
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                # Get title from link text
                title_text = link.get_text(strip=True)
                if len(title_text) < 15:
                    continue
                
                article = self._extract_article_from_link(link, href, title_text)
                if article and len(article.title) > 10:
                    articles.append(article)
                    
            except Exception as e:
                logger.debug(f"Error parsing TechCrunch article: {e}")
                continue
        
        # Deduplicate by URL and limit
        seen = set()
        unique_articles = []
        for a in articles:
            if a.url not in seen:
                seen.add(a.url)
                unique_articles.append(a)
        
        return unique_articles[:20]
    
    def _extract_article_from_link(self, link, href: str, title_text: str) -> ArticleData:
        """Extract article data from a link element"""
        
        # Clean title
        title = self.clean_text(title_text)
        
        # URL is already validated
        article_url = href
        
        # Try to get summary from nearby paragraph
        summary = None
        parent = link.parent
        if parent:
            p = parent.find("p") or parent.find_next_sibling("p")
            if p:
                summary_text = self.clean_text(p.get_text())
                if len(summary_text) > 30:
                    summary = summary_text
        
        # Try to get date from URL (format: /2026/04/15/...)
        published_at = None
        import re
        date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', article_url)
        if date_match:
            try:
                published_at = datetime(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            except ValueError:
                pass
        
        # Try to find image
        image_url = None
        # Look in parent/grandparent for image
        for ancestor in [link.parent, link.parent.parent if link.parent else None]:
            if ancestor:
                img = ancestor.find("img")
                if img:
                    image_url = img.get("src") or img.get("data-src")
                    break
        
        return ArticleData(
            title=title or "No title",
            url=article_url,
            summary=summary,
            image_url=image_url,
            published_at=published_at or datetime.utcnow(),
            tags=["AI", "TechCrunch", "Business", "Startup"]
        )


from src.scrapers.base import ScraperRegistry
ScraperRegistry.register("techcrunch_ai", TechCrunchScraper)