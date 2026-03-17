# DOC-KB-RAG

Retrieval-Augmented Generation for interchangeable documentation sets. This
repository keeps the RAG application, the local Supabase setup, and a sample
documentation corpus in one place.

## What Lives Here

- `rag-agent/` contains the runnable RAG app.
- `docs/` is the documentation corpus currently being indexed.
- `.agent/` provides agent personas, skills, and workflows for coordinating
  multi-agent development work. See `.agent/ARCHITECTURE.md`.
- Root-level files such as `AGENTS.md`, `GEMINI.md`, and `CHANGELOG.md` are
  project guidance and imported reference material.

## Structure Map

```text
DOC-KB-RAG/
|-- .agent/                  # Agent coordination framework (see ARCHITECTURE.md)
|-- AGENTS.md                # Local agent instructions for this repo
|-- CHANGELOG.md             # Imported/source project changelog
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

### 2. Activate the virtual environment

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

### 3. Start local Supabase

```bash
npx supabase start
```

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

## Notes

- Keep `ingest.py` and `query.py` at the top of `rag-agent/`; CI and local
  usage depend on those entrypoints.
- Avoid moving `rag-agent/venv/` or `rag-agent/supabase/` unless you are also
  rebuilding the environment and command assumptions around them.
