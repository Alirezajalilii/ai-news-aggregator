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
1. ⏰ Scheduler triggers fetch_all_sources every 15 minutes (at :05)
2. 🔄 scraper_worker.py runs:
   a. Gets all enabled sources from config.yaml
   b. Scrape each source in batches (concurrent)
   c. Each scraper fetches → parses → returns ArticleData list
   d. For each article:
      - Extract entities (EntityExtractor)
      - Check duplicates (DeduplicationService.is_duplicate)
      - Fetch FULL article content
      - ⭐ Generate AI summary (SummarizationService → Ollama API)
      - Save to PostgreSQL (Article table with content_hash)
3. 📤 digest_worker runs after scraper completes:
   a. Load unsent articles (is_sent=False, is_duplicate=False)
   b. For each article:
      - Format with TelegramFormatter
      - Send to Telegram channel
      - Mark is_sent=True
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Scrapers | `scrapers/{name}_scraper.py` | Fetch listing pages, extract article metadata |
| Fetch Strategies | `scrapers/fetch_strategies.py` | Different HTTP methods (httpx, curl, ollama, playwright, brave) |
| Base Scraper | `scrapers/base.py` | HTTP fetching, content extraction, retry logic |
| ArticleData | `scrapers/base.py` | Article data with generate_hash() for deduplication |
| Scraper Worker | `workers/scraper_worker.py` | Orchestrates scraping → summarization → DB save |
| Summarizer | `services/summarizer.py` | Calls Ollama API for AI-generated summaries |
| Entity Extractor | `services/entity_extractor.py` | Extracts person/company names |
| Deduplication | `services/deduplication.py` | Detects duplicate articles via content hash |
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

## Fetch Strategies

Each scraper can use a different fetch strategy:

| Strategy | Use Case | Sources |
|----------|----------|---------|
| `httpx` | Default | Most sources |
| `curl` | Sites blocking httpx | - |
| `ollama` | Cloudflare/protected pages | openai |
| `playwright` | JavaScript challenges | - |
| `brave` | Brave Search API | - |

## Deduplication

Articles are deduplicated using content hash:
- Hash = SHA256(title | url | summary)
- `ArticleData.generate_hash()` creates the hash
- `DeduplicationService.is_duplicate()` checks against DB
- Duplicate articles are marked with `is_duplicate=True`
- Only `is_sent=False AND is_duplicate=False` articles are published

## Tech Stack
- **Backend**: Python 3.12, asyncio, SQLAlchemy (async)
- **Database**: PostgreSQL (ai_news database)
- **Cache/Queue**: Redis (port 6380)
- **LLM**: Ollama API (localhost:11434)
- **Scheduler**: APScheduler with cron triggers
- **Telegram**: python-telegram-bot library

## Schedule (Fixed)

| Job | Cron | Description |
|-----|------|-------------|
| fetch_all_sources | `5/15 * * * *` | Every 15 min at :05 |
| cleanup_old_news | `0 3 * * *` | Daily at 3 AM |
| send_digest | Runs inside fetch job | After scraper completes |

**Note**: Digest runs automatically after scraper in same job cycle to ensure articles are saved first.

## Configuration
- `config.yaml` - Main configuration file
- `news.summarization` - AI summarization settings (model, length bounds, prompt)
- `scraper.sources[].fetch_strategy` - Per-source fetch method
- Database credentials, Telegram bot token, scheduler jobs

## Known Issues (Fixed)

1. **Missing generate_hash()** - ArticleData now has generate_hash() and generate_title_hash() methods
2. **Concurrent session commits** - Scraper batch commits once after all sources, not per-source
3. **HTML parsing** - BaseScraper._html_to_soup() converts string to BeautifulSoup before parsing