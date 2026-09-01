"""
`DesignGenerator` (sección 22): interfaz general. Solo se implementa un
generador determinista básico en esta fase (`deterministic.py`) para
demostrar que el contrato funciona — sección 22 explícita: "no implementes
todavía una IA que intente inventar cualquier diseño físico".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from design_contract.candidate import CandidateDesign
    from design_contract.design_space import DesignSpace


class GeneratorKind(str, Enum):
    """Sección 22 — extensible; solo PARAMETER tiene implementación en esta fase."""

    PARAMETER = "PARAMETER"
    RULE_BASED = "RULE_BASED"
    COMBINATORIAL = "COMBINATORIAL"
    EVOLUTIONARY = "EVOLUTIONARY"
    LLM_PROPOSAL = "LLM_PROPOSAL"
    HYBRID = "HYBRID"


class DesignGenerator(ABC):
    id: str
    kind: GeneratorKind

    @abstractmethod
    def generate(self, design_space: "DesignSpace", *, n: int, seed: Optional[int] = None) -> list["CandidateDesign"]:
        """Devuelve hasta `n` CandidateDesign dentro de los dominios de las variables DESIGN/CONTROL del DesignSpace."""
        ...
