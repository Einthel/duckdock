---
name: sqlite-migrations
description: Non-destructive schema migration patterns for SQLite in Lan7. Safe column additions and index creation without losing user production database.
---

# Lan7 SQLite Schema Migration Skill

Lan7 distributes as a portable desktop/server application (`dist/lan7.exe`) using a local SQLite WAL database (`db/lan7.db`). Users cannot run manual Alembic CLI commands upon update.

## 1. Migration Principles
- **Never DROP existing tables** on application startup.
- All migrations must be automatic, idempotent, and non-destructive.
- Run migrations during `init_db()` in `lan7/storage/database.py`.

## 2. Safe Column Addition Pattern
Before adding a column to an existing table, inspect `PRAGMA table_info`:

```python
async def safe_add_column(engine, table_name: str, column_name: str, column_type: str):
    async with engine.begin() as conn:
        result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result.fetchall()]
        if column_name not in columns:
            await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
```

## 3. SQLite Limitations to Remember
- SQLite does **NOT** support `ALTER TABLE DROP COLUMN` in older versions or `ALTER COLUMN TYPE`.
- SQLite does **NOT** support adding columns with `NOT NULL` without a default value. Always provide a default or make the new column nullable (`nullable=True`).
- Safe index creation: always use `CREATE INDEX IF NOT EXISTS idx_name ON table_name (column)`.
