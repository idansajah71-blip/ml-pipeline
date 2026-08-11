import sys
sys.path.insert(0, '.')
import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.begin() as conn:
        for table in ['scrape_jobs', 'datasets', 'models', 'experiments', 'predictions', 'ab_tests', 'serving_endpoints', 'batch_jobs']:
            try:
                r = await conn.execute(text(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position"
                ))
                cols = [row[0] for row in r.fetchall()]
                print(f'{table} ({len(cols)}): {", ".join(cols)}')
            except Exception as e:
                print(f'{table}: ERROR - {e}')

asyncio.run(check())
