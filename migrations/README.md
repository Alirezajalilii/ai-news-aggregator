# Database Migrations

This directory contains Alembic migrations for database schema management.

## Usage

```bash
# Create a new migration
alembic revision --autogenerate -m "Add articles table"

# Run migrations
alembic upgrade head

# Check current version
alembic current

# Rollback
alembic downgrade -1
```

## Notes

- Migrations are managed by Alembic
- Models are defined in `src/database/models.py`
- Use `alembic revision --autogenerate` to auto-generate from model changes
