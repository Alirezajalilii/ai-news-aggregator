"""
AI News Aggregator - Services Module
Business logic services
"""

from src.services.entity_extractor import EntityExtractor
from src.services.deduplication import DeduplicationService, SimilarityCalculator, EntityMatcher
from src.services.scheduler import NewsScheduler, get_scheduler

__all__ = [
    "EntityExtractor",
    "DeduplicationService",
    "SimilarityCalculator",
    "EntityMatcher",
    "NewsScheduler",
    "get_scheduler",
]
