"""Tests for the Dependency Graph"""
import _realreq.requtils.dependency_tree as graph


class TestDependencyGraph:
    def test_add_dependency_works_for_empty_graph(self):
        g = graph.DependencyGraph()
        g.add_dependency("foo", "bar")
        assert g.get_dependencies("bar") == {"foo"}

    def test_add_node(self):
        g = graph.DependencyGraph()
        g.add_node("foo")
        assert set() == g.get_dependencies("foo")

    def test_invert(self):
        g = graph.DependencyGraph()
        g.add_dependency("foo", "bar")
        g = g.invert()
        assert g.get_dependencies("foo") == {"bar"}
