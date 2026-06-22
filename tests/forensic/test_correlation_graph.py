"""Tests for the forensic correlation EvidenceGraph."""

import pytest
from forensic.correlation.graph import EvidenceGraph


def test_add_nodes():
    """Test that adding unique nodes works."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message", body="Hello")
    graph.add_node("contact_1", "contact", name="Alice")

    assert len(graph.nodes) == 2
    assert "msg_1" in graph.nodes
    assert "contact_1" in graph.nodes
    assert graph.nodes["msg_1"].node_type == "message"
    assert graph.nodes["msg_1"].properties["body"] == "Hello"


def test_add_duplicate_node():
    """Test that adding a duplicate node doesn't create duplicates."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message", body="Hello")
    graph.add_node("msg_1", "message", body="Overwritten")

    assert len(graph.nodes) == 1
    assert graph.nodes["msg_1"].properties["body"] == "Hello"


def test_add_edge():
    """Test adding an edge between nodes."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message")
    graph.add_node("contact_1", "contact")
    graph.add_edge("msg_1", "contact_1", "sent_by")

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source == "msg_1"
    assert edge.target == "contact_1"
    assert edge.relation_type == "sent_by"


def test_add_edge_missing_nodes():
    """Test that adding an edge with missing nodes raises an error."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message")

    with pytest.raises(ValueError):
        graph.add_edge("msg_1", "nonexistent", "sent_by")

    with pytest.raises(ValueError):
        graph.add_edge("nonexistent", "msg_1", "sent_by")


def test_get_node():
    """Test retrieving a node by its ID."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message", body="Hello")

    node = graph.get_node("msg_1")
    assert node is not None
    assert node.node_id == "msg_1"
    assert node.node_type == "message"

    missing = graph.get_node("nonexistent")
    assert missing is None


def test_get_edges():
    """Test retrieving edges connected to a node."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message")
    graph.add_node("contact_1", "contact")
    graph.add_edge("msg_1", "contact_1", "sent_by")

    edges = graph.get_edges("msg_1")
    assert len(edges) == 1
    assert edges[0].relation_type == "sent_by"

    # Check that the edge is found for the target node too
    edges_target = graph.get_edges("contact_1")
    assert len(edges_target) == 1


def test_get_neighbors():
    """Test retrieving neighbors of a node."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message")
    graph.add_node("contact_1", "contact")
    graph.add_node("media_1", "media")
    graph.add_edge("msg_1", "contact_1", "sent_by")
    graph.add_edge("msg_1", "media_1", "contains_media")

    neighbors = graph.get_neighbors("msg_1")
    assert len(neighbors) == 2

    neighbor_ids = [n[0] for n in neighbors]
    relation_types = [n[1] for n in neighbors]

    assert "contact_1" in neighbor_ids
    assert "media_1" in neighbor_ids
    assert "sent_by" in relation_types
    assert "contains_media" in relation_types


def test_to_dict():
    """Test converting the graph to a dictionary."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message", body="Hello")
    graph.add_node("contact_1", "contact", name="Alice")
    graph.add_edge("msg_1", "contact_1", "sent_by")

    data = graph.to_dict()

    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    # Check node representation
    node_ids = [n["id"] for n in data["nodes"]]
    assert "msg_1" in node_ids
    assert "contact_1" in node_ids

    # Check edge representation
    edge = data["edges"][0]
    assert edge["source"] == "msg_1"
    assert edge["target"] == "contact_1"
    assert edge["type"] == "sent_by"


def test_from_dict():
    """Test reconstructing a graph from a dictionary."""
    data = {
        "nodes": [
            {"id": "msg_1", "type": "message", "properties": {"body": "Hello"}},
            {"id": "contact_1", "type": "contact", "properties": {"name": "Alice"}},
        ],
        "edges": [
            {
                "source": "msg_1",
                "target": "contact_1",
                "type": "sent_by",
                "properties": {},
            },
        ],
    }

    graph = EvidenceGraph.from_dict(data)

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert "msg_1" in graph.nodes
    assert "contact_1" in graph.nodes

    # Verify the edge
    edge = graph.edges[0]
    assert edge.source == "msg_1"
    assert edge.target == "contact_1"
    assert edge.relation_type == "sent_by"


def test_round_trip():
    """Test that to_dict -> from_dict preserves the graph."""
    graph = EvidenceGraph()
    graph.add_node("msg_1", "message", body="Hello")
    graph.add_node("contact_1", "contact", name="Alice")
    graph.add_node("media_1", "media", path="/tmp/media.jpg")
    graph.add_edge("msg_1", "contact_1", "sent_by")
    graph.add_edge("msg_1", "media_1", "contains_media")

    data = graph.to_dict()
    reconstructed = EvidenceGraph.from_dict(data)

    assert len(reconstructed.nodes) == 3
    assert len(reconstructed.edges) == 2
    assert "msg_1" in reconstructed.nodes
    assert "contact_1" in reconstructed.nodes
    assert "media_1" in reconstructed.nodes

    # Verify edges are correct
    edge_types = [e.relation_type for e in reconstructed.edges]
    assert "sent_by" in edge_types
    assert "contains_media" in edge_types


def test_empty_graph():
    """Test operations on an empty graph."""
    graph = EvidenceGraph()

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0
    assert graph.get_node("nonexistent") is None
    assert graph.get_edges("nonexistent") == []
    assert graph.get_neighbors("nonexistent") == []

    data = graph.to_dict()
    assert data["nodes"] == []
    assert data["edges"] == []

    reconstructed = EvidenceGraph.from_dict(data)
    assert len(reconstructed.nodes) == 0
    assert len(reconstructed.edges) == 0
