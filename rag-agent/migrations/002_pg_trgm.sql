-- Migration 002: Enable pg_trgm extension for trigram-based text search support.
--
-- Run this ONCE in the Supabase SQL editor (or via psql) BEFORE migration 003.
-- pg_trgm provides trigram similarity functions and operators that complement
-- tsvector full-text search for fuzzy matching scenarios.
--
-- This is safe to run multiple times (IF NOT EXISTS).

CREATE EXTENSION IF NOT EXISTS pg_trgm;
