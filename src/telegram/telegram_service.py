"""
AI News Aggregator - Telegram Service
Handles sending messages to Telegram channels and users
"""

import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from src.core.config import get_config
from src.database.models import Article, SentMessage

logger = logging.getLogger(__name__)


class TelegramFormatter:
    """Formats articles for Telegram HTML rendering"""
    
    @staticmethod
    def format_article(article: Article, config: Dict[str, Any]) -> str:
        """Format single article as HTML message"""
        lines = []
        
        # Category emoji
        category_emoji = config.get("categories", {}).get(article.category, {}).get("emoji", "📰")
        
        # Title
        lines.append(f"{category_emoji} <b>{article.title}</b>")
        lines.append("")
        
        # Summary (natural summary, truncated at sentence boundary between 400-900 chars)
        if article.summary:
            # Clean HTML tags if any
            clean_summary = article.summary.replace("\u200b", "").replace("<br>", "\n").replace("<br/>", "\n")
            clean_summary = re.sub(r'<[^>]+>', '', clean_summary)  # Remove any HTML tags
            # Allow natural summary between 400-900 chars, truncate at sentence boundary
            if len(clean_summary) > 900:
                # Find last sentence boundary before 900 chars
                truncated = clean_summary[:900]
                last_period = max(truncated.rfind('.'), truncated.rfind('؟'), truncated.rfind('!'), truncated.rfind('.'))
                if last_period > 400:
                    clean_summary = truncated[:last_period + 1]
                else:
                    clean_summary = truncated + "..."
            lines.append(clean_summary)
            lines.append("")
        
        # Source and link
        source_name = article.source_name.replace("_", " ").title() if article.source_name else "AI News"
        lines.append(f"📌 منبع: {source_name}")
        
        if config.get("include_timestamp", True) and article.published_at:
            time_str = article.published_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"⏰ {time_str}")
        
        lines.append(f"🔗 <a href=\"{article.url}\">لینک خبر</a>")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_article_forPhoto(article: Article, config: Dict[str, Any]) -> str:
        """Format article caption for photo message"""
        lines = []
        
        # Category emoji
        category_emoji = config.get("categories", {}).get(article.category, {}).get("emoji", "📰")
        
        # Title
        lines.append(f"{category_emoji} <b>{article.title}</b>")
        lines.append("")
        
        # Summary (natural summary between 400-900 chars, truncated at sentence boundary)
        if article.summary:
            clean_summary = article.summary.replace("\u200b", "").replace("<br>", "\n").replace("<br/>", "\n")
            clean_summary = re.sub(r'<[^>]+>', '', clean_summary)
            # Allow natural summary between 400-900 chars, truncate at sentence boundary
            if len(clean_summary) > 900:
                # Find last sentence boundary before 900 chars
                truncated = clean_summary[:900]
                last_period = max(truncated.rfind('.'), truncated.rfind('؟'), truncated.rfind('!'), truncated.rfind('.'))
                if last_period > 400:
                    clean_summary = truncated[:last_period + 1]
                else:
                    clean_summary = truncated + "..."
            lines.append(clean_summary)
            lines.append("")
        # Source and link
        source_name = article.source_name.replace("_", " ").title() if article.source_name else "AI News"
        lines.append("")
        lines.append(f"📌 منبع: {source_name}")
        
        if config.get("include_timestamp", True) and article.published_at:
            time_str = article.published_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"⏰ {time_str}")
        
        lines.append(f"🔗 <a href=\"{article.url}\">لینک خبر</a>")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_digest(articles: List[Article], config: Dict[str, Any]) -> List[str]:
        """
        Format multiple articles as digest messages
        
        Returns list of formatted messages (split by max_articles_per_message)
        """
        messages = []
        max_per_message = config.get("max_articles_per_message", 10)
        
        # Group by category
        by_category: Dict[str, List[Article]] = {}
        for article in articles:
            cat = article.category or "general"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(article)
        
        # Format each category
        for category, cat_articles in by_category.items():
            if not cat_articles:
                continue
            
            category_info = config.get("categories", {}).get(category, {})
            emoji = category_info.get("emoji", "📰")
            name = category_info.get("name", category.title())
            
            header = f"<b>{emoji} {name}</b>"
            header += f"\n━━━━━━━━━━━━━━━━━━━━"
            
            current_batch = [header]
            
            for i, article in enumerate(cat_articles[:max_per_message]):
                article_text = TelegramFormatter.format_article(article, config)
                # Skip the first line (title with emoji) since we have category header
                lines = article_text.split("\n")
                if len(lines) > 1:
                    lines = lines[1:]  # Remove duplicate emoji+title
                article_text = "\n".join(lines)
                
                current_batch.append(article_text)
                
                # If reached max, start new message
                if len(current_batch) >= max_per_message + 1:
                    messages.append("\n\n".join(current_batch))
                    current_batch = [header]
            
            # Add remaining
            if len(current_batch) > 1:
                messages.append("\n\n".join(current_batch))
        
        return messages


