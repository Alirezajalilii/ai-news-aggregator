"""
AI News Aggregator - Database Module
PostgreSQL database models and connection management
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, BigInteger, DateTime, 
    ForeignKey, Index, create_engine, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from src.core.config import get_config

Base = declarative_base()


# ============== Database Models ==============

class Source(Base):
    """News source model"""
    __tablename__ = "sources"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None, nullable=True)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fetch_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    articles: Mapped[List["Article"]] = relationship("Article", back_populates="source", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Source(name={self.name}, url={self.url})>"


class Article(Base):
    """News article model"""
    __tablename__ = "articles"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Denormalized for easy access
    
    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Categorization
    category: Mapped[str] = mapped_column(String(50), default="general")
    entities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Extracted entities
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Deduplication
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    title_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    similarity_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Publishing info
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Status
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metrics
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="articles")
    sent_messages: Mapped[List["SentMessage"]] = relationship("SentMessage", back_populates="article", cascade="all, delete-orphan")
    similar_articles: Mapped[List["Article"]] = relationship(
        "Article",
        primaryjoin="Article.id == Article.duplicate_of_id",
        remote_side=[id],
        backref="duplicates"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_articles_source_published", "source_id", "published_at"),
        Index("ix_articles_category_published", "category", "published_at"),
        Index("ix_articles_scraped_at", "scraped_at"),
        UniqueConstraint("source_id", "content_hash", name="uq_article_source_hash"),
    )
    
    def __repr__(self):
        return f"<Article(title={self.title[:50]}..., source={self.source.name})>"


class SentMessage(Base):
    """Record of sent messages for tracking"""
    __tablename__ = "sent_messages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    
    # Channel info
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)  # telegram_channel, telegram_dm, etc.
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Channel ID or user ID
    
    # Message info
    message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Status
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    article: Mapped["Article"] = relationship("Article", back_populates="sent_messages")
    
    def __repr__(self):
        return f"<SentMessage(article={self.article_id}, channel={self.channel_type})>"


class Subscription(Base):
    """User/channel subscription to news digests"""
    __tablename__ = "subscriptions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Subscriber info
    subscriber_type: Mapped[str] = mapped_column(String(50), nullable=False)  # telegram_user, telegram_channel
    subscriber_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Subscription preferences
    categories: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)  # Empty = all
    frequency: Mapped[str] = mapped_column(String(50), default="immediate")  # immediate, hourly, daily
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None, nullable=True)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Stats
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    
    __table_args__ = (
        UniqueConstraint("subscriber_type", "subscriber_id", name="uq_subscription"),
    )
    
    def __repr__(self):
        return f"<Subscription(type={self.subscriber_type}, id={self.subscriber_id})>"


class User(Base):
    """Bot users"""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Preferences
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tehran")
    parse_mode: Mapped[str] = mapped_column(String(20), default="HTML")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class SimilarityCache(Base):
    """Cache for article similarity calculations"""
    __tablename__ = "similarity_cache"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Article pair
    article1_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    article2_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    
    # Similarity scores
    title_similarity: Mapped[float] = mapped_column(nullable=False)
    entity_similarity: Mapped[float] = mapped_column(nullable=False)
    content_similarity: Mapped[float] = mapped_column(nullable=False)
    overall_similarity: Mapped[float] = mapped_column(nullable=False)
    
    # Metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    __table_args__ = (
        UniqueConstraint("article1_id", "article2_id", name="uq_similarity_pair"),
        Index("ix_similarity_expires", "expires_at"),
    )
    
    def __repr__(self):
        return f"<SimilarityCache(articles={self.article1_id},{self.article2_id}, sim={self.overall_similarity:.2f})>"


# ============== Database Engine ==============

def get_database_url() -> str:
    """Get async database URL"""
    config = get_config()
    return f"postgresql+asyncpg://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.name}"


def get_sync_database_url() -> str:
    """Get sync database URL for migrations"""
    config = get_config()
    return f"postgresql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.name}"


# Async engine and session
_async_engine = None
_async_session_factory = None


async def get_async_engine():
    """Get or create async database engine"""
    global _async_engine
    
    if _async_engine is None:
        config = get_config()
        _async_engine = create_async_engine(
            get_database_url(),
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            echo=config.database.echo,
        )
    
    return _async_engine


async def get_async_session() -> AsyncSession:
    """Get async database session"""
    global _async_session_factory
    
    if _async_session_factory is None:
        engine = await get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    return _async_session_factory()


async def init_db():
    """Initialize database tables"""
    engine = await get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    global _async_engine, _async_session_factory
    
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
