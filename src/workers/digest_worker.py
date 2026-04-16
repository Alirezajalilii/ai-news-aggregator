"""
AI News Aggregator - Digest Worker
Background worker that sends news digests to subscribers
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_config
from src.database.models import Article, Subscription, SentMessage, init_db, get_async_session
from src.telegram.telegram_service import get_telegram_service, TelegramService

logger = logging.getLogger(__name__)


class DigestWorker:
    """
    Worker that sends news digests to subscribed users/channels
    """
    
    def __init__(self):
        self.config = get_config()
        self.telegram: TelegramService = get_telegram_service()
        self._session: Optional[AsyncSession] = None
    
    async def get_session(self) -> AsyncSession:
        """Get or create database session"""
        if self._session is None:
            self._session = await get_async_session()
        return self._session
    
    async def close_session(self):
        """Close database session"""
        if self._session is not None:
            await self._session.close()
            self._session = None
    
    async def run(self, category_filter: Optional[List[str]] = None) -> Dict:
        """
        Run the digest worker
        
        Args:
            category_filter: Only include these categories. None = all.
            
        Returns:
            Dict with digest statistics
        """
        logger.info("Starting digest worker")
        start_time = datetime.utcnow()
        
        stats = {
            "subscribers_notified": 0,
            "messages_sent": 0,
            "articles_included": 0,
            "errors": []
        }
        
        try:
            await init_db()
            session = await self.get_session()
            
            # Get unsent articles from last 24 hours
            articles = await self._get_unsent_articles(session, category_filter)
            
            if not articles:
                logger.info("No new articles to send")
                return stats
            
            stats["articles_included"] = len(articles)
            
            # Get all active subscriptions
            subscriptions = await self._get_active_subscriptions(session)
            
            if not subscriptions:
                logger.info("No active subscriptions")
                return stats
            
            # Send to each subscriber
            for subscription in subscriptions:
                try:
                    messages_sent = await self._send_to_subscriber(
                        subscription, articles, session
                    )
                    stats["messages_sent"] += messages_sent
                    stats["subscribers_notified"] += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error sending to subscriber {subscription.subscriber_id}: {e}")
                    stats["errors"].append({
                        "subscriber": subscription.subscriber_id,
                        "error": str(e)
                    })
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            stats["duration_seconds"] = duration
            
            logger.info(
                f"Digest worker completed in {duration:.2f}s. "
                f"Notified {stats['subscribers_notified']} subscribers, "
                f"sent {stats['messages_sent']} messages"
            )
            
        except Exception as e:
            logger.error(f"Error in digest worker: {e}")
            stats["errors"].append({"general": str(e)})
        
        finally:
            await self.close_session()
            await self.telegram.close()
        
        return stats
    
    async def _get_unsent_articles(
        self,
        session: AsyncSession,
        category_filter: Optional[List[str]] = None
    ) -> List[Article]:
        """Get articles that haven't been sent yet, with valid Persian summaries"""
        # Get articles from last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        query = (
            select(Article)
            .where(
                and_(
                    Article.is_sent == False,
                    Article.is_duplicate == False,
                    Article.scraped_at >= cutoff,
                    # Only send articles that have a summary
                    Article.summary != None,
                    Article.summary != '',
                    # Must have a valid URL
                    Article.url != None,
                    Article.url != ''
                )
            )
            .order_by(Article.published_at.desc())
            .limit(50)
        )
        
        result = await session.execute(query)
        articles = result.scalars().all()
        
        # Filter: only articles with Persian content in summary
        articles = [a for a in articles if self._has_persian(a.summary)]
        
        # Filter by category if specified
        if category_filter:
            articles = [a for a in articles if a.category in category_filter]
        
        return articles
    
    @staticmethod
    def _has_persian(text: str) -> bool:
        """Check if text contains Persian characters"""
        if not text:
            return False
        for char in text:
            if '\u0600' <= char <= '\u06FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
                return True
        return False
    
    async def _get_active_subscriptions(self, session: AsyncSession) -> List[Subscription]:
        """Get all active subscriptions"""
        query = (
            select(Subscription)
            .where(Subscription.enabled == True)
        )
        result = await session.execute(query)
        return result.scalars().all()
    
    async def _send_to_subscriber(
        self,
        subscription: Subscription,
        articles: List[Article],
        session: AsyncSession
    ) -> int:
        """Send digest to a subscriber"""
        # Filter articles by subscription preferences
        if subscription.categories:
            filtered_articles = [
                a for a in articles 
                if a.category in subscription.categories
            ]
        else:
            filtered_articles = articles
        
        if not filtered_articles:
            return 0
        
        # Send digest
        chat_id = subscription.subscriber_id
        
        # Handle different channel types
        if subscription.subscriber_type == "telegram_user":
            responses = await self.telegram.send_digest(filtered_articles, str(chat_id))
        elif subscription.subscriber_type == "telegram_channel":
            responses = await self.telegram.send_digest(filtered_articles, chat_id)
        else:
            responses = await self.telegram.send_digest(filtered_articles, chat_id)
        
        messages_sent = sum(1 for r in responses if r.get("ok"))
        
        # Record sent messages
        # Send each article and track success
        for idx, article in enumerate(filtered_articles):
            sent_msg = SentMessage(
                article_id=article.id,
                channel_type=subscription.subscriber_type,
                channel_id=subscription.subscriber_id,
                message_id=str(responses[idx].get("result", {}).get("message_id")) if responses and idx < len(responses) and responses[idx].get("ok") else None,
                content=f"Digest: {article.title}",
                delivered=responses[idx].get("ok") if responses and idx < len(responses) else False
            )
            session.add(sent_msg)
            
            # Mark article as sent ONLY if delivery was successful
            if responses and idx < len(responses) and responses[idx].get("ok"):
                article.is_sent = True
                article.sent_count += 1
        
        # Update subscription
        subscription.last_sent_at = datetime.utcnow()
        subscription.message_count += messages_sent
        
        await session.commit()
        
        return messages_sent
    
    async def send_instant(
        self,
        article: Article,
        subscriber_id: str,
        subscriber_type: str = "telegram_user"
    ) -> bool:
        """Send single article instantly to a subscriber"""
        try:
            if subscriber_type == "telegram_user":
                await self.telegram.send_article(article, str(subscriber_id))
            else:
                await self.telegram.send_article(article, subscriber_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending instant article: {e}")
            return False
