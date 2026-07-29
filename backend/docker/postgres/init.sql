-- PostgreSQL initialization script for Temple AI Crowd Management System
-- Runs once when the container is first created.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Ensure the database exists (already created by POSTGRES_DB env var)
-- This script runs inside the target database.

-- Grant all privileges to the application user
GRANT ALL PRIVILEGES ON DATABASE temple_crowd_db TO postgres;

-- Set default timezone
ALTER DATABASE temple_crowd_db SET timezone TO 'Asia/Kolkata';

-- Set statement timeout to prevent runaway queries
ALTER DATABASE temple_crowd_db SET statement_timeout = '30s';

-- Enable pg_stat_statements for query analysis (optional)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

SELECT 'Temple AI Crowd Management System database initialized.' AS message;
