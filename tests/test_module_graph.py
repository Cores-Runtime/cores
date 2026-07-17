import pytest
from cores.core.module_graph import (
    ModuleRelationType,
    ModuleRelation,
    ModuleGraph,
    ModuleClassifier,
    ModuleClass,
    ModuleProfile,
    DefaultModuleClassifier,
)


# ─── ModuleRelationType ────────────────────────────────────────────────────────

class TestModuleRelationType:
    def test_enum_values(self) -> None:
        assert ModuleRelationType.DEPENDS_ON == "depends_on"
        assert ModuleRelationType.REDUNDANT_WITH == "redundant_with"
        assert ModuleRelationType.MUTUALLY_EXCLUSIVE == "mutually_exclusive"
        assert ModuleRelationType.SHARES_INFO_WITH == "shares_info_with"
        assert ModuleRelationType.PREREQUISITE_FOR == "prerequisite_for"

    def test_all_relations_covered(self) -> None:
        expected = {"depends_on", "redundant_with", "mutually_exclusive", "shares_info_with", "prerequisite_for"}
        actual = {m.value for m in ModuleRelationType}
        assert actual == expected


# ─── ModuleRelation ────────────────────────────────────────────────────────────

class TestModuleRelation:
    def test_creation(self) -> None:
        rel = ModuleRelation(source="A", target="B", relation_type=ModuleRelationType.DEPENDS_ON)
        assert rel.source == "A"
        assert rel.target == "B"
        assert rel.relation_type == ModuleRelationType.DEPENDS_ON
        assert rel.weight == 1.0

    def test_custom_weight(self) -> None:
        rel = ModuleRelation(source="A", target="B", relation_type=ModuleRelationType.DEPENDS_ON, weight=0.5)
        assert rel.weight == 0.5

    def test_immutability(self) -> None:
        rel = ModuleRelation(source="A", target="B", relation_type=ModuleRelationType.DEPENDS_ON)
        with pytest.raises((AttributeError, TypeError)):
            rel.source = "C"  # type: ignore[attr-defined]


# ─── ModuleGraph — Dependency Queries ──────────────────────────────────────────

class TestModuleGraphDependencies:
    def test_linear_chain(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("C", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
            }),
        )
        assert graph.get_dependencies("C") == {"B"}
        assert graph.get_dependencies("B") == {"A"}
        assert graph.get_dependencies("A") == set()

    def test_diamond(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C", "D"}),
            relations=frozenset({
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("C", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("D", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("D", "C", ModuleRelationType.DEPENDS_ON),
            }),
        )
        assert graph.get_dependencies("D") == {"B", "C"}
        assert graph.get_dependencies("B") == {"A"}
        assert graph.get_dependencies("C") == {"A"}
        assert graph.get_dependencies("A") == set()

    def test_no_dependencies(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset(),
        )
        assert graph.get_dependencies("A") == set()
        assert graph.get_dependencies("B") == set()

    def test_missing_module_returns_empty(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A"}),
            relations=frozenset(),
        )
        assert graph.get_dependencies("NONEXISTENT") == set()

    def test_only_depends_on_considered(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("B", "C", ModuleRelationType.REDUNDANT_WITH),
            }),
        )
        assert graph.get_dependencies("B") == {"A"}


# ─── ModuleGraph — Dependent Queries ───────────────────────────────────────────

class TestModuleGraphDependents:
    def test_linear_chain(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("C", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
            }),
        )
        assert graph.get_dependents("A") == {"B"}
        assert graph.get_dependents("B") == {"C"}
        assert graph.get_dependents("C") == set()

    def test_multiple_dependents(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("C", "A", ModuleRelationType.DEPENDS_ON),
            }),
        )
        assert graph.get_dependents("A") == {"B", "C"}

    def test_no_dependents(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A"}),
            relations=frozenset(),
        )
        assert graph.get_dependents("A") == set()

    def test_missing_module_returns_empty(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A"}),
            relations=frozenset(),
        )
        assert graph.get_dependents("NONEXISTENT") == set()


# ─── ModuleGraph — Redundancy Groups ───────────────────────────────────────────

class TestModuleGraphRedundancy:
    def test_self_included(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset(),
        )
        assert graph.get_redundancy_group("A") == {"A"}
        assert graph.get_redundancy_group("NONEXISTENT") == {"NONEXISTENT"}

    def test_pair_redundancy(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.REDUNDANT_WITH),
            }),
        )
        assert graph.get_redundancy_group("A") == {"A", "B"}
        assert graph.get_redundancy_group("B") == {"B", "A"}

    def test_chain_redundancy(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.REDUNDANT_WITH),
                ModuleRelation("B", "C", ModuleRelationType.REDUNDANT_WITH),
            }),
        )
        # Note: chain is not transitive — only direct relations
        assert graph.get_redundancy_group("A") == {"A", "B"}
        assert graph.get_redundancy_group("B") == {"B", "A", "C"}
        assert graph.get_redundancy_group("C") == {"C", "B"}

    def test_missing_node_in_group_returns_self(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A"}),
            relations=frozenset(),
        )
        assert graph.get_redundancy_group("NONEXISTENT") == {"NONEXISTENT"}


