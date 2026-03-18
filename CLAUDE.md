# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DOC-KB-RAG is a Retrieval-Augmented Generation system. It ingests Markdown/JSON documentation into a Supabase pgvector store and answers questions about it using Google Gemini embeddings and LLM. The `docs/` corpus is fully interchangeable — the RAG engine makes no assumptions about the content.

## Working Directory

All commands run from `rag-agent/`. That directory owns the `.env`, `venv/`, and Supabase config. Never run `ingest.py` or `query.py` from the repo root.

## Commands

### Environment Setup
```bash
# Windows Git Bash (the active shell on this machine)
source venv/Scripts/activate

# Start local Supabase (requires Docker Desktop running)
npx supabase start

# Stop when done
npx supabase stop
```

### Running the Pipeline
```bash
# Ingest docs into vector store (re-run when corpus changes; SHA-256 dedup skips unchanged files)
python ingest.py

# Query the indexed docs
python query.py "Your question here"
```

### Verifying Changes
Before marking any feature complete, run a live query to confirm the pipeline is unbroken:
```bash
python query.py "What is X?"
```

### CI
The CI pipeline (`.github/workflows/ci.yml`) currently only runs a syntax check (`py_compile`) on `ingest.py` and `query.py` against Python 3.10 and 3.11. There are no automated tests yet.

### Helper Tools
```bash
python tools/list_models.py       # List available embedding models
python tools/list_llm_models.py   # List available LLM models
python tools/check_dim.py         # Check embedding dimensions
```

## Architecture

### Data Flow

**Ingest:**
`Docs (.md/.mdx/.json)` → `SimpleDirectoryReader` → `MarkdownNodeParser` (header-aware splits) → `SentenceSplitter` (512 tokens, 64 overlap) → `GoogleGenAIEmbedding` (3072 dims) → `SupabaseVectorStore` + `docstore.json` (SHA-256 dedup cache)

**Query:**
`Question` → `GoogleGenAIEmbedding` → `asyncpg` RPC `hybrid_search_rrf()` (dense cosine + BM25 full-text fused via RRF, top_k=5) → *(optional)* FlashRank cross-encoder reranking → `RAG_PROMPT_TEMPLATE` → `GoogleGenAI LLM` → Answer + source attribution with RRF scores (+ rerank scores when enabled)

### Key Files
- `rag-agent/ingest.py` — Full ingestion pipeline with path validation and dedup
- `rag-agent/query.py` — Query engine with prompt injection protection, optional FlashRank reranking, and source attribution
- `rag-agent/mcp_server.py` — MCP server (stdio transport) exposing `query_docs` tool
- `rag-agent/.env` — Secrets/config (gitignored; copy from `.env.example`)
- `rag-agent/migrations/001_hnsw_index.sql` — HNSW cosine index (m=16, ef_construction=64)
- `rag-agent/migrations/003_hybrid_search_rrf.sql` — DB-native hybrid search RPC (RRF fusion)
- `rag-agent/supabase/config.toml` — Local Supabase ports (DB: 54322, API: 54321, Studio: 54323)

### Configuration (`rag-agent/.env`)
| Variable | Default | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | — | Gemini API key (required) |
| `DB_CONNECTION_STRING` | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` | Supabase local DB |
| `DOCS_PATH` | — | Directory to ingest (validated against path-traversal list) |
| `EMBED_MODEL` | `models/gemini-embedding-2-preview` | Embedding model |
| `LLM_MODEL` | `models/gemini-3.1-flash-lite-preview` | Generation model |
| `EMBED_DIMENSIONS` | `3072` | Must match the embedding model output |
| `COLLECTION_NAME` | `openclaw_docs` | pgvector collection (`vecs.<name>`) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `512` / `64` | SentenceSplitter params |
| `SIMILARITY_TOP_K` | `5` | Number of results from hybrid search RPC |
| `RERANKER_ENABLED` | `false` | Enable FlashRank cross-encoder reranking |
| `RERANK_TOP_N` | `5` | Number of results to keep after reranking |
| `RERANKER_MODEL` | `ms-marco-MiniLM-L-12-v2` | FlashRank model name |

## Development Rules

- **Scope:** Work is confined to `ingest.py`, `query.py`, the Supabase integration, and Gemini configuration. Do not build tangential functionality outside RAG scope unless explicitly asked.
- **Modularity:** Keep the vector DB layer and LLM layer loosely coupled and pluggable even as you add features.
- **Virtual environment:** All Python execution must use `rag-agent/venv`. Never install global pip packages.
- **Docker required:** Supabase (`npx supabase ...`) requires Docker Desktop to be running.
- **No destructive migrations:** Never drop or permanently alter the vector DB schema without explicit user approval.
- **Secrets:** Never log, print, or commit `GOOGLE_API_KEY` or `DB_CONNECTION_STRING`.
- **README as source of truth:** If a script argument changes in a breaking way, update `README.md` immediately.

## Roadmap Context

- **Phase 1** (done): Foundation — MarkdownNodeParser chunking, top-k tuning, source attribution, config centralization
- **Phase 2** (done): Incremental ingestion — `IngestionPipeline` + SHA-256 dedup via `docstore.json`
- **Phase 3** (done): Hybrid search — BM25 + dense vector RRF via Postgres RPC (`hybrid_search_rrf`)
- **Phase 4** (done): MCP server + FlashRank reranking + mimalloc allocator (WSL2 deployment)

## Agent Framework

`.agent/` contains 8 specialist agent personas, 11 skills, and 14 workflow slash commands for coordinating multi-agent development. See `.agent/ARCHITECTURE.md` for the coordination model. Workflows include `/orchestrate`, `/plan`, `/debug`, `/test`, `/refactor`, `/create-pr`, and others.
