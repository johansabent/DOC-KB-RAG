import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.supabase import SupabaseVectorStore

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Security: Deny-list of dangerous root paths that should never be ingested.
DENIED_ROOTS = {Path(p).resolve() for p in ["/", "C:\\", "C:\\Windows", "C:\\Users"]}


def _validate_docs_path(raw_path: str | None) -> Path:
    """Validate DOCS_PATH to prevent path traversal or accidental system ingestion."""
    if not raw_path:
        raise SystemExit("Error: DOCS_PATH not set in .env")

    resolved = Path(raw_path).resolve()

    if not resolved.exists() or not resolved.is_dir():
        raise SystemExit(f"Error: DOCS_PATH '{resolved}' does not exist or is not a directory.")

    if resolved in DENIED_ROOTS:
        raise SystemExit(
            f"Error: DOCS_PATH '{resolved}' points to a sensitive system root. "
            "Please set DOCS_PATH to a specific documentation directory."
        )

    return resolved


def ingest():
    api_key = os.getenv("GOOGLE_API_KEY")
    db_connection = os.getenv("DB_CONNECTION_STRING")
    docs_path = _validate_docs_path(os.getenv("DOCS_PATH"))

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        log.error("GOOGLE_API_KEY not set in .env")
        return

    embed_model_name = os.getenv("EMBED_MODEL", "models/gemini-embedding-2-preview")
    dimensions = int(os.getenv("EMBED_DIMENSIONS", "3072"))
    collection_name = os.getenv("COLLECTION_NAME", "openclaw_docs")
    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "100"))
    chunk_size = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "64"))

    Settings.embed_batch_size = batch_size

    embed_model = GoogleGenAIEmbedding(
        model_name=embed_model_name,
        api_key=api_key,
        output_dimensionality=dimensions,
    )

    vector_store = SupabaseVectorStore(
        postgres_connection_string=db_connection,
        collection_name=collection_name,
        dimension=dimensions,
    )

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    log.info("Loading documents from %s ...", docs_path)
    reader = SimpleDirectoryReader(
        input_dir=str(docs_path),
        recursive=True,
        required_exts=[".md", ".mdx", ".json"],
    )
    documents = reader.load_data()
    log.info("Loaded %d document sections.", len(documents))

    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    log.info(
        "Generating embeddings using %s (chunk_size=%d, overlap=%d) ...",
        embed_model_name, chunk_size, chunk_overlap,
    )

    try:
        VectorStoreIndex.from_documents(
            documents,
            transformations=[splitter],
            storage_context=storage_context,
            embed_model=embed_model,
            show_progress=True,
        )
        log.info("Ingestion complete. Everything is indexed in Supabase.")
    except Exception as e:
        log.exception("Ingestion failed: %s", e)


if __name__ == "__main__":
    ingest()
