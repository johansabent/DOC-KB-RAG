-- Migration 003: Create hybrid_search_rrf() RPC function.
--
-- Run this ONCE in the Supabase SQL editor (or via psql) AFTER migrations 001 and 002.
-- This function fuses dense vector search (cosine) with full-text BM25-style search
-- using Reciprocal Rank Fusion (RRF).  Both retrieval methods run inside the DB;
-- only the final top-K rows cross the network.
--
-- NOTE: If you changed COLLECTION_NAME in .env from the default "openclaw_docs",
-- replace every occurrence of "openclaw_docs" in this file with your collection name.
--
-- Schema note: The vecs library stores node text inside metadata->'_node_content'
-- (a serialized JSON string).  The text is extracted via:
--   (metadata->>'_node_content')::jsonb->>'text'
--
-- Parameters:
--   query_text       — raw user question (for full-text search via websearch_to_tsquery)
--   query_embedding  — dense embedding vector from Gemini (3072 dims)
--   match_count      — number of fused results to return (default 5)
--   rrf_k            — RRF smoothing constant (default 60, standard value)
--   semantic_weight  — weight for semantic (vector) results in fusion (default 0.5)
--   fulltext_weight  — weight for full-text (BM25) results in fusion (default 0.5)

CREATE OR REPLACE FUNCTION hybrid_search_rrf(
    query_text       text,
    query_embedding  vector(3072),
    match_count      int     DEFAULT 5,
    rrf_k            int     DEFAULT 60,
    semantic_weight  float   DEFAULT 0.5,
    fulltext_weight  float   DEFAULT 0.5
)
RETURNS TABLE (
    id       text,
    content  text,
    metadata jsonb,
    score    float
)
LANGUAGE sql
STABLE
AS $$
    -- 1. Dense vector search: cosine distance, uses HNSW index from migration 001
    WITH semantic AS (
        SELECT
            s.id,
            ROW_NUMBER() OVER (ORDER BY s.vec <=> query_embedding) AS rank_ix
        FROM vecs.openclaw_docs s
        ORDER BY s.vec <=> query_embedding
        LIMIT (match_count * 2)
    ),

    -- 2. Full-text search: BM25-style ranking via tsvector/tsquery
    --    Text is extracted from the serialized _node_content JSON inside metadata.
    --    Computed on-the-fly (no stored tsvector column — we do not own the vecs schema).
    fulltext AS (
        SELECT
            f.id,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector('english', (f.metadata ->> '_node_content')::jsonb ->> 'text'),
                    websearch_to_tsquery('english', query_text)
                ) DESC
            ) AS rank_ix
        FROM vecs.openclaw_docs f
        WHERE
            f.metadata ->> '_node_content' IS NOT NULL
            AND to_tsvector('english', (f.metadata ->> '_node_content')::jsonb ->> 'text')
                @@ websearch_to_tsquery('english', query_text)
        LIMIT (match_count * 2)
    ),

    -- 3. Reciprocal Rank Fusion: score = sum of weight/(k + rank) per method.
    --    Documents found by only one method get 0 for the missing term.
    fused AS (
        SELECT
            COALESCE(sem.id, ft.id) AS id,
            (COALESCE(semantic_weight / (rrf_k + sem.rank_ix), 0.0)
           + COALESCE(fulltext_weight / (rrf_k + ft.rank_ix), 0.0)) AS score
        FROM semantic sem
        FULL OUTER JOIN fulltext ft ON sem.id = ft.id
        ORDER BY score DESC
        LIMIT match_count
    )

    -- 4. Re-join to fetch content and lightweight metadata (strip _node_content).
    SELECT
        fused.id,
        (doc.metadata ->> '_node_content')::jsonb ->> 'text' AS content,
        doc.metadata - '_node_content'                        AS metadata,
        fused.score
    FROM fused
    JOIN vecs.openclaw_docs doc ON doc.id = fused.id
    ORDER BY fused.score DESC;
$$;
