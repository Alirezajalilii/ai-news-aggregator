"""
AI News Aggregator - Fetch Strategies
Each strategy is self-contained and handles its own HTTP/browser logic.
"""

import asyncio
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FetchStrategy(ABC):
    """Base class for fetch strategies"""
    
    name: str = "base"
    
    @abstractmethod
    async def fetch(self, url: str) -> Optional[str]:
        """Fetch content, return HTML text or None"""
        pass


class HttpxStrategy(FetchStrategy):
    """Simple HTTP fetch using httpx"""
    
    name = "httpx"
    
    def __init__(self, timeout: int = 30, user_agent: str = "AI-News-Aggregator/1.0"):
        self.timeout = timeout
        self.user_agent = user_agent
    
    async def fetch(self, url: str) -> Optional[str]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.debug(f"Httpx failed for {url}: {e}")
            return None


class CurlStrategy(FetchStrategy):
    """Fetch using curl command"""
    
    name = "curl"
    
    def __init__(self, timeout: int = 30, user_agent: str = "AI-News-Aggregator/1.0"):
        self.timeout = timeout
        self.user_agent = user_agent
    
    async def fetch(self, url: str) -> Optional[str]:
        cmd = [
            "curl", "-s", "-L",
            "--max-time", str(self.timeout),
            "-A", self.user_agent,
            "-H", "Accept: text/html",
            "--compressed",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 5)
            if result.returncode == 0:
                return result.stdout
            logger.debug(f"Curl failed for {url}: returncode {result.returncode}")
            return None
        except Exception as e:
            logger.debug(f"Curl error for {url}: {e}")
            return None


class OllamaStrategy(FetchStrategy):
    """Use LLM to extract content from blocked/troublesome pages"""
    
    name = "ollama"
    
    def __init__(self, timeout: int = 120, model: str = "minimax-m2.7:cloud", ollama_base_url: str = "http://localhost:11434"):
        self.timeout = timeout
        self.model = model
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def fetch(self, url: str) -> Optional[str]:
        """
        Use LLM to extract article content.
        First tries simple fetch, then uses LLM if blocked.
        """
        # Try simple fetch first
        simple = HttpxStrategy(timeout=30)
        html = await simple.fetch(url)
        
        if html and len(html) > 1000 and "verify" not in html.lower():
            return html
        
        # Use LLM to extract
        logger.info(f"Using Ollama to extract content from {url}")
        return await self._fetch_with_llm(url)
    
    async def _fetch_with_llm(self, url: str) -> Optional[str]:
        """Extract content using LLM"""
        prompt = f"""You are a web scraping assistant. Your task is to:

1. Go to this URL: {url}
2. Extract the main article information
3. Return in this exact format:

TITLE: [actual article title]
SUMMARY: [2-3 sentence summary of the article]
CONTENT: [full article body text - be thorough, include all important details]

If the page is blocked or inaccessible, return:
TITLE: FAILED
SUMMARY: [brief explanation]
CONTENT: ERROR"""

        try:
            response = await self.client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 6000}
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")
                
                # Parse LLM output into simple HTML for BeautifulSoup
                if "TITLE:" in content:
                    return self._parse_llm_output(content)
                
                return content
            else:
                logger.warning(f"Ollama fetch failed: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Ollama error: {e}")
            return None
    
    def _parse_llm_output(self, content: str) -> str:
        """Convert LLM output to simple HTML"""
        lines = content.split("\n")
        title = ""
        summary = ""
        article_body = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("CONTENT:"):
                current_section = "content"
            elif current_section == "content":
                if line and not line.startswith("TITLE") and not line.startswith("SUMMARY"):
                    article_body.append(line)
        
        article_text = " ".join(article_body)
        
        # Create simple HTML
        html = f"""<html><head><title>{title}</title></head><body>
<article>
<h1>{title}</h1>
<p>{summary}</p>
<div>{article_text}</div>
</article>
</body></html>"""
        
        return html


class PlaywrightStrategy(FetchStrategy):
    """Use Playwright (real browser) for JavaScript-challenged sites"""
    
    name = "playwright"
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self._browser = None
        self._playwright = None
    
    async def fetch(self, url: str) -> Optional[str]:
        """Launch browser and get page content"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed. Install with: pip install playwright && playwright install")
            return None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                
                # Set timeout
                page.set_default_timeout(self.timeout * 1000)
                
                # Navigate
                await page.goto(url, wait_until="networkidle")
                
                # Get content
                content = await page.content()
                
                await browser.close()
                return content
                
        except Exception as e:
            logger.warning(f"Playwright error for {url}: {e}")
            return None


class BraveStrategy(FetchStrategy):
    """Use Brave Search API for news aggregation"""
    
    name = "brave"
    
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def fetch(self, url: str) -> Optional[str]:
        """Use Brave Search to find and fetch article"""
        if not self.api_key:
            # Try environment variable
            import os
            self.api_key = os.getenv("BRAVE_API_KEY")
        
        if not self.api_key:
            logger.warning("Brave API key not configured")
            return None
        
        # Extract topic from URL for search
        topic = url.split("/")[-1].replace("-", " ").replace("_", " ")
        
        try:
            response = await self.client.get(
                "https://api.search.brave.com/res/v1/news/search",
                params={"q": topic, "count": 5},
                headers={"X-Subscription-Token": self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("results", [])
                
                aggregated = []
                for article in articles[:3]:
                    title = article.get("title", "")
                    desc = article.get("description", "")
                    article_url = article.get("url", "")
                    aggregated.append(f"## {title}\n{desc}\nSource: {article_url}")
                
                return "\n\n".join(aggregated) if aggregated else None
            else:
                logger.warning(f"Brave search failed: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Brave error: {e}")
            return None


# Registry of strategies
STRATEGIES = {
    "httpx": HttpxStrategy,
    "curl": CurlStrategy,
    "ollama": OllamaStrategy,
    "playwright": PlaywrightStrategy,
    "brave": BraveStrategy,
}


def get_fetch_strategy(name: str, **kwargs) -> FetchStrategy:
    """Get a fetch strategy by name"""
    strategy_class = STRATEGIES.get(name, HttpxStrategy)
    return strategy_class(**kwargs)