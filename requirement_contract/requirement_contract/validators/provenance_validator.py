"""
ProvenanceValidator (sección 14, paso 5 / sección 7): exige que
`Provenance` tenga los campos estructurados obligatorios según su
`source_type` — nunca acepta procedencia solo como texto libre.
"""
from __future__ import annotations

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import ProvenanceSource
from requirement_contract.validators.base import Severity, ValidationContext, ValidationResult, Validator

_REQUIRED_FIELDS: dict[ProvenanceSource, tuple[str, ...]] = {
    ProvenanceSource.DOCUMENT: ("document_id",),
    ProvenanceSource.COMPUTED: ("derivation_id",),
    ProvenanceSource.ASSUMPTION: ("assumption_text",),
    # USER y SYSTEM no exigen un campo estructurado adicional obligatorio —
    # 'actor' es recomendado pero no obligatorio (WARNING, no ERROR).
    ProvenanceSource.USER: (),
    ProvenanceSource.SYSTEM: (),
}


class ProvenanceValidator(Validator):
    name = "provenance_validator"

    def validate(self, candidate: RequirementCandidate, *, context: ValidationContext) -> ValidationResult:
        issues = []
        provenance = candidate.provenance
        required = _REQUIRED_FIELDS.get(provenance.source_type, ())

        for field_name in required:
            if getattr(provenance, field_name, None) in (None, ""):
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field=f"provenance.{field_name}",
                        message=f"source_type={provenance.source_type.value} requiere '{field_name}', no fue provisto.",
                    )
                )

        if provenance.source_type == ProvenanceSource.COMPUTED and not provenance.derived_from:
            issues.append(
                self._issue(
                    severity=Severity.ERROR,
                    field="provenance.derived_from",
                    message="source_type=COMPUTED requiere 'derived_from' con al menos un id de origen.",
                )
            )

        if provenance.source_type in (ProvenanceSource.USER, ProvenanceSource.SYSTEM) and not provenance.actor:
            issues.append(
                self._issue(
                    severity=Severity.WARNING,
                    field="provenance.actor",
                    message=f"source_type={provenance.source_type.value} sin 'actor' — recomendado para trazabilidad completa.",
                )
            )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
