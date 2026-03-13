# Agent Guidelines for DOC-KB-RAG

## Repository Focus
This repository contains a RAG (Retrieval-Augmented Generation) agent that reads Markdown/JSON manuals and provides AI-powered answers. The documentation it reads is completely **interchangeable**. 

As an AI Agent working entirely within this codebase, you must adhere strictly to the following rules:

## General Rules
1. **Scope:** Your primary scope is the Python RAG implementation (`ingest.py` and `query.py`), the local Supabase integration, and the Gemini configuration. Do not build tangential functionality outside the RAG scope unless explicitly told.
2. **Modularity:** The scripts default to Gemini and Supabase, but architect any new changes so the data layer (Vector DB) and reasoning layer (LLM) remain loosely coupled and pluggable.

## CLI and Execution
1. **Virtual Environment First:** All Python scripts must execute within the `venv`. Never install global pip packages. 
2. **Docker Dependency:** Before executing any Supabase node scripts (`npx supabase...`), verify that Docker Desktop is running, as it is a strict dependency for the local Postgres Vector instance.
3. **Execution Verification:** Before proposing that a feature is complete, use the `run_command` tools to verify your changes by literally running `python query.py "<Test Question>"` to ensure the RAG pipeline is unbroken.

## Safety & Boundaries
1. **No Destructive Migrations:** Never delete, drop, or permanently alter the Vector Database schemas using Supabase commands or raw SQL without explicit, confirming approval from the user.
2. **Git Hygiene:** Suggest clear, concise Git commits, but do not automatically push, force-push, rebase, or delete branches without asking.
3. **Secret Management:** Never log, print, or commit `GOOGLE_API_KEY` or `DB_CONNECTION_STRING` anywhere. 

## Documentation
1. Keep the `README.md` as the definitive source of truth for onboarding users. If you change a fundamentally required script argument, update the README immediately.
2. Treat `DOCS_PATH` as an agnostic source. The user can inject *any* repository's documentation into this engine. Ensure your code does not blindly assume content layout or structure.
