from __future__ import annotations

from design_contract.search_space import SearchSpace, SearchStrategyKind
from tests.conftest import cylinder_design_space


class TestSearchSpaceRestrictsDesignSpace:
    def test_valid_subregion_has_no_errors(self):
        space = cylinder_design_space()
        search = SearchSpace(design_space_id=space.id, strategy=SearchStrategyKind.RANDOM, variable_bounds_override={"diameter": (0.2, 0.3)})
        assert search.restricts(space) == []

    def test_region_wider_than_design_space_is_rejected(self):
        space = cylinder_design_space()
        search = SearchSpace(design_space_id=space.id, strategy=SearchStrategyKind.GRID, variable_bounds_override={"diameter": (0.05, 0.60)})
        errors = search.restricts(space)
        assert errors  # amplía el DesignSpace -> inválido

    def test_unknown_variable_is_rejected(self):
        space = cylinder_design_space()
        search = SearchSpace(design_space_id=space.id, strategy=SearchStrategyKind.GRID, variable_bounds_override={"nonexistent": (0.0, 1.0)})
        assert search.restricts(space)

    def test_inverted_bounds_rejected(self):
        space = cylinder_design_space()
        search = SearchSpace(design_space_id=space.id, strategy=SearchStrategyKind.GRID, variable_bounds_override={"diameter": (0.4, 0.2)})
        assert search.restricts(space)

    def test_max_candidates_is_the_10_to_6_of_the_spec_example(self):
        search = SearchSpace(design_space_id="x", strategy=SearchStrategyKind.RANDOM, max_candidates=1_000_000)
        assert search.max_candidates == 1_000_000


class TestSearchStrategyKindIsExtensible:
    def test_all_eight_strategies_from_spec_exist(self):
        expected = {"GRID", "RANDOM", "LATIN_HYPERCUBE", "BAYESIAN", "EVOLUTIONARY", "ADAPTIVE", "LLM_GUIDED", "HYBRID"}
        assert {s.value for s in SearchStrategyKind} == expected
