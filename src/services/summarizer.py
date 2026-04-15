"""
AI News Aggregator - Summarization Service
Uses LLM to generate proper Persian summaries for articles
"""

import logging
from typing import Optional
import httpx

from src.core.config import get_config

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for generating article summaries using LLM"""
    
    def __init__(self):
        self.config = get_config()
        self.summarization_config = self.config.news.summarization
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for Ollama"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client
    
    async def summarize(self, content: str, article_url: str) -> Optional[str]:
        """
        Generate a summary for the given article content
        
        Args:
            content: Full article text
            article_url: Article URL for context
            
        Returns:
            Generated summary in Persian, or None on failure
        """
        if not self.summarization_config.enabled:
            logger.debug("Summarization disabled, returning original content")
            return content
        
        if not content or len(content) < 100:
            logger.debug(f"Content too short to summarize: {len(content)} chars")
            return content
        
        try:
            # Build prompt from template
            prompt = self.summarization_config.prompt_template.format(
                content=content[:8000],  # Limit input to prevent token overflow
                min_len=self.summarization_config.min_summary_length,
                max_len=self.summarization_config.max_summary_length
            )
            
            # Call Ollama API
            response = await self.client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.summarization_config.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": self.summarization_config.max_summary_length + 200
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return content
            
            result = response.json()
            summary = result.get("response", "").strip()
            
            if summary:
                logger.debug(f"Generated summary: {len(summary)} chars")
                return summary
            else:
                logger.warning("Empty response from Ollama")
                return content
                
        except httpx.ConnectError:
            logger.warning("Cannot connect to Ollama - using original content")
            return content
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return content
    
    async def summarize_batch(self, articles: list) -> list:
        """
        Generate summaries for multiple articles
        
        Args:
            articles: List of (content, url) tuples
            
        Returns:
            List of summaries
        """
        results = []
        for content, url in articles:
            summary = await self.summarize(content, url)
            results.append(summary)
            # Rate limit to avoid overwhelming Ollama
            import asyncio
            await asyncio.sleep(0.5)
        
        return results
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_summarization_service: Optional[SummarizationService] = None


def get_summarization_service() -> SummarizationService:
    """Get singleton summarization service instance"""
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = SummarizationService()
    return _summarization_service