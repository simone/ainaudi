-- PostgreSQL initialization script for RDL Referendum
-- This runs automatically when the container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Note: pgvector extension for AI embeddings (uncomment when needed)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE rdl_referendum TO postgres;

-- Log that initialization is complete
DO $$
BEGIN
    RAISE NOTICE 'RDL Referendum database initialized successfully';
END
$$;
