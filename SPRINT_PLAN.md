# RAG MCP Server — Implementation Phases

**Status:** Planned · **Updated:** 2026-03-17
**Deployment target:** WSL2 (Ubuntu) — same environment as Openclaw
**Branch strategy:** Each phase = one feature branch → one PR → merge to `main`

---

## Architecture (Target State)

```text
User / Openclaw Agent
        │
        ▼
  MCP Server  (FastMCP, async Python, WSL2)
  LD_PRELOAD=libmimalloc  ← Mandate 3, active from Phase 4
        │
        ├─► Ingest tool
        │     IngestionPipeline
        │       MarkdownNodeParser → SHA-256 hash → SentenceSplitter(512,64)
        │       → embed (Gemini) → Supabase      ← Mandate 4
        │
        └─► Query tool
              embed(query) via Gemini
                    │
                    ▼
              Supabase RPC: hybrid_search_rrf()   ← Mandate 1
              (dense + BM25 fused IN-DB, only top-K crosses network)
                    │
                    ▼
              FlashRank (local CPU reranker, <200ms)  ← Mandate 2
                    │
                    ▼
              Gemini LLM → answer + source citations
```

---

## Resolved Decisions

| Decision | Resolution |
| --- | --- |
| Deployment | WSL2 — co-located with Openclaw. Consequence: Mandate 3 active day one. |
| Hybrid search | DB-native RPC only, no Python-side `QueryFusionRetriever`. |
| Reranker | FlashRank local (CPU). Cohere deferred — network latency unacceptable. |
| Docstore | `docstore.json` gitignored — it is a local build cache, not source. |
| vecs schema | Verify `vecs.openclaw_docs` column names in Phase 3 before writing RPC SQL. |

---

## Phase 1 — Foundation & Quick Wins

**Branch:** `feat/phase1-foundation`
**PR title:** `feat: foundation fixes — chunking, top-k, attribution, config`
**Goal:** Fix every issue that can be resolved with surgical edits to the existing files.
No new architecture. Each change is independently testable.

### Phase 1 Tasks

#### 1.1 · Fix SentenceSplitter (currently imported but unused)

- File: `rag-agent/ingest.py`
- Wire `SentenceSplitter(chunk_size=512, chunk_overlap=64)` into `VectorStoreIndex.from_documents()` via `transformations=[splitter]`

#### 1.2 · Raise `similarity_top_k` to 5

- File: `rag-agent/query.py`
- Default is 2, which misses chunks ranked 3rd–5th in a 967-chunk corpus

#### 1.3 · Add source attribution to query output

- File: `rag-agent/query.py`
- Print `response.source_nodes` with score + `file_name` metadata after every answer

#### 1.4 · Centralise all hardcoded config into `.env`

- Files: `rag-agent/ingest.py`, `rag-agent/query.py`
- Move to `.env`: `EMBED_MODEL`, `LLM_MODEL`, `EMBED_DIMENSIONS`, `COLLECTION_NAME`, `EMBED_BATCH_SIZE`, `SIMILARITY_TOP_K`
- Update `rag-agent/.env.example` (public template, no secrets)

#### 1.5 · Add `.mdx` to ingestion file extensions

- File: `rag-agent/ingest.py`
- Adds `install/northflank.mdx`, `install/railway.mdx`, `install/render.mdx` to the corpus

#### 1.6 · Add `SimilarityPostprocessor` cutoff (0.65)

- File: `rag-agent/query.py`
- Prevents the LLM from being called when no chunk clears the relevance bar

#### 1.7 · Add structured logging (replace `print`)

- Files: `rag-agent/ingest.py`, `rag-agent/query.py`
- Use `logging` module; level controlled by `LOG_LEVEL` env var

#### 1.8 · Create HNSW index SQL migration

- New file: `rag-agent/migrations/001_hnsw_index.sql`
- Contains the `CREATE INDEX … USING hnsw` statement to be run once in Supabase
- Documents how to run it in the README

### Phase 1 Acceptance Criteria

