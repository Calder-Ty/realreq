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
import graph_data
from tests.fixtures.cli import (
    tempdir,
    source_flag,
    alias_flag,
    deep_flag,
    invert_flag,
    alias_file,
    source_files,
)


import _realreq.realreq as realreq
import _realreq.requtils as requtils

HERE = pathlib.Path(__file__).parent
GRAPH_PATH = HERE / "dependency_graphs/default.graph"
GRAPH = graph_data.GraphTestData(HERE / "dependency_graphs/default.graph")
# Use Abbrev to test builtin ALIASES
MOCK_ALIASES = {"abbrev": "abbreviation"}
realreq.ALIASES = MOCK_ALIASES

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


def mock_pip_show(*args, **kwargs):
    pkgs = args[0][2:]
    pkg_output = []
    for pkg in pkgs:
        try:
            deps = GRAPH.show_output(pkg)
        except KeyError:
            continue
        pkg_output.append(deps)

    mock_result = unittest.mock.MagicMock()
    mock_result.configure_mock(**{"stdout": "\n---\n".join(pkg_output).encode()})

    return mock_result


def mock_pip_freeze(*args, **kwargs):
    result = b"\n".join(
        ["{0}=={1}".format(k, v).encode() for k, v in GRAPH.dep_versions().items()]
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


def test_search_source_for_used_packages(source_files):
    """Source code is searched and acquires the name of all packages used"""
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
    expected = list(graph_data.GraphTestData(GRAPH_PATH, subset=pkgs).dep_list().keys())

    assert all([_ in dep_tree for _ in expected])
    assert all([_ in expected for _ in dep_tree])


def test_get_dependency_versions(mocker):
    """Dependency Versions should return dictionary with packages and versions"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = mock_pip_freeze

    pkgs = GRAPH.dep_list().keys()
    versions = requtils.get_dependency_versions(pkgs)
    assert versions == {
        "foo": "foo==1.0.0",
        "bar": "bar==git-repo @ git+https://github.com/example/user/bar.git@1.2.3",
        "baz": "baz==0.1.0",
        "devdep": "devdep==7.1.2",
        "spam": "spam==3.2.12",
        "egg": "egg==13.0",
        "notused": "notused==201.10.1",
        "pip": "pip==2.12.1",
        "wheel": "wheel==1.1.1",
        "testdep": "testdep==0.1.3",
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
        graph = graph_data.GraphTestData(
            GRAPH_PATH, subset=["requests", "foo", "abbreviation", "fake_pkg"]
        )
        expected = graph.shallow_dep_versions()
        assert actual == "".join("{0}=={1}\n".format(k, v) for k, v in expected.items())

    def test_deep_flag(self, source_flag, source_files, deep_flag):
        args = (
            ArgvBuilder()
            .add_flag(source_flag(source_files))
            .add_flag(deep_flag())
            .arguments()
        )
        graph = graph_data.GraphTestData(
            GRAPH_PATH, subset=["requests", "foo", "abbreviation", "fake_pkg"]
        )
        expected = graph.dep_versions()
        actual = self.execute_with_args(args)
        assert actual == "".join("{0}=={1}\n".format(k, v) for k, v in expected.items())

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
