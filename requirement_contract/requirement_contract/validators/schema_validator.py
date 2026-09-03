"""
SchemaValidator (sección 14, paso 1): coherencia estructural entre
`type`, `operator` y la forma de `value_original` — lo que Pydantic por sí
solo no puede expresar (Pydantic ya garantizó los tipos básicos al
construir el `RequirementCandidate`; esto valida la combinación).
"""
from __future__ import annotations

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import Operator, RequirementType
from requirement_contract.validators.base import Severity, ValidationContext, ValidationResult, Validator

_MEMBERSHIP_OPERATORS = {Operator.IN, Operator.NOT_IN}

_TYPE_ALLOWED_OPERATORS: dict[RequirementType, set[Operator]] = {
    RequirementType.LIMIT: {Operator.LT, Operator.LTE, Operator.GT, Operator.GTE},
    RequirementType.TARGET: {Operator.EQ, Operator.APPROX},
    RequirementType.RANGE: {Operator.IN},
    RequirementType.EQUALITY: {Operator.EQ},
    RequirementType.INEQUALITY: {Operator.NEQ, Operator.LT, Operator.LTE, Operator.GT, Operator.GTE},
    RequirementType.BOOLEAN: {Operator.EQ, Operator.NEQ},
    RequirementType.DISCRETE: {Operator.IN, Operator.NOT_IN},
    RequirementType.QUALITATIVE: {Operator.EQ, Operator.NEQ, Operator.APPROX},
}


class SchemaValidator(Validator):
    name = "schema_validator"

    def validate(self, candidate: RequirementCandidate, *, context: ValidationContext) -> ValidationResult:
        issues = []

        allowed_ops = _TYPE_ALLOWED_OPERATORS.get(candidate.type, set())
        if candidate.operator not in allowed_ops:
            issues.append(
                self._issue(
                    severity=Severity.ERROR,
                    field="operator",
                    message=(
                        f"Operador '{candidate.operator.value}' no es válido para type={candidate.type.value}. "
                        f"Operadores permitidos: {sorted(o.value for o in allowed_ops)}"
                    ),
                )
            )

        value = candidate.value_original
        is_list = isinstance(value, list)

        if candidate.operator in _MEMBERSHIP_OPERATORS and not is_list:
            issues.append(
                self._issue(
                    severity=Severity.ERROR,
                    field="value_original",
                    message=f"Operador {candidate.operator.value} requiere 'value_original' como lista.",
                )
            )
        if candidate.operator not in _MEMBERSHIP_OPERATORS and is_list:
            issues.append(
                self._issue(
                    severity=Severity.ERROR,
                    field="value_original",
                    message=f"Operador {candidate.operator.value} no admite 'value_original' como lista.",
                )
            )

        if candidate.type == RequirementType.RANGE:
            if is_list and len(value) != 2:
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="value_original",
                        message=f"RequirementType.RANGE requiere exactamente 2 valores (min, max), recibidos: {len(value)}.",
                    )
                )
            elif is_list and len(value) == 2 and all(isinstance(v, (int, float)) for v in value) and value[0] > value[1]:
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="value_original",
                        message=f"RequirementType.RANGE con bounds desordenados: {value[0]} > {value[1]}.",
                    )
                )

        if candidate.type == RequirementType.DISCRETE and is_list and len(value) == 0:
            issues.append(
                self._issue(severity=Severity.ERROR, field="value_original", message="RequirementType.DISCRETE requiere al menos un valor permitido.")
            )

        if candidate.type == RequirementType.BOOLEAN and not isinstance(value, bool):
            issues.append(
                self._issue(
                    severity=Severity.ERROR,
                    field="value_original",
                    message=f"RequirementType.BOOLEAN requiere un valor booleano, recibido: {type(value).__name__}.",
                )
            )

        if candidate.type == RequirementType.QUALITATIVE and isinstance(value, (int, float)) and not isinstance(value, bool):
            issues.append(
                self._issue(
                    severity=Severity.WARNING,
                    field="value_original",
                    message="RequirementType.QUALITATIVE con un valor numérico — ¿el type debería ser LIMIT/TARGET/RANGE?",
                )
            )

        if not candidate.subject.strip():
            issues.append(self._issue(severity=Severity.ERROR, field="subject", message="'subject' no puede estar vacío."))
        if not candidate.parameter.strip():
            issues.append(self._issue(severity=Severity.ERROR, field="parameter", message="'parameter' no puede estar vacío."))

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
