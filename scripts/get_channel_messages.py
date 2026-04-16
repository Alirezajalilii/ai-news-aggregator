#!/usr/bin/env python3
"""
Fetch recent messages from Telegram channel
Usage: python scripts/get_channel_messages.py [--limit N]
"""

import argparse
import asyncio
import httpx
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import get_config


async def get_channel_messages(limit: int = 20):
    """Fetch recent messages from the configured channel"""
    config = get_config()
    bot_token = config.telegram.bot_token
    channel = config.telegram.channels[0] if config.telegram.channels else "@ainews_ramzbank"
    
    base_url = f"https://api.telegram.org/bot{bot_token}"
    
    # Get chat ID for the channel
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, get chat info
        chat_id = channel
        if channel.startswith("@"):
            # For channels with username, we need to use getChat
            try:
                resp = await client.get(f"{base_url}/getChat", params={"chat_id": channel})
                resp.raise_for_status()
                chat_info = resp.json()
                if chat_info.get("ok"):
                    print(f"📢 Channel: {chat_info['result'].get('title', channel)}")
                    print(f"   Type: {chat_info['result'].get('type', 'unknown')}")
                    print()
            except Exception as e:
                print(f"⚠️ Could not get chat info: {e}")
        
        # Get recent messages using getUpdates
        # We need to get updates and filter for the channel
        resp = await client.get(f"{base_url}/getUpdates", params={"limit": 100, "timeout": 0})
        resp.raise_for_status()
        updates = resp.json()
        
        if not updates.get("ok"):
            print(f"❌ Error: {updates}")
            return
        
        messages = updates.get("result", [])
        
        # Filter messages from our channel
        channel_messages = []
        for update in messages:
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            
            # Check if it's from our channel
            if chat.get("username", "").lstrip("@") == channel.lstrip("@"):
                channel_messages.append({
                    "message_id": msg.get("message_id"),
                    "date": datetime.fromtimestamp(msg.get("date", 0)),
                    "text": msg.get("text", "") or msg.get("caption", ""),
                    "has_media": bool(msg.get("photo") or msg.get("document")),
                })
        
        # Sort by message_id descending and take last N
        channel_messages.sort(key=lambda x: x["message_id"], reverse=True)
        recent = channel_messages[:limit]
        
        print(f"📋 Last {len(recent)} messages from {channel}:\n")
        print("-" * 80)
        
        for i, msg in enumerate(recent):
            date_str = msg["date"].strftime("%Y-%m-%d %H:%M")
            text_preview = (msg["text"][:100] + "...") if len(msg["text"]) > 100 else msg["text"]
            media_indicator = "📷" if msg["has_media"] else "💬"
            
            print(f"[{i+1}] {media_indicator} ID:{msg['message_id']} | {date_str}")
            print(f"    {text_preview}")
            print()
        
        print("-" * 80)
        
        # Analyze for duplicates
        print("\n🔍 Duplicate Analysis:\n")
        
        titles = []
        for msg in recent:
            if msg["text"]:
                # Extract title from HTML (between <b> tags)
                import re
                title_match = re.search(r'<b>(.*?)</b>', msg["text"])
                if title_match:
                    titles.append(title_match.group(1))
        
        # Find potential duplicates
        from difflib import SequenceMatcher
        
        duplicates_found = []
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                ratio = SequenceMatcher(None, titles[i], titles[j]).ratio()
                if ratio > 0.7:  # 70% similarity
                    duplicates_found.append({
                        "msg1_index": len(recent) - 1 - i,
                        "msg2_index": len(recent) - 1 - j,
                        "title1": titles[i],
                        "title2": titles[j],
                        "similarity": ratio
                    })
        
        if duplicates_found:
            print(f"⚠️ Found {len(duplicates_found)} potential duplicate pairs:\n")
            for dup in duplicates_found:
                print(f"  📌 Similarity: {dup['similarity']:.0%}")
                print(f"     Msg #{dup['msg1_index']+1}: {dup['title1']}")
                print(f"     Msg #{dup['msg2_index']+1}: {dup['title2']}")
                print()
        else:
            print("✅ No obvious duplicates found in recent messages")


def main():
    parser = argparse.ArgumentParser(description="Fetch recent Telegram channel messages")
    parser.add_argument("--limit", type=int, default=20, help="Number of messages to fetch")
    args = parser.parse_args()
    
    asyncio.run(get_channel_messages(args.limit))


if __name__ == "__main__":
    main()
