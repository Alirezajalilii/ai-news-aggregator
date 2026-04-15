# Web Scrapers

## Overview
The AI News Aggregator uses 11 scrapers to fetch news from various sources. Each scraper is tailored to a specific website's HTML structure.

## Health Check

Run the health check script to see current status:

```bash
python scripts/health_check.py
python scripts/health_check.py --json  # JSON output
```

## Registered Sources (11)

| Source | Display Name | Category | Status | Articles |
|--------|--------------|----------|--------|----------|
| openai | OpenAI | company | ❌ 403 Forbidden | - |
| anthropic | Anthropic | company | ✅ OK | 14 |
| google_ai | Google AI | company | ✅ OK | 9 |
| huggingface | Hugging Face | research | ✅ OK | 20 |
| marktechpost | MarkTechPost | news | ✅ OK | 14 |
| techcrunch_ai | TechCrunch AI | news | ✅ OK | 7 |
| venturebeat_ai | VentureBeat AI | news | ❌ 429 Rate Limited | - |
| mit_news_ai | MIT News AI | research | ❌ 404 Not Found | - |
| unite_ai | Unite.AI | news | ✅ OK | 7 |
| ai_news | AI News | news | ✅ OK | 2 |
| the_verge_ai | The Verge AI | news | ✅ OK | 1 |

**Summary: 8 OK, 3 FAILED out of 11 scrapers**

## Failed Scrapers

### openai (403 Forbidden)
- **Issue**: OpenAI's blog is protected by Cloudflare anti-bot protection
- **Solution**: Would need to use official API or alternative approach
- **Status**: Not fixable without significant changes

### venturebeat_ai (429 Rate Limited)
- **Issue**: Rate limited by VentureBeat
- **Solution**: Could reduce request frequency or use RSS
- **Status**: Temporary - rate limit may clear

### mit_news_ai (404 Not Found)
- **Issue**: MIT News URL structure changed
- **URL used**: `https://news.mit.edu/topic/artificial-intelligence`
- **Solution**: Find new MIT AI news URL
- **Status**: Needs URL update in config.yaml

## Working Scrapers

### anthropic
- **URL**: `https://www.anthropic.com/news`
- **Selector**: Links with `/news/` pattern
- **Articles**: 14

### google_ai
- **URL**: `https://blog.google/technology/ai/`
- **Selector**: `div.card` elements
- **Articles**: 9

### huggingface
- **URL**: `https://huggingface.co/blog`
- **Selector**: Standard article structure
- **Articles**: 20

### marktechpost
- **URL**: `https://www.marktechpost.com/`
- **Selector**: `div.td_module_flex` elements
- **Articles**: 14

### techcrunch_ai
- **URL**: `https://techcrunch.com/category/artificial-intelligence/`
- **Selector**: Standard article structure
- **Articles**: 7

### unite_ai
- **URL**: `https://www.unite.ai/`
- **Selector**: Links with meaningful text (5+ words)
- **Articles**: 7

### ai_news
- **URL**: `https://www.ainews.com/`
- **Selector**: Standard article structure
- **Articles**: 2

### the_verge_ai
- **URL**: `https://www.theverge.com/ai-artificial-intelligence`
- **Selector**: Standard article structure
- **Articles**: 1

## Scraper Base Class

All scrapers inherit from `BaseScraper` in `src/scrapers/base.py`:

```python
class BaseScraper(ABC):
    name: str           # Unique identifier
    base_url: str       # Starting URL
    
    async def scrape() -> ScraperResult:
        """Scrape articles, return ScraperResult"""
        
    async def fetch_page(url: str) -> BeautifulSoup:
        """Fetch and parse a webpage"""
        
    async def fetch_article_content(url: str) -> str:
        """Fetch full article text from URL"""
```

## Fetch Strategies

Each scraper can use a different fetch strategy based on the source requirements:

| Strategy | Use Case | Example Sources |
|----------|----------|----------------|
| `httpx` | Default - simple HTTP | Most sources |
| `curl` | Sites blocking httpx | venturebeat |
| `ollama` | Cloudflare/protected pages | openai |
| `playwright` | JavaScript challenges | Sites with JS verification |
| `brave` | Brave Search API | Alternative news search |

**Configuring in config.yaml:**
```yaml
sources:
  - name: "openai"
    fetch_strategy: "ollama"  # Use LLM for Cloudflare-protected sites
  - name: "venturebeat_ai"
    fetch_strategy: "playwright"  # Use browser for JS challenges
```

## Article Extraction Flow

```
1. scraper.scrape() → _fetch() using configured strategy
2. parse_articles() → Extract ArticleData list
3. For each article:
   a. title: From h1/h2/h3 or link text
   b. url: From anchor href
   c. summary: From paragraph or card text
   d. image_url: From img src
   e. published_at: From time tag or date pattern
4. ArticleData.generate_hash() → Unique ID for deduplication
5. DeduplicationService.is_duplicate() → Check against DB
6. If not duplicate → Save to DB
7. If duplicate → Mark as duplicate (is_duplicate=True)
```

## Content Fetching

- Each scraper calls `fetch_article_content(url)` to get full article text
- Full content is passed to **SummarizationService** for AI-generated summaries
- Average content length: 2000-8000 characters

## Deduplication

Articles are deduplicated using content hash:
- Hash = SHA256(title | url | summary)
- Duplicate articles are marked with `is_duplicate=True`
- Only `is_sent=False AND is_duplicate=False` articles are published

## Error Handling

| Error Code | Meaning | Cause |
|------------|---------|-------|
| 403 Forbidden | Access denied | Cloudflare, anti-bot, IP block |
| 429 Too Many Requests | Rate limited | Too many requests in short time |
| 404 Not Found | Page missing | URL changed or deleted |
| Timeout | No response | Server slow or unreachable |

## Adding New Sources

1. Create `src/scrapers/{source_name}_scraper.py`
2. Inherit from `BaseScraper`
3. Implement `parse_articles()` method
4. Register in `src/scrapers/__init__.py`
5. Add to `config.yaml` under `scraper.sources`
6. Test with `python scripts/health_check.py`