# AI News Aggregator - Documentation

## Overview

AI News Aggregator is a production-ready system for collecting, deduplicating, and distributing AI news from multiple sources via Telegram.

## Key Concepts

### Deduplication Strategy

Articles are compared using:
- **Title similarity** (40% weight): Jaccard index on words
- **Entity overlap** (40% weight): Common extracted entities (companies, products)
- **Content similarity** (20% weight): Word overlap

Articles with similarity > 0.75 are marked as duplicates.

### Entity Extraction

The system extracts:
- **Companies**: OpenAI, Anthropic, Google, Meta, etc.
- **Products**: GPT-5, Claude 3, Gemini 2, etc.
- **Technologies**: Transformer, RAG, RLHF, etc.

### Categories

| ID | Name | Emoji |
|----|------|-------|
| model | مدل‌های جدید | 🤖 |
| company | شرکت‌ها | 🏢 |
| startup | استارتاپ/سرمایه‌گذاری | 💰 |
| research | تحقیقات | 🔬 |
| tool | ابزارها | ⚡ |
| general | عمومی | 📰 |

## API Reference

### CLI Commands

```bash
# Initialize database
python -m src.main init

# Scrape all sources
python -m src.main scrape

# Send digest
python -m src.main digest

# Start scheduler
python -m src.main scheduler
```

## Architecture

See README.md for detailed architecture.
