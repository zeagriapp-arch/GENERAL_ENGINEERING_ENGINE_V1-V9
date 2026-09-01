"""
`SearchSpace` (sección 17): la región que un algoritmo decide explorar
REALMENTE, distinta del `DesignSpace` (universo matemáticamente permitido).
Un `DesignSpace` de 10^12 combinaciones puede tener un `SearchSpace` de
10^6 candidatos seleccionados para esta ronda de búsqueda — más acotado,
y explícitamente vinculado a la estrategia que lo generó.

`SearchStrategy` es una interfaz extensible (sección 18) — ninguna
implementación real todavía salvo lo mínimo necesario para probar el
contrato (ver `generators/deterministic.py`).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from design_contract.design_space import DesignSpace
from design_contract.schema import new_id


class SearchStrategyKind(str, Enum):
    """Sección 18 — extensible; no todas tienen implementación en esta fase."""

    GRID = "GRID"
    RANDOM = "RANDOM"
    LATIN_HYPERCUBE = "LATIN_HYPERCUBE"
    BAYESIAN = "BAYESIAN"
    EVOLUTIONARY = "EVOLUTIONARY"
    ADAPTIVE = "ADAPTIVE"
    LLM_GUIDED = "LLM_GUIDED"
    HYBRID = "HYBRID"


class SearchSpace(BaseModel):
    """
    Una región concreta del DesignSpace que se decidió explorar en esta
    ronda — restringe (nunca amplía) los bounds del DesignSpace de origen.
    """

    id: str = Field(default_factory=new_id)
    design_space_id: str = Field(description="id del DesignSpace del que esta región es un subconjunto — nunca amplía sus bounds.")
    strategy: SearchStrategyKind
    variable_bounds_override: dict[str, tuple[float, float]] = Field(
        default_factory=dict, description="Sub-rango explorado por variable (solo CONTINUOUS/INTEGER) — subconjunto del bound original."
    )
    max_candidates: Optional[int] = Field(default=None, description="Tamaño previsto de esta región de búsqueda — el '10^6' del ejemplo de la sección 17.")
    metadata: dict = Field(default_factory=dict)

    def restricts(self, design_space: DesignSpace) -> list[str]:
        """
        Verifica que `variable_bounds_override` sea efectivamente un
        SUBCONJUNTO de los bounds del DesignSpace de origen — un
        SearchSpace nunca puede ampliar el universo permitido. Devuelve
        errores (vacío == válido).
        """
        errors: list[str] = []
        for name, (lo, hi) in self.variable_bounds_override.items():
            var = design_space.variables.get(name)
            if var is None:
                errors.append(f"SearchSpace referencia variable '{name}' que no existe en el DesignSpace.")
                continue
            if var.domain.lower_bound is None or var.domain.upper_bound is None:
                errors.append(f"Variable '{name}' no tiene bounds continuos/enteros — no se puede acotar un SearchSpace sobre ella así.")
                continue
            if lo < var.domain.lower_bound or hi > var.domain.upper_bound:
                errors.append(
                    f"SearchSpace amplía el DesignSpace en '{name}': [{lo}, {hi}] excede "
                    f"[{var.domain.lower_bound}, {var.domain.upper_bound}]."
                )
            if lo > hi:
                errors.append(f"SearchSpace inválido para '{name}': lower={lo} > upper={hi}.")
        return errors


# Nota de diseño (sección 18): no hay una clase "SearchStrategyInterface"
# separada aquí — la interfaz DE COMPORTAMIENTO (cómo se genera una región
# de búsqueda) es `generators.base.DesignGenerator`, que ya recibe un
# `SearchStrategyKind` como parte de su identidad (`generator.strategy`).
# `SearchSpace` (arriba) es el DATO que un generador produce/restringe;
# `DesignGenerator` es el COMPORTAMIENTO que lo produce — mismo split que
# `core.design.generator.DesignGenerator` (comportamiento) vs.
# `core.design.design_space.DesignSpace` (dato) en v09_advanced_ai.
