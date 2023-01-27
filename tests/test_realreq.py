# Copyright 2020-2023 Tyler Calder
import collections
import contextlib
import io
import unittest.mock
import os
import sys
import typing
import pathlib

import pytest
import pytest_mock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import _realreq.realreq as realreq
import _realreq.requtils as requtils

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

MOCK_ALIASES = {"abbrev": "abbreviation"}
realreq.ALIASES = MOCK_ALIASES

_MOCK_DEPENDENCY_TREE = {
    "foo": ["bar"],
    "requests": ["baz", "spam"],
    "baz": [],
    "spam": ["egg", "wheel"],
    "egg": ["pip"],
    "pip": [],
    "wheel": [],
    "abbreviation": [],
    "fake-pkg": [],
}

_MOCK_DEPENDENCY_TREE_INVERTED = {
    "foo": [],
    "bar": ["foo"],
    "baz": ["requests"],
    "spam": ["requests"],
    "egg": ["spam"],
    "wheel": ["spam"],
    "pip": ["egg"],
    "abbreviation": [],
    "fake-pkg": [],
    "requests": [],
}

_MOCK_DEPENDENCY_TREE_OUTPUT = """- abbreviation
- bar
  |- foo
- baz
  |- requests
- fake-pkg
- pip
  |- egg
    |- spam
      |- requests
- wheel
  |- spam
    |- requests
"""

_MOCK_DEP_VERSIONS = {
    "foo": "1.0.0",
    "bar": "git-repo @ git+https://github.com/example/user/bar.git@1.2.3",
    "baz": "0.1.0",
    "spam": "3.2.12",
    "egg": "13.0",
    "pip": "2.12.1",
    "wheel": "1.1.1",
    "notused": "201.10.1",
    "DevDep": "0.1.1",
    "testDep": "0.1.3",
    "abbreviation": "1.2.1",
    "requests": "0.2.0",
    "fake-pkg": "0.0.1",
}

_DEEP_DEPENDENCIES = collections.OrderedDict(
    [
        ("abbreviation", "1.2.1"),
        ("bar", "git-repo @ git+https://github.com/example/user/bar.git@1.2.3"),
        ("baz", "0.1.0"),
        ("egg", "13.0"),
        ("foo", "1.0.0"),
        ("pip", "2.12.1"),
        ("requests", "0.2.0"),
        ("spam", "3.2.12"),
        ("wheel", "1.1.1"),
    ]
)

_SHALLOW_DEPENDENCIES = collections.OrderedDict(
    [
        ("abbreviation", "1.2.1"),
        ("foo", "1.0.0"),
        ("requests", "0.2.0"),
    ]
)


def mock_pip_show(*args, **kwargs):
    pkgs = args[0][2:]
    pkg_output = []
    for pkg in pkgs:
        try:
            deps = _MOCK_DEPENDENCY_TREE[pkg]
        except KeyError:
            continue
        pkg_output.append(
            "Name: {name}\nstuff\nRequires: {deps}\nmore stuff\n".format(
                name=pkg, deps=", ".join(deps)
            )
        )

    mock_result = unittest.mock.MagicMock()
    mock_result.configure_mock(**{"stdout": "---\n".join(pkg_output).encode()})

    return mock_result


def mock_pip_freeze(*args, **kwargs):
    result = b"\n".join(
        ["{0}=={1}".format(k, v).encode() for k, v in _MOCK_DEP_VERSIONS.items()]
    )
    mock_result = unittest.mock.MagicMock()
    mock_result.configure_mock(**{"stdout": result})
    return mock_result


def mock_subprocess_run(*args, **kwargs):
    """Mock calls to subprocess by routing them to the right mock"""
    command = args[0][1]
    if command == "show":
        return mock_pip_show(*args, **kwargs)
    elif command == "freeze":
        return mock_pip_freeze(*args, **kwargs)


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


def test_search_source_for_used_packages(source_files):
    """Source code is searched and aquires the name of all packages used"""
    pkgs = realreq.search_source(source_files)
    expected = [
        "requests",
        "foo",
        "local_module2",
        "abbrev",
        "fake_pkg",
    ]
    assert set(pkgs) == set(expected)


def test_build_dependency_list(mocker):
    """Dependency Tree build out should identify all the dependencies a module has"""
    # Essentially we want to make sure that the values returned from the system
    # are what we would get by running `pip show x`, and then getting the "Requires" value
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = mock_pip_show

    pkgs = ["requests", "foo", "local_module2", "abbreviation", "fake-pkg"]
    dep_tree = requtils.build_dep_list(pkgs)
    assert all([_ in dep_tree for _ in list(_MOCK_DEPENDENCY_TREE.keys())])


