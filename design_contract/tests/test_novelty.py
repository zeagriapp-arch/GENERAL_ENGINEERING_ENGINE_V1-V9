from __future__ import annotations

from requirement_contract.schema import Value

from design_contract.novelty import ParameterDistanceNoveltyScorer
from design_contract.schema import Design
from tests.conftest import make_design_provenance


def _design(**params) -> Design:
    return Design(
        name="d",
        parameters={k: Value(original_value=v, original_unit=None, normalized_value=v, normalized_unit=None) for k, v in params.items()},
        provenance=make_design_provenance(),
    )


class TestNoveltyIndependentOfPerformanceAndFeasibility:
    def test_novelty_score_has_no_performance_or_feasibility_fields(self):
        from design_contract.novelty import NoveltyScore

        assert "performance" not in NoveltyScore.model_fields
        assert "feasible" not in NoveltyScore.model_fields


class TestFirstDesignIsMaximallyNovel:
    def test_empty_known_designs_gives_novelty_one(self):
        scorer = ParameterDistanceNoveltyScorer()
        result = scorer.score(_design(mass=10.0), known_designs=[])
        assert result.value == 1.0
        assert result.nearest_known_design_id is None


class TestNoveltyDecreasesWithSimilarity:
    def test_identical_design_has_zero_novelty(self):
        scorer = ParameterDistanceNoveltyScorer()
        known = _design(mass=10.0, cost=100.0)
        target = _design(mass=10.0, cost=100.0)
        result = scorer.score(target, known_designs=[known])
        assert result.value == 0.0
        assert result.nearest_known_design_id == known.id

    def test_distant_design_has_higher_novelty_than_close_one(self):
        scorer = ParameterDistanceNoveltyScorer()
        known = _design(mass=10.0)
        close = _design(mass=10.5)
        far = _design(mass=100.0)
        close_score = scorer.score(close, known_designs=[known])
        far_score = scorer.score(far, known_designs=[known])
        assert far_score.value > close_score.value

    def test_score_bounded_between_zero_and_one(self):
        scorer = ParameterDistanceNoveltyScorer()
        known = _design(mass=1.0)
        far = _design(mass=1e9)
        result = scorer.score(far, known_designs=[known])
        assert 0.0 <= result.value <= 1.0


class TestNoveltyNoSharedParameters:
    def test_no_shared_numeric_parameters_treated_as_maximally_novel(self):
        scorer = ParameterDistanceNoveltyScorer()
        known = _design(mass=10.0)
        target = _design(cost=100.0)
        result = scorer.score(target, known_designs=[known])
        assert result.value == 1.0
