---
type: domain
domain: operations
status: compiled
updated: 2026-04-16
tags: [operations, deployment, monitoring, docker, celery]
sources:
  - config.yaml
  - src/main.py
---

# Operations Guide

## Starting the System

### Start Scheduler
```bash
cd /opt/ai-news-aggregator
./venv/bin/python -m src.main scheduler
```

### Run Manual Scrape
```bash
cd /opt/ai-news-aggregator
./venv/bin/python -m src.main scrape
```

### Send Manual Digest
```bash
cd /opt/ai-news-aggregator
./venv/bin/python -m src.main digest
```

## Database Operations

### Connect to PostgreSQL
```bash
PGPASSWORD=dev_password psql -h localhost -p 5432 -U planchin -d ai_news
```

### Check Article Counts
```sql
SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_sent = true) as sent FROM articles;
```

### Reset Unsant Articles
```sql
DELETE FROM sent_messages;
UPDATE articles SET is_sent = false, sent_count = 0;
```

### Check Running Processes
```bash
ps aux | grep "src.main" | grep scheduler
```

### Kill All Schedulers
```bash
pkill -f "src.main scheduler"
```

## Monitoring

### Scheduler Jobs (config.yaml)
- **Scrape**: `0/15 * * * *` - Every 15 minutes
- **Digest**: `0/15 * * * *` - Every 15 minutes  
- **Cleanup**: `0 3 * * *` - Daily at 3 AM

### Log Locations
- APScheduler logs to stdout
- Use `journalctl` for systemd logs

## Troubleshooting

### Scheduler Won't Start (no running event loop)
Use threading approach in `main.py`:
```python
def run_scheduler():
    asyncio.run(_run_scheduler())
thread = threading.Thread(target=run_scheduler, daemon=True)
thread.start()
```

### Articles Sending Duplicate
1. Check multiple schedulers running: `ps aux | grep scheduler`
2. Kill extras: `pkill -f "src.main scheduler"`
3. Reset sent flags: `UPDATE articles SET is_sent = false`

### Photo Not Sending (400 Bad Request)
- Check if image URL is absolute (starts with http)
- Relative URLs (`/avatars/...`) fallback to text message
- This is expected behavior

### Telegram Rate Limited (429)
- Increase delay between messages (currently 3 seconds)
- Wait for rate limit window to reset

## Git Workflow
```bash
git add -A
git commit -m "Description of changes"
git push
```