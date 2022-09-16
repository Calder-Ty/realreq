"""Implementation of a Dependency Tree stucture"""
import typing


class _Dependency:
    def __init__(
        self, name: str, dependencies: typing.Optional[typing.List[str]] = None
    ):
        self.name = name
        self.dependencies = set(dependencies) if dependencies is not None else set()


class DependencyTree:
    pass


class DependencyGraph:
    """
    A dependency graph that holds information on all dependencies and their connections.
    """

    def __init__(self):
        self._dependencies: typing.dict[str, _Dependency] = {}

    def add_node(self, name: str):
        """Add a Node to the dependency Graph"""
        self._dependencies[name] = _Dependency(name)

    def add_dependency(self, name: str, dependant: str):
        """Add the name as a dependency of the given dependant"""
        _ = self._dependencies.setdefault(name, _Dependency(name))
        dep = self._dependencies.setdefault(dependant, _Dependency(dependant))
        dep.dependencies.add(name)

    def get_dependencies(self, name) -> typing.Collection[str]:
        """Get a list of dependencies"""
        deps = self._get_node(name).dependencies
        if deps is None:
            KeyError(f"Node {name} does not exist in the graph")
        return deps

    def _get_node(self, name) -> _Dependency:
        dep = self._dependencies.get(name)
        return dep
