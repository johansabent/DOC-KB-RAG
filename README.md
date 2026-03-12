# Openclaw RAG System - Usage Guide

This system allows you to perform Retrieval-Augmented Generation (RAG) queries against the Openclaw Gateway documentation using Google Gemini and a local Supabase vector database.

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Docker Desktop** (Must be running)
- **Node.js** (For Supabase CLI)

### 2. Activate the Environment
Open a terminal in `C:\Users\johan\Openclaw Gateway\rag-agent` and run:
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Ensure the Database is Running
The system uses a local Supabase instance. If it's not running, start it:
```powershell
npx supabase start
```

---

## 🔍 How to Query
To ask a question about the Openclaw Gateway documentation, use the `query.py` script:

```powershell
python query.py "What is the command to onboard a new user?"
```

The script will:
1. Search the local Supabase DB for relevant context.
2. Send that context to Gemini 3.1 Flash Lite Preview.
3. Provide a synthesized answer based on your files.

---

## 📥 How to Ingest (Update Data)
If you add new Markdown or JSON files to the `Openclaw Gateway` folder, you need to re-index them:

```powershell
python ingest.py
```
*Note: This script uses the `gemini-embedding-2-preview` model with 3,072 dimensions for high accuracy.*

---

## ⚙️ Configuration
The configuration is stored in the `.env` file:
- `GOOGLE_API_KEY`: Your Gemini API key.
- `DB_CONNECTION_STRING`: Local Postgres URI.
- `DOCS_PATH`: The source folder for your documentation.

---

## 🛠️ Maintenance & Troubleshooting

### Stopping the Database
To save system resources when not using the RAG agent:
```powershell
npx supabase stop
```

### Resetting the Database
If you ever want to wipe the index and start fresh:
1. Stop Supabase: `npx supabase stop`
2. Start Supabase: `npx supabase start`
3. Run ingestion: `python ingest.py`

### Common Errors
- **403 Forbidden**: Ensure the "Generative Language API" is enabled in your Google Cloud Project.
- **Docker Connection Error**: Ensure Docker Desktop is running and you are in the correct context (`docker context use default`).
