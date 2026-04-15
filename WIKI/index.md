---
type: index
domain: ai-news-aggregator
status: compiled
updated: 2026-04-16
tags: [ai-news, aggregator, telegram, python, scraper]
---

# Wiki Index - AI News Aggregator

## Pages

| Page | Type | Last Updated | Status |
|------|------|--------------|--------|
| [[wiki:SYSTEM_OVERVIEW]] | system | 2026-04-16 | compiled |
| [[wiki:SCRAPERS]] | domain | 2026-04-16 | compiled |
| [[wiki:TELEGRAM_BOT]] | domain | 2026-04-15 | compiled |
| [[wiki:DATABASE_SCHEMA]] | entity | 2026-04-15 | compiled |
| [[wiki:OPERATIONS]] | domain | 2026-04-15 | compiled |

## Structure

```
wiki/
├── index.md          # This file - master catalog
├── log.md            # Operation history (append-only)
├── schema.md         # Page templates and conventions
├── SYSTEM_OVERVIEW.md   # Full system architecture
├── SCRAPERS.md       # All scrapers status and details
├── TELEGRAM_BOT.md   # Telegram integration docs
├── DATABASE_SCHEMA.md    # Database entities
└── OPERATIONS.md     # Operations guide
```

## Domains

### Scraper Domain
- [[wiki:SCRAPERS]] - All registered scrapers, health status, fetch strategies
- Related: [[wiki:SYSTEM_OVERVIEW]]

### Infrastructure Domain
- [[wiki:TELEGRAM_BOT]] - Telegram bot setup, commands, formatting
- [[wiki:DATABASE_SCHEMA]] - PostgreSQL schema, Article/Source tables

### Operations Domain
- [[wiki:OPERATIONS]] - Deployment, monitoring, troubleshooting
- Related: [[wiki:SYSTEM_OVERVIEW]]

## Recent Changes

| Date | Operation | Pages | Summary |
|------|-----------|-------|---------|
| 2026-04-16 | fix | SCRAPERS | Fixed 3 broken scrapers (OpenAI, VentureBeat, MIT) using RSS feeds |
| 2026-04-16 | fix | SCRAPERS | Added frontmatter, updated status table |
| 2026-04-16 | create | index, log | Created wiki index and log per Karpathy protocol |

## Gaps / TODOs

- [ ] Gap: No health_check script documentation in OPERATIONS.md
- [ ] Gap: No backup/restore procedure documented
- [ ] Gap: No error monitoring/alerting documented

## Stale Pages

- OPERATIONS.md - Last updated 2026-04-15, needs review
- TELEGRAM_BOT.md - Last updated 2026-04-15, verify commands still accurate