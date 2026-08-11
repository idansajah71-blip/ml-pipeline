import sys, asyncio
sys.path.insert(0, '.')
from sqlalchemy import text
from app.core.database import get_db

async def check():
    async for db in get_db():
        result = await db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'scrape_jobs' ORDER BY ordinal_position"
        ))
        cols = [r[0] for r in result.fetchall()]
        print(f"Columns ({len(cols)}): {cols}")
        await db.close()
        break

asyncio.run(check())
