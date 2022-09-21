"""Implementation of a Dependency Tree stucture"""
import typing


class _Dependency:
    def __init__(
        self,
        name: str,
        dependencies: typing.Optional[typing.List[str]] = None,
        dependants: typing.Optional[typing.List[str]] = None,
    ):
        self.name = name
        self.dependencies = set(dependencies) if dependencies is not None else set()
        self.dependants = set(dependants) if dependants is not None else set()

    def invert(self):
        self.dependants, self.dependencies = self.dependencies, self.dependants


class DependencyTree:
    pass


class DependencyGraph:
    """
    A dependency graph that holds information on all dependencies and their connections.

    Iterating over the graph will return every node and it's dependencies.
    """

    def __init__(self):
        self._nodes: typing.dict[str, _Dependency] = {}

    def __iter__(self):
        for k in self._nodes.keys():
            yield (k, self.get_dependencies(k))

    def nodes(self):
        """Return name of all nodes in the graph"""
        return list(self._nodes.keys())

    def add_node(self, name: str):
        """Add a Node to the dependency Graph"""
        self._nodes.setdefault(name, _Dependency(name))

    def add_dependency(self, name: str, dependant: str):
        """Add the name as a dependency of the given dependant"""
        requirement = self._nodes.setdefault(name, _Dependency(name))
        dep = self._nodes.setdefault(dependant, _Dependency(dependant))

        dep.dependencies.add(name)
        requirement.dependants.add(dependant)

    def get_dependencies(self, name) -> typing.Collection[str]:
        """Get a list of dependencies"""
        deps = self._get_node(name)
        if deps is None:
            KeyError(f"Node {name} does not exist in the graph")
        return deps.dependencies

    def get_dependants(self, name) -> typing.Collection[str]:
        deps = self._get_node(name)
        if deps is None:
            KeyError(f"Node {name} does not exist in the graph")
        return deps.dependants

    def _get_node(self, name) -> _Dependency:
        dep = self._nodes.get(name)
        return dep

    def invert(self):
        """Inverts the relationships in the graph"""
        for deps in self._nodes.values():
            deps.invert()
        return self
