# Telegram Bot Configuration

## Bot Details
- **Bot Name**: `@Ainews_rbot`
- **Bot Token**: `7856786987:AAF6ikQ_C_VXDYO78CKW6V_X-US-PKS7w3U`
- **Channel**: `@ainews_ramzbank`
- **Admin User**: `6492129439` (Alireza Jalili / @aj_ramzbank)

## Message Format

### Photo Message (with image)
```
📰 <b>Article Title</b>

Article summary text (max 500 chars)...

📌 منبع: Source Name
⏰ 2026-04-15 14:45
🔗 <a href="https://example.com">لینک خبر</a>
```
- Caption limited to 1024 characters (Telegram limit)
- **Summary Length**: 400-900 characters (truncated at sentence boundary)
- **Scraper**: Fetches full article content - no limit on input
- **Truncation**: Happens at Telegram formatting stage only

### Text Message (no valid image)
Same format but sent via `sendMessage` instead of `sendPhoto`

## Rate Limiting
- **Delay**: 3 seconds between messages
- **Reason**: Telegram allows ~20 messages/minute to channels
- **Implementation**: `asyncio.sleep(3.0)` after each send

## Subscription Setup
```python
type: "telegram_channel"
channel_id: "@ainews_ramzbank"
categories: ["company", "research", "news", "community", "general", "business"]
```

## is_sent Flag
- Articles marked `is_sent = True` **only** after Telegram API returns `{"ok": true}`
- Prevents duplicate sends on retry
- `sent_messages` table tracks delivery confirmation

## Troubleshooting
- **400 Bad Request**: Image URL invalid or Telegram API issue
- **403 Forbidden**: Bot not admin in channel
- **429 Too Many Requests**: Rate limit exceeded
- **Photo fails → Text**: Automatic fallback for relative URLs