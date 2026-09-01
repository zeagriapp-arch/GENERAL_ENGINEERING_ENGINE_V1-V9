"""
Sección 33 — test de integración obligatorio, ejecutado de verdad (sin
mocks):

Requirement -> DesignSpace -> Variables -> Relations -> Constraints ->
CandidateGenerator -> CandidateDesign -> Feasibility -> Design

Usa el ejemplo canónico de la especificación: diameter/length/thickness/
material, con un Requirement real de `requirement_contract` conectado por
referencia (sección 30: `DesignSpace.requirement_ids`, nunca duplicando su
contenido).
"""
from __future__ import annotations

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import Operator as ReqOperator
from requirement_contract.schema import Priority as ReqPriority
from requirement_contract.schema import Provenance as ReqProvenance
from requirement_contract.schema import ProvenanceSource as ReqProvenanceSource
from requirement_contract.schema import RequirementType as ReqType
from requirement_contract.validators.pipeline import validate_candidate as validate_requirement_candidate
from requirement_contract.versioning import lock as lock_requirement

from design_contract.constraints import DesignConstraint
from design_contract.design_space import DesignSpace
from design_contract.feasibility import FeasibilityStatus
from design_contract.generators.deterministic import GridSweepDesignGenerator
from design_contract.relations import CandidateRelation, validate_candidate_relation
from design_contract.schema import DesignProvenance, DesignProvenanceSource, DesignStatus
from design_contract.validators.pipeline import DesignValidationPipeline
from design_contract.variables import DesignDomain, DesignVariable, VariableRole
from design_contract.versioning import lock as lock_design


