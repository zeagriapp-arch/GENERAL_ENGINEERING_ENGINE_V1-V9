"""
`NoveltyScorer` (sección 21) — interfaz limpia, sin implementación de
embeddings todavía (explícitamente diferido). Un diseño novedoso no es
necesariamente mejor: `Novelty` se mantiene como un eje independiente de
`Performance`/`Feasibility`, nunca mezclado en un único score dentro de
este contrato.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from design_contract.schema import Design


class NoveltyScore(BaseModel):
    value: float = Field(ge=0.0, le=1.0, description="0 = idéntico a algo ya visto, 1 = completamente distinto. Escala relativa, no absoluta.")
    nearest_known_design_id: str | None = None
    method: str = Field(description="Cómo se calculó — ej. 'parameter_distance', 'embedding_cosine' (futuro).")


class NoveltyScorer(ABC):
    """Sin implementación de embeddings en esta fase (sección 21) — solo la interfaz."""

    @abstractmethod
    def score(self, design: Design, *, known_designs: list[Design]) -> NoveltyScore: ...


class ParameterDistanceNoveltyScorer(NoveltyScorer):
    """
    Única implementación de esta fase: distancia euclídea normalizada
    sobre los parámetros numéricos compartidos — deliberadamente simple
    (no un sistema de embeddings), suficiente para demostrar que el
    contrato funciona (mismo espíritu que `HashingEmbedder` en
    `core.knowledge.embeddings` de v09_advanced_ai: un sustituto simple y
    determinista, reemplazable después sin tocar el resto del sistema).
    """

    def score(self, design: Design, *, known_designs: list[Design]) -> NoveltyScore:
        if not known_designs:
            return NoveltyScore(value=1.0, nearest_known_design_id=None, method="parameter_distance")

        def _numeric_params(d: Design) -> dict[str, float]:
            return {
                name: v.normalized_value if v.is_normalized else v.original_value
                for name, v in d.parameters.items()
                if isinstance(v.normalized_value if v.is_normalized else v.original_value, (int, float))
            }

        target = _numeric_params(design)
        best_distance = None
        nearest_id = None
        for other in known_designs:
            if other.id == design.id:
                continue
            other_params = _numeric_params(other)
            shared = set(target) & set(other_params)
            if not shared:
                continue
            distance = sum((float(target[k]) - float(other_params[k])) ** 2 for k in shared) ** 0.5
            if best_distance is None or distance < best_distance:
                best_distance = distance
                nearest_id = other.id

        if best_distance is None:
            return NoveltyScore(value=1.0, nearest_known_design_id=None, method="parameter_distance")

        # Normalización simple y determinista a (0, 1] vía 1/(1+d) invertido —
        # documentado como heurístico, no una medida calibrada (mismo
        # espíritu honesto que las "confidence" heurísticas de v09_advanced_ai,
        # explícitamente marcadas como tales en su momento).
        normalized = 1.0 - (1.0 / (1.0 + best_distance))
        return NoveltyScore(value=round(min(max(normalized, 0.0), 1.0), 6), nearest_known_design_id=nearest_id, method="parameter_distance")
