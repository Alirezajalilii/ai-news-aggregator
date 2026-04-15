"""
Tests for EntityExtractor
"""

import pytest
from src.services.entity_extractor import EntityExtractor


class TestEntityExtractor:
    """Test cases for EntityExtractor"""
    
    @pytest.fixture
    def extractor(self):
        return EntityExtractor()
    
    def test_extract_companies(self, extractor):
        """Test company extraction"""
        text = "OpenAI released GPT-5 today. Google also announced Gemini 2.0"
        
        companies = extractor.extract_companies(text)
        
        assert "OpenAI" in companies
        assert "Google" in companies
    
    def test_extract_products(self, extractor):
        """Test product/model extraction"""
        text = "GPT-5 outperforms Claude 3 on benchmarks. Gemini 2.0 is also impressive."
        
        products = extractor.extract_products(text)
        
        assert "GPT-5" in products
        assert "Claude 3" in products
        assert "Gemini 2.0" in products
    
    def test_extract_combined(self, extractor):
        """Test combined entity extraction"""
        text = "Anthropic's Claude 3.5 Sonnet beats GPT-4 on reasoning tasks"
        
        entities = extractor.extract(text)
        
        assert len(entities) >= 2
        assert any(e.type == "company" for e in entities.values())
        assert any(e.type == "product" for e in entities.values())
    
    def test_extract_empty_text(self, extractor):
        """Test extraction from empty text"""
        entities = extractor.extract("")
        assert len(entities) == 0
    
    def test_extract_no_entities(self, extractor):
        """Test extraction when no known entities present"""
        text = "Something happened today in the world."
        entities = extractor.extract(text)
        # Should return empty or minimal entities
        assert len(entities) == 0 or all(e.confidence < 1.0 for e in entities.values())


class TestEntityMatcher:
    """Test cases for EntityMatcher"""
    
    def test_normalize_entity(self):
        """Test entity normalization"""
        from src.services.deduplication import EntityMatcher
        
        assert EntityMatcher.normalize_entity("OpenAI") == "openai"
        assert EntityMatcher.normalize_entity("openai") == "openai"
    
    def test_entities_match(self):
        """Test entity matching with aliases"""
        from src.services.deduplication import EntityMatcher
        
        assert EntityMatcher.entities_match("OpenAI", "openai")
        assert EntityMatcher.entities_match("GPT-4", "GPT-4")
