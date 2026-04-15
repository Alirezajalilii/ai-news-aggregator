# AI News Aggregator

A production-ready news aggregation system that scrapes AI news from multiple sources, removes duplicates, and publishes to Telegram channels.

## Features

- **Multi-Source Scraping**: 11 AI news sources including OpenAI, Anthropic, Google AI, HuggingFace, TechCrunch, and more
- **Smart Deduplication**: Entity-based similarity detection to avoid duplicate articles
- **Category Classification**: Automatically categorizes articles into Model, Company, Startup, Research, Tool, and General
- **Telegram Integration**: Sends formatted HTML digests to channels and users
- **Scheduled Jobs**: Automatic scraping and digest delivery on configurable schedules
- **PostgreSQL Storage**: Production-grade database for article storage and tracking
- **Redis Caching**: Fast caching layer for performance optimization

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI News Aggregator                     │
├─────────────────────────────────────────────────────────┤
│  Sources          │  Workers          │  Services       │
│  ─────────────    │  ───────────      │  ──────────     │
│  OpenAI Blog      │  Scraper Worker   │  Entity Extract │
│  Anthropic News   │  Digest Worker   │  Deduplication  │
│  Google AI Blog   │  Scheduler       │  Telegram       │
│  HuggingFace      │                  │  Scheduler     │
│  MarkTechPost     │                  │                 │
│  TechCrunch AI    │                  │                 │
│  VentureBeat AI   │                  │                 │
│  MIT News AI      │                  │                 │
│  Unite.AI         │                  │                 │
│  AI News          │                  │                 │
│  The Verge AI     │                  │                 │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│  PostgreSQL (Articles, Sources, Subscriptions)           │
│  Redis (Caching, Rate Limiting)                         │
└─────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.10+
- PostgreSQL 14+
- Redis 6+

## Installation

```bash
# Clone the repository
cd /opt/ai-news-aggregator

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure config
cp config.yaml.example config.yaml
# Edit config.yaml with your settings

# Initialize database
python scripts/init_db.py
```

## Configuration

Edit `config.yaml`:

```yaml
app:
  name: "AI News Aggregator"
  version: "1.0.0"
  environment: "development"
  debug: true

database:
  host: "localhost"
  port: 5432
  name: "ai_news"
  username: "postgres"
  password: "your_password"

redis:
  host: "localhost"
  port: 6379
  db: 0

telegram:
  bot_token: "YOUR_BOT_TOKEN"
  allowed_users:
    - 123456789  # Your Telegram user ID
  channels:
    - "@your_channel"

scraper:
  sources:
    - name: "openai"
      url: "https://openai.com/blog"
      enabled: true
      priority: 1
```

## Usage

### Initialize Database

```bash
python scripts/init_db.py
```

### Manual Scrape

```bash
# Scrape all sources
python -m src.main scrape

# Scrape specific source
python -m src.main scrape --source openai
```

### Send Digest

```bash
# Send to all subscribers
python -m src.main digest

# Filter by category
python -m src.main digest --category model --category company
```

### Start Scheduler

```bash
# Start automatic scraping and digest delivery
python -m src.main scheduler
```

## Project Structure

```
ai-news-aggregator/
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── src/
│   ├── main.py            # CLI entry point
│   ├── core/             # Core functionality
│   │   └── config.py     # Configuration management
│   ├── database/          # Database layer
│   │   ├── models.py     # SQLAlchemy models
│   │   └── __init__.py
│   ├── scrapers/         # Web scrapers
│   │   ├── base.py       # Base scraper class
│   │   └── [source].py   # Source-specific scrapers
│   ├── services/          # Business logic
│   │   ├── entity_extractor.py
│   │   ├── deduplication.py
│   │   └── scheduler.py
│   ├── workers/          # Background workers
│   │   ├── scraper_worker.py
│   │   └── digest_worker.py
│   └── telegram/         # Telegram integration
│       └── telegram_service.py
├── scripts/
│   └── init_db.py        # Database initialization
├── tests/                # Test files
├── migrations/            # Alembic migrations
└── docs/                # Documentation
```

## Deduplication System

The deduplication system uses multiple strategies:

1. **Exact Hash Matching**: Content hash for exact duplicates
2. **Title Similarity**: Jaccard index on words (40% weight)
3. **Entity Overlap**: Common entities between articles (40% weight)
4. **Content Similarity**: Word overlap in content (20% weight)

Articles with similarity > 0.75 are marked as duplicates.

## Categories

Articles are classified into these categories:

| Category | Emoji | Description |
|----------|-------|-------------|
| model | 🤖 | New AI models and releases |
| company | 🏢 | Company news and announcements |
| startup | 💰 | Startups and funding |
| research | 🔬 | Research papers and studies |
| tool | ⚡ | Tools and products |
| general | 📰 | General AI news |

## API (Future)

REST API for external integrations:

- `GET /api/articles` - List articles
- `GET /api/articles/{id}` - Get single article
- `POST /api/subscriptions` - Create subscription
- `GET /api/stats` - Get statistics

## Monitoring

Health check endpoint: `GET /health`

Metrics endpoint: `GET /metrics` (Prometheus format)

## License

MIT License

## Author

Dobby 🪄 - AI Assistant for Alireza
