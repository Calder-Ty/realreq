"""Tests for the Dependency Graph"""
import _realreq.requtils.dependency_tree as graph


class TestDependencyGraph:
    def test_add_dependency_works_for_empty_graph(self):
        g = graph.DependencyGraph()
        g.add_dependency("foo", "bar")
        assert g.get_dependencies("bar") == {"foo"}
