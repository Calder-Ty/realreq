# Copyright 2020-2022 Tyler Calder
import collections
import contextlib
import io
import unittest.mock
import os
import subprocess
import sys

import pytest
from pytest_mock import mocker


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


@pytest.fixture(scope="session", params=["src", "path/to/src"])
def source_files(
    tmp_path_factory,
    request,
):
    """Creates a temp directory that tests different source files

    returns: path to directory being used for test
    """
    path = os.path.normpath(request.param)
    paths = path.split("/")
    if len(paths) > 1 and isinstance(paths, list):
        src = tmp_path_factory.mktemp(path[0], numbered=False)
        for p in paths:
            src = src / p
            src.mkdir()
    else:
        src = tmp_path_factory.mktemp(path, numbered=False)
    main = src / "main.py"
    main.write_text(CONTENT)
    return src


def test_search_source_for_used_packages(source_files):
    """Source code is searched and aquires the name of all packages used"""
    pkgs = realreq.search_source(str(source_files))
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


class TestCLI:
    """Tests for the CLI of realreq"""

    @pytest.mark.parametrize("s_flag", ["-s", "--source"])
    def test_default_flags(self, source_files, mocker, s_flag):
        args = ["cmd", s_flag, str(source_files)]
        mocker.patch.object(sys, "argv", args)
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = mock_subprocess_run

        sbuff = io.StringIO()
        with contextlib.redirect_stdout(sbuff):
            app = realreq.RealReq()
            app()
        sbuff.seek(0)
        assert sbuff.read() == "".join(
            "{0}=={1}\n".format(k, v) for k, v in _SHALLOW_DEPENDENCIES.items()
        )

    @pytest.mark.parametrize("s_flag", ["-s", "--source"])
    @pytest.mark.parametrize("d_flag", ["-d", "--deep"])
    def test_deep_flag(self, source_files, mocker, s_flag, d_flag):
        args = ["cmd", s_flag, str(source_files), d_flag]
        mocker.patch.object(sys, "argv", args)
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = mock_subprocess_run

        sbuff = io.StringIO()
        with contextlib.redirect_stdout(sbuff):
            app = realreq.RealReq()
            app()
        sbuff.seek(0)
        assert sbuff.read() == "".join(
            "{0}=={1}\n".format(k, v) for k, v in _DEEP_DEPENDENCIES.items()
        )

    @pytest.mark.parametrize("s_flag", ["-s", "--source"])
    @pytest.mark.parametrize("a_flag", ["-a", "--alias"])
    def test_cli_aliases(
        self,
        source_files,
        mocker,
        s_flag,
        a_flag,
    ):
        """Makes Sure Aliases are used"""
        args = ["cmd", s_flag, str(source_files), a_flag, "fake_pkg=fake-pkg"]
        mocker.patch.object(sys, "argv", args)
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = mock_subprocess_run

        sbuff = io.StringIO()
        with contextlib.redirect_stdout(sbuff):
            app = realreq.RealReq()
            app()
        sbuff.seek(0)
        assert "fake-pkg==0.0.1" in sbuff.read()

    @pytest.mark.parametrize("s_flag", ["-s", "--source"])
    def test_file_aliases(
        self,
        source_files,
        tmp_path,
        mocker,
        s_flag,
    ):
        """Makes Sure Aliases are used"""
        f = tmp_path / "alias_file.txt"
        f.write_bytes(b"fake_pkg=fake-pkg")
        args = ["cmd", s_flag, str(source_files), "--alias-file", str(f.absolute())]
        mocker.patch.object(sys, "argv", args)
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = mock_subprocess_run

        sbuff = io.StringIO()
        with contextlib.redirect_stdout(sbuff):
            app = realreq.RealReq()
            app()
        sbuff.seek(0)
        assert "fake-pkg==0.0.1" in sbuff.read()

    @pytest.mark.parametrize("s_flag", ["-s", "--source"])
    @pytest.mark.parametrize("a_flag", ["-a", "--alias"])
    def test_cli_overrides_file_aliases(
        self,
        source_files,
        tmp_path,
        mocker,
        s_flag,
        a_flag,
    ):
        """Makes Sure Aliases are used"""
        f = tmp_path / "alias_file.txt"
        f.write_bytes(b"fake_pkg=false-pkg")

        args = [
            "cmd",
            s_flag,
            str(source_files),
            "--alias-file",
            str(f.absolute()),
            a_flag,
            "fake_pkg=fake-pkg",
        ]
        mocker.patch.object(sys, "argv", args)
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = mock_subprocess_run

        sbuff = io.StringIO()
        with contextlib.redirect_stdout(sbuff):
            app = realreq.RealReq()
            app()
        sbuff.seek(0)
        assert "fake-pkg==0.0.1" in sbuff.read()

    @pytest.mark.parametrize("s_flag", ["-s", "--source"])
    @pytest.mark.parametrize("a_flag", ["-a", "--alias"])
    @pytest.mark.parametrize("i_flag", ["-i", "--invert"])
    def test_cli_invert_tree(self, source_files, mocker, s_flag, a_flag, i_flag):
        args = ["cmd", s_flag, str(source_files), i_flag, a_flag, "fake_pkg=fake-pkg"]
        mocker.patch.object(sys, "argv", args)
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = mock_subprocess_run

        sbuff = io.StringIO()
        with contextlib.redirect_stdout(sbuff):
            app = realreq.RealReq()
            app()
        sbuff.seek(0)
        assert sbuff.read() == _MOCK_DEPENDENCY_TREE_OUTPUT
