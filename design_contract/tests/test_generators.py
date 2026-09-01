from __future__ import annotations

from design_contract.generators.base import GeneratorKind
from design_contract.generators.deterministic import GridSweepDesignGenerator, RandomSamplingDesignGenerator
from tests.conftest import cylinder_design_space


class TestGridSweepDesignGenerator:
    def test_generates_requested_count_or_fewer(self, basic_design_space):
        gen = GridSweepDesignGenerator()
        candidates = gen.generate(basic_design_space, n=20, seed=1)
        assert 0 < len(candidates) <= 20

    def test_deterministic_same_seed_same_result(self, basic_design_space):
        gen = GridSweepDesignGenerator()
        a = gen.generate(basic_design_space, n=10, seed=7)
        b = gen.generate(basic_design_space, n=10, seed=7)
        assert [c.variable_values for c in a] == [c.variable_values for c in b]

    def test_all_generated_values_within_domain(self, basic_design_space):
        gen = GridSweepDesignGenerator()
        for c in gen.generate(basic_design_space, n=10, seed=1):
            for name, value in c.variable_values.items():
                assert basic_design_space.variables[name].contains(value)

    def test_covers_categorical_values_not_just_continuous(self, basic_design_space):
        gen = GridSweepDesignGenerator()
        candidates = gen.generate(basic_design_space, n=30, seed=1)
        materials_seen = {c.variable_values["material"] for c in candidates}
        assert len(materials_seen) > 1  # el grid recorre A/B/C, no se queda en un solo valor

    def test_generator_kind_is_parameter(self):
        assert GridSweepDesignGenerator().kind == GeneratorKind.PARAMETER

    def test_provenance_marks_generated(self, basic_design_space):
        gen = GridSweepDesignGenerator()
        c = gen.generate(basic_design_space, n=1, seed=1)[0]
        assert c.provenance.source_type.value == "GENERATED"
        assert c.provenance.generator_id == "grid_sweep"


class TestRandomSamplingDesignGenerator:
    def test_generates_exactly_n(self, basic_design_space):
        gen = RandomSamplingDesignGenerator()
        candidates = gen.generate(basic_design_space, n=15, seed=1)
        assert len(candidates) == 15

    def test_deterministic_with_seed(self, basic_design_space):
        gen = RandomSamplingDesignGenerator()
        a = gen.generate(basic_design_space, n=10, seed=42)
        b = gen.generate(basic_design_space, n=10, seed=42)
        assert [c.variable_values for c in a] == [c.variable_values for c in b]

    def test_different_seeds_differ(self, basic_design_space):
        gen = RandomSamplingDesignGenerator()
        a = gen.generate(basic_design_space, n=10, seed=1)
        b = gen.generate(basic_design_space, n=10, seed=2)
        assert [c.variable_values for c in a] != [c.variable_values for c in b]

    def test_all_generated_values_within_domain(self, basic_design_space):
        gen = RandomSamplingDesignGenerator()
        for c in gen.generate(basic_design_space, n=15, seed=3):
            for name, value in c.variable_values.items():
                assert basic_design_space.variables[name].contains(value)


class TestGeneratorWithNoFreeVariables:
    def test_returns_single_empty_candidate(self):
        space = cylinder_design_space(variables={})
        assert len(GridSweepDesignGenerator().generate(space, n=10)) == 1
        assert len(RandomSamplingDesignGenerator().generate(space, n=10)) == 1
