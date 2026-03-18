#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database..."
python -c "
import asyncio
from app.seed import seed_all
from app.database import async_session
async def run():
    async with async_session() as db:
        await seed_all(db)
asyncio.run(run())
" 2>/dev/null || echo "Seeding skipped or already done"

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
