import os
import pytest
import pathlib
import shutil
import tempfile
import typing
import configparser

cfg = configparser.ConfigParser()
cfg.read("./tests/sources/default.cfg")

CONTENT = cfg["source"]["source_text"]


@pytest.fixture
def tempdir():
    tmp = pathlib.Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp)


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
    params=["src", "double//to//src", "path/to/src", "go/to/src/module.py"],
)
def source_files(
    tempdir,
    request,
):
    """
    Creates a temp directory with a source file

    Returns: path to directory being used for test
    """
    path = pathlib.Path(request.param)
    src = _create_source_directory(tempdir, path)

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


def _create_source_directory(tempdir: pathlib.Path, path: pathlib.Path) -> pathlib.Path:
    """Creates the source directory given by path"""
    parents = _parent_dirs(path)

    # Minus 1 because of the implicit "." dir at the top of the parents list
    src = tempdir
    for p in list(reversed(parents))[1:]:
        src = src / p.stem
    src.mkdir(parents=True)
    return src


def _parent_dirs(path: pathlib.Path) -> typing.Sequence[pathlib.Path]:
    if not _is_module(path):
        # Hack to get all parts of the path
        return (path / "child").parents
    return path.parents
