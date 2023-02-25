"""Create the Graph Data for testing"""
import configparser
import typing
import pathlib


def _config_list(data: str) -> typing.List[str]:
    """Convenience Function to explain how we handle lists in the config"""
    return data.split(",")


Subset = typing.Optional[typing.Iterator[str]]


class GraphTestData:
    """Reads in a Graph config and generates the expected values for testing"""

    def __init__(self, config_path: pathlib.Path):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        assert (
            len(self.config.sections()) != 0
        ), f"Empty or Non-Existant Config: {str(config_path.absolute())}"

    def dep_list(self) -> typing.Dict[str, str]:
        return {
            key: _config_list(self.config[key]["dependencies"])
            for key in self.config.sections()
        }

    def inverted_list(self) -> typing.Dict[str, str]:
        return {
            key: _config_list(self.config[key]["dependents"])
            for key in self.config.sections()
        }
