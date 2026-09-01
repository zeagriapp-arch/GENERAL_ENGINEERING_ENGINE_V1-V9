"""
`FeasibilityChecker` (sección 20).

"Factible" (`FEASIBLE`) NUNCA se confunde con "simulado": esta fase solo
implementa checks ESTRUCTURALES deterministas (¿el candidato respeta los
dominios de sus variables? ¿satisface los DesignConstraint del
DesignSpace, evaluando las DesignRelation necesarias?) — nunca invoca un
simulador físico ni construye un modelo físico nuevo (prohibido
explícitamente en la sección 35).

```
Candidate -> Structural feasibility (ESTA FASE) -> Physics simulation (FUTURO) -> Physical feasibility
```
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from design_contract.relations import ExpressionEvaluationError
from design_contract.variables import VariableRole

if TYPE_CHECKING:
    from design_contract.design_space import DesignSpace


class FeasibilityStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


class FeasibilityReport(BaseModel):
    status: FeasibilityStatus
    violated_domains: list[str] = Field(default_factory=list, description="Nombres de variables fuera de su DesignDomain.")
    violated_constraints: list[str] = Field(default_factory=list, description="ids de DesignConstraint no satisfechos.")
    notes: list[str] = Field(default_factory=list)

    @property
    def is_feasible(self) -> bool:
        return self.status == FeasibilityStatus.FEASIBLE


class FeasibilityCheckerInterface:
    """Marcador de interfaz — ver `StructuralFeasibilityChecker.check()` como la firma real a implementar."""

    def check(self, candidate_values: dict[str, Any], design_space: "DesignSpace") -> FeasibilityReport:  # pragma: no cover - interfaz
        raise NotImplementedError


class StructuralFeasibilityChecker(FeasibilityCheckerInterface):
    """Única implementación de esta fase — determinista, sin simulación física."""

    def check(self, candidate_values: dict[str, Any], design_space: "DesignSpace") -> FeasibilityReport:
        violated_domains: list[str] = []
        for name, var in design_space.variables.items():
            if var.role not in (VariableRole.DESIGN, VariableRole.CONTROL):
                continue
            if name in candidate_values and not var.contains(candidate_values[name]):
                violated_domains.append(name)

        values: dict[str, Any] = dict(candidate_values)
        notes: list[str] = []
        for relation in design_space.relations:
            try:
                values[relation.output] = relation.evaluate(values)
            except ExpressionEvaluationError as exc:
                notes.append(f"Relation '{relation.name}' no evaluable: {exc}")

        violated_constraints: list[str] = []
        for constraint in design_space.constraints:
            try:
                satisfied = constraint.evaluate(values)
            except (ExpressionEvaluationError, TypeError) as exc:
                notes.append(f"Constraint '{constraint.name}' no evaluable: {exc}")
                continue
            if not satisfied:
                violated_constraints.append(constraint.id)

        if violated_domains or violated_constraints:
            status = FeasibilityStatus.INFEASIBLE
        elif notes:
            # Algo no se pudo evaluar (falta un input) — no es lo mismo que
            # "no factible": no hay evidencia suficiente todavía.
            status = FeasibilityStatus.UNKNOWN
        else:
            status = FeasibilityStatus.FEASIBLE

        return FeasibilityReport(status=status, violated_domains=violated_domains, violated_constraints=violated_constraints, notes=notes)