# ─── ModuleGraph — Mutual Exclusion ────────────────────────────────────────────

class TestModuleGraphExclusions:
    def test_no_exclusions(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset(),
        )
        assert graph.get_mutual_exclusions("A") == set()

    def test_pair_exclusion(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.MUTUALLY_EXCLUSIVE),
            }),
        )
        assert graph.get_mutual_exclusions("A") == {"B"}
        assert graph.get_mutual_exclusions("B") == {"A"}

    def test_multiple_exclusions(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.MUTUALLY_EXCLUSIVE),
                ModuleRelation("A", "C", ModuleRelationType.MUTUALLY_EXCLUSIVE),
            }),
        )
        assert graph.get_mutual_exclusions("A") == {"B", "C"}
        assert graph.get_mutual_exclusions("B") == {"A"}

    def test_missing_module_returns_empty(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A"}),
            relations=frozenset(),
        )
        assert graph.get_mutual_exclusions("NONEXISTENT") == set()


# ─── ModuleGraph — Shared Info ─────────────────────────────────────────────────

class TestModuleGraphSharedInfo:
    def test_no_shared_info(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset(),
        )
        assert graph.get_shared_info("A") == set()

    def test_pair_shared_info(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.SHARES_INFO_WITH),
            }),
        )
        assert graph.get_shared_info("A") == {"B"}
        assert graph.get_shared_info("B") == {"A"}

    def test_missing_module_returns_empty(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A"}),
            relations=frozenset(),
        )
        assert graph.get_shared_info("NONEXISTENT") == set()


# ─── ModuleGraph — Topological Order ───────────────────────────────────────────

