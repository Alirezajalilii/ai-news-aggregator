"""
AI News Aggregator - Deduplication Service
Handles article deduplication using multiple similarity strategies
"""

import hashlib
import logging
from typing import List, Tuple, Optional, Set
from datetime import datetime, timedelta
import re

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Article, SimilarityCache
from src.core.config import get_config

logger = logging.getLogger(__name__)


class SimilarityCalculator:
    """
    Calculates similarity between articles using multiple strategies:
    1. Title similarity (Jaccard / TF-IDF)
    2. Entity overlap
    3. Content similarity (if available)
    """
    
    def __init__(self):
        self.config = get_config()
        self.dedup_config = self.config.news.deduplication
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate title similarity using Jaccard index on words
        Returns value between 0.0 and 1.0
        """
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles
        title1 = self._normalize_text(title1)
        title2 = self._normalize_text(title2)
        
        # Tokenize
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        # Remove common stopwords
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "for", "on", "with", "and", "or", "as", "at", "by", "from", "new", "ai"}
        words1 = words1 - stopwords
        words2 = words2 - stopwords
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def calculate_entity_similarity(self, entities1: List[str], entities2: List[str]) -> float:
        """
        Calculate entity overlap similarity
        Returns value between 0.0 and 1.0
        """
        if not entities1 or not entities2:
            return 0.0
        
        set1 = set(e.lower() for e in entities1)
        set2 = set(e.lower() for e in entities2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = set1 & set2
        union = set1 | set2
        
        return len(intersection) / len(union) if union else 0.0
    
    def calculate_content_similarity(self, content1: Optional[str], content2: Optional[str]) -> float:
        """
        Calculate content similarity using simple word overlap
        Returns value between 0.0 and 1.0
        """
        if not content1 or not content2:
            return 0.0
        
        # Normalize
        text1 = self._normalize_text(content1)
        text2 = self._normalize_text(content2)
        
        # Simple ratio of common words
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        min_len = min(len(words1), len(words2))
        
        return len(intersection) / min_len if min_len else 0.0
    
    def calculate_overall_similarity(
        self,
        title1: str,
        title2: str,
        entities1: List[str],
        entities2: List[str],
        content1: Optional[str] = None,
        content2: Optional[str] = None
    ) -> Tuple[float, dict]:
        """
        Calculate weighted overall similarity
        
        Returns:
            Tuple of (similarity_score, breakdown_dict)
        """
        title_sim = self.calculate_title_similarity(title1, title2)
        entity_sim = self.calculate_entity_similarity(entities1, entities2)
        content_sim = self.calculate_content_similarity(content1, content2)
        
        # Weighted average
        weights = self.dedup_config
        overall = (
            title_sim * weights.title_similarity_weight +
            entity_sim * weights.entity_similarity_weight +
            content_sim * weights.content_similarity_weight
        )
        
        breakdown = {
            "title_similarity": title_sim,
            "entity_similarity": entity_sim,
            "content_similarity": content_sim,
            "overall": overall
        }
        
        return overall, breakdown
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison"""
        # Lowercase
        text = text.lower()
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text


class DeduplicationService:
    """
    Service for detecting and handling duplicate articles
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.config = get_config()
        self.dedup_config = self.config.news.deduplication
        self.calculator = SimilarityCalculator()
    
    async def is_duplicate(
        self,
        title: str,
        url: str,
        entities: List[str],
        content: Optional[str] = None
    ) -> Tuple[bool, Optional[Article], dict]:
        """
        Check if an article is a duplicate of an existing one
        
        Returns:
            Tuple of (is_duplicate, original_article, similarity_breakdown)
        """
        if not self.dedup_config.enabled:
            return False, None, {}
        
        # First, check by exact hash
        content_hash = self._generate_hash(title, url, content)
        existing = await self._find_by_hash(content_hash)
        if existing:
            return True, existing, {"method": "exact_hash"}
        
        # Get recent articles to compare (last 48 hours by default)
        max_age = datetime.utcnow() - timedelta(hours=self.dedup_config.max_age_hours)
        
        # Get articles from last N hours
        query = (
            select(Article)
            .where(
                and_(
                    Article.scraped_at >= max_age,
                    Article.is_duplicate == False
                )
            )
            .order_by(Article.scraped_at.desc())
            .limit(100)  # Limit for performance
        )
        
        result = await self.session.execute(query)
        recent_articles = result.scalars().all()
        
        if not recent_articles:
            return False, None, {}
        
        # Calculate similarity with recent articles
        best_match = None
        best_similarity = 0.0
        best_breakdown = {}
        
        for article in recent_articles:
            article_entities = article.entities or []
            
            similarity, breakdown = self.calculator.calculate_overall_similarity(
                title, article.title,
                entities, article_entities,
                content, article.content
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = article
                best_breakdown = breakdown
        
        # Check if similarity exceeds threshold
        threshold = self.dedup_config.similarity_threshold
        is_dup = best_similarity >= threshold
        
        if is_dup and best_match:
            best_breakdown["threshold"] = threshold
            best_breakdown["match"] = True
        
        return is_dup, best_match, best_breakdown
    
    async def mark_as_duplicate(self, article: Article, original: Article) -> None:
        """Mark an article as a duplicate of another"""
        article.is_duplicate = True
        article.duplicate_of_id = original.id
        
        # Copy similarity hash from original if available
        if original.similarity_hash:
            article.similarity_hash = original.similarity_hash
        
        await self.session.commit()
        logger.info(f"Marked article '{article.title[:50]}...' as duplicate of '{original.title[:50]}...'")
    
    async def _find_by_hash(self, content_hash: str) -> Optional[Article]:
        """Find article by content hash"""
        query = select(Article).where(Article.content_hash == content_hash)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    def _generate_hash(title: str, url: str, content: Optional[str] = None) -> str:
        """Generate content hash for deduplication"""
        text = f"{title}|{url}|{content or ''}"
        return hashlib.sha256(text.encode()).hexdigest()


class EntityMatcher:
    """
    Matches entities between articles to detect duplicates
    Uses fuzzy matching and alias resolution
    """
    
    # Common aliases
    ALIASES = {
        "openai": ["OpenAI", "Open AI"],
        "anthropic": ["Anthropic"],
        "google": ["Google", "Alphabet", "GOOGL"],
        "microsoft": ["Microsoft", "MSFT", "MS"],
        "meta": ["Meta", "Facebook", "FB"],
        "nvidia": ["NVIDIA", "NVDA"],
        "gpt": ["GPT", "GPT-4", "GPT-5"],
        "claude": ["Claude", "Claude AI"],
        "gemini": ["Gemini", "Google Gemini", "Bard"],
    }
    
    @classmethod
    def normalize_entity(cls, entity: str) -> str:
        """Normalize entity name using aliases"""
        entity_lower = entity.lower()
        
        # Check if it's an alias
        for canonical, aliases in cls.ALIASES.items():
            if entity_lower in [a.lower() for a in aliases]:
                return canonical
        
        return entity_lower
    
    @classmethod
    def entities_match(cls, entity1: str, entity2: str) -> bool:
        """Check if two entities match (considering aliases)"""
        norm1 = cls.normalize_entity(entity1)
        norm2 = cls.normalize_entity(entity2)
        return norm1 == norm2
