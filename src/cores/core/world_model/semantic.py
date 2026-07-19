from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from cores.core.world_model.types import (
    EnvironmentState,
    DetectedObject,
    UncertaintyState,
)
from cores.core.world_model.interface import WorldModelStrategy


class SemanticNode:
    __slots__ = ("id", "node_type", "properties", "created_cycle", "last_seen_cycle")

    def __init__(
        self,
        node_id: str,
        node_type: str,
        properties: Optional[Dict[str, Any]] = None,
        created_cycle: int = 0,
    ) -> None:
        self.id: str = node_id
        self.node_type: str = node_type
        self.properties: Dict[str, Any] = properties or {}
        self.created_cycle: int = created_cycle
        self.last_seen_cycle: int = created_cycle


class SemanticEdge:
    __slots__ = ("source_id", "target_id", "relation", "weight", "properties")

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.source_id: str = source_id
        self.target_id: str = target_id
        self.relation: str = relation
        self.weight: float = weight
        self.properties: Dict[str, Any] = properties or {}


class SemanticWorldModel(WorldModelStrategy):
    """Physical reasoning strategy using a knowledge-graph representation with typed nodes and relations."""
    def __init__(self) -> None:
        self._nodes: Dict[str, SemanticNode] = {}
        self._edges: List[SemanticEdge] = []
        self._node_edges: Dict[str, List[int]] = {}
        self._environment: EnvironmentState = EnvironmentState()
        self._uncertainty: UncertaintyState = UncertaintyState()
        self._last_update_cycle: int = 0
        self._next_edge_id: int = 0

        self._init_default_schema()

    def _init_default_schema(self) -> None:
        self._add_node("environment", "region", {
            "terrain": "unknown",
            "weather": "clear",
            "temperature": 20.0,
            "lighting": "day",
        })
        self._add_node("robot", "agent", {"role": "explorer"})

    def _add_node(self, node_id: str, node_type: str, properties: Dict[str, Any]) -> SemanticNode:
        node = SemanticNode(node_id, node_type, properties, self._last_update_cycle)
        self._nodes[node_id] = node
        self._node_edges[node_id] = []
        return node

    def _add_edge(
        self, source: str, target: str, relation: str, weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> int:
        edge = SemanticEdge(source, target, relation, weight, properties)
        edge_idx = self._next_edge_id
        self._next_edge_id += 1
        self._edges.append(edge)
        if source in self._node_edges:
            self._node_edges[source].append(edge_idx)
        if target in self._node_edges:
            self._node_edges[target].append(edge_idx)
        return edge_idx

    # --- WorldModel interface ---

    @property
    def environment(self) -> EnvironmentState:
        return self._environment

    @property
    def objects(self) -> List[DetectedObject]:
        result = []
        for node in self._nodes.values():
            if node.node_type in ("object", "obstacle", "waypoint", "landmark"):
                pos = node.properties.get("position", {})
                if isinstance(pos, dict):
                    result.append(DetectedObject(
                        id=node.id,
                        object_type=node.node_type,
                        position=pos,
                        confidence=node.properties.get("confidence", 0.0),
                        last_seen_cycle=node.last_seen_cycle,
                        properties={
                            k: v for k, v in node.properties.items()
                            if k not in ("position", "confidence")
                        },
                    ))
        return result

    @property
    def uncertainty(self) -> UncertaintyState:
        return self._uncertainty

    @property
    def obstacle_count(self) -> int:
        return sum(
            1 for n in self._nodes.values() if n.node_type == "obstacle"
        )

    @property
    def has_sensor_degradation(self) -> bool:
        return any(h < 0.5 for h in self._uncertainty.sensor_health.values())

    @property
    def last_update_cycle(self) -> int:
        return self._last_update_cycle

    def update_environment(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self._environment, key):
                setattr(self._environment, key, value)
            if key in ("terrain", "weather", "temperature", "lighting") and "environment" in self._nodes:
                self._nodes["environment"].properties[key] = value
        self._last_update_cycle = max(self._last_update_cycle, 0) + 1

    def upsert_object(
        self,
        object_id: str,
        object_type: str,
        position: Dict[str, float],
        confidence: float,
        cycle: int,
        properties: Optional[Dict[str, Any]] = None,
    ) -> DetectedObject:
        if object_id in self._nodes:
            node = self._nodes[object_id]
            node.node_type = object_type
            node.properties["position"] = position
            node.properties["confidence"] = confidence
            node.last_seen_cycle = cycle
            if properties:
                node.properties.update(properties)
        else:
            merged_props = {
                "position": position,
                "confidence": confidence,
                **(properties or {}),
            }
            new_node = SemanticNode(object_id, object_type, merged_props, cycle)
            self._nodes[object_id] = new_node
            self._node_edges[object_id] = []
            self._add_edge(object_id, "environment", "located_in")

        self._last_update_cycle = max(self._last_update_cycle, cycle)
        pos = position or {}
        return DetectedObject(
            id=object_id,
            object_type=object_type,
            position=dict(pos) if isinstance(pos, dict) else {},
            confidence=confidence,
            last_seen_cycle=cycle,
            properties=properties or {},
        )

    def get_object(self, object_id: str) -> Optional[DetectedObject]:
        node = self._nodes.get(object_id)
        if node is None:
            return None
        pos = node.properties.get("position", {})
        return DetectedObject(
            id=node.id,
            object_type=node.node_type,
            position=dict(pos) if isinstance(pos, dict) else {},
            confidence=node.properties.get("confidence", 0.0),
            last_seen_cycle=node.last_seen_cycle,
            properties={
                k: v for k, v in node.properties.items()
                if k not in ("position", "confidence")
            },
        )

    def get_objects_by_type(self, object_type: str) -> List[DetectedObject]:
        return [
            self.get_object(n.id) for n in self._nodes.values()
            if n.node_type == object_type
        ]

    def remove_stale_objects(self, current_cycle: int, max_age: int = 10) -> int:
        before = len(self._nodes)
        stale_ids = [
            nid for nid, n in self._nodes.items()
            if n.node_type in ("object", "obstacle", "waypoint", "landmark")
            and current_cycle - n.last_seen_cycle > max_age
        ]
        for sid in stale_ids:
            self.remove_object(sid)
        return len(stale_ids)

    def remove_object(self, object_id: str) -> bool:
        if object_id not in self._nodes:
            return False
        del self._nodes[object_id]
        if object_id in self._node_edges:
            edge_indices = set(self._node_edges[object_id])
            self._edges = [
                e for i, e in enumerate(self._edges) if i not in edge_indices
            ]
            del self._node_edges[object_id]
        for nid in self._node_edges:
            self._node_edges[nid] = [
                i for i in self._node_edges[nid]
                if i < len(self._edges) and not (
                    self._edges[i].source_id == object_id
                    or self._edges[i].target_id == object_id
                )
            ]
        return True

    def predict(self, steps: int = 1, **kwargs: Any) -> Dict[str, Any]:
        return {
            "predicted_obstacle_count": self.obstacle_count,
            "method": "semantic_inference",
            "note": "SemanticWorldModel does not perform temporal prediction",
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "type": "semantic",
            "nodes": [
                {
                    "id": n.id,
                    "node_type": n.node_type,
                    "properties": dict(n.properties),
                    "created_cycle": n.created_cycle,
                    "last_seen_cycle": n.last_seen_cycle,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "relation": e.relation,
                    "weight": e.weight,
                    "properties": dict(e.properties),
                }
                for e in self._edges
            ],
            "environment": self._environment.model_dump(),
            "uncertainty": self._uncertainty.model_dump(),
            "obstacle_count": self.obstacle_count,
        }

    def explain(self) -> str:
        parts = [
            "SemanticWorldModel",
            f"{len(self._nodes)} nodes, {len(self._edges)} edges",
        ]
        obstacles = self.obstacle_count
        if obstacles:
            parts.append(f"{obstacles} obstacle(s)")
        relations = set(e.relation for e in self._edges)
        if relations:
            parts.append(f"relations: {', '.join(sorted(relations))}")
        if self.has_sensor_degradation:
            degraded = [k for k, v in self._uncertainty.sensor_health.items() if v < 0.5]
            parts.append(f"sensor degradation: {', '.join(degraded)}")
        return " | ".join(parts)

    # --- semantic query methods ---

    def query_relations(self, node_id: str) -> List[Dict[str, Any]]:
        result = []
        edge_indices = self._node_edges.get(node_id, [])
        for ei in edge_indices:
            if ei < len(self._edges):
                e = self._edges[ei]
                result.append({
                    "source": e.source_id,
                    "target": e.target_id,
                    "relation": e.relation,
                    "weight": e.weight,
                })
        return result

    def query_connected_nodes(self, node_id: str, relation: Optional[str] = None) -> List[str]:
        connected: Set[str] = set()
        edge_indices = self._node_edges.get(node_id, [])
        for ei in edge_indices:
            if ei < len(self._edges):
                e = self._edges[ei]
                if relation is None or e.relation == relation:
                    if e.source_id == node_id:
                        connected.add(e.target_id)
                    else:
                        connected.add(e.source_id)
        return list(connected)

    def add_relation(
        self, source_id: str, target_id: str, relation: str,
        weight: float = 1.0,
    ) -> None:
        if source_id in self._nodes and target_id in self._nodes:
            self._add_edge(source_id, target_id, relation, weight)