class TestModuleGraphTopologicalOrder:
    def test_linear_chain(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("C", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
            }),
        )
        # A has no deps → first; B depends on A → second; C depends on B → third
        order = graph.topological_order()
        assert order == ["A", "B", "C"]

    def test_diamond(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C", "D"}),
            relations=frozenset({
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("C", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("D", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("D", "C", ModuleRelationType.DEPENDS_ON),
            }),
        )
        order = graph.topological_order()
        # A first. B and C have same in-degree after A → sorted: B, C. D last.
        assert order == ["A", "B", "C", "D"]

    def test_multiple_independent_subgraphs(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C", "D"}),
            relations=frozenset({
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("D", "C", ModuleRelationType.DEPENDS_ON),
            }),
        )
        order = graph.topological_order()
        assert set(order) == {"A", "B", "C", "D"}
        assert len(order) == 4
        assert order.index("A") < order.index("B")
        assert order.index("C") < order.index("D")

    def test_no_relations(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"B", "A", "C"}),
            relations=frozenset(),
        )
        # No dependencies → sorted alphabetical
        assert graph.topological_order() == ["A", "B", "C"]

    def test_single_module(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A"}),
            relations=frozenset(),
        )
        assert graph.topological_order() == ["A"]

    def test_empty_graph(self) -> None:
        graph = ModuleGraph(
            modules=frozenset(),
            relations=frozenset(),
        )
        assert graph.topological_order() == []

    def test_cycle_of_two(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
            }),
        )
        order = graph.topological_order()
        # Both have in_degree > 0 → fallback to sorted
        assert order == ["A", "B"]

    def test_cycle_of_three(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("B", "C", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("C", "A", ModuleRelationType.DEPENDS_ON),
            }),
        )
        order = graph.topological_order()
        # All have in_degree 1 → no node starts with 0 → fallback to sorted
        assert order == ["A", "B", "C"]

    def test_partial_cycle(self) -> None:
        """One subgraph has a cycle, another is independent."""
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C", "D", "E"}),
            relations=frozenset({
                ModuleRelation("B", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("D", "E", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("E", "D", ModuleRelationType.DEPENDS_ON),
            }),
        )
        order = graph.topological_order()
        assert set(order) == {"A", "B", "C", "D", "E"}
        assert len(order) == 5
        assert order.index("A") < order.index("B")

    def test_valid_order_respects_dependencies(self) -> None:
        """Verify that every module appears after its dependencies."""
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C", "D", "E"}),
            relations=frozenset({
                ModuleRelation("C", "A", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("C", "B", ModuleRelationType.DEPENDS_ON),
                ModuleRelation("E", "D", ModuleRelationType.DEPENDS_ON),
            }),
        )
        order = graph.topological_order()
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("C")
        assert order.index("D") < order.index("E")

    def test_non_dependency_relations_ignored(self) -> None:
        graph = ModuleGraph(
            modules=frozenset({"A", "B", "C"}),
            relations=frozenset({
                ModuleRelation("A", "B", ModuleRelationType.REDUNDANT_WITH),
                ModuleRelation("B", "C", ModuleRelationType.MUTUALLY_EXCLUSIVE),
            }),
        )
        # No DEPENDS_ON relations → all nodes are in-degree 0
        order = graph.topological_order()
        assert order == ["A", "B", "C"]


# ─── ModuleClass ───────────────────────────────────────────────────────────────

class TestModuleClass:
    def test_enum_values(self) -> None:
        assert ModuleClass.MANDATORY == "mandatory"
        assert ModuleClass.SAFETY_CRITICAL == "safety_critical"
        assert ModuleClass.MISSION == "mission"
        assert ModuleClass.OPTIONAL == "optional"

    def test_all_classes_covered(self) -> None:
        expected = {"mandatory", "safety_critical", "mission", "optional"}
        actual = {m.value for m in ModuleClass}
        assert actual == expected


# ─── ModuleProfile ─────────────────────────────────────────────────────────────

class TestModuleProfile:
    def test_default_creation(self) -> None:
        profile = ModuleProfile()
        assert profile.safety_weight == 0.0
        assert profile.mission_weight == 0.0
        assert profile.urgency_weight == 0.0
        assert profile.compute_cost == 0.0
        assert profile.time_cost_ms == 0.0
        assert profile.energy_cost == 0.0
        assert profile.mission_tags == frozenset()
        assert not profile.is_safety_critical
        assert not profile.is_diagnostic
        assert not profile.is_recovery
        assert not profile.is_localization

    def test_custom_values(self) -> None:
        profile = ModuleProfile(
            safety_weight=0.8,
            mission_weight=0.6,
            compute_cost=12.0,
            is_safety_critical=True,
            mission_tags=frozenset({"exploration", "science"}),
        )
        assert profile.safety_weight == 0.8
        assert profile.mission_weight == 0.6
        assert profile.is_safety_critical

    def test_immutability(self) -> None:
        profile = ModuleProfile()
        with pytest.raises((AttributeError, TypeError)):
            profile.safety_weight = 0.5  # type: ignore[attr-defined]


# ─── DefaultModuleClassifier ───────────────────────────────────────────────────

class TestDefaultModuleClassifier:
    def setup_method(self) -> None:
        self.classifier = DefaultModuleClassifier()

    def test_mandatory_by_name(self) -> None:
        assert self.classifier.classify("battery_monitor", ModuleProfile()) == ModuleClass.MANDATORY
        assert self.classifier.classify("logger", ModuleProfile()) == ModuleClass.MANDATORY

    def test_safety_critical_by_name(self) -> None:
        assert self.classifier.classify("localization", ModuleProfile()) == ModuleClass.SAFETY_CRITICAL
        assert self.classifier.classify("collision_avoidance", ModuleProfile()) == ModuleClass.SAFETY_CRITICAL
        assert self.classifier.classify("safety_monitor", ModuleProfile()) == ModuleClass.SAFETY_CRITICAL

    def test_safety_critical_by_profile_flag(self) -> None:
        profile = ModuleProfile(is_safety_critical=True)
        assert self.classifier.classify("arbitrary_module", profile) == ModuleClass.SAFETY_CRITICAL

    def test_safety_critical_by_name_takes_precedence(self) -> None:
        assert self.classifier.classify("safety_monitor", ModuleProfile()) == ModuleClass.SAFETY_CRITICAL

    def test_mission_by_name(self) -> None:
        assert self.classifier.classify("explorer", ModuleProfile()) == ModuleClass.MISSION
        assert self.classifier.classify("mapper", ModuleProfile()) == ModuleClass.MISSION
        assert self.classifier.classify("recovery", ModuleProfile()) == ModuleClass.MISSION
        assert self.classifier.classify("navigator", ModuleProfile()) == ModuleClass.MISSION

    def test_mission_by_mission_weight(self) -> None:
        profile = ModuleProfile(mission_weight=0.5)
        assert self.classifier.classify("terrain_scanner", profile) == ModuleClass.MISSION

    def test_safety_takes_precedence_over_mission(self) -> None:
        profile = ModuleProfile(mission_weight=0.5, is_safety_critical=True)
        assert self.classifier.classify("explorer", profile) == ModuleClass.SAFETY_CRITICAL

    def test_optional_fallback(self) -> None:
        assert self.classifier.classify("unknown_module", ModuleProfile()) == ModuleClass.OPTIONAL
        assert self.classifier.classify("debug_tool", ModuleProfile()) == ModuleClass.OPTIONAL

    def test_optional_with_only_urgency_weight(self) -> None:
        profile = ModuleProfile(urgency_weight=0.9)
        # urgency_weight alone does not trigger any classifier rule
        assert self.classifier.classify("urgency_module", profile) == ModuleClass.OPTIONAL

    def test_diagnostic_flag_does_not_affect_classification(self) -> None:
        profile = ModuleProfile(is_diagnostic=True)
        assert self.classifier.classify("diagnostic_module", profile) == ModuleClass.OPTIONAL


# ─── ModuleClassifier ABC ──────────────────────────────────────────────────────

class TestModuleClassifierABC:
    def test_abstract_class_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            ModuleClassifier()  # type: ignore[abstract]
