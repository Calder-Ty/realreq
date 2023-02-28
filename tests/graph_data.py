"""Create the Graph Data for testing"""
import configparser
import typing
import pathlib


def _config_list(data: str) -> typing.List[str]:
    """Convenience Function to explain how we handle lists in the config"""
    list_data = data.split(",")
    list_data = [d.strip() for d in list_data]
    if list_data == [""]:
        list_data = []
    return list_data


Subset = typing.Optional[typing.Iterator[str]]


class GraphTestData:
    """Reads in a Graph config and generates the expected values for testing"""

    def __init__(self, config_path: pathlib.Path, subset: Subset = None):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        assert (
            len(self.config.sections()) != 0
        ), f"Empty or Non-Existant Config: {str(config_path.absolute())}"
        self._subset: Subset = subset
        self._set_dependencies()

    def _set_dependencies(
        self,
    ):
        self._dependencies = {
            key: _config_list(self.config[key]["dependencies"])
            for key in self.config.sections()
        }
        if self._subset:
            self._limit_dependencies()

    def _limit_dependencies(self):
        # Start by priming deps with all the dependencies
        # That exist in subset list given
        deps = [d for d in self._dependencies if d in self._subset]
        # Start with the given Deps as our parents
        parents = deps
        while True:
            # Get the children of our current crop of parents
            children = list(self._get_dependencies(parents))
            if len(children) == 0:
                # No More Children, lets end
                break
            # Don't forget to add the children to the deps
            deps.extend(children)
            # Use the children as the parents for next generation to get the
            # Next group of children
            parents = children

        self._dependencies = {
            key: value for key, value in self._dependencies.items() if key in deps
        }

    def _get_dependencies(self, deps) -> typing.Set:
        children = set()
        for dep in deps:
            children |= set(self._dependencies[dep])
        return children

    def dep_list(self) -> typing.Dict[str, str]:
        return self._dependencies

    def inverted_list(self) -> typing.Dict[str, str]:
        return {
            key: _config_list(self.config[key]["dependents"])
            for key in self.config.sections()
        }

    def dep_versions(self) -> typing.Dict[str, str]:
        """Returns a Dictionary that is Ordered to be in alphabetical order"""
        deps = [(dep, self.config[dep]["version"]) for dep in self._dependencies]
        deps = sorted(deps, key=lambda tup: tup[0])
        return dict(deps)
