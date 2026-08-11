import asyncio
from app.core.database import engine
from sqlalchemy import text


async def fix():
    async with engine.begin() as conn:
        # Drop and recreate scrape_type with correct type
        try:
            await conn.execute(text("ALTER TABLE scrape_jobs DROP COLUMN IF EXISTS scrape_type"))
            await conn.execute(text("ALTER TABLE scrape_jobs ADD COLUMN scrape_type VARCHAR(30) DEFAULT 'single'"))
            print("Fixed scrape_type -> VARCHAR(30)")
        except Exception as e:
            print(f"scrape_type: {e}")

        # Verify all columns
        result = await conn.execute(
            text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'scrape_jobs' ORDER BY ordinal_position")
        )
        rows = result.fetchall()
        print(f"\nscrape_jobs columns ({len(rows)}):")
        for r in rows:
            print(f"  {r[0]:30s} {r[1]}")


if __name__ == "__main__":
    asyncio.run(fix())
