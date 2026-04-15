"""
AI News Aggregator - Database Module
PostgreSQL database connection and session management
"""

from src.database.models import (
    Base,
    Source,
    Article,
    SentMessage,
    Subscription,
    User,
    SimilarityCache,
    init_db,
    close_db,
    get_async_session,
    get_database_url,
    get_sync_database_url,
)

__all__ = [
    "Base",
    "Source",
    "Article",
    "SentMessage",
    "Subscription",
    "User",
    "SimilarityCache",
    "init_db",
    "close_db",
    "get_async_session",
    "get_database_url",
    "get_sync_database_url",
]
