"""
`DesignValidationPipeline` (sección 19): el único camino sancionado de
`CandidateDesign` a `Design`.

```
CandidateDesign -> SchemaValidator -> StructuralValidator -> UnitValidator
                 -> ConstraintValidator (= "Constraint validation" + "Feasibility",
                    ver docstring de constraint_validator.py)
                 -> Design (status VALIDATED o FEASIBLE, según si hay
                    violaciones SOFT)
```

Convención de resolución de valores (documentada aquí porque no hay un
paso "Unit normalization" separado como en Requirement — las variables de
diseño usan la unidad canónica declarada en `DesignVariable.unit`, no una
unidad arbitraria propuesta por el LLM):

- Variables DESIGN/CONTROL: su valor viene de `candidate.variable_values`.
- Variables FIXED: su valor único vive en `domain` (bounds colapsados a un
  punto, o `allowed_values[0]`) — no se pide en el candidato.
- Variables DERIVED: se calculan evaluando el `DesignRelation`
  correspondiente — nunca se aceptan si el candidato las propone
  directamente (rechazado por `SchemaValidator`).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from requirement_contract.schema import Value

from design_contract.candidate import CandidateDesign
from design_contract.design_space import DesignSpace
from design_contract.feasibility import FeasibilityStatus
from design_contract.relations import ExpressionEvaluationError
from design_contract.schema import Architecture, Design, DesignStatus, new_id
from design_contract.validators.base import DesignValidationContext, ValidationIssue, ValidationResult
from design_contract.validators.constraint_validator import ConstraintValidator
from design_contract.validators.schema_validator import SchemaValidator
from design_contract.validators.structural_validator import StructuralValidator
from design_contract.validators.unit_validator import UnitValidator
from design_contract.variables import VariableRole


class DesignValidationReport(BaseModel):
    design_space_id: str
    results: list[ValidationResult]
    overall_status: DesignStatus

    @property
    def all_issues(self) -> list[ValidationIssue]:
        return [issue for result in self.results for issue in result.issues]

    @property
    def has_errors(self) -> bool:
        return any(r.has_errors for r in self.results)

    @property
    def is_valid(self) -> bool:
        return self.overall_status in (DesignStatus.VALIDATED, DesignStatus.FEASIBLE)


class DesignValueResolutionError(ValueError):
    pass


def resolve_variable_values(design_space: DesignSpace, candidate_values: dict) -> dict:
    """Combina DESIGN/CONTROL (del candidato) + FIXED (del domain) + DERIVED (evaluadas vía DesignRelation)."""
    values: dict = dict(candidate_values)

    for name, var in design_space.variables.items():
        if var.role != VariableRole.FIXED or name in values:
            continue
        domain = var.domain
        if domain.lower_bound is not None and domain.upper_bound is not None and domain.lower_bound == domain.upper_bound:
            values[name] = domain.lower_bound
        elif domain.allowed_values:
            values[name] = domain.allowed_values[0]
        else:
            raise DesignValueResolutionError(f"Variable FIXED '{name}' no tiene un valor único resoluble en su domain.")

    # Relations en orden de dependencia simple (una pasada; asume sin
    # dependencias derivadas encadenadas complejas — suficiente para esta
    # fase, ver limitaciones en el informe).
    for relation in design_space.relations:
        if relation.output in values:
            continue
        try:
            values[relation.output] = relation.evaluate(values)
        except ExpressionEvaluationError:
            continue  # el candidato puede no tener aún todos los inputs — se reporta como INFO en ConstraintValidator

    return values


class DesignValidationPipeline:
    def __init__(self, design_space: DesignSpace):
        self._design_space = design_space
        self.schema_validator = SchemaValidator(design_space)
        self.structural_validator = StructuralValidator(design_space)
        self.unit_validator = UnitValidator()
        self.constraint_validator = ConstraintValidator(design_space)

    def run(self, candidate: CandidateDesign, *, known_designs: Optional[list[Design]] = None) -> tuple[Optional[Design], DesignValidationReport]:
        context = DesignValidationContext(known_designs=known_designs or [])
        results: list[ValidationResult] = []

        schema_result = self.schema_validator.validate(candidate, context=context)
        results.append(schema_result)
        if not schema_result.passed:
            return None, self._report(results, DesignStatus.INVALID)

        results.append(self.structural_validator.validate(candidate, context=context))
        results.append(self.unit_validator.validate(candidate, context=context))
        constraint_result = self.constraint_validator.validate(candidate, context=context)
        results.append(constraint_result)

        if any(r.has_errors for r in results):
            return None, self._report(results, DesignStatus.INVALID)

        feasibility = self.constraint_validator.check_feasibility(candidate)
        status = DesignStatus.FEASIBLE if feasibility.status == FeasibilityStatus.FEASIBLE else DesignStatus.VALIDATED

        design = self._build_design(candidate, status=status)
        return design, self._report(results, status)

    def _report(self, results: list[ValidationResult], status: DesignStatus) -> DesignValidationReport:
        return DesignValidationReport(design_space_id=self._design_space.id, results=results, overall_status=status)

    def _build_design(self, candidate: CandidateDesign, *, status: DesignStatus) -> Design:
        resolved = resolve_variable_values(self._design_space, candidate.variable_values)

        parameters: dict[str, Value] = {}
        derived_quantities: dict[str, Value] = {}
        derived_names = self._design_space.derived_variable_names()
        for name, value in resolved.items():
            var = self._design_space.variables.get(name)
            unit = var.unit if var else None
            wrapped = Value(original_value=value, original_unit=unit, normalized_value=value, normalized_unit=unit)
            (derived_quantities if name in derived_names else parameters)[name] = wrapped

        return Design(
            id=new_id(),
            name=candidate.name or f"design-from-{candidate.design_space_id}",
            description=candidate.description,
            architecture=candidate.architecture or Architecture(),
            components=list(candidate.components),
            geometry=candidate.geometry,
            materials=list(candidate.materials),
            parameters=parameters,
            variables=dict(self._design_space.variables),
            derived_quantities=derived_quantities,
            interfaces=[],
            provenance=candidate.provenance,
            status=status,
            metadata=dict(candidate.metadata),
        )
