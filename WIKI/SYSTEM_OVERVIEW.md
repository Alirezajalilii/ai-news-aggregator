# AI News Aggregator - System Overview

## Purpose
Automated news aggregation system that scrapes AI news from 11 sources, stores in PostgreSQL, and sends digests to Telegram channels.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Scrapers  │────▶│  PostgreSQL  │────▶│   Telegram  │
│   (11 src)  │     │   (ai_news)  │     │     Bot     │
└─────────────┘     └──────────────┘     └─────────────┘
       │                                        │
       ▼                                        ▼
┌─────────────┐                         ┌─────────────┐
│  Scheduler  │                         │   Digest    │
│ (APScheduler)│                         │   Worker    │
└─────────────┘                         └─────────────┘
```

## Tech Stack
- **Backend**: Python 3.12, asyncio, SQLAlchemy (async)
- **Database**: PostgreSQL (ai_news database)
- **Cache/Queue**: Redis (port 6380)
- **Scheduler**: APScheduler with cron triggers
- **Telegram**: python-telegram-bot library
- **Frontend**: React Native (future)

## Configuration
- `config.yaml` - Main configuration file
- Database credentials, Telegram bot token, scheduler jobs

## Schedule
- **Scrape**: Every 15 minutes (`0/15 * * * *`)
- **Digest**: Every 15 minutes (`0/15 * * * *`)
- **Cleanup**: Daily at 3 AM (`0 3 * * *`)