- [ ] `python ingest.py` shows correct chunk count with 512-token splitter
- [ ] `python query.py "..."` prints answer + source file names + scores
- [ ] Re-running `ingest.py` on unchanged docs produces identical chunk count
- [ ] `LOG_LEVEL=DEBUG python query.py "..."` shows verbose debug lines
- [ ] No hardcoded strings remain in `.py` files (only env var reads)

---

## Phase 2 — Incremental Ingestion (Mandate 4)

**Branch:** `feat/phase2-incremental-ingestion`
**PR title:** `feat(ingest): IngestionPipeline with MarkdownNodeParser + SHA-256 dedup`
**Depends on:** Phase 1 merged
**Goal:** Replace `VectorStoreIndex.from_documents()` with a proper `IngestionPipeline`
that skips unchanged nodes. A header rename alone must invalidate the hash.

### Phase 2 Tasks

#### 2.1 · Replace ingest pipeline core

- File: `rag-agent/ingest.py`
- Replace `VectorStoreIndex.from_documents()` with `IngestionPipeline`:

```python
IngestionPipeline(
    transformations=[MarkdownNodeParser(), SentenceSplitter(512, 64), embed_model],
    vector_store=vector_store,
    docstore=SimpleDocumentStore(),
    docstore_strategy="upserts_and_delete",
)
```

#### 2.2 · Persist docstore between runs

- New file: `rag-agent/docstore.json` (gitignored — add to `.gitignore`)
- Load from disk if exists; create fresh if not
- Persist after each successful run

#### 2.3 · Validate hash divergence

- Manual test: change a heading in one `.md` file, re-run ingest
- Confirm only that one file's nodes are re-embedded, not the full corpus

#### 2.4 · Update `.gitignore`

- Add `rag-agent/docstore.json` and `rag-agent/models/` (FlashRank model cache, pre-empting Phase 4)

### Phase 2 Acceptance Criteria

- [ ] First run: all nodes embedded (baseline)
- [ ] Second run (no changes): `0 new/changed nodes` printed
- [ ] After header rename: only changed file's nodes re-embedded
- [ ] `docstore.json` absent from `git status`

---

## Phase 3 — DB-Native Hybrid Search (Mandate 1)

**Branch:** `feat/phase3-hybrid-search-rrf`
**PR title:** `feat(retrieval): DB-native RRF via Supabase RPC, drop Python-side fusion`
**Depends on:** Phase 2 merged
**Goal:** Implement the `hybrid_search_rrf()` Postgres RPC. All BM25 + dense fusion
happens inside the DB. Only the final top-K rows cross the network.

### Phase 3 Tasks

#### 3.1 · Verify Supabase schema

- Before writing SQL: confirm `vecs.openclaw_docs` column names
- Expected: `id`, `vec` (vector), `metadata` (jsonb)
- Confirm whether `content`/`text` is a column or stored inside `metadata`
- Adjust RPC SQL accordingly

#### 3.2 · Create SQL migrations

