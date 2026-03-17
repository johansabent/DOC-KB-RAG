# RAG System Improvement Report
**Project:** DOC-KB-RAG · **Date:** 2026-03-17 · **Audited by:** Claude Code

---

## Executive Summary

The current RAG system works but is in a "prototype" state. It successfully ingests docs
and returns grounded answers, but has several critical gaps that hurt reliability, retrieval
quality, and usability before it can be considered production-ready.

**DOCS_PATH bug fixed during this session** — was pointing to a non-existent path
(`C:/Users/johan/Openclaw Gateway/`). Updated to the actual docs folder.

---

## 1. Issues Found (Ranked by Severity)

### 🔴 CRITICAL

#### C1 — Missing pgvector cosine distance index
Every query prints:
```
UserWarning: Query does not have a covering index for IndexMeasure.cosine_distance.
```
This means Supabase is doing a **full table scan** on every query instead of using an
ANN (Approximate Nearest Neighbor) index. At 967 chunks this is tolerable, but it will
degrade sharply as the corpus grows.

**Fix:** Create an HNSW index on the vector column after ingestion.
```sql
-- Run once in Supabase SQL editor or add to ingest.py post-ingestion
CREATE INDEX ON vecs.openclaw_docs
USING hnsw (vec vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
HNSW is preferred over IVFFlat because it can be built on an empty table and updates
automatically as new data is added.

---

### 🟠 HIGH

#### H1 — Index reloaded on every single query
In `query.py`, `VectorStoreIndex.from_vector_store()` is called fresh on **every** query.
This adds ~500ms–2s of cold-start overhead and wastes API calls.

**Fix:** Wrap the query system in a persistent server/daemon (FastAPI, Flask, or a simple
REPL loop) that keeps the index and LLM clients in memory between calls.

#### H2 — No source attribution in answers
Answers contain no reference to which document was retrieved. Users cannot verify the
answer or navigate to the source file. This is a critical usability gap for a doc assistant.

**Fix:** Use `response.source_nodes` in LlamaIndex to append citations:
```python
response = query_engine.query(question)
print(response)
print("\nSources:")
for node in response.source_nodes:
    print(f"  - {node.metadata.get('file_name', 'unknown')} (score: {node.score:.3f})")
```
But this also requires preserving `file_name` metadata during ingestion (see H3).

#### H3 — No metadata preserved during ingestion
`ingest.py` uses `SimpleDirectoryReader` but doesn't store source file paths in document
metadata. Without this, retrieved chunks have no traceable origin.

**Fix:** LlamaIndex's `SimpleDirectoryReader` automatically fills `file_name`,
`file_path`, and `creation_date` in `doc.metadata` — but the metadata must flow through
to the vector store. Verify this is happening by inspecting a stored node's metadata.

#### H4 — SentenceSplitter imported but never configured
In `ingest.py`, `SentenceSplitter` is imported but never used. LlamaIndex falls back to
its global default chunker, which is not tuned for this corpus.

**Fix:** Explicitly configure the splitter:
```python
from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
index = VectorStoreIndex.from_documents(
    documents,
    transformations=[splitter],
    storage_context=storage_context,
    embed_model=embed_model,
    show_progress=True,
)
```
Research (Feb 2026 benchmark) shows 512-token chunks with 10–20% overlap outperform
other strategies at 69% accuracy vs 54% for pure semantic chunking.

---

### 🟡 MEDIUM

#### M1 — No hybrid search (dense + BM25)
The system uses only dense vector similarity. Hybrid search combining vector similarity
with BM25 keyword matching improves MRR by ~9.3 percentage points (56.72% → 66.43%)
according to current benchmarks.

**Recommended approach:** Supabase supports full-text search natively via `tsvector`.
LlamaIndex has a `QueryFusionRetriever` that can merge dense and BM25 results using
Reciprocal Rank Fusion (RRF).

#### M2 — No reranking stage
After retrieval, results are passed directly to the LLM without a reranking pass.
A cross-encoder reranker (e.g. `FlashRankRerank`, `CohereRerank`, or a local model)
can improve retrieval quality by up to 48%.

**Recommended approach:** Add a reranker as a post-processor:
```python
from llama_index.core.postprocessor import SimilarityPostprocessor

