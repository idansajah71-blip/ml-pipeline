import asyncpg, asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')

async def check():
    conn = await asyncpg.connect('postgresql://ml_user:ml_password@localhost:5432/ml_pipeline_db')
    rows = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'experiments' ORDER BY ordinal_position"
    )
    print("Experiments table schema:")
    for r in rows:
        print(f"  {r['column_name']}: {r['data_type']}")
    await conn.close()

asyncio.run(check())
