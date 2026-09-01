from __future__ import annotations

import pytest
from requirement_contract.schema import Provenance, ProvenanceSource

from design_contract.constraints import DesignConstraint
from design_contract.design_space import DesignSpace
from design_contract.schema import DesignProvenance, DesignProvenanceSource
from design_contract.variables import DesignDomain, DesignVariable, VariableRole


def make_provenance(actor: str = "test-user") -> Provenance:
    return Provenance(source_type=ProvenanceSource.USER, actor=actor)


def make_design_provenance(source_type: DesignProvenanceSource = DesignProvenanceSource.USER, **overrides) -> DesignProvenance:
    defaults = {"source_type": source_type}
    if source_type == DesignProvenanceSource.USER:
        defaults["actor"] = "test-user"
    elif source_type == DesignProvenanceSource.GENERATED:
        defaults["generator_id"] = "test-generator"
    elif source_type == DesignProvenanceSource.IMPORTED:
        defaults["import_reference"] = "test-file.step"
    elif source_type in (DesignProvenanceSource.DERIVED, DesignProvenanceSource.OPTIMIZED):
        defaults["derived_from"] = ["D000"]
    elif source_type == DesignProvenanceSource.LLM_PROPOSED:
        defaults["llm_model"] = "reasoning"
    elif source_type == DesignProvenanceSource.SYSTEM:
        defaults["actor"] = "design_contract"
    defaults.update(overrides)
    return DesignProvenance(**defaults)


def make_variable(
    name: str = "diameter", *, role: VariableRole = VariableRole.DESIGN, domain: DesignDomain | None = None, unit: str | None = "m", **overrides
) -> DesignVariable:
    return DesignVariable(
        name=name, role=role, domain=domain or DesignDomain.continuous(0.10, 0.50), unit=unit, provenance=make_provenance(), **overrides
    )


def cylinder_design_space(**overrides) -> DesignSpace:
    """Ejemplo canónico de la especificación: diameter/length/thickness/material."""
    variables = {
        "diameter": make_variable("diameter", domain=DesignDomain.continuous(0.10, 0.50), unit="m"),
        "length": make_variable("length", domain=DesignDomain.continuous(0.20, 1.00), unit="m"),
        "thickness": make_variable("thickness", domain=DesignDomain.continuous(0.001, 0.010), unit="m"),
        "material": make_variable("material", domain=DesignDomain.categorical(["A", "B", "C"]), unit=None),
    }
    defaults = dict(name="cylinder-space", variables=variables, provenance=make_design_provenance())
    defaults.update(overrides)
    return DesignSpace(**defaults)


@pytest.fixture
def basic_design_space() -> DesignSpace:
    return cylinder_design_space()
