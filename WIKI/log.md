---
type: log
domain: ai-news-aggregator
status: compiled
updated: 2026-04-16
tags: [log, operations, history]
---

# Wiki Log - AI News Aggregator

Append-only operation history. Format: `## [YYYY-MM-DD] {operation} | {summary}`

---

## [2026-04-16] fix | Added frontmatter to all wiki pages

**Pages Changed:** SCRAPERS.md, SYSTEM_OVERVIEW.md, TELEGRAM_BOT.md, DATABASE_SCHEMA.md, OPERATIONS.md, index.md, log.md
**Source:** WIKI/ files
**Summary:**
- Added required frontmatter (type, domain, status, updated, tags, sources) to all wiki pages
- Fixed SCRAPERS.md status table (all 11 working, not 3 failed)
- Created index.md with master catalog
- Created log.md for append-only operation history

**Evidence:** Git working tree (not yet committed)

---

## [2026-04-16] fix | Fixed 3 broken scrapers using RSS feeds

**Pages Changed:** SCRAPERS.md, SYSTEM_OVERVIEW.md, index.md, log.md
**Source:** config.yaml, src/scrapers/*.py
**Summary:**
- OpenAI (403) → Changed to RSS feed `openai.com/news/rss.xml`, rewrote openai_scraper.py for RSS parsing
- VentureBeat (429) → Changed to RSS feed `venturebeat.com/feed/`, rewrote venturebeat_scraper.py for RSS parsing
- MIT (404) → URL changed to `artificial-intelligence2` in config.yaml and mit_news_scraper.py
- All 3 scrapers tested and working: OpenAI (15), VentureBeat (7), MIT (15) articles

**Evidence:** Git commit `31d85e6`

---

## [2026-04-16] create | Created wiki index and log

**Pages Changed:** index.md, log.md
**Source:** Karpathy Wiki Protocol adoption
**Summary:**
- Created index.md per protocol (required for all wiki directories)
- Created log.md per protocol (append-only operation history)
- Added frontmatter to all pages that lacked it
- Documented recent changes in index.md recent-changes table

---

## [2026-04-16] fix | Added frontmatter to SCRAPERS.md

**Pages Changed:** SCRAPERS.md
**Source:** wiki/SCRAPERS.md
**Summary:**
- Added frontmatter (type, domain, status, updated, tags) to SCRAPERS.md
- Updated status table with correct status (all 11 working, not 3 failed)
- Added "Fixed Scrapers" section documenting fixes with evidence

---

## [2026-04-15] ingest | Initial wiki structure

**Pages Changed:** All wiki pages
**Source:** Initial project documentation
**Summary:**
- Created initial WIKI/ directory with:
  - SYSTEM_OVERVIEW.md - System architecture and workflow
  - SCRAPERS.md - All scrapers documentation
  - TELEGRAM_BOT.md - Telegram integration
  - DATABASE_SCHEMA.md - PostgreSQL schema
  - OPERATIONS.md - Deployment and operations guide

**Evidence:** Initial git commit