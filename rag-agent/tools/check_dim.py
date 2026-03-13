import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = 'models/gemini-embedding-001'
result = genai.embed_content(
    model=model,
    content="Hello world",
    task_type="retrieval_document"
)
print(f"Dimension for {model}: {len(result['embedding'])}")

model2 = 'models/text-embedding-004'
try:
    result2 = genai.embed_content(
        model=model2,
        content="Hello world",
        task_type="retrieval_document"
    )
    print(f"Dimension for {model2}: {len(result2['embedding'])}")
except Exception as e:
    print(f"Could not get dimension for {model2}: {e}")
