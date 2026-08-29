---
name: rag-chroma-python
description: Conventions for embeddings, chunking, and similarity thresholds using ChromaDB + sentence-transformers in this project.
---

- Embedding model: `all-MiniLM-L6-v2` (local, free, no API call).
- Chunk each `kb/*.md` doc by section (## headers), not the whole file as one chunk — keeps retrieved context focused.
- Retrieval: `k=3` by default.
- Similarity threshold: if the top result's score is below the threshold, treat it as "no match" — this is what forces `action=escalate` per `support-agent-domain`.
- Persist ChromaDB to disk (`./chroma_data/`), not in-memory — so `kb/` isn't re-embedded on every process restart. Re-embed only when `kb/` changes.