def test_full_discovery_flow_from_requirement_to_locked_design():
    # 1. Requirement — "el sistema no debe superar 5 kg" (fase anterior, reutilizada de verdad, no simulada).
    requirement_candidate = RequirementCandidate(
        subject="cylinder_assembly",
        parameter="mass",
        type=ReqType.LIMIT,
        operator=ReqOperator.LTE,
        value_original=5.0,
        value_unit="kg",
        priority=ReqPriority.HARD,
        provenance=ReqProvenance(source_type=ReqProvenanceSource.USER, actor="ingeniero-diseño"),
    )
    requirement, req_report = validate_requirement_candidate(requirement_candidate)
    assert req_report.is_valid
    locked_requirement = lock_requirement(requirement)

    # 2. DesignSpace — referencia al Requirement por id (nunca duplica su contenido).
    variables = {
        "diameter": DesignVariable(
            name="diameter", role=VariableRole.DESIGN, domain=DesignDomain.continuous(0.10, 0.50), unit="m",
            provenance=ReqProvenance(source_type=ReqProvenanceSource.USER, actor="ingeniero-diseño"),
        ),
        "length": DesignVariable(
            name="length", role=VariableRole.DESIGN, domain=DesignDomain.continuous(0.20, 1.00), unit="m",
            provenance=ReqProvenance(source_type=ReqProvenanceSource.USER, actor="ingeniero-diseño"),
        ),
        "thickness": DesignVariable(
            name="thickness", role=VariableRole.DESIGN, domain=DesignDomain.continuous(0.001, 0.010), unit="m",
            provenance=ReqProvenance(source_type=ReqProvenanceSource.USER, actor="ingeniero-diseño"),
        ),
        "material": DesignVariable(
            name="material", role=VariableRole.DESIGN, domain=DesignDomain.categorical(["A", "B", "C"]),
            provenance=ReqProvenance(source_type=ReqProvenanceSource.USER, actor="ingeniero-diseño"),
        ),
        "estimated_mass": DesignVariable(
            name="estimated_mass", role=VariableRole.DERIVED, domain=DesignDomain.continuous(0.0, 1000.0), unit="kg",
            provenance=ReqProvenance(source_type=ReqProvenanceSource.SYSTEM, actor="design_contract"),
        ),
    }

    # 3. Relations — estimated_mass se CALCULA, nunca se propone directamente.
    mass_relation_candidate = CandidateRelation(
        name="estimated_mass_from_geometry",
        inputs=["diameter", "length", "thickness"],
        output="estimated_mass",
        expression="3.14159 * diameter * length * thickness * 2700",  # cascarón cilíndrico, densidad ~aluminio kg/m^3
        provenance=ReqProvenance(source_type=ReqProvenanceSource.SYSTEM, actor="design_contract"),
    )
    mass_relation, relation_errors = validate_candidate_relation(mass_relation_candidate, known_variable_names=set(variables))
    assert relation_errors == []

    # 4. Constraints — DesignConstraint que referencia explícitamente el Requirement.
    mass_constraint = DesignConstraint(
        name="mass_within_requirement",
        expression="estimated_mass <= 5.0",
        priority=ReqPriority.HARD,
        requirement_id=locked_requirement.id,
        provenance=DesignProvenance(source_type=DesignProvenanceSource.DERIVED, derived_from=[locked_requirement.id]),
    )

    design_space = DesignSpace(
        name="cylinder-design-space",
        variables=variables,
        relations=[mass_relation],
        constraints=[mass_constraint],
        requirement_ids=[locked_requirement.id],
        provenance=DesignProvenance(source_type=DesignProvenanceSource.USER, actor="ingeniero-diseño"),
    )
    assert design_space.validate_internal_consistency() == []

    # 5. CandidateGenerator -> CandidateDesign (generación determinista real, no un mock).
    # n=30 pero solo hay 2*2*2*3=24 combinaciones de grid posibles (3 continuas a
    # 2 puntos + material categórico) — se piden de más a propósito para cubrir
    # las 24 combinaciones completas, incluida la de peor caso (diameter/length/
    # thickness máximos), que sí debe violar el Requirement de masa.
    generator = GridSweepDesignGenerator()
    candidates = generator.generate(design_space, n=30, seed=42)
    assert len(candidates) == 24

    # 6. Feasibility -> Design (pipeline completa, ejecutada de verdad).
    pipeline = DesignValidationPipeline(design_space)
    valid_designs = []
    rejected = []
    for candidate in candidates:
        design, report = pipeline.run(candidate)
        if design is not None:
            valid_designs.append((design, report))
        else:
            rejected.append((candidate, report))

    assert valid_designs, "El flujo completo debe producir al menos un Design válido."
    assert rejected, "Al menos un candidato debe violar la restricción de masa derivada del Requirement (verifica que Feasibility realmente filtra)."

    # 7. Verificación de que el Requirement realmente restringió el resultado:
    # todo Design válido debe cumplir estimated_mass <= 5.0 kg — nunca se acepta uno que lo viole.
    # (el propio pipeline ya lo garantiza vía ConstraintValidator; se re-verifica aquí explícitamente).
    for candidate in candidates:
        d, _r = pipeline.run(candidate)
        if d is not None:
            mass = d.derived_quantities["estimated_mass"].original_value
            assert mass <= 5.0 + 1e-9

    # 8. Design -> Locked Design.
    best_design, best_report = valid_designs[0]
    feasible_or_validated = best_report.overall_status in (DesignStatus.FEASIBLE, DesignStatus.VALIDATED)
    assert feasible_or_validated
    if best_report.overall_status == DesignStatus.FEASIBLE:
        locked_design = lock_design(best_design)
        assert locked_design.status == DesignStatus.LOCKED
        assert locked_design.provenance.source_type.value in ("GENERATED", "USER", "SYSTEM", "DERIVED", "OPTIMIZED", "LLM_PROPOSED", "IMPORTED")

    # 9. Trazabilidad completa, de punta a punta: el Design final referencia (indirectamente, vía
    # el DesignSpace del que salió) el Requirement original.
    assert locked_requirement.id in design_space.requirement_ids
    assert design_space.constraints[0].requirement_id == locked_requirement.id
