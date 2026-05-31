-- Create required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS vector;           -- pgvector: semantic similarity (C6)
CREATE EXTENSION IF NOT EXISTS timescaledb;      -- TimescaleDB: wearable time-series (F-WEAR)
CREATE EXTENSION IF NOT EXISTS age;              -- Apache AGE: Cypher graph queries (C6)
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Create a separate database for ZITADEL
CREATE DATABASE zitadel;
