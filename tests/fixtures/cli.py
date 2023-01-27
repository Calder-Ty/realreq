import pytest
import pathlib
import typing

CONTENT = """
import os
import requests
from foo import bar
from . import local_module
import local_module2
from foo.baz import frum
import abbrev
import src.local_module
import fake_pkg
"""

@pytest.fixture(params=["-s", "--source"])
def source_flag(request):
    return lambda path: (request.param, str(path))


@pytest.fixture(params=["-a", "--alias"])
def alias_flag(request):
    return lambda mapping: (request.param, mapping)


@pytest.fixture(params=["-d", "--deep"])
def deep_flag(request):
    return lambda: (request.param,)


@pytest.fixture(params=["-i", "--invert"])
def invert_flag(request):
    return lambda: (request.param,)


@pytest.fixture()
def alias_file():
    return lambda path: ("--alias-file", str(path))


@pytest.fixture(
    scope="session",
    params=["src", "double//to//src", "path/to/src", "go/to/src/module.py"],
)
def source_files(
    tmp_path_factory,
    request,
):
    """
    Creates a temp directory with a source file

    This is a session scoped directory, so the files should be ONLY be read, and not modified.

    Returns: path to directory being used for test
    """
    path = pathlib.Path(request.param)
    src = _create_source_directory(tmp_path_factory, path)

    # Write out source file
    if _is_module(path):
        module = path.name
        src = src / module
        src.write_text(CONTENT)
    else:
        main = src / "main.py"
        main.write_text(CONTENT)
    return src


def _is_module(path: pathlib.Path) -> bool:
    """Tests if path is a Python Module"""
    return path.suffix.lower() == ".py"


def _create_source_directory(tmp_path_factory, path: pathlib.Path) -> pathlib.Path:
    """Creates the source directory given by path"""
    parents = _parent_dirs(path)

    # Minus 2 because of the implicit "." dir at the top of the parents list
    src = tmp_path_factory.mktemp(parents[len(parents) - 2], numbered=False)
    for p in list(reversed(parents))[2:]:
        src = src / p.stem
        src.mkdir()
    return src


def _parent_dirs(path: pathlib.Path) -> typing.Sequence[pathlib.Path]:
    if not _is_module(path):
        # Hack to get all parts of the path
        return (path / "child").parents
    return path.parents
