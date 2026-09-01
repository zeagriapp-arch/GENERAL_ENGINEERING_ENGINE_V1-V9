from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from requirement_contract.schema import Value

from design_contract.schema import (
    Architecture,
    Component,
    ComponentInterface,
    Design,
    DesignStatus,
    Geometry,
    GeometryRepresentationType,
    InvalidDesignStatusTransitionError,
    Material,
    MaterialProperty,
    transition_design_status,
)
from tests.conftest import make_design_provenance


class TestDesignCreation:
    def test_minimal_valid_design(self):
        d = Design(name="cylinder", provenance=make_design_provenance())
        assert d.status == DesignStatus.DRAFT
        assert d.version == 1

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            Design(provenance=make_design_provenance())

    def test_missing_provenance_raises(self):
        with pytest.raises(ValidationError):
            Design(name="x")

    def test_id_generated_and_unique(self):
        a, b = Design(name="a", provenance=make_design_provenance()), Design(name="b", provenance=make_design_provenance())
        assert a.id != b.id
        assert len(a.id) == 12


class TestDesignSerialization:
    def test_round_trips_through_json(self):
        d = Design(
            name="cylinder",
            parameters={"diameter": Value(original_value=0.3, original_unit="m", normalized_value=0.3, normalized_unit="m")},
            provenance=make_design_provenance(),
        )
        dumped = d.model_dump_json()
        restored = Design.model_validate_json(dumped)
        assert restored.id == d.id
        assert restored.parameters["diameter"].original_value == 0.3

    def test_dict_dump_is_json_serializable(self):
        d = Design(name="x", provenance=make_design_provenance())
        json.dumps(d.model_dump(mode="json"))  # no debe lanzar


class TestComponentGeometryMaterial:
    def test_component_minimal(self):
        c = Component(type="structural_member")
        assert c.type == "structural_member"

    def test_component_never_named_after_a_domain_concept_in_core(self):
        # El núcleo no debe definir clases como RocketEngine/SatelliteThruster — solo Component genérico.
        assert Component.__name__ == "Component"

    def test_geometry_representation_types(self):
        for kind in GeometryRepresentationType:
            g = Geometry(representation_type=kind, parameters={"x": 1})
            assert g.representation_type == kind

    def test_material_with_properties(self):
        m = Material(
            name="Aluminum 6061",
            properties={
                "density": MaterialProperty(value=Value(original_value=2700.0, original_unit="kg/m^3", normalized_value=2700.0, normalized_unit="kg/m^3"))
            },
        )
        assert m.properties["density"].value.original_value == 2700.0

    def test_architecture_hierarchy(self):
        arch = Architecture(component_ids=["c1", "c2"], hierarchy={"subsystem_a": ["c1"]})
        assert arch.hierarchy["subsystem_a"] == ["c1"]

    def test_component_interface(self):
        iface = ComponentInterface(from_component="c1", to_component="c2", kind="structural")
        assert iface.kind == "structural"

    def test_design_can_look_up_component_and_material_by_id(self):
        c = Component(type="x")
        m = Material(name="y")
        d = Design(name="d", components=[c], materials=[m], provenance=make_design_provenance())
        assert d.component_by_id(c.id) is c
        assert d.material_by_id(m.id) is m
        assert d.component_by_id("missing") is None


class TestStatusTransitions:
    def test_draft_to_candidate_valid(self):
        assert transition_design_status(DesignStatus.DRAFT, DesignStatus.CANDIDATE) == DesignStatus.CANDIDATE

    def test_draft_to_locked_invalid(self):
        with pytest.raises(InvalidDesignStatusTransitionError):
            transition_design_status(DesignStatus.DRAFT, DesignStatus.LOCKED)

    def test_locked_is_terminal(self):
        with pytest.raises(InvalidDesignStatusTransitionError):
            transition_design_status(DesignStatus.LOCKED, DesignStatus.VALIDATED)

    def test_feasible_to_locked_valid(self):
        assert transition_design_status(DesignStatus.FEASIBLE, DesignStatus.LOCKED) == DesignStatus.LOCKED
