"""
Experiment Store (secciones 21, 22, 38).

Interfaz `ExperimentStore` + implementación SQLite para V1. Guardar un
Experiment con status PENDING/SIMULATED/EVALUATED es válido (representa
trabajo en progreso); una vez el status es ACCEPTED/REJECTED/FAILED, el
store rechaza cualquier `save()` posterior sobre el mismo id
(inmutabilidad tras cierre, sección 8 del Architecture Design Document).
"""
from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

from core.experiments.schema import Experiment, ExperimentGraph, ExperimentStatus


class ExperimentAlreadyClosedError(ValueError):
    pass


class ExperimentNotFoundError(KeyError):
    pass


class ExperimentStore(ABC):
    @abstractmethod
    def save(self, experiment: Experiment) -> str: ...

    @abstractmethod
    def get(self, experiment_id: str) -> Experiment: ...

    @abstractmethod
    def get_graph(self, root_id: str) -> ExperimentGraph: ...

    @abstractmethod
    def find_similar(self, design_param_values: dict[str, float], tolerance: float) -> list[Experiment]: ...


class SQLiteExperimentStore(ExperimentStore):
    """
    Implementación SQLite. Cada Experiment se guarda como JSON (Pydantic
    `model_dump_json`) más columnas indexadas (id, parent_id, root_id,
    status, timestamp) para poder consultar el grafo y hacer dedup sin
    deserializar todo. Ver decisión #1 del Architecture Design Document:
    migrar a Postgres es un cambio de connection string, no de código,
    porque todo el acceso pasa por esta clase.
    """

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
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    parent_id TEXT,
                    root_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_parent ON experiments(parent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_root ON experiments(root_id)")

    def _root_id_of(self, experiment: Experiment) -> str:
        """Sube por parent_id hasta encontrar la raíz (baseline sin parent)."""
        if experiment.parent_id is None:
            return experiment.id
        current = experiment.parent_id
        with self._connect() as conn:
            while True:
                row = conn.execute(
                    "SELECT parent_id, root_id FROM experiments WHERE id = ?", (current,)
                ).fetchone()
                if row is None:
                    # parent no encontrado todavía guardado explícitamente: current es la raíz conocida
                    return current
                if row["parent_id"] is None:
                    return current
                return row["root_id"]

    def save(self, experiment: Experiment) -> str:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT status FROM experiments WHERE id = ?", (experiment.id,)
            ).fetchone()
            if existing is not None and existing["status"] in (
                ExperimentStatus.ACCEPTED.value,
                ExperimentStatus.REJECTED.value,
                ExperimentStatus.FAILED.value,
            ):
                raise ExperimentAlreadyClosedError(
                    f"Experiment {experiment.id} ya está cerrado (status={existing['status']}); "
                    f"no se puede modificar. Crea un experimento hijo."
                )

            root_id = self._root_id_of(experiment)
            conn.execute(
                """
                INSERT INTO experiments (id, parent_id, root_id, status, timestamp, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status, timestamp=excluded.timestamp, payload=excluded.payload
                """,
                (
                    experiment.id,
                    experiment.parent_id,
                    root_id,
                    experiment.status.value,
                    experiment.timestamp.isoformat(),
                    experiment.model_dump_json(),
                ),
            )
        return experiment.id

    def get(self, experiment_id: str) -> Experiment:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM experiments WHERE id = ?", (experiment_id,)
            ).fetchone()
        if row is None:
            raise ExperimentNotFoundError(experiment_id)
        return Experiment.model_validate_json(row["payload"])

    def get_graph(self, root_id: str) -> ExperimentGraph:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload, parent_id, id FROM experiments WHERE root_id = ?", (root_id,)
            ).fetchall()
        nodes: dict[str, Experiment] = {}
        edges: list[tuple[str, str]] = []
        for row in rows:
            exp = Experiment.model_validate_json(row["payload"])
            nodes[exp.id] = exp
            if row["parent_id"] is not None:
                edges.append((row["parent_id"], row["id"]))
        return ExperimentGraph(root_id=root_id, nodes=nodes, edges=edges)

    def find_similar(self, design_param_values: dict[str, float], tolerance: float) -> list[Experiment]:
        """
        Dedup básico (sección 22: "evitar repetir innecesariamente
        experimentos conocidos"). V1: comparación por distancia relativa
        sobre los parámetros compartidos. No usa índices espaciales —
        aceptable para el volumen de V1 (ver riesgos, sección 17 del ADD).
        """
        matches: list[Experiment] = []
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM experiments").fetchall()
        for row in rows:
            exp = Experiment.model_validate_json(row["payload"])
            shared = set(design_param_values) & set(exp.design.parameters)
            if not shared:
                continue
            close_enough = True
            for name in shared:
                target = design_param_values[name]
                actual = exp.design.parameters[name].value
                if actual is None or not isinstance(actual, (int, float)):
                    close_enough = False
                    break
                denom = abs(target) if target != 0 else 1.0
                if abs(actual - target) / denom > tolerance:
                    close_enough = False
                    break
            if close_enough:
                matches.append(exp)
        return matches
