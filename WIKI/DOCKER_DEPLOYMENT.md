# Docker & Deployment

_Last updated: 2026-04-16_

## Overview

AI News Aggregator is containerized with production-grade Docker patterns:
- Multi-stage build (builder + runtime)
- Non-root user (`appuser`)
- Health checks (liveness + readiness)
- Graceful shutdown (SIGTERM handler, 30s drain)
- Environment variable overrides (12-factor)
- Centralized JSON log aggregation

## Architecture

```
┌─────────────────┐   ┌──────────────┐   ┌──────────────┐
│   ainews-app    │──▶│ ainews-redis │   │ ainews-postgres│
│  (Python app)   │   │  (Redis 7)   │   │  (PG 16)      │
│  port 8080      │   │  port 6379   │   │  port 5432    │
└────────┬────────┘   └──────────────┘   └──────────────┘
         │
         │ OLLAMA_BASE_URL
         ▼
┌─────────────────┐
│  Host Ollama    │
│  port 11434     │
│  (GPU required) │
└─────────────────┘
```

All containers on `ainews-net` (172.28.0.0/16). App reaches Ollama via `host.docker.internal`.

## Quick Start

```bash
# Copy env config
cp .env.example .env
# Edit .env with your bot token and passwords

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f app

# Stop all services
docker compose down
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment name |
| `LOG_LEVEL` | `INFO` | Python log level |
| `DB_HOST` | `postgres` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port (internal) |
| `DB_NAME` | `ai_news` | Database name |
| `DB_USERNAME` | `planchin` | DB user |
| `DB_PASSWORD` | — | DB password (required) |
| `REDIS_HOST` | `redis` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | — | Redis password |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token (required) |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API URL |
| `HEALTHCHECK_PORT` | `8080` | Health check HTTP port |

Priority: Environment variables > config.yaml > defaults

## Production Deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production overrides:
- Restart policies: `always`
- Higher resource limits
- No external DB/Redis ports
- Larger log rotation (50m, 5 files)
- Redis persistence + password

## Host Requirements

### Ollama

Ollama runs on the host (GPU access required). Must listen on `0.0.0.0`:

```bash
# Create systemd override
sudo mkdir -p /etc/systemd/system/ollama.service.d/
cat << 'EOF' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Firewall

Allow Docker bridge networks to reach host:

```bash
sudo iptables -I INPUT -s 172.28.0.0/16 -j ACCEPT
sudo iptables -I INPUT -s 172.17.0.0/16 -j ACCEPT
sudo ufw allow from 172.28.0.0/16 to any port 11434
sudo ufw allow from 172.17.0.0/16 to any port 11434
```

## Health Endpoints

| Endpoint | Purpose | Status Codes |
|----------|---------|---------------|
| `GET /health` | Liveness (is the process alive?) | 200 = healthy |
| `GET /ready` | Readiness (are deps reachable?) | 200 = ready, 503 = degraded |

Response format: `{"status": "ready", "checks": {"postgres": true, "redis": true, "ollama": true}}`

## Lifecycle Management

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all services |
| `docker compose down` | Stop and remove containers |
| `docker compose restart app` | Restart app only |
| `docker compose logs -f app` | Follow app logs |
| `docker compose ps` | Check service status |
| `docker compose build app` | Rebuild app image |

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build (builder + runtime) |
| `docker-compose.yml` | Development orchestration |
| `docker-compose.prod.yml` | Production overrides |
| `docker/entrypoint.sh` | Startup: wait deps, migrate, health server, app |
| `docker/healthcheck.py` | Health HTTP server + CLI check mode |
| `.env.example` | Template for environment variables |
| `.dockerignore` | Exclude patterns for build context |

## Configuration Override Flow

```
config.yaml (defaults)
       ↓
.env file (Docker Compose vars)
       ↓
Environment variables (runtime)
       ↓
Final config (load_config merges all)
```

Each config model (DatabaseConfig, RedisConfig, TelegramConfig, SummarizationConfig, LoggingConfig) has a `from_env()` classmethod that applies env var overrides on top of YAML values.