from __future__ import annotations

import pytest

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import (
    Operator,
    Priority,
    Provenance,
    ProvenanceSource,
    RequirementType,
    Uncertainty,
    Validity,
)


def make_provenance(source_type: ProvenanceSource = ProvenanceSource.USER, **overrides) -> Provenance:
    defaults = {"source_type": source_type}
    if source_type == ProvenanceSource.USER:
        defaults["actor"] = "test-user"
    elif source_type == ProvenanceSource.DOCUMENT:
        defaults["document_id"] = "doc-001"
    elif source_type == ProvenanceSource.COMPUTED:
        defaults["derivation_id"] = "deriv-001"
        defaults["derived_from"] = ["R000"]
    elif source_type == ProvenanceSource.ASSUMPTION:
        defaults["assumption_text"] = "Supuesto de prueba"
    elif source_type == ProvenanceSource.SYSTEM:
        defaults["actor"] = "requirement_contract"
    defaults.update(overrides)
    return Provenance(**defaults)


def make_candidate(
    *,
    subject: str = "system",
    parameter: str = "mass",
    type: RequirementType = RequirementType.LIMIT,
    operator: Operator = Operator.LTE,
    value_original=20.0,
    value_unit: str | None = "kg",
    priority: Priority = Priority.HARD,
    provenance: Provenance | None = None,
    uncertainty: Uncertainty | None = None,
    validity: Validity | None = None,
    dependencies: list[str] | None = None,
    **extra,
) -> RequirementCandidate:
    """Factory terso para construir RequirementCandidate en tests — análogo a
    `_design(**overrides)` en tests/unit/test_cold_gas_physics_model.py de v09."""
    return RequirementCandidate(
        subject=subject,
        parameter=parameter,
        type=type,
        operator=operator,
        value_original=value_original,
        value_unit=value_unit,
        priority=priority,
        provenance=provenance or make_provenance(),
        uncertainty=uncertainty or Uncertainty(),
        validity=validity or Validity(),
        dependencies=dependencies or [],
        **extra,
    )


@pytest.fixture
def mass_limit_candidate() -> RequirementCandidate:
    """'El sistema no debe superar 20 kg' -> mass <= 20 kg, HARD, USER."""
    return make_candidate(subject="system", parameter="mass", operator=Operator.LTE, value_original=20.0, value_unit="kg", priority=Priority.HARD)
