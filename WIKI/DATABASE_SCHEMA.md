---
type: entity
domain: database
status: compiled
updated: 2026-04-16
tags: [postgresql, database, schema, article, source]
sources:
  - src/database/models.py
---

# Database Schema

## Database: `ai_news`
Host: `localhost:5432`, User: `planchin`, Password: `dev_password`

## Tables

### `sources`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| name | String(100) | Unique, e.g., "huggingface" |
| display_name | String(100) | Human readable, e.g., "Hugging Face" |
| url | String(500) | Base URL |
| category | String(50) | e.g., "research", "news", "company" |
| enabled | Boolean | Default true |
| created_at | DateTime | |
| updated_at | DateTime | Nullable |

### `articles`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| source_id | UUID | FK to sources |
| source_name | String(100) | Denormalized for easy access |
| title | String(500) | |
| summary | Text | Full article content (2000-8000 chars) |
| url | String(500) | |
| image_url | String(500) | May be relative (`/avatars/...`) or absolute |
| published_at | DateTime | |
| is_sent | Boolean | Only True when Telegram confirms delivery |
| sent_count | Integer | Default 0 |
| created_at | DateTime | |

### `subscriptions`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| type | String(50) | "telegram_channel", "telegram_user", "email" |
| channel_id | String(255) | e.g., "@ainews_ramzbank" |
| chat_id | String(255) | Target identifier |
| categories | JSON | Array of category names |
| enabled | Boolean | |
| created_at | DateTime | |

### `sent_messages`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| article_id | UUID | FK to articles |
| channel_type | String(50) | |
| channel_id | String(255) | |
| message_id | String(100) | Telegram message ID |
| content | Text | Sent content |
| delivered | Boolean | Confirmation flag |
| sent_at | DateTime | |

## Key Indexes
- `articles.is_sent` - For finding unsent articles
- `articles.published_at` - For ordering
- `articles.source_id` - For source filtering