# AI News Aggregator - System Overview

## Purpose
Automated news aggregation system that scrapes AI news from 11 sources, generates AI-powered Persian summaries, stores in PostgreSQL, and sends digests to Telegram channels.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│   Scrapers  │────▶│  PostgreSQL  │────▶│   Ollama    │────▶│   Telegram  │
│   (11 src)  │     │   (ai_news)  │     │  (summarize)│     │     Bot     │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
       │                                        │
       ▼                                        ▼
┌─────────────┐                         ┌─────────────┐
│  Scheduler  │                         │   Digest    │
│ (APScheduler)│                         │   Worker    │
└─────────────┘                         └─────────────┘
```

## Workflow (Detailed)

```
1. ⏰ Scheduler triggers scraper_worker.run() every 15 minutes
2. 📄 scraper_worker.py:
   a. Gets all enabled sources from config.yaml
   b. Scrape each source in batches (ScraperRegistry)
   c. Each scraper fetches article listing page → extracts (title, summary, url, image)
   d. For each article:
      - Extract entities (EntityExtractor)
      - Check duplicates (DeduplicationService)
      - Fetch FULL article content (fetch_article_content)
      - ⭐ Generate AI summary (SummarizationService → Ollama API)
      - Save to PostgreSQL (Article table)
3. 📤 telegram_service.send_digest():
   a. Load unsent articles from DB
   b. For each article:
      - Format with TelegramFormatter (AI summary already generated)
      - If valid image_url → sendPhoto with caption
      - Else → sendMessage as text
   c. Mark is_sent=True after Telegram confirms
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Scrapers | `scrapers/{name}_scraper.py` | Fetch listing pages, extract article metadata |
| Base Scraper | `scrapers/base.py` | HTTP fetching, content extraction, retry logic |
| Scraper Worker | `workers/scraper_worker.py` | Orchestrates scraping → summarization → DB save |
| Summarizer | `services/summarizer.py` | **NEW** Calls Ollama API for AI-generated summaries |
| Entity Extractor | `services/entity_extractor.py` | Extracts person/company names |
| Deduplication | `services/deduplication.py` | Detects duplicate articles |
| Telegram Formatter | `telegram/telegram_service.py` | Formats messages for Telegram (HTML) |
| Telegram Sender | `telegram/telegram_service.py` | Sends messages via Bot API |

## AI Summarization

**Model**: Configurable in `config.yaml` → `news.summarization.model`  
**Default**: `minimax-m2.7:cloud` (via Ollama at localhost:11434)

**Prompt Template** (Persian):
```
این خبر رو به صورت خلاصه و جذاب برای کانال تلگرام فارسی بنویس.
- طول خلاصه: بین 400 تا 900 کاراکتر
- تمام اطلاعات مهم رو حفظ کنه
- در انتها: "🔗 ادامه خبر در لینک"
```

**Summary Length**: 400-900 characters (configurable)

## Tech Stack
- **Backend**: Python 3.12, asyncio, SQLAlchemy (async)
- **Database**: PostgreSQL (ai_news database)
- **Cache/Queue**: Redis (port 6380)
- **LLM**: Ollama API (localhost:11434)
- **Scheduler**: APScheduler with cron triggers
- **Telegram**: python-telegram-bot library

## Schedule
- **Scrape + Summarize**: Every 15 minutes (`0/15 * * * *`)
- **Digest**: Every 15 minutes (`0/15 * * * *`)
- **Cleanup**: Daily at 3 AM (`0 3 * * *`)

## Configuration
- `config.yaml` - Main configuration file
- `news.summarization` - AI summarization settings (model, length bounds, prompt)
- Database credentials, Telegram bot token, scheduler jobs