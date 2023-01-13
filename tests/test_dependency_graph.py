"""Tests for the Dependency Graph"""
import pytest
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

    def test_get_nonexistent_dependency(self):
        g = graph.DependencyGraph()
        with pytest.raises(KeyError):
            g.get_dependencies("no")

    def test_get_nonexistent_dependant(self):
        g = graph.DependencyGraph()
        with pytest.raises(KeyError):
            g.get_dependants("no")
