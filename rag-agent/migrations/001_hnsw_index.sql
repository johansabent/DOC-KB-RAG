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

CREATE INDEX IF NOT EXISTS openclaw_docs_vec_hnsw_idx
ON vecs.openclaw_docs
USING hnsw (vec vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