query_engine = index.as_query_engine(
    llm=llm,
    node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)],
)
```
For production: use `FlashRankRerank` (free, local) or `CohereRerank` (API, best quality).

#### M3 — No incremental ingestion
Every run of `ingest.py` re-embeds all 353 documents from scratch. This wastes ~2 minutes
and Gemini API quota on unchanged files.

**Fix:** Track a checksum (MD5/SHA256) of each file before ingesting. Skip files whose
checksum hasn't changed since the last run.

#### M4 — `similarity_top_k` not configured
`query.py` uses LlamaIndex's default of `similarity_top_k=2`. For a 967-chunk corpus this
is very low — the system may miss relevant content that ranks 3rd or 4th.

**Fix:**
```python
query_engine = index.as_query_engine(
    llm=llm,
    similarity_top_k=5,  # retrieve more candidates
    text_qa_template=RAG_PROMPT_TEMPLATE,
)
```

#### M5 — All config hardcoded in Python files
Model names, dimensions, collection name, batch size, and doc extensions are all
hardcoded. These should be in `.env` so they can be changed without touching code.

**Variables to move to `.env`:**
```
EMBED_MODEL=models/gemini-embedding-2-preview
LLM_MODEL=models/gemini-3.1-flash-lite-preview
EMBED_DIMENSIONS=3072
COLLECTION_NAME=openclaw_docs
EMBED_BATCH_SIZE=100
SIMILARITY_TOP_K=5
```

#### M6 — No error handling in query.py
The entire query pipeline has no try/except. A network error, API quota exceeded, or
DB timeout will crash with an unformatted stack trace.

---

### 🔵 LOW / FUTURE

#### L1 — No query caching
Repeated identical questions hit the embedding API and LLM every time. A simple
`functools.lru_cache` or Redis cache on the query function would eliminate redundant costs.

#### L2 — No similarity score threshold
The system returns an answer even if the best matching chunk has very low cosine similarity
(i.e. the question is about something not in the docs at all). The `SimilarityPostprocessor`
with a cutoff (e.g. 0.65) would filter out these low-confidence retrievals and trigger the
"not found" fallback.

#### L3 — MDX files not indexed
3 files (`install/northflank.mdx`, `install/railway.mdx`, `install/render.mdx`) are skipped
because `ingest.py` only accepts `.md` and `.json`. Add `.mdx` to `required_exts`.

#### L4 — No structured logging
`print()` statements throughout. Replace with Python's `logging` module so log level can
be controlled via env var (`LOG_LEVEL=DEBUG`).

---

## 2. Improvement Plan (Prioritized)

| # | Task | Impact | Effort | When |
|---|------|--------|--------|------|
| 1 | Create HNSW cosine index in Supabase | Perf | 15 min | Now |
| 2 | Add `similarity_top_k=5` to query engine | Quality | 5 min | Now |
| 3 | Configure `SentenceSplitter(512, 64)` in ingest | Quality | 10 min | Now |
| 4 | Add source attribution to query output | UX | 20 min | Now |
| 5 | Move all hardcoded config to `.env` | Maintainability | 30 min | Soon |
| 6 | Add `SimilarityPostprocessor` score cutoff | Quality | 10 min | Soon |
| 7 | Add try/except + structured logging | Reliability | 1 hr | Soon |
| 8 | Add `.mdx` to ingestion file types | Coverage | 5 min | Soon |
| 9 | Implement incremental ingestion (checksums) | Cost/Perf | 2–3 hr | Next sprint |
| 10 | Add hybrid BM25 + dense retrieval | Quality | 3–4 hr | Next sprint |
| 11 | Add reranking (FlashRank or Cohere) | Quality | 2–3 hr | Next sprint |
| 12 | Wrap query in FastAPI for persistent index | Perf | 4–6 hr | Next sprint |
| 13 | Add query result caching | Cost | 2 hr | Future |

---

## 3. Key Research Findings (Online)

### Chunking
- **512 tokens with 64-token overlap** is the current top-performing general strategy
  (Feb 2026 benchmark: 69% accuracy vs 54% for semantic chunking).
- **Hierarchical chunking** (summary chunk + detail chunk) is the most robust default
  for production doc systems — retrieves summary first, then pulls detail chunks.
- **Header-aware chunking** (preserve section headings in each chunk) significantly
  improves match accuracy for documentation corpora.

### Hybrid Search
- Combine **BM25** (keyword) + **dense vector** retrieval via Reciprocal Rank Fusion.
- MRR improvement: 56.72% (dense only) → 66.43% (hybrid) = **+9.3 pp**.
- LlamaIndex: use `QueryFusionRetriever` with `mode="reciprocal_rerank"`.

### Reranking
- **Cross-encoder reranking** can improve retrieval quality by up to **48%**.
- Two options: `FlashRankRerank` (free, local, fast) or `CohereRerank` (API, best quality).
- Use as a `node_postprocessor` in LlamaIndex query engine.

### pgvector Index
- **HNSW** (Hierarchical Navigable Small Worlds) is preferred over IVFFlat for this use case:
  - Can be created before OR after data is loaded
  - Auto-updates as new data is inserted
  - Better recall/latency tradeoff at this corpus size (~1K–100K vectors)
- Recommended params: `m=16, ef_construction=64` (balanced quality/speed).

---

## 4. Search Prompts (use these in Perplexity, ChatGPT, or Google)

If you want to dig deeper yourself, here are ready-to-use search queries:

```
# Chunking strategies
"best chunk size for RAG documentation site 2025 LlamaIndex SentenceSplitter overlap"

