from __future__ import annotations

from requirement_contract.schema import Operator, Requirement, RequirementStatus, RequirementType, Value
from requirement_contract.validators.base import ValidationContext
from requirement_contract.validators.conflict_validator import ConflictValidator
from requirement_contract.validators.pipeline import validate_candidate
from tests.conftest import make_candidate, make_provenance


def _existing_requirement(req_id: str, *, parameter: str, operator: Operator, value: float, unit: str = "kg") -> Requirement:
    return Requirement(
        id=req_id,
        subject="system",
        parameter=parameter,
        type=RequirementType.LIMIT,
        operator=operator,
        value=Value(original_value=value, original_unit=unit, normalized_value=value, normalized_unit=unit),
        provenance=make_provenance(),
        status=RequirementStatus.VALIDATED,
    )


class TestDirectConflict:
    def test_mass_lte_20_conflicts_with_mass_gte_30(self):
        """El ejemplo explícito de la especificación (sección 15)."""
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.LTE, value=20.0)
        candidate = make_candidate(subject="system", parameter="mass", operator=Operator.GTE, value_original=30.0, value_unit="kg")

        result = ConflictValidator().validate(candidate, context=ValidationContext(known_requirements=[r001]))

        assert not result.passed
        assert "R001" in result.issues[0].details["conflicting_requirement_ids"]

    def test_pipeline_marks_conflicting_status_and_still_returns_a_requirement(self):
        """Sección 15: nunca inventa quién gana — informa el conflicto y no lo esconde."""
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.LTE, value=20.0)
        candidate = make_candidate(subject="system", parameter="mass", operator=Operator.GTE, value_original=30.0, value_unit="kg")

        requirement, report = validate_candidate(candidate, known_requirements=[r001])

        assert report.overall_status == RequirementStatus.CONFLICTING
        assert requirement is not None
        assert requirement.status == RequirementStatus.CONFLICTING
        assert not report.is_valid

    def test_conflict_does_not_auto_resolve_by_priority(self):
        """No debe inventar cuál tiene prioridad, incluso si una es HARD y otra SOFT."""
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.LTE, value=20.0)
        candidate = make_candidate(
            subject="system", parameter="mass", operator=Operator.GTE, value_original=30.0, value_unit="kg", priority="HARD"
        )
        requirement, report = validate_candidate(candidate, known_requirements=[r001])
        assert report.overall_status == RequirementStatus.CONFLICTING  # no ACCEPT/REJECT automático


class TestNoConflict:
    def test_tightening_bound_does_not_conflict(self):
        """mass <= 20 (existente) y mass <= 15 (nuevo) no son contradictorios: solo más estricto."""
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.LTE, value=20.0)
        candidate = make_candidate(subject="system", parameter="mass", operator=Operator.LTE, value_original=15.0, value_unit="kg")

        result = ConflictValidator().validate(candidate, context=ValidationContext(known_requirements=[r001]))
        assert result.passed

    def test_different_parameter_never_conflicts(self):
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.LTE, value=20.0)
        candidate = make_candidate(subject="system", parameter="temperature", operator=Operator.GTE, value_original=500.0, value_unit="K")

        result = ConflictValidator().validate(candidate, context=ValidationContext(known_requirements=[r001]))
        assert result.passed

    def test_different_subject_same_parameter_never_conflicts(self):
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.LTE, value=20.0)
        candidate = make_candidate(subject="payload", parameter="mass", operator=Operator.GTE, value_original=30.0, value_unit="kg")

        result = ConflictValidator().validate(candidate, context=ValidationContext(known_requirements=[r001]))
        assert result.passed

    def test_overlapping_ranges_do_not_conflict(self):
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.GTE, value=10.0)
        candidate = make_candidate(subject="system", parameter="mass", operator=Operator.LTE, value_original=20.0, value_unit="kg")

        result = ConflictValidator().validate(candidate, context=ValidationContext(known_requirements=[r001]))
        assert result.passed  # [10, inf) ∩ (-inf, 20] = [10, 20], no vacío


class TestConflictAcrossUnits:
    def test_conflict_detected_even_with_different_but_compatible_units(self):
        # 20 kg vs "queremos que pese al menos 50 lb" (~22.68 kg) -> [10,inf) en kg tras normalizar
        r001 = _existing_requirement("R001", parameter="mass", operator=Operator.LTE, value=20.0, unit="kg")
        candidate = make_candidate(subject="system", parameter="mass", operator=Operator.GTE, value_original=50.0, value_unit="lb")

        result = ConflictValidator().validate(candidate, context=ValidationContext(known_requirements=[r001]))
        assert not result.passed  # 50 lb ~= 22.68 kg > 20 kg -> conflicto real tras normalizar
