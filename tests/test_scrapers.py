"""
Tests for Scraper modules
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.scrapers.base import BaseScraper, ArticleData, ScraperResult


class TestArticleData:
    """Test cases for ArticleData"""
    
    def test_generate_hash(self):
        """Test hash generation"""
        article = ArticleData(
            title="Test Article",
            url="https://example.com/article",
            summary="Test summary"
        )
        
        hash1 = article.generate_hash()
        hash2 = article.generate_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
    
    def test_generate_title_hash(self):
        """Test title hash generation"""
        article = ArticleData(
            title="Test Article Title",
            url="https://example.com"
        )
        
        hash1 = article.generate_title_hash()
        hash2 = article.generate_title_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64


class TestScraperResult:
    """Test cases for ScraperResult"""
    
    def test_article_count(self):
        """Test article count property"""
        result = ScraperResult(
            source_name="test",
            success=True,
            articles=[
                ArticleData(title="Article 1", url="https://example.com/1"),
                ArticleData(title="Article 2", url="https://example.com/2"),
            ]
        )
        
        assert result.article_count == 2
    
    def test_empty_result(self):
        """Test empty result"""
        result = ScraperResult(source_name="test", success=True)
        
        assert result.article_count == 0
        assert result.success is True


class TestScraperRegistry:
    """Test cases for ScraperRegistry"""
    
    def test_register_and_get(self):
        """Test scraper registration"""
        from src.scrapers.base import ScraperRegistry
        
        class TestScraper(BaseScraper):
            name = "test_scraper"
            base_url = "https://test.com"
            
            async def parse_articles(self, soup, url):
                return []
        
        ScraperRegistry.register("test_scraper", TestScraper)
        
        scraper = ScraperRegistry.get_scraper("test_scraper")
        assert scraper is not None
        assert scraper.name == "test_scraper"
    
    def test_get_nonexistent(self):
        """Test getting non-existent scraper"""
        from src.scrapers.base import ScraperRegistry
        
        scraper = ScraperRegistry.get_scraper("nonexistent")
        assert scraper is None
    
    def test_list_scrapers(self):
        """Test listing scrapers"""
        from src.scrapers.base import ScraperRegistry
        
        scrapers = ScraperRegistry.list_srapers()
        assert isinstance(scrapers, list)
