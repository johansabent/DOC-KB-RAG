# Database Migrations

Run these SQL files **in order** against your Supabase database
(SQL Editor or `psql`). Each file is idempotent (safe to re-run).

| File | Purpose |
|---|---|
| `001_hnsw_index.sql` | HNSW cosine distance index on `vecs.openclaw_docs.vec` |
| `002_pg_trgm.sql` | Enable `pg_trgm` extension for trigram text search |
| `003_hybrid_search_rrf.sql` | `hybrid_search_rrf()` RPC — fuses vector + full-text via RRF |

## Running via psql

```bash
# From rag-agent/ with local Supabase running:
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -f migrations/001_hnsw_index.sql \
  -f migrations/002_pg_trgm.sql \
  -f migrations/003_hybrid_search_rrf.sql
```

## Notes

- Migrations target the default collection `openclaw_docs`. If you use a
  different `COLLECTION_NAME`, update the table references in each file.
- None of these migrations are destructive — they only add indexes,
  extensions, and functions.
