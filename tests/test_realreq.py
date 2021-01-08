# Copyright 2020 Tyler Calder
import unittest.mock
import os
import subprocess
import sys

import pytest
from pytest_mock import mocker


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import _realreq.realreq as realreq

CONTENT = """
import os
import requests
from foo import bar
from . import local_module
import local_module2
from foo.baz import frum
import abbrev
import src.local_module
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
}

_MOCK_DEP_VERSIONS = {
    "foo": "1.0.0",
    "baz": "0.1.0",
    "spam": "3.2.12",
    "egg": "13.0",
    "pip": "2.12.1",
    "wheel": "1.1.1",
    "notused": "201.10.1",
    "DevDep": "0.1.1",
    "testDep": "0.1.3",
    "abbreviation": "1.2.1",
}


def mock_pip_show(*args, **kwargs):
    pkg = args[0][2]
    try:
        deps = _MOCK_DEPENDENCY_TREE[pkg]
    except KeyError:
        raise subprocess.CalledProcessError(1, cmd="Test Command")
    mock_result = unittest.mock.MagicMock()
    mock_result.configure_mock(
        **{
            "stdout": "stuff\nRequires: {0}\nmore stuff".format(
                ", ".join(deps)
            ).encode()
        }
    )

    return mock_result


def mock_pip_freeze(*args, **kwargs):
    result = b"\n".join(
        ["{0}=={1}".format(k, v).encode() for k, v in _MOCK_DEP_VERSIONS.items()]
    )
    mock_result = unittest.mock.MagicMock()
    mock_result.configure_mock(**{"stdout": result})
    return mock_result


@pytest.fixture(scope="session", params=["src", "path/to/src"])
def source_files(
    tmp_path_factory, request,
):
    path = os.path.normpath(request.param)
    paths = path.split("/")
    if len(paths) > 1 and isinstance(paths, list):
        src = tmp_path_factory.mktemp(path[0], numbered=False)
        print(paths)
        for p in paths:
            src = src / p
            src.mkdir()
    else:
        src = tmp_path_factory.mktemp(path, numbered=False)
    main = src / "main.py"
    main.write_text(CONTENT)
    print(src)
    return src


def test_search_source_for_used_packages(source_files):
    """Source code is searched and aquires the name of all packages used"""
    print(source_files)
    pkgs = realreq._search_source(str(source_files))
    expected = [
        "requests",
        "foo",
        "local_module2",
        "abbreviation",
    ]
    assert set(pkgs) == set(expected)


def test_build_dependency_list(mocker):
    """Dependency Tree build out should identify all the dependencies a module has"""
    # Essentially we want to make sure that the values returned from the system
    # are what we would get by running `pip show x`, and then getting the "Requires" value
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = mock_pip_show

    pkgs = ["requests", "foo", "local_module2", "abbreviation"]
    dep_tree = realreq._build_dep_list(pkgs)
    assert all([_ in dep_tree for _ in list(_MOCK_DEPENDENCY_TREE.keys())])


def test_get_dependency_versions(mocker):
    """Dependency Versions should return dictionary with packages and versions"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = mock_pip_freeze

    pkgs = _MOCK_DEPENDENCY_TREE.keys()
    versions = realreq._get_dependency_versions(pkgs)
    assert versions == {
        "foo": "1.0.0",
        "baz": "0.1.0",
        "spam": "3.2.12",
        "egg": "13.0",
        "pip": "2.12.1",
        "wheel": "1.1.1",
        "abbreviation": "1.2.1",
    }


# class TestCLI:
#     """Tests for the CLI of realreq"""

#     def test_source_parameter_is_treated_as_path(self, source_files, mocker):
#         args = ["-s", "/fake/path"]
#         app = realreq._RealReq()
#         app(args)
#         assert False

