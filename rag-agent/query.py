import os
import argparse
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.supabase import SupabaseVectorStore

load_dotenv()

def query(question):
    api_key = os.getenv("GOOGLE_API_KEY")
    db_connection = os.getenv("DB_CONNECTION_STRING")

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("Error: GOOGLE_API_KEY not set in .env")
        return

    # Configuration matches ingestion
    EMBED_MODEL_NAME = "models/gemini-embedding-2-preview"
    DIMENSIONS = 3072

    # Initialize Gemini LLM and Embedding Model
    llm = GoogleGenAI(api_key=api_key, model="models/gemini-3.1-flash-lite-preview")
    embed_model = GoogleGenAIEmbedding(
        model_name=EMBED_MODEL_NAME, 
        api_key=api_key,
        output_dimensionality=DIMENSIONS
    )
    
    # Initialize Vector Store
    vector_store = SupabaseVectorStore(
        postgres_connection_string=db_connection,
        collection_name="openclaw_docs",
        dimension=DIMENSIONS,
    )
    
    # Load the index from the vector store
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model,
    )
    
    # Query the index
    query_engine = index.as_query_engine(llm=llm)
    print(f"\nQuestion: {question}")
    print("Searching high-resolution vector space...")
    response = query_engine.query(question)
    
    print("\nAnswer:")
    print(response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the Openclaw Gateway RAG system.")
    parser.add_argument("question", type=str, help="The question you want to ask the docs.")
    args = parser.parse_args()
    
    query(args.question)
