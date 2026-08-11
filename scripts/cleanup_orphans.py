import sys
sys.path.insert(0, '.')
import asyncio
from app.core.database import engine
from sqlalchemy import text

async def cleanup():
    async with engine.begin() as conn:
        # Find orphaned model_versions
        r = await conn.execute(text("""
            SELECT mv.id, mv.model_id FROM model_versions mv
            LEFT JOIN models m ON mv.model_id = m.id
            WHERE m.id IS NULL
        """))
        orphans = r.fetchall()
        print(f"Orphaned model_versions: {len(orphans)}")
        for o in orphans:
            print(f"  version {o[0]} -> missing model {o[1]}")

        if orphans:
            # Delete orphaned versions
            await conn.execute(text("""
                DELETE FROM model_versions WHERE model_id NOT IN (SELECT id FROM models)
            """))
            print(f"Deleted {len(orphans)} orphaned versions")

        # Also check other foreign key issues
        for fk_table, fk_col, ref_table in [
            ('model_versions', 'model_id', 'models'),
            ('experiments', 'model_id', 'models'),
            ('experiments', 'dataset_id', 'datasets'),
            ('predictions', 'model_id', 'models'),
            ('ab_tests', 'model_a_id', 'models'),
            ('ab_tests', 'model_b_id', 'models'),
            ('batch_jobs', 'model_id', 'models'),
        ]:
            r = await conn.execute(text(f"""
                SELECT COUNT(*) FROM {fk_table} t
                LEFT JOIN {ref_table} r ON t.{fk_col} = r.id
                WHERE r.id IS NULL AND t.{fk_col} IS NOT NULL
            """))
            count = r.scalar()
            if count and count > 0:
                print(f"Orphaned {fk_table}.{fk_col}: {count} rows")
                await conn.execute(text(f"""
                    DELETE FROM {fk_table} WHERE {fk_col} NOT IN (SELECT id FROM {ref_table})
                """))
                print(f"  -> Cleaned up")

asyncio.run(cleanup())
