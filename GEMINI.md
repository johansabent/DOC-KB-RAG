# DOC-KB-RAG System Context for Gemini

Welcome to **DOC-KB-RAG**. This repository houses a standalone application designed to perform Retrieval-Augmented Generation (RAG) against a changeable set of documentation.

## Core Purpose

- To ingest arbitrary documentation (like Markdown and JSON files) into a localized high-performance vector database.
- To serve a query interface powered by Google Gemini, giving accurate, synthesized answers based purely on the local documentation context.

## Tech Stack Overview

- **Language:** Python 3.10+
- **Database:** Local Supabase (Vector Database) via `npx supabase`
- **AI Framework:** LlamaIndex
- **LLM/Embeddings:** 
  - Embeddings: `gemini-embedding-2-preview` (3072 dims)
  - LLM: `gemini-3.1-flash-lite-preview`

## Operation Guidelines for Gemini

1. **Environment Awareness:** The Python environment operates within the `rag-agent` directory. If dependencies are required, always make sure you are executing inside the `venv` virtual environment. For Windows PowerShell, this is `.\venv\Scripts\Activate.ps1`.
2. **Database Start/Stop:** When required to execute database operations or queries, ensure the Docker instance is active and use `npx supabase start`. To conserve resources, cleanly exit with `npx supabase stop`.
3. **Docs Directory:** The document root is defined by the `DOCS_PATH` in the `.env` file. These documents are interchangeable. Do not assume they belong to OpenClaw. Treat the content agnostically.
4. **Ingestion Execution:** When new documents are added or existing ones modified, run `python ingest.py` to recreate the vector index.
5. **No Destructive Database Commands:** Avoid running SQL or Supabase CLI commands that drop data, tables, or projects outside of the intended RAG schema workflow unless the user provides explicit verbal clearance.
6. **Focus Scope:** Despite the path name possibly resembling `OpenClaw Gateway`, the core focus of this repository is now strictly the `DOC-KB-RAG` pipeline. Abstract away original application specifics.