- New file: `rag-agent/migrations/002_pg_trgm.sql` — `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
- New file: `rag-agent/migrations/003_hybrid_search_rrf.sql` — full RPC function
- Document run order in `rag-agent/migrations/README.md`

#### 3.3 · Replace LlamaIndex retriever with direct asyncpg RPC call

- File: `rag-agent/query.py`
- Add `asyncpg` connection pool (initialised once at startup)
- Replace `index.as_query_engine()` with direct `hybrid_search_rrf()` call
- Pass query embedding (from Gemini) + raw query text to the RPC

#### 3.4 · Build context from RPC results and call LLM directly

- Construct context string from returned rows
- Call Gemini LLM with existing `RAG_PROMPT_TEMPLATE`
- Re-attach source attribution from `metadata` JSONB field

#### 3.5 · Update `requirements.txt`

- Add `asyncpg>=0.29.0`

### Phase 3 Acceptance Criteria

- [ ] Query returns answer with sources, no LlamaIndex retriever in the call path
- [ ] No `UserWarning` about missing covering index (HNSW from Phase 1 covers this)
- [ ] Query for a keyword-exact term returns better results than Phase 2 baseline
- [ ] `asyncpg` pool reused across multiple queries in the same process

---

## Phase 4 — FlashRank + MCP Server (Mandates 2 & 3)

**Branch:** `feat/phase4-mcp-server`
**PR title:** `feat: FastMCP server with FlashRank reranking and mimalloc allocator`
**Depends on:** Phase 3 merged
**Goal:** Expose the full query pipeline as a persistent MCP tool. Apply mimalloc
allocator override. This is the final production-ready state.

### Phase 4 Tasks

#### 4.1 · Add FlashRank reranking step

- File: `rag-agent/query.py` (then moved to `rag_server.py`)
- Initialise `Ranker` once at startup (model: `ms-marco-MiniLM-L-12-v2`, cache: `./models/`)
- After RPC returns `k=20` candidates, rerank locally → take top 5

#### 4.2 · Create `rag_server.py` — FastMCP persistent server

- New file: `rag-agent/rag_server.py`
- Two MCP tools:
  - `search_docs(question: str) -> str` — full query pipeline (embed → RPC → rerank → LLM)
  - `ingest_docs() -> str` — trigger a fresh ingestion run
- Shared state initialised once at startup: asyncpg pool, embed model, LLM client, FlashRank ranker

#### 4.3 · mimalloc startup script (Mandate 3)

- New file: `rag-agent/start_server.sh`

```bash
#!/usr/bin/env bash
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libmimalloc.so.2 python rag_server.py
```

- New file: `rag-agent/setup_wsl.md` — one-time WSL2 setup instructions:
  - `sudo apt-get install -y libmimalloc2.0`
  - Verify `.so` path with `dpkg -L libmimalloc2.0 | grep .so`

#### 4.4 · Update `requirements.txt`

- Add: `flashrank>=0.2.9`, `mcp[cli]>=1.0.0`

#### 4.5 · Wire MCP server into Openclaw agent config

- Point Openclaw's MCP config at the new `rag_server.py` (via `start_server.sh`)
- Document in `rag-agent/README.md`

### Phase 4 Acceptance Criteria

- [ ] `bash start_server.sh` launches without errors on WSL2
- [ ] Openclaw agent can call `search_docs` as an MCP tool
- [ ] Query latency: embed + RPC + rerank + LLM < 3s on WSL2
- [ ] FlashRank rerank step completes in < 200ms (log it)
- [ ] RSS memory stable after 50+ consecutive queries (no linear growth)
- [ ] `ingest_docs` tool triggers incremental ingest and returns changed node count

---

## Phase Summary

| Phase | Branch | Key files changed | Complexity |
| --- | --- | --- | --- |
| 1 — Foundation | `feat/phase1-foundation` | `ingest.py`, `query.py`, `.env`, `migrations/001` | Low |
| 2 — Incremental ingest | `feat/phase2-incremental-ingestion` | `ingest.py`, `.gitignore` | Medium |
| 3 — Hybrid search RRF | `feat/phase3-hybrid-search-rrf` | `query.py`, `migrations/002+003` | High |
| 4 — MCP server | `feat/phase4-mcp-server` | new `rag_server.py`, `start_server.sh`, `setup_wsl.md` | High |

---

## Dependencies (install before each phase)

```bash
# Phase 1 — no new deps

# Phase 3
pip install asyncpg>=0.29.0

# Phase 4
pip install flashrank>=0.2.9 mcp[cli]>=1.0.0

# Phase 4 — WSL2 one-time system package (Mandate 3)
sudo apt-get install -y libmimalloc2.0
```

---

## What Is NOT Changing

- Gemini embedding model (`models/gemini-embedding-2-preview`, 3072 dims)
- Gemini LLM (`models/gemini-3.1-flash-lite-preview`)
- Supabase as the vector store
- Prompt injection defence template in `query.py` — preserved in all phases
- `docs/` directory and document corpus — read-only, untouched
