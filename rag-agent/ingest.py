import os
import time
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.supabase import SupabaseVectorStore
import logging
import sys

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

load_dotenv()

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
        print("Error: GOOGLE_API_KEY not set in .env")
        return

    # Use the cutting-edge 2-preview model
    EMBED_MODEL_NAME = "models/gemini-embedding-2-preview"
    DIMENSIONS = 3072

    # Global settings for performance (Paid Tier)
    Settings.embed_batch_size = 100 # Batching is much faster
    
    # Initialize Google GenAI Embedding Model
    embed_model = GoogleGenAIEmbedding(
        model_name=EMBED_MODEL_NAME, 
        api_key=api_key,
        output_dimensionality=DIMENSIONS
    )
    
    # Initialize Vector Store with high-res dimensions
    vector_store = SupabaseVectorStore(
        postgres_connection_string=db_connection,
        collection_name="openclaw_docs",
        dimension=DIMENSIONS,
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Load Documents
    print(f"Loading documents from {docs_path}...")
    reader = SimpleDirectoryReader(
        input_dir=str(docs_path),
        recursive=True,
        required_exts=[".md", ".json"],
    )
    documents = reader.load_data()
    print(f"Loaded {len(documents)} document sections.")
    
    # Create Index (Automatic chunking and embedding)
    print(f"Generating embeddings using {EMBED_MODEL_NAME}...")
    print("This will be fast since you are on the paid tier!")
    
    try:
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=embed_model,
            show_progress=True
        )
        print("\n✅ Ingestion complete! Everything is indexed in Supabase.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    ingest()
