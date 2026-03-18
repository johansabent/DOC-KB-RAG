# DOC-KB-RAG

Retrieval-Augmented Generation for interchangeable documentation sets. This
repository keeps the RAG application, the local Supabase setup, and a sample
documentation corpus in one place.

## What Lives Here

- `rag-agent/` contains the runnable RAG app.
- `docs/` is the documentation corpus currently being indexed.
- `.agent/` provides agent personas, skills, and workflows for coordinating
  multi-agent development work. See `.agent/ARCHITECTURE.md`.
- Root-level files such as `AGENTS.md` and `GEMINI.md` are project guidance.

## Structure Map

```text
DOC-KB-RAG/
|-- .agent/                  # Agent coordination framework (see ARCHITECTURE.md)
|-- AGENTS.md                # Local agent instructions for this repo
|-- GEMINI.md                # Gemini-specific project context
|-- LICENSE
|-- README.md
|-- docs/                    # Documentation corpus to ingest (replaceable)
|   |-- index.md
|   |-- start/
|   |-- concepts/
|   |-- tools/
|   |-- providers/
|   `-- ...many topic folders
`-- rag-agent/               # RAG application workspace
    |-- .env                 # Local secrets/config (gitignored)
    |-- ingest.py            # Ingest docs into the vector store
    |-- query.py             # Query the indexed docs
    |-- mcp_server.py        # MCP server (stdio transport)
    |-- tools/               # One-off helper scripts
    |   |-- README.md
    |   |-- check_dim.py
    |   |-- list_llm_models.py
    |   `-- list_models.py
    |-- supabase/            # Local Supabase project files
    |-- venv/                # Python virtual environment
    |-- package.json         # Supabase CLI dependency
    `-- package-lock.json
```

## Working Directory Rules

Run the Python and Supabase commands from `rag-agent/`. That directory is the
application root and contains the local `.env`, `venv`, and Supabase config.

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Docker Desktop running
- Node.js

### 2. Install Python dependencies

From `rag-agent/`:

```bash
pip install -r requirements.txt
```

### 3. Activate the virtual environment

From `rag-agent/`:

**On Linux/macOS:**

```bash
source venv/bin/activate
```

**On Windows (Git Bash):**

```bash
source venv/Scripts/activate
```

**On Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Start local Supabase

```bash
npx supabase start
```

### 5. Run database migrations

After the first ingestion, run the SQL migrations once:

```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -f migrations/001_hnsw_index.sql \
  -f migrations/002_pg_trgm.sql \
  -f migrations/003_hybrid_search_rrf.sql
```

See `migrations/README.md` for details.

## Configuration

Set these values in `rag-agent/.env`:

- `GOOGLE_API_KEY`: Gemini API key
- `DB_CONNECTION_STRING`: local Postgres connection string
- `DOCS_PATH`: directory to ingest

`DOCS_PATH` is intentionally agnostic. It can point to this repository's
`docs/` folder or to any other Markdown/JSON documentation source.

## Main Commands

From `rag-agent/`:

Ingest the configured documentation set:

```bash
python ingest.py
```

Query the indexed documentation:

```bash
python query.py "What is the command to onboard a new user?"
```

Optional helper scripts:

```bash
python tools/list_models.py
python tools/list_llm_models.py
python tools/check_dim.py
```

## Maintenance

Stop Supabase when you are done:

```bash
npx supabase stop
```

If the corpus changes, rerun:

```bash
python ingest.py
```

## Reranking

FlashRank cross-encoder reranking can optionally re-score the hybrid search
results for better precision. Enable it by setting these env vars in `.env`:

```env
RERANKER_ENABLED=true
RERANK_TOP_N=5
RERANKER_MODEL=ms-marco-MiniLM-L-12-v2
SIMILARITY_TOP_K=20          # over-fetch so the reranker has candidates to prune
```

The reranker model (~34 MB) is downloaded automatically on first use.

When reranking is active, source attribution shows both RRF and rerank scores.

## MCP Server

`mcp_server.py` exposes the RAG pipeline as a single `query_docs` tool over
MCP stdio transport, so external agents (Claude Desktop, VS Code, etc.) can
query the knowledge base.

Start it manually:

```bash
cd rag-agent
python mcp_server.py
```

### Claude Desktop / VS Code configuration

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "doc-kb-rag": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/DOC-KB-RAG/rag-agent"
    }
  }
}
```

On WSL2, use the full path to the Python binary inside the virtual environment:

```json
{
  "mcpServers": {
    "doc-kb-rag": {
      "command": "/path/to/DOC-KB-RAG/rag-agent/venv/bin/python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/DOC-KB-RAG/rag-agent"
    }
  }
}
```

## WSL2 Deployment with mimalloc

On WSL2 (Ubuntu), using mimalloc as the system allocator can reduce memory
fragmentation for long-running processes like the MCP server.

Install:

```bash
sudo apt install libmimalloc2.0
```

Run the MCP server with mimalloc:

```bash
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libmimalloc.so.2.0 python mcp_server.py
```

For MCP client configs on WSL2, set the env var in the config:

```json
{
  "mcpServers": {
    "doc-kb-rag": {
      "command": "/path/to/DOC-KB-RAG/rag-agent/venv/bin/python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/DOC-KB-RAG/rag-agent",
      "env": {
        "LD_PRELOAD": "/usr/lib/x86_64-linux-gnu/libmimalloc.so.2.0"
      }
    }
  }
}
```

## Notes

- Keep `ingest.py` and `query.py` at the top of `rag-agent/`; CI and local
  usage depend on those entrypoints.
- Avoid moving `rag-agent/venv/` or `rag-agent/supabase/` unless you are also
  rebuilding the environment and command assumptions around them.

## Known Limitations (v0.1.0-beta)

- CI runs syntax checks only (`py_compile`) — no automated test suite yet.
- The collection name `openclaw_docs` is hardcoded in the SQL migrations; update
  manually if you change `COLLECTION_NAME`.
- `hybrid_search_rrf()` computes `tsvector` on-the-fly; no stored/indexed
  tsvector column (planned optimisation).
