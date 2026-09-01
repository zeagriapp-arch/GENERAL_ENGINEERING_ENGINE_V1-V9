from __future__ import annotations

import pytest
from pydantic import ValidationError

from design_contract.schema import DesignProvenance, DesignProvenanceSource
from tests.conftest import make_design_provenance


class TestAllSevenSourceTypes:
    @pytest.mark.parametrize(
        "source_type",
        [
            DesignProvenanceSource.USER,
            DesignProvenanceSource.GENERATED,
            DesignProvenanceSource.IMPORTED,
            DesignProvenanceSource.DERIVED,
            DesignProvenanceSource.OPTIMIZED,
            DesignProvenanceSource.LLM_PROPOSED,
            DesignProvenanceSource.SYSTEM,
        ],
    )
    def test_each_source_type_constructs(self, source_type):
        prov = make_design_provenance(source_type)
        assert prov.source_type == source_type


class TestStructuredNotFreeText:
    def test_source_type_required(self):
        with pytest.raises(ValidationError):
            DesignProvenance()

    def test_generated_carries_generator_id(self):
        prov = make_design_provenance(DesignProvenanceSource.GENERATED)
        assert prov.generator_id == "test-generator"

    def test_imported_carries_reference(self):
        prov = make_design_provenance(DesignProvenanceSource.IMPORTED)
        assert prov.import_reference == "test-file.step"

    def test_derived_carries_derived_from(self):
        prov = make_design_provenance(DesignProvenanceSource.DERIVED)
        assert prov.derived_from == ["D000"]

    def test_llm_proposed_carries_model_role_not_a_provider(self):
        prov = make_design_provenance(DesignProvenanceSource.LLM_PROPOSED)
        assert prov.llm_model == "reasoning"
        # nunca un nombre de proveedor concreto (ollama/openai/claude) hardcodeado en el schema
        assert "ollama" not in DesignProvenance.model_fields
        assert "openai" not in DesignProvenance.model_fields


class TestDesignProvenanceVocabularyDistinctFromRequirementProvenance:
    def test_design_provenance_is_process_oriented(self):
        design_sources = {s.value for s in DesignProvenanceSource}
        assert "GENERATED" in design_sources and "OPTIMIZED" in design_sources and "LLM_PROPOSED" in design_sources

    def test_requirement_provenance_is_epistemic_and_distinct(self):
        from requirement_contract.schema import ProvenanceSource

        requirement_sources = {s.value for s in ProvenanceSource}
        assert "DOCUMENT" in requirement_sources and "ASSUMPTION" in requirement_sources
        # Vocabularios deliberadamente distintos, no el mismo enum reutilizado sin más.
        design_sources = {s.value for s in DesignProvenanceSource}
        assert design_sources != requirement_sources