class TelegramService:
    """Service for sending messages via Telegram Bot API"""
    
    def __init__(self):
        self.config = get_config()
        self.bot_config = self.config.telegram
        self.bot_token = self.bot_config.bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.parse_mode = self.bot_config.parse_mode
        self.formatter = TelegramFormatter()
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_web_preview: bool = True,
        reply_to_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send message to Telegram chat
        
        Args:
            text: Message text (HTML supported)
            chat_id: Chat ID (user or channel). If None, sends to configured channels
            parse_mode: HTML or Markdown
            disable_web_preview: Disable link previews
            reply_to_message_id: Reply to specific message
            
        Returns:
            API response dict
        """
        if chat_id is None:
            chat_id = self.bot_config.channels[0] if self.bot_config.channels else None
        
        if not chat_id:
            raise ValueError("No chat_id provided and no default channels configured")
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_preview,
        }
        
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        
        try:
            response = await self.client.post(
                f"{self.base_url}/sendMessage",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok"):
                logger.error(f"Telegram API error: {result}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending message: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def send_photo(
        self,
        photo_url: str,
        caption: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML"
    ) -> Dict[str, Any]:
        """
        Send photo with caption to Telegram chat
        
        Args:
            photo_url: URL of the photo
            caption: Photo caption (HTML supported)
            chat_id: Chat ID
            parse_mode: HTML or Markdown
            
        Returns:
            API response dict
        """
        if chat_id is None:
            chat_id = self.bot_config.channels[0] if self.bot_config.channels else None
        
        if not chat_id:
            raise ValueError("No chat_id provided and no default channels configured")
        
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": parse_mode,
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/sendPhoto",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            raise
    
    async def send_article(self, article: Article, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Send single article to chat"""
        format_config = {
            "categories": {
                cat.id: {"emoji": cat.emoji, "name": cat.name}
                for cat in self.config.news.categories
            },
            "include_source": True,
            "include_timestamp": True,
        }
        
        text = self.formatter.format_article(article, format_config)
        return await self.send_message(text, chat_id)
    
    async def send_digest(self, articles: List[Article], chat_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Send news digest to chat - each article as separate message
        
        Args:
            articles: List of articles to send
            chat_id: Target chat ID
            
        Returns:
            List of API responses for each message sent
        """
        format_config = {
            "categories": {
                cat.id: {"emoji": cat.emoji, "name": cat.name}
                for cat in self.config.news.categories
            },
            "include_source": True,
            "include_timestamp": True,
        }
        
        responses = []
        
        for article in articles:
            try:
                # Check if article has valid absolute image URL (not relative path)
                if article.image_url and article.image_url.startswith('http'):
                    caption = self.formatter.format_article_forPhoto(article, format_config)
                    try:
                        response = await self.send_photo(article.image_url, caption, chat_id)
                        if response.get('ok'):
                            responses.append(response)
                            await asyncio.sleep(3.0)
                            continue
                    except Exception as photo_error:
                        logger.debug(f"Photo failed, falling back to text: {photo_error}")
                
                # Send as text message (either no image or photo failed)
                text = self.formatter.format_article(article, format_config)
                response = await self.send_message(text, chat_id)
                responses.append(response)
                
                # Rate limit protection (Telegram: 20 msg/min to channel)
                await asyncio.sleep(3.0)
                
            except Exception as e:
                logger.error(f"Error sending article '{article.title[:30]}...': {e}")
                responses.append({"ok": False, "error": str(e)})
        
        return responses
    
    async def send_to_channel(self, text: str) -> Dict[str, Any]:
        """Send message to configured channel"""
        return await self.send_message(text)
    
    async def send_to_user(self, user_id: int, text: str) -> Dict[str, Any]:
        """Send message to specific user"""
        return await self.send_message(text, str(user_id))
    
    async def get_me(self) -> Dict[str, Any]:
        """Get bot info"""
        response = await self.client.get(f"{self.base_url}/getMe")
        response.raise_for_status()
        return response.json()
    
    async def get_updates(self, offset: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
        """Get bot updates"""
        params = {"limit": limit}
        if offset:
            params["offset"] = offset
        
        response = await self.client.get(f"{self.base_url}/getUpdates", params=params)
        response.raise_for_status()
        return response.json()
    
    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Set webhook for bot updates"""
        response = await self.client.post(
            f"{self.base_url}/setWebhook",
            json={"url": webhook_url}
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_telegram_service: Optional[TelegramService] = None


def get_telegram_service() -> TelegramService:
    """Get singleton Telegram service instance"""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service
