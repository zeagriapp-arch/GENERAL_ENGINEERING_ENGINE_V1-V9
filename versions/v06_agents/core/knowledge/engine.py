"""
Knowledge Engine (sección 8): arquitectura híbrida VECTOR SEARCH +
STRUCTURED KNOWLEDGE + SOURCE PROVENANCE.

`ingest_document` es la vía de entrada en V1 (curación manual — decisión
#6 del Architecture Design Document: sin extracción NLP automática
todavía). `search` es RAG semántico. `get_source`/`extract_facts` cierran
el círculo de provenance: "¿de dónde salió este dato?".
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from core.knowledge.embeddings import Embedder, HashingEmbedder
from core.knowledge.schema import Chunk, Equation, ExtractedFact, RawDocument, RetrievedChunk, Source
from core.knowledge.structured_store import SQLiteStructuredKnowledgeStore, StructuredKnowledgeStore
from core.knowledge.vector_store import SQLiteCosineVectorStore, VectorStore


def _chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Splitter simple por párrafos, respetando un tope de caracteres (V1 — 'no reinventar')."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for p in paragraphs:
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            for i in range(0, len(p), max_chars):
                chunks.append(p[i : i + max_chars])
    return chunks


class KnowledgeEngine:
    def __init__(
        self,
        vector_store: VectorStore,
        structured_store: StructuredKnowledgeStore,
        embedder: Embedder,
    ):
        self._vectors = vector_store
        self._structured = structured_store
        self._embedder = embedder

    async def ingest_document(self, document: RawDocument, full_text: str) -> list[str]:
        """
        Ingesta un documento curado: guarda Source + RawDocument (structured
        store), trocea `full_text`, embebe cada chunk, y lo indexa en el
        vector store con metadata suficiente para reconstruir provenance.
        Devuelve los ids de los chunks creados.
        """
        self._structured.save_source(document.source)
        self._structured.save_document(document)

        pieces = _chunk_text(full_text)
        embeddings = await self._embedder.embed(pieces)

        chunk_ids = []
        for idx, (text, vector) in enumerate(zip(pieces, embeddings)):
            chunk = Chunk(document_id=document.id, text=text, chunk_index=idx)
            self._vectors.add(
                chunk.id,
                vector,
                metadata={
                    "document_id": document.id,
                    "document_title": document.title,
                    "source_id": document.source.id,
                    "chunk_index": idx,
                    "text": text,
                },
            )
            chunk_ids.append(chunk.id)
        return chunk_ids

    def save_equation(self, equation: Equation) -> str:
        return self._structured.save_equation(equation)

    def save_fact(self, fact: ExtractedFact) -> str:
        return self._structured.save_fact(fact)

    async def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Tool: search_knowledge."""
        [query_vec] = await self._embedder.embed([query])
        hits = self._vectors.query(query_vec, top_k=top_k)

        results: list[RetrievedChunk] = []
        for chunk_id, score, metadata in hits:
            source = self._structured.get_source(metadata["source_id"])
            chunk = Chunk(
                id=chunk_id,
                document_id=metadata["document_id"],
                text=metadata["text"],
                chunk_index=metadata["chunk_index"],
            )
            results.append(
                RetrievedChunk(chunk=chunk, score=score, source=source, document_title=metadata["document_title"])
            )
        return results

    def get_source(self, source_id: str) -> Source:
        """Tool: get_source. Responde '¿de dónde salió este dato?'."""
        return self._structured.get_source(source_id)

    def extract_facts(self, document_id: str) -> list[ExtractedFact]:
        """
        Tool: extract_parameters.

        V1: devuelve los ExtractedFact curados manualmente para este
        documento (decisión #6 — sin NLP automático todavía). La firma
        es la misma que tendrá la versión automática de Phase 9, así que
        ningún caller necesita cambiar cuando se automatice.
        """
        return self._structured.get_facts_for_document(document_id)

    def equations_for_domain(self, domain: str) -> list[Equation]:
        return self._structured.get_equations_for_domain(domain)


# ---------------------------------------------------------------------------
# Funciones libres para Tool Registry (config/tools.yaml apunta a estas).
# Usan un engine por defecto (lazy singleton) sobre un path de DB fijo.
# En Phase 6, el Orchestrator inyectará el KnowledgeEngine real (con
# OllamaEmbedder) en vez de depender de este singleton de conveniencia.
# ---------------------------------------------------------------------------
_default_engine: Optional[KnowledgeEngine] = None
_default_db_path = Path("gede_knowledge.db")


def _get_default_engine() -> KnowledgeEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = KnowledgeEngine(
            vector_store=SQLiteCosineVectorStore(_default_db_path.with_suffix(".vectors.db")),
            structured_store=SQLiteStructuredKnowledgeStore(_default_db_path),
            embedder=HashingEmbedder(),
        )
    return _default_engine


def set_default_engine(engine: KnowledgeEngine) -> None:
    """Permite a tests/Orchestrator inyectar un engine concreto."""
    global _default_engine
    _default_engine = engine


async def search(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    return await _get_default_engine().search(query, top_k=top_k)


def get_source(source_id: str) -> Source:
    return _get_default_engine().get_source(source_id)


def extract_facts(document_id: str) -> list[ExtractedFact]:
    return _get_default_engine().extract_facts(document_id)