def test_get_dependency_versions(mocker):
    """Dependency Versions should return dictionary with packages and versions"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = mock_pip_freeze

    pkgs = _MOCK_DEPENDENCY_TREE.keys()
    versions = requtils.get_dependency_versions(pkgs)
    assert versions == {
        "foo": "foo==1.0.0",
        "baz": "baz==0.1.0",
        "spam": "spam==3.2.12",
        "egg": "egg==13.0",
        "pip": "pip==2.12.1",
        "wheel": "wheel==1.1.1",
        "abbreviation": "abbreviation==1.2.1",
        "requests": "requests==0.2.0",
        "fake-pkg": "fake-pkg==0.0.1",
    }


def test_parse_versions():
    out_ = b"foo==1.0.0\nbaz==0.1.0\ngit-repo @ git+https://github.com/gitrepo@commit"
    assert {
        "foo": "foo==1.0.0",
        "baz": "baz==0.1.0",
        "git-repo": "git-repo @ git+https://github.com/gitrepo@commit",
    } == requtils.parse_versions(out_)


class CLIMocker:
    def __init__(self, cli_args):
        self._cli_args = cli_args
        self._orig_argv = None

    def __enter__(self):
        self._orig_argv = sys.argv
        patched_argv = unittest.mock.patch.object(sys, "argv", self._cli_args)
        self._patched_argv = patched_argv.start()
        self._mock_run = unittest.mock.patch("subprocess.run").start()
        self._mock_run.side_effect = mock_subprocess_run

    def __exit__(self, exc_type, exc_value, traceback):
        sys.argv = self._orig_argv
        self._mock_run.stop()


def run_realreq():
    app = realreq.RealReq()
    app()


CLIFlag = typing.Tuple


class ArgvBuilder:
    """Builds out the Command Line Argv"""

    def __init__(self):
        self._argvs = ["cmd"]

    def add_flag(self, flag: CLIFlag):
        self._argvs.extend(flag)
        return self

    def arguments(self):
        return self._argvs.copy()


class TestCLI:
    """Tests for the CLI of realreq"""

    def execute_with_args(self, args: typing.List[str]) -> str:
        """
        Executes realreq with the given args returning

        Args:
            args: List of the arguments that would be passed via the CLI

        Returns: the output of the execution
        """
        output_buff = io.StringIO()

        with CLIMocker(args), contextlib.redirect_stdout(output_buff):
            run_realreq()
        output_buff.seek(0)
        return output_buff.read()

    def test_default_flags(self, source_flag, source_files):
        args = ArgvBuilder().add_flag(source_flag(source_files)).arguments()
        actual = self.execute_with_args(args)
        assert actual == "".join(
            "{0}=={1}\n".format(k, v) for k, v in _SHALLOW_DEPENDENCIES.items()
        )

    def test_deep_flag(self, source_flag, source_files, deep_flag):
        args = (
            ArgvBuilder()
            .add_flag(source_flag(source_files))
            .add_flag(deep_flag())
            .arguments()
        )
        actual = self.execute_with_args(args)
        assert actual == "".join(
            "{0}=={1}\n".format(k, v) for k, v in _DEEP_DEPENDENCIES.items()
        )

    def test_cli_aliases(
        self,
        source_flag,
        source_files,
        alias_flag,
    ):
        """Makes Sure Aliases are used"""
        args = (
            ArgvBuilder()
            .add_flag(source_flag(source_files))
            .add_flag(alias_flag("fake_pkg=fake-pkg"))
            .arguments()
        )
        actual = self.execute_with_args(args)
        assert "fake-pkg==0.0.1" in actual

    def test_file_aliases(self, source_flag, source_files, tmp_path, alias_file):
        """Makes Sure Aliases are used"""
        f = tmp_path / "alias_file.txt"
        f.write_bytes(b"fake_pkg=fake-pkg")
        args = (
            ArgvBuilder()
            .add_flag(source_flag(source_files))
            .add_flag(alias_file(f.absolute()))
            .arguments()
        )
        actual = self.execute_with_args(args)
        assert "fake-pkg==0.0.1" in actual

    def test_cli_overrides_file_aliases(
        self, source_flag, source_files, tmp_path, alias_flag, alias_file
    ):
        """Makes Sure cli args overrides file aliases"""
        f = tmp_path / "alias_file.txt"
        f.write_bytes(b"fake_pkg=false-pkg")

        args = (
            ArgvBuilder()
            .add_flag(source_flag(source_files))
            .add_flag(alias_file(f.absolute()))
            .add_flag(alias_flag("fake_pkg=fake-pkg"))
            .arguments()
        )
        actual = self.execute_with_args(args)
        assert "fake-pkg==0.0.1" in actual

    def test_cli_invert_tree(self, source_flag, source_files, invert_flag, alias_flag):
        args = (
            ArgvBuilder()
            .add_flag(source_flag(source_files))
            .add_flag(invert_flag())
            .add_flag(alias_flag("fake_pkg=fake-pkg"))
            .arguments()
        )
        actual = self.execute_with_args(args)
        assert actual == _MOCK_DEPENDENCY_TREE_OUTPUT
