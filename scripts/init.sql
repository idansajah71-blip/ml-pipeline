-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom types (ignore if already exists)
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'data_scientist', 'user');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE model_status AS ENUM ('training', 'trained', 'deployed', 'archived', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE experiment_status AS ENUM ('pending', 'running', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create indexes only if the table exists (tables are created by SQLAlchemy)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'users') THEN
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'models') THEN
        CREATE INDEX IF NOT EXISTS idx_models_owner ON models(owner_id);
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'experiments') THEN
        CREATE INDEX IF NOT EXISTS idx_experiments_model ON experiments(model_id);
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'predictions') THEN
        CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions(model_id);
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'datasets') THEN
        CREATE INDEX IF NOT EXISTS idx_datasets_owner ON datasets(owner_id);
    END IF;
END $$;
