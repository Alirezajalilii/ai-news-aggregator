# Web Scrapers

## Registered Sources (11)

| Source | Display Name | Category | Status |
|--------|--------------|----------|--------|
| openai | OpenAI | company | ⚠️ 403 Forbidden |
| anthropic | Anthropic | company | ✅ |
| google_ai | Google AI | company | ✅ |
| huggingface | Hugging Face | research | ✅ |
| marktechpost | MarkTechPost | news | ✅ |
| techcrunch_ai | TechCrunch AI | news | ✅ |
| venturebeat_ai | VentureBeat AI | news | ⚠️ 429 Rate Limited |
| mit_news_ai | MIT News AI | research | ⚠️ 404 Not Found |
| unite_ai | Unite.AI | news | ✅ |
| ai_news | AI News | news | ✅ |
| the_verge_ai | The Verge AI | news | ✅ |

## Scraper Base Class

All scrapers inherit from `ScraperBase` in `src/scrapers/base.py`:

```python
class ScraperBase:
    name: str           # Unique identifier
    display_name: str   # Human readable
    base_url: str       # Starting URL
    category: str       # e.g., "research", "news"
    
    async def fetch_article_content(url: str) -> str:
        """Fetch full article text from URL"""
        
    async def scrape() -> List[Article]:
        """Scrape articles, return list of Article objects"""
```

## Content Fetching

- Each scraper calls `self.fetch_article_content(url)` to get full article text
- Content is stored in `article.summary` field
- Average content length: 2000-8000 characters

## Image URLs

- Some sources return relative URLs (e.g., `/avatars/...`)
- Telegram `sendPhoto` requires absolute URLs with `http://` or `https://`
- **Fallback**: If image URL is relative, send as text message instead

## Error Handling

- 403 Forbidden: Source blocks bots
- 429 Too Many Requests: Rate limited
- 404 Not Found: Page moved or deleted
- 400 Bad Request: Invalid URL or Telegram API issue