"""
Tests for DeduplicationService
"""

import pytest
from src.services.deduplication import SimilarityCalculator


class TestSimilarityCalculator:
    """Test cases for SimilarityCalculator"""
    
    @pytest.fixture
    def calculator(self):
        return SimilarityCalculator()
    
    def test_title_similarity_identical(self, calculator):
        """Test similarity of identical titles"""
        title1 = "OpenAI releases GPT-5"
        title2 = "OpenAI releases GPT-5"
        
        similarity = calculator.calculate_title_similarity(title1, title2)
        
        assert similarity == 1.0
    
    def test_title_similarity_similar(self, calculator):
        """Test similarity of similar titles"""
        title1 = "OpenAI releases GPT-5 today"
        title2 = "OpenAI releases GPT-5 tomorrow"
        
        similarity = calculator.calculate_title_similarity(title1, title2)
        
        assert 0.5 < similarity < 1.0
    
    def test_title_similarity_different(self, calculator):
        """Test similarity of different titles"""
        title1 = "OpenAI releases GPT-5"
        title2 = "Google announces Gemini 2"
        
        similarity = calculator.calculate_title_similarity(title1, title2)
        
        assert similarity < 0.5
    
    def test_title_similarity_empty(self, calculator):
        """Test similarity with empty title"""
        similarity = calculator.calculate_title_similarity("", "OpenAI releases GPT-5")
        assert similarity == 0.0
    
    def test_entity_similarity_complete_overlap(self, calculator):
        """Test entity similarity with complete overlap"""
        entities1 = ["OpenAI", "GPT-5", "AI"]
        entities2 = ["OpenAI", "GPT-5", "AI"]
        
        similarity = calculator.calculate_entity_similarity(entities1, entities2)
        
        assert similarity == 1.0
    
    def test_entity_similarity_partial_overlap(self, calculator):
        """Test entity similarity with partial overlap"""
        entities1 = ["OpenAI", "GPT-5", "AI"]
        entities2 = ["OpenAI", "Claude", "AI"]
        
        similarity = calculator.calculate_entity_similarity(entities1, entities2)
        
        assert 0.3 < similarity < 0.7
    
    def test_entity_similarity_no_overlap(self, calculator):
        """Test entity similarity with no overlap"""
        entities1 = ["OpenAI", "GPT-5"]
        entities2 = ["Google", "Gemini"]
        
        similarity = calculator.calculate_entity_similarity(entities1, entities2)
        
        assert similarity == 0.0
    
    def test_overall_similarity_calculation(self, calculator):
        """Test overall similarity with weights"""
        title1 = "OpenAI releases GPT-5"
        title2 = "OpenAI releases GPT-5 today"
        entities1 = ["OpenAI", "GPT-5"]
        entities2 = ["OpenAI", "GPT-5"]
        
        overall, breakdown = calculator.calculate_overall_similarity(
            title1, title2, entities1, entities2
        )
        
        assert "title_similarity" in breakdown
        assert "entity_similarity" in breakdown
        assert "overall" in breakdown
        assert 0.0 <= overall <= 1.0
    
    def test_normalize_text(self, calculator):
        """Test text normalization"""
        text = "  OpenAI  releases GPT-5!!!  "
        normalized = calculator._normalize_text(text)
        
        assert normalized == "openai releases gpt-5"
