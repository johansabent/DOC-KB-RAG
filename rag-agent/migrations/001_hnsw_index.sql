-- Migration 001: Create HNSW cosine distance index on the vector column.
--
-- Run this ONCE in the Supabase SQL editor (or via psql) after ingestion.
-- This eliminates the full-table-scan warning:
--   "Query does not have a covering index for IndexMeasure.cosine_distance"
--
-- HNSW is preferred over IVFFlat here because:
--   - It can be built on a non-empty table (no need to re-ingest first)
--   - It auto-updates as new vectors are inserted
--   - Better recall/latency tradeoff at this corpus size (<100K vectors)
--
-- Parameters:
--   m               = 16   (number of bi-directional links per node — balanced default)
--   ef_construction = 64   (build-time search depth — higher = better recall, slower build)
--
-- NOTE: If you changed COLLECTION_NAME in .env from the default "openclaw_docs",
-- replace "openclaw_docs" in the statement below with your collection name before running.
-- The table lives in the "vecs" schema: vecs.<COLLECTION_NAME>

CREATE INDEX IF NOT EXISTS openclaw_docs_vec_hnsw_idx
ON vecs.openclaw_docs
USING hnsw (vec vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================
-- Alternative: parameterized version for non-default collections
-- Replace 'my_collection' with your COLLECTION_NAME value.
-- ============================================================
--
-- DO $$
-- DECLARE
--   collection TEXT := 'my_collection';
-- BEGIN
--   EXECUTE format(
--     'CREATE INDEX IF NOT EXISTS %I ON vecs.%I USING hnsw (vec vector_cosine_ops) WITH (m = 16, ef_construction = 64)',
--     collection || '_vec_hnsw_idx',
--     collection
--   );
-- END $$;
