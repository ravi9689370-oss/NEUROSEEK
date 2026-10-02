-- Database initialization script for NeuroSeek AI
-- This runs automatically when PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create additional indexes for performance
-- These will be created by Alembic migrations, but we can add some here

-- Full-text search configuration (optional)
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Set timezone
SET timezone = 'UTC';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE neuroseek TO neuroseek;
GRANT ALL ON SCHEMA public TO neuroseek;

-- Create a function for automatic updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Note: Tables will be created by SQLAlchemy/Alembic on first run
-- This script just ensures extensions and base configuration