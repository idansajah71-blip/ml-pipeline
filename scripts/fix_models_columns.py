"""Add missing columns to models table directly."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.SYNC_DATABASE_URL)

with engine.connect() as conn:
    migrations = [
        "ALTER TABLE models ADD COLUMN IF NOT EXISTS task_id VARCHAR(255)",
        "ALTER TABLE models ADD COLUMN IF NOT EXISTS stage VARCHAR(50) DEFAULT 'development'",
        "ALTER TABLE models ADD COLUMN IF NOT EXISTS parent_model_id UUID REFERENCES models(id)",
        "ALTER TABLE models ADD COLUMN IF NOT EXISTS model_card JSONB DEFAULT '{}'::jsonb",
        "CREATE INDEX IF NOT EXISTS ix_models_stage ON models (stage)",
    ]
    for sql in migrations:
        try:
            conn.execute(text(sql))
            print(f"OK: {sql[:70]}")
        except Exception as e:
            print(f"SKIP: {sql[:70]} -> {e}")
    conn.commit()
    
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'models' ORDER BY ordinal_position"))
    cols = [row[0] for row in result]
    print(f"\nFinal models columns: {cols}")
