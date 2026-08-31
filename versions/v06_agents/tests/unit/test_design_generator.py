from core.design.design_space import DesignSpace, DesignVariable
from core.design.generator import GridSweepGenerator, RandomSamplingGenerator


def _space_1var():
    return DesignSpace(
        domain="generic.mechanics",
        variables={"x": DesignVariable(name="x", lower_bound=0.0, upper_bound=10.0)},
    )


def _space_2var():
    return DesignSpace(
        domain="generic.mechanics",
        variables={
            "x": DesignVariable(name="x", lower_bound=0.0, upper_bound=10.0),
            "y": DesignVariable(name="y", lower_bound=100.0, upper_bound=200.0),
        },
    )


class TestRandomSamplingGenerator:
    def test_generates_n_points_within_bounds(self):
        gen = RandomSamplingGenerator()
        points = gen.generate(_space_1var(), n=20, seed=1)
        assert len(points) == 20
        assert all(0.0 <= p["x"] <= 10.0 for p in points)

    def test_same_seed_is_deterministic(self):
        gen = RandomSamplingGenerator()
        p1 = gen.generate(_space_1var(), n=5, seed=42)
        p2 = gen.generate(_space_1var(), n=5, seed=42)
        assert p1 == p2

    def test_different_seed_gives_different_points(self):
        gen = RandomSamplingGenerator()
        p1 = gen.generate(_space_1var(), n=5, seed=1)
        p2 = gen.generate(_space_1var(), n=5, seed=2)
        assert p1 != p2

    def test_empty_design_space_returns_single_empty_point(self):
        gen = RandomSamplingGenerator()
        empty_space = DesignSpace(domain="d", variables={})
        assert gen.generate(empty_space, n=5) == [{}]


class TestGridSweepGenerator:
    def test_single_variable_covers_full_range_including_bounds(self):
        gen = GridSweepGenerator()
        points = gen.generate(_space_1var(), n=5)
        values = [p["x"] for p in points]
        assert values[0] == 0.0
        assert values[-1] == 10.0
        assert len(values) == 5

    def test_is_deterministic_regardless_of_seed(self):
        gen = GridSweepGenerator()
        p1 = gen.generate(_space_1var(), n=5, seed=1)
        p2 = gen.generate(_space_1var(), n=5, seed=999)
        assert p1 == p2

    def test_two_variables_produces_cartesian_grid_within_bounds(self):
        gen = GridSweepGenerator()
        points = gen.generate(_space_2var(), n=9)
        assert len(points) <= 9
        assert all(0.0 <= p["x"] <= 10.0 and 100.0 <= p["y"] <= 200.0 for p in points)
