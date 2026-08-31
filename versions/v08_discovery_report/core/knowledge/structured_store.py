"""
Capa estructurada del Knowledge Engine (sección 8): separada del vector
store. Guarda Sources, RawDocuments, Equations, ExtractedFacts — la
parte de "no confiar únicamente en embeddings".
"""
from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

from core.knowledge.schema import Equation, ExtractedFact, RawDocument, Source


class StructuredKnowledgeNotFoundError(KeyError):
    pass


class StructuredKnowledgeStore(ABC):
    @abstractmethod
    def save_source(self, source: Source) -> str: ...
    @abstractmethod
    def get_source(self, source_id: str) -> Source: ...
    @abstractmethod
    def save_document(self, document: RawDocument) -> str: ...
    @abstractmethod
    def get_document(self, document_id: str) -> RawDocument: ...
    @abstractmethod
    def save_equation(self, equation: Equation) -> str: ...
    @abstractmethod
    def get_equations_for_domain(self, domain: str) -> list[Equation]: ...
    @abstractmethod
    def save_fact(self, fact: ExtractedFact) -> str: ...
    @abstractmethod
    def get_facts_for_document(self, document_id: str) -> list[ExtractedFact]: ...


class SQLiteStructuredKnowledgeStore(StructuredKnowledgeStore):
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, domain TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS equations (id TEXT PRIMARY KEY, domain TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, document_id TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def save_source(self, source: Source) -> str:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sources (id, payload) VALUES (?, ?)",
                (source.id, source.model_dump_json()),
            )
        return source.id

    def get_source(self, source_id: str) -> Source:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            raise StructuredKnowledgeNotFoundError(f"Source '{source_id}' no encontrada.")
        return Source.model_validate_json(row["payload"])

    def save_document(self, document: RawDocument) -> str:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO documents (id, domain, payload) VALUES (?, ?, ?)",
                (document.id, document.domain, document.model_dump_json()),
            )
        return document.id

    def get_document(self, document_id: str) -> RawDocument:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            raise StructuredKnowledgeNotFoundError(f"Document '{document_id}' no encontrado.")
        return RawDocument.model_validate_json(row["payload"])

    def save_equation(self, equation: Equation) -> str:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO equations (id, domain, payload) VALUES (?, ?, ?)",
                (equation.id, equation.domain, equation.model_dump_json()),
            )
        return equation.id

    def get_equations_for_domain(self, domain: str) -> list[Equation]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM equations WHERE domain = ?", (domain,)).fetchall()
        return [Equation.model_validate_json(r["payload"]) for r in rows]

    def save_fact(self, fact: ExtractedFact) -> str:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO facts (id, document_id, payload) VALUES (?, ?, ?)",
                (fact.id, fact.document_id, fact.model_dump_json()),
            )
        return fact.id

    def get_facts_for_document(self, document_id: str) -> list[ExtractedFact]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM facts WHERE document_id = ?", (document_id,)).fetchall()
        return [ExtractedFact.model_validate_json(r["payload"]) for r in rows]