# Hybrid search with Supabase
"LlamaIndex hybrid BM25 vector search Supabase pgvector QueryFusionRetriever example"

# Reranking
"LlamaIndex FlashRankRerank postprocessor example 2025"
"CohereRerank vs FlashRank RAG quality comparison"

# pgvector HNSW index
"Supabase pgvector HNSW index cosine distance create index SQL example"
"vecs python create_index cosine HNSW LlamaIndex"

# Incremental ingestion
"LlamaIndex incremental document indexing skip unchanged files checksum"

# Evaluation / benchmarking your RAG
"LlamaIndex RAGAs evaluation framework precision recall 2025"
"how to evaluate RAG retrieval quality without labels"

# Persistent query server
"LlamaIndex FastAPI persistent index server example 2025"
```

---

## 5. Sources

- [Advanced RAG Cheat Sheet & Recipes — LlamaIndex](https://www.llamaindex.ai/blog/a-cheat-sheet-and-some-recipes-for-building-advanced-rag-803a9d94c41b)
- [RAG in 2025: 7 Proven Strategies at Scale — Morphik](https://www.morphik.ai/blog/retrieval-augmented-generation-strategies)
- [Optimizing RAG with Hybrid Search & Reranking — Superlinked VectorHub](https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking)
- [Best Chunking Strategies for RAG in 2025 — Firecrawl](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- [9 Advanced RAG Techniques — Meilisearch](https://www.meilisearch.com/blog/rag-techniques)
- [Supabase HNSW Index Docs](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes)
- [Supabase Vector Indexes Overview](https://supabase.com/docs/guides/ai/vector-indexes)
- [LlamaIndex + Supabase Vector Store Docs](https://developers.llamaindex.ai/python/framework/integrations/vector_stores/supabasevectorindexdemo/)
- [Enhancing RAG: Study of Best Practices — arXiv 2501.07391](https://arxiv.org/abs/2501.07391)
