"""
ConflictValidator (sección 14, paso 4 / sección 15).

Detecta contradicciones directas entre el candidato y los Requirements ya
conocidos (`context.known_requirements`) sobre el MISMO `subject.parameter`
— ej. `mass <= 20 kg` (ya existente) vs `mass >= 30 kg` (candidato nuevo).

Generaliza el ejemplo de la especificación (un par de requirements) a
cualquier cantidad de requirements sobre la misma magnitud: cada
comparación LT/LTE/GT/GTE/EQ se traduce a un intervalo numérico
(`operators.as_interval`) en unidades normalizadas, y se verifica que la
intersección de todos los intervalos (existentes + candidato) sea no
vacía. Nunca decide automáticamente "quién gana" por prioridad (sección
15: "no debe inventar cuál tiene prioridad") — la arquitectura existente
(`core.orchestrator`) tampoco tiene un mecanismo de resolución automática
de conflictos entre requirements que se pueda reutilizar aquí, así que un
conflicto detectado siempre se reporta y se deja bloqueado para
resolución humana/posterior, nunca resuelto en silencio.
"""
from __future__ import annotations

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.operators import as_interval
from requirement_contract.schema import Requirement
from requirement_contract.validators.base import Severity, ValidationContext, ValidationResult, Validator
from requirement_contract.validators.unit_validator import normalize_value


def _candidate_interval(subject: str, parameter: str, operator, value, unit) -> tuple[float, float] | None:
    normalized_value, _normalized_unit, _notes = normalize_value(value, unit)
    if isinstance(normalized_value, list):
        return None  # RANGE/DISCRETE no se representan como intervalo simple aquí
    return as_interval(operator, normalized_value) if isinstance(normalized_value, (int, float)) else None


def intersect(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float] | None:
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    return (lo, hi) if lo <= hi else None


class ConflictValidator(Validator):
    name = "conflict_validator"

    def validate(self, candidate: RequirementCandidate, *, context: ValidationContext) -> ValidationResult:
        issues = []

        candidate_qualified = f"{candidate.subject}.{candidate.parameter}"
        candidate_interval = _candidate_interval(
            candidate.subject, candidate.parameter, candidate.operator, candidate.value_original, candidate.value_unit
        )

        if candidate_interval is not None:
            combined = candidate_interval
            conflicting_with: list[str] = []

            for existing in context.known_requirements:
                if not isinstance(existing, Requirement):
                    continue
                if existing.qualified_name() != candidate_qualified:
                    continue
                existing_value = existing.value.normalized_value if existing.value.is_normalized else existing.value.original_value
                existing_interval = as_interval(existing.operator, existing_value) if isinstance(existing_value, (int, float)) else None
                if existing_interval is None:
                    continue

                new_combined = intersect(combined, existing_interval)
                if new_combined is None:
                    conflicting_with.append(existing.id)
                else:
                    combined = new_combined

            if conflicting_with:
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="value",
                        message=(
                            f"Conflicto detectado sobre '{candidate_qualified}': el candidato es incompatible con "
                            f"{len(conflicting_with)} Requirement(s) existente(s): {conflicting_with}. "
                            f"No se resuelve automáticamente por prioridad."
                        ),
                        conflicting_requirement_ids=conflicting_with,
                    )
                )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
