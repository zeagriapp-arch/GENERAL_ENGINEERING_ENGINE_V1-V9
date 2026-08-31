"""
VectorStore (decisión #2 del Architecture Design Document).

Nota de implementación V1: la decisión original proponía Chroma
embebido. En este entorno de desarrollo no hay acceso de red a modelos
de embeddings descargables ni conviene depender del servicio de
telemetría por defecto de `chromadb`, así que V1 implementa
`SQLiteCosineVectorStore`: guarda vectores en SQLite y hace similarity
search por coseno en memoria (numpy). Para el volumen de documentos
curados de V1 (decisión #6: 5-10 documentos, no una knowledge graph
gigantesca) esto es más que suficiente y evita una dependencia pesada.

Migrar a Chroma/Qdrant real en producción es un cambio de UNA clase
nueva que implemente `VectorStore` — nada más en el sistema lo sabe.
"""
from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class VectorStore(ABC):
    @abstractmethod
    def add(self, id: str, embedding: list[float], metadata: dict) -> None: ...

    @abstractmethod
    def query(self, embedding: list[float], top_k: int = 5) -> list[tuple[str, float, dict]]:
        """Devuelve [(id, score_similitud, metadata)], score más alto = más similar."""
        ...


class SQLiteCosineVectorStore(VectorStore):
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    id TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )

    def add(self, id: str, embedding: list[float], metadata: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vectors (id, embedding, metadata) VALUES (?, ?, ?)",
                (id, json.dumps(embedding), json.dumps(metadata)),
            )

    def query(self, embedding: list[float], top_k: int = 5) -> list[tuple[str, float, dict]]:
        query_vec = np.array(embedding, dtype=float)
        query_norm = np.linalg.norm(query_vec) or 1.0

        with self._connect() as conn:
            rows = conn.execute("SELECT id, embedding, metadata FROM vectors").fetchall()

        scored: list[tuple[str, float, dict]] = []
        for row in rows:
            vec = np.array(json.loads(row["embedding"]), dtype=float)
            vec_norm = np.linalg.norm(vec) or 1.0
            similarity = float(np.dot(query_vec, vec) / (query_norm * vec_norm))
            scored.append((row["id"], similarity, json.loads(row["metadata"])))

        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:top_k]
