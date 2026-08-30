from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import pytest

from src.agent.retrieval import (
    COLLECTION_NAME,
    DEFAULT_K,
    EXCERPT_MAX_CHARS,
    KbChunk,
    Retriever,
    Source,
    chunk_markdown,
    index_kb,
    load_kb_chunks,
)
from src.errors import EmptyKnowledgeBaseError

KB_DIR = Path(__file__).resolve().parents[1] / "kb"


def _vector(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9]+", text.lower()))


def _cosine_distance(a: Counter[str], b: Counter[str]) -> float:
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    dot = sum(count * b[token] for token, count in a.items())
    return 1.0 - dot / (norm_a * norm_b)


class FakeCollection:
    def __init__(self) -> None:
        self._ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict[str, str]] = []

    def count(self) -> int:
        return len(self._ids)

    def add(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        self._ids.extend(ids)
        self._documents.extend(documents)
        self._metadatas.extend(metadatas)

    def query(self, *, query_texts: list[str], n_results: int) -> dict[str, list]:
        query_vector = _vector(query_texts[0])
        ranked = sorted(
            range(len(self._ids)),
            key=lambda i: _cosine_distance(query_vector, _vector(self._documents[i])),
        )[:n_results]
        return {
            "ids": [[self._ids[i] for i in ranked]],
            "documents": [[self._documents[i] for i in ranked]],
            "metadatas": [[self._metadatas[i] for i in ranked]],
            "distances": [
                [
                    _cosine_distance(query_vector, _vector(self._documents[i]))
                    for i in ranked
                ]
            ],
        }


@pytest.fixture
def retriever() -> Retriever:
    collection = FakeCollection()
    index_kb(collection, KB_DIR)
    return Retriever(collection)


def test_chunk_markdown_splits_multi_section_doc_by_h2_header() -> None:
    content = (KB_DIR / "vpn-issues.md").read_text(encoding="utf-8")

    chunks = chunk_markdown("vpn-issues", content)

    assert len(chunks) > 1
    assert [c.section for c in chunks] == [
        "When this applies",
        "Common fixes, in order",
        "Information needed before resolving",
        "When to escalate",
    ]
    assert all(isinstance(c, KbChunk) for c in chunks)
    assert all(c.doc_id == "vpn-issues" for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_chunk_markdown_keeps_title_context_and_drops_title_only_preamble() -> None:
    content = "# Doc title\n\n## First\nbody one\n\n## Second\nbody two\n"

    chunks = chunk_markdown("doc", content)

    assert len(chunks) == 2
    assert chunks[0].text.startswith("Doc title")
    assert "body one" in chunks[0].text
    assert "body two" not in chunks[0].text


def test_chunk_markdown_ignores_sections_with_no_body() -> None:
    chunks = chunk_markdown("doc", "# T\n\n## Empty\n\n## Real\ncontent here\n")

    assert [c.section for c in chunks] == ["Real"]


def test_load_kb_chunks_reads_every_markdown_doc() -> None:
    chunks = load_kb_chunks(KB_DIR)

    assert {c.doc_id for c in chunks} == {
        "password-reset",
        "vpn-issues",
        "email-folder-access",
        "hardware-request",
        "software-install",
    }
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_load_kb_chunks_raises_on_missing_or_empty_kb_dir(tmp_path: Path) -> None:
    with pytest.raises(EmptyKnowledgeBaseError):
        load_kb_chunks(tmp_path / "does-not-exist")

    with pytest.raises(EmptyKnowledgeBaseError):
        load_kb_chunks(tmp_path)


def test_index_kb_embeds_all_chunks_once_and_skips_when_populated() -> None:
    collection = FakeCollection()

    indexed = index_kb(collection, KB_DIR)

    assert indexed == len(load_kb_chunks(KB_DIR))
    assert collection.count() == indexed

    assert index_kb(collection, KB_DIR) == 0
    assert collection.count() == indexed


def test_index_kb_force_reindexes_an_already_populated_collection() -> None:
    collection = FakeCollection()
    chunk_count = len(load_kb_chunks(KB_DIR))

    assert index_kb(collection, KB_DIR) == chunk_count
    assert collection.count() == chunk_count

    assert index_kb(collection, KB_DIR, force=True) == chunk_count
    assert collection.count() == chunk_count * 2


def test_default_k_is_three() -> None:
    assert DEFAULT_K == 3


def test_collection_name_satisfies_chromadb_naming_rules() -> None:
    assert re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]", COLLECTION_NAME)


def test_retrieve_returns_at_most_k_scored_sources_ordered_by_score(
    retriever: Retriever,
) -> None:
    results = retriever.retrieve("how do I reset my password", k=3)

    assert len(results) == 3
    assert all(isinstance(r, Source) for r in results)
    assert [r.score for r in results] == sorted(
        (r.score for r in results), reverse=True
    )
    assert all(r.doc_id for r in results)
    assert all(r.excerpt for r in results)
    assert all(0.0 <= r.score <= 1.0 for r in results)
    assert results[0].doc_id == "password-reset"


def test_retrieve_defaults_to_three_results(retriever: Retriever) -> None:
    assert len(retriever.retrieve("my vpn keeps disconnecting")) == DEFAULT_K


def test_retrieve_honours_smaller_k(retriever: Retriever) -> None:
    assert len(retriever.retrieve("my vpn keeps disconnecting", k=1)) == 1


def test_retrieve_rejects_non_positive_k(retriever: Retriever) -> None:
    with pytest.raises(ValueError):
        retriever.retrieve("anything", k=0)


def test_retrieve_returns_nothing_for_a_blank_query(retriever: Retriever) -> None:
    assert retriever.retrieve("   ") == []


def test_retrieve_keeps_full_chunk_in_text_and_a_short_body_excerpt(
    retriever: Retriever,
) -> None:
    results = retriever.retrieve("how do I reset my password")

    for source in results:
        lines = source.text.splitlines()
        assert lines[1] == f"## {source.section}"
        body = "\n".join(lines[2:])
        assert source.excerpt
        assert "## " not in source.excerpt
        assert len(source.excerpt) <= EXCERPT_MAX_CHARS + 1
        assert body.startswith(source.excerpt.removesuffix("…"))


def test_excerpt_truncates_a_long_body_on_a_word_boundary_with_an_ellipsis() -> None:
    body = " ".join(f"word{i:03d}" for i in range(200))
    collection = FakeCollection()
    chunks = chunk_markdown("long-doc", f"# Long doc\n\n## Long section\n{body}\n")
    collection.add(
        ids=[c.chunk_id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[{"doc_id": c.doc_id, "section": c.section} for c in chunks],
    )

    source = Retriever(collection).retrieve("word001 word002", k=1)[0]

    assert source.text == chunks[0].text
    assert len(source.excerpt) <= EXCERPT_MAX_CHARS + 1
    assert source.excerpt.endswith("…")
    prefix = source.excerpt.removesuffix("…")
    assert body.startswith(prefix)
    assert body[len(prefix)].isspace()


def test_retrieve_excerpt_is_not_truncated_when_the_body_is_short() -> None:
    collection = FakeCollection()
    chunks = chunk_markdown("short-doc", "# Short doc\n\n## Short section\ntiny body\n")
    collection.add(
        ids=[c.chunk_id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[{"doc_id": c.doc_id, "section": c.section} for c in chunks],
    )

    source = Retriever(collection).retrieve("tiny body", k=1)[0]

    assert source.excerpt == "tiny body"


def test_retrieve_preserves_the_indexed_section_metadata() -> None:
    collection = FakeCollection()
    index_kb(collection, KB_DIR)
    sections_by_document = {
        document: metadata["section"]
        for document, metadata in zip(
            collection._documents, collection._metadatas, strict=False
        )
    }

    results = Retriever(collection).retrieve("how do I reset my password")

    assert results
    for source in results:
        assert source.section
        assert source.section == sections_by_document[source.text]
    assert results[0].doc_id == "password-reset"
    assert results[0].section == "Self-service reset"


def test_unrelated_query_scores_far_below_a_relevant_one(retriever: Retriever) -> None:
    relevant = retriever.retrieve("I forgot my password and need a reset")
    unrelated = retriever.retrieve("pineapple gardening antarctica submarine recipes")

    assert unrelated[0].score < 0.1
    assert relevant[0].score > unrelated[0].score
