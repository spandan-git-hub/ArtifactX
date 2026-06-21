"""Evidence graph for forensic correlation."""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class Node:
    """A node in the evidence graph."""
    node_id: str
    node_type: str  # e.g., 'wa_message', 'wa_contact', 'media_item'
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """An edge in the evidence graph."""
    source: str
    target: str
    relation_type: str  # e.g., 'sent_by', 'contains_media', 'matches_contact'
    properties: Dict[str, Any] = field(default_factory=dict)


class EvidenceGraph:
    """A graph representing entities and relationships in forensic evidence."""

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        # Index for fast lookup: node_id -> set of edge indices
        self._edge_indices: Dict[str, Set[int]] = {}

    def add_node(self, node_id: str, node_type: str, **properties) -> None:
        """Add a node to the graph."""
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id=node_id, node_type=node_type, properties=properties)
            self._edge_indices[node_id] = set()

    def add_edge(
        self, source: str, target: str, relation_type: str, **properties
    ) -> None:
        """Add an edge to the graph."""
        # Ensure nodes exist
        if source not in self.nodes:
            raise ValueError(f"Source node {source} does not exist.")
        if target not in self.nodes:
            raise ValueError(f"Target node {target} does not exist.")

        edge_index = len(self.edges)
        edge = Edge(source=source, target=target, relation_type=relation_type, properties=properties)
        self.edges.append(edge)

        # Update index
        self._edge_indices[source].add(edge_index)
        self._edge_indices[target].add(edge_index)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by its ID."""
        return self.nodes.get(node_id)

    def get_edges(self, node_id: str) -> List[Edge]:
        """Get all edges connected to a node."""
        if node_id not in self._edge_indices:
            return []
        return [self.edges[i] for i in self._edge_indices[node_id]]

    def get_neighbors(self, node_id: str) -> List[Tuple[str, str]]:
        """Get (neighbor_id, relation_type) for a node."""
        neighbors = []
        for edge in self.get_edges(node_id):
            neighbor = edge.target if edge.source == node_id else edge.source
            neighbors.append((neighbor, edge.relation_type))
        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        """Convert the graph to a dictionary representation."""
        return {
            "nodes": [
                {"id": nid, "type": node.node_type, "properties": node.properties}
                for nid, node in self.nodes.items()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.relation_type,
                    "properties": edge.properties,
                }
                for edge in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceGraph":
        """Create a graph from a dictionary representation."""
        graph = cls()
        for node_data in data.get("nodes", []):
            graph.add_node(
                node_data["id"],
                node_data["type"],
                **node_data.get("properties", {}),
            )
        for edge_data in data.get("edges", []):
            graph.add_edge(
                edge_data["source"],
                edge_data["target"],
                edge_data["type"],
                **edge_data.get("properties", {}),
            )
        return graph