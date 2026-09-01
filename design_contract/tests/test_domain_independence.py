"""
Sección 32: "crear al menos un test que demuestre que el núcleo puede
representar un sistema genérico sin importar terminología aeroespacial."

Este test modela un sistema de ingeniería MECÁNICA genérico (una viga
soportando una carga) — cero vocabulario satelital/de propulsión/
aeroespacial en ningún identificador, nombre de variable o texto.
"""
from __future__ import annotations

import inspect

from requirement_contract.schema import Priority

from design_contract.candidate import CandidateDesign
from design_contract.constraints import DesignConstraint
from design_contract.design_space import DesignSpace
from design_contract.generators.deterministic import GridSweepDesignGenerator
from design_contract.relations import CandidateRelation, register_relation_function, validate_candidate_relation
from design_contract.schema import DesignProvenance, DesignProvenanceSource
from design_contract.validators.pipeline import DesignValidationPipeline
from design_contract.variables import DesignDomain, DesignVariable, VariableRole
from tests.conftest import make_provenance

_FORBIDDEN_AEROSPACE_TERMS = {
    "satellite",
    "satelite",
    "thruster",
    "propulsion",
    "propulsi",
    "rocket",
    "cohete",
    "nozzle",
    "tobera",
    "isp",
    "specific_impulse",
    "chamber_pressure",
    "spacecraft",
    "orbital",
    "aerospace",
    "aeroespacial",
}


def _generic_beam_system():
    """Sistema genérico: una viga rectangular soportando una carga puntual — ingeniería mecánica/estructural básica."""
    register_relation_function("_beam_cross_section_area", lambda width, height: width * height)

    variables = {
        "width": DesignVariable(name="width", role=VariableRole.DESIGN, domain=DesignDomain.continuous(0.05, 0.30), unit="m", provenance=make_provenance()),
        "height": DesignVariable(name="height", role=VariableRole.DESIGN, domain=DesignDomain.continuous(0.05, 0.40), unit="m", provenance=make_provenance()),
        "load": DesignVariable(name="load", role=VariableRole.CONTROL, domain=DesignDomain.continuous(100.0, 5000.0), unit="N", provenance=make_provenance()),
        "material_grade": DesignVariable(
            name="material_grade", role=VariableRole.DESIGN, domain=DesignDomain.categorical(["steel_a", "steel_b", "aluminum_x"]), provenance=make_provenance()
        ),
        "cross_section_area": DesignVariable(
            name="cross_section_area", role=VariableRole.DERIVED, domain=DesignDomain.continuous(0.0, 1.0), unit="m^2", provenance=make_provenance()
        ),
    }

    relation_candidate = CandidateRelation(
        name="cross_section_area_from_dimensions",
        inputs=["width", "height"],
        output="cross_section_area",
        expression="_beam_cross_section_area(width, height)",
        provenance=make_provenance(),
    )
    relation, errors = validate_candidate_relation(relation_candidate, known_variable_names=set(variables))
    assert errors == []

    constraint = DesignConstraint(
        name="minimum_cross_section",
        expression="cross_section_area >= 0.01",
        priority=Priority.HARD,
        provenance=DesignProvenance(source_type=DesignProvenanceSource.SYSTEM, actor="test"),
    )

    return DesignSpace(
        name="generic-structural-beam",
        variables=variables,
        relations=[relation],
        constraints=[constraint],
        provenance=DesignProvenance(source_type=DesignProvenanceSource.USER, actor="structural-engineer"),
    )


class TestGenericMechanicalSystemNoAerospaceVocabulary:
    def test_full_flow_on_a_generic_beam_system(self):
        space = _generic_beam_system()
        assert space.validate_internal_consistency() == []

        gen = GridSweepDesignGenerator()
        candidates = gen.generate(space, n=8, seed=1)
        assert candidates

        pipeline = DesignValidationPipeline(space)
        designs = []
        for candidate in candidates:
            design, _report = pipeline.run(candidate)
            if design is not None:
                designs.append(design)
        assert designs  # al menos un Design construido de un sistema NO aeroespacial

    def test_no_forbidden_aerospace_vocabulary_anywhere_in_this_scenario(self):
        space = _generic_beam_system()
        text_blob = " ".join(
            [
                space.name,
                *space.variables.keys(),
                *[c.name for c in space.constraints],
                *[c.expression for c in space.constraints],
                *[r.name for r in space.relations],
                *[r.expression for r in space.relations],
            ]
        ).lower()
        for term in _FORBIDDEN_AEROSPACE_TERMS:
            assert term not in text_blob, f"Vocabulario aeroespacial encontrado donde no debería: '{term}'"

    def test_core_module_source_never_hardcodes_aerospace_class_names(self):
        """Verifica en el propio código fuente (no solo en este escenario) — sección 29."""
        import design_contract.schema as schema_mod
        import design_contract.variables as variables_mod

        source = inspect.getsource(schema_mod) + inspect.getsource(variables_mod)
        forbidden_class_names = {"SatelliteDesign", "RocketDesign", "ThrusterDesign", "SemiconductorDesign", "AircraftDesign"}
        for name in forbidden_class_names:
            assert name not in source
