"""Markdown knowledge-base chunking and vector retrieval."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.errors import EmptyKnowledgeBaseError

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

KB_DIR: Path = _PROJECT_ROOT / "kb"
CHROMA_DIR: Path = _PROJECT_ROOT / "chroma_data"
COLLECTION_NAME = "kb_chunks"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_K = 3
EXCERPT_MAX_CHARS = 240
ELLIPSIS = "…"

# Chunking is driven entirely by the kb/*.md header layout: a single "# " H1
# per doc (the title) and one chunk per "## " H2 section. _CHUNK_PREFIX_PATTERN
# strips that "title + section" preamble back off a stored chunk so excerpts
# show body text only.
_H1_PATTERN = re.compile(r"^#[ \t]+(.+?)\s*$", re.MULTILINE)
_H2_PATTERN = re.compile(r"^##[ \t]+(.+?)\s*$")
_CHUNK_PREFIX_PATTERN = re.compile(r"\A[^\n]*\n##[ \t]+[^\n]*\n")


@dataclass(frozen=True)
class KbChunk:
    chunk_id: str
    doc_id: str
    section: str
    text: str


@dataclass(frozen=True)
class Source:
    doc_id: str
    section: str
    text: str
    excerpt: str
    score: float


class VectorCollection(Protocol):
    def count(self) -> int: ...

    def add(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None: ...

    def query(
        self,
        *,
        query_texts: list[str],
        n_results: int,
    ) -> Mapping[str, Any]: ...


def chunk_markdown(doc_id: str, content: str) -> list[KbChunk]:
    title_match = _H1_PATTERN.search(content)
    title = title_match.group(1) if title_match else doc_id

    chunks: list[KbChunk] = []
    section: str | None = None
    body_lines: list[str] = []

    def flush() -> None:
        if section is None:
            return
        body = "\n".join(body_lines).strip()
        if not body:
            return
        chunks.append(
            KbChunk(
                chunk_id=f"{doc_id}#{len(chunks)}",
                doc_id=doc_id,
                section=section,
                text=f"{title}\n## {section}\n{body}",
            )
        )

    for line in content.splitlines():
        header = _H2_PATTERN.match(line)
        if header:
            flush()
            section = header.group(1)
            body_lines = []
        elif section is not None:
            body_lines.append(line)
    flush()

    return chunks


def load_kb_chunks(kb_dir: Path = KB_DIR) -> list[KbChunk]:
    chunks: list[KbChunk] = []
    for path in sorted(kb_dir.glob("*.md")) if kb_dir.is_dir() else []:
        chunks.extend(chunk_markdown(path.stem, path.read_text(encoding="utf-8")))

    if not chunks:
        raise EmptyKnowledgeBaseError(f"No indexable markdown found in {kb_dir}")
    return chunks


def index_kb(
    collection: VectorCollection,
    kb_dir: Path = KB_DIR,
    *,
    force: bool = False,
) -> int:
    if collection.count() > 0 and not force:
        return 0

    chunks = load_kb_chunks(kb_dir)
    collection.add(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {"doc_id": chunk.doc_id, "section": chunk.section} for chunk in chunks
        ],
    )
    return len(chunks)


def _similarity(distance: float) -> float:
    return min(1.0, max(0.0, 1.0 - float(distance)))


def _section_body(chunk_text: str) -> str:
    return _CHUNK_PREFIX_PATTERN.sub("", chunk_text, count=1)


def _make_excerpt(chunk_text: str, max_chars: int = EXCERPT_MAX_CHARS) -> str:
    body = _section_body(chunk_text).strip()
    if len(body) <= max_chars:
        return body

    window = body[:max_chars]
    if not body[max_chars].isspace():
        cut = max(window.rfind(" "), window.rfind("\n"))
        if cut > 0:
            window = window[:cut]
    return window.rstrip() + ELLIPSIS


class Retriever:
    def __init__(self, collection: VectorCollection) -> None:
        self._collection = collection

    def retrieve(self, query: str, k: int = DEFAULT_K) -> list[Source]:
        if k <= 0:
            raise ValueError("k must be a positive integer")
        if not query.strip():
            return []

        result = self._collection.query(query_texts=[query], n_results=k)
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        sources = [
            Source(
                doc_id=str(metadata["doc_id"]),
                section=str(metadata["section"]),
                text=str(document),
                excerpt=_make_excerpt(str(document)),
                score=_similarity(distance),
            )
            for document, metadata, distance in zip(
                documents, metadatas, distances, strict=False
            )
        ]
        return sorted(sources, key=lambda source: source.score, reverse=True)


def build_retriever(
    kb_dir: Path = KB_DIR,
    persist_dir: Path = CHROMA_DIR,
) -> Retriever:
    import chromadb
    from chromadb.utils import embedding_functions

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        ),
        metadata={"hnsw:space": "cosine"},
    )
    index_kb(collection, kb_dir)
    return Retriever(collection)
