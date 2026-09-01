from __future__ import annotations

from design_contract.lineage import DesignLineage


class TestParentChild:
    def test_record_adds_edge_and_root(self):
        lineage = DesignLineage()
        lineage2 = lineage.record(parent_id="A", child_id="B", transformation="mutation")
        assert lineage2.children_of("A") == ["B"]
        assert lineage2.parents_of("B") == ["A"]
        assert "A" in lineage2.root_ids

    def test_record_never_mutates_original(self):
        lineage = DesignLineage()
        lineage.record(parent_id="A", child_id="B", transformation="mutation")
        assert lineage.edges == []  # el original sigue vacío


class TestBranchingLineage:
    """El ejemplo de la especificación: A -> B, A -> C, B -> D."""

    def _example_lineage(self) -> DesignLineage:
        lineage = DesignLineage()
        lineage = lineage.record(parent_id="A", child_id="B", transformation="mutation")
        lineage = lineage.record(parent_id="A", child_id="C", transformation="crossover")
        lineage = lineage.record(parent_id="B", child_id="D", transformation="optimization_step")
        return lineage

    def test_a_has_two_children(self):
        lineage = self._example_lineage()
        assert set(lineage.children_of("A")) == {"B", "C"}

    def test_d_has_one_parent(self):
        lineage = self._example_lineage()
        assert lineage.parents_of("D") == ["B"]


class TestGeneration:
    def test_root_is_generation_zero(self):
        lineage = DesignLineage().record(parent_id="A", child_id="B", transformation="mutation")
        assert lineage.generation_of("A") == 0

    def test_direct_child_is_generation_one(self):
        lineage = DesignLineage().record(parent_id="A", child_id="B", transformation="mutation")
        assert lineage.generation_of("B") == 1

    def test_grandchild_is_generation_two(self):
        lineage = DesignLineage().record(parent_id="A", child_id="B", transformation="mutation").record(parent_id="B", child_id="D", transformation="opt")
        assert lineage.generation_of("D") == 2

    def test_unknown_design_has_no_generation(self):
        lineage = DesignLineage()
        assert lineage.generation_of("unknown") is None


class TestTransformationMetadata:
    def test_transformation_history_in_order(self):
        lineage = DesignLineage().record(parent_id="A", child_id="B", transformation="mutation").record(parent_id="B", child_id="D", transformation="optimization_step")
        history = lineage.transformation_history("D")
        assert [e.transformation for e in history] == ["mutation", "optimization_step"]

    def test_edge_carries_arbitrary_metadata(self):
        lineage = DesignLineage().record(parent_id="A", child_id="B", transformation="mutation", mutation_rate=0.1)
        assert lineage.edges[0].metadata["mutation_rate"] == 0.1
