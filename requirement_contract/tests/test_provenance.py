from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_contract.schema import Provenance, ProvenanceSource
from requirement_contract.validators.base import Severity, ValidationContext
from requirement_contract.validators.provenance_validator import ProvenanceValidator
from tests.conftest import make_candidate, make_provenance


class TestProvenanceSchemaShape:
    def test_source_type_required(self):
        with pytest.raises(ValidationError):
            Provenance()

    def test_user_provenance_minimal(self):
        p = Provenance(source_type=ProvenanceSource.USER, actor="alice")
        assert p.source_type == ProvenanceSource.USER


class TestProvenanceValidatorUser:
    def test_user_with_actor_passes(self):
        candidate = make_candidate(provenance=make_provenance(ProvenanceSource.USER, actor="alice"))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert result.passed

    def test_user_without_actor_warns_but_passes(self):
        candidate = make_candidate(provenance=Provenance(source_type=ProvenanceSource.USER))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert result.passed
        assert any(i.severity == Severity.WARNING for i in result.issues)


class TestProvenanceValidatorDocument:
    def test_document_with_id_passes(self):
        candidate = make_candidate(provenance=make_provenance(ProvenanceSource.DOCUMENT, document_id="doc-42"))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert result.passed

    def test_document_without_id_fails(self):
        candidate = make_candidate(provenance=Provenance(source_type=ProvenanceSource.DOCUMENT))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any(i.field == "provenance.document_id" for i in result.issues)


class TestProvenanceValidatorComputed:
    def test_computed_with_derivation_and_derived_from_passes(self):
        candidate = make_candidate(provenance=make_provenance(ProvenanceSource.COMPUTED, derivation_id="d1", derived_from=["R001"]))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert result.passed

    def test_computed_without_derivation_id_fails(self):
        candidate = make_candidate(provenance=Provenance(source_type=ProvenanceSource.COMPUTED, derived_from=["R001"]))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any(i.field == "provenance.derivation_id" for i in result.issues)

    def test_computed_without_derived_from_fails(self):
        candidate = make_candidate(provenance=Provenance(source_type=ProvenanceSource.COMPUTED, derivation_id="d1"))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any(i.field == "provenance.derived_from" for i in result.issues)


class TestProvenanceValidatorAssumption:
    def test_assumption_with_text_passes(self):
        candidate = make_candidate(provenance=make_provenance(ProvenanceSource.ASSUMPTION, assumption_text="valor típico de referencia"))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert result.passed

    def test_assumption_without_text_fails(self):
        candidate = make_candidate(provenance=Provenance(source_type=ProvenanceSource.ASSUMPTION))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any(i.field == "provenance.assumption_text" for i in result.issues)


class TestProvenanceValidatorSystem:
    def test_system_with_actor_passes_no_warning(self):
        candidate = make_candidate(provenance=make_provenance(ProvenanceSource.SYSTEM, actor="requirement_contract"))
        result = ProvenanceValidator().validate(candidate, context=ValidationContext())
        assert result.passed
        assert not any(i.severity == Severity.WARNING for i in result.issues)
