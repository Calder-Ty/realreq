# Copyright 2022, Tyler Calder
"""Classes for outputing Dependency trees"""
# Can't use Typing.protocol, because it is only introduced in 3.8, until then
# We must just Support a simple protocol for display.
# def display(dependency_tree: Mapping[str, List[str]])
import typing
from . import requtils


class FreezeDisplay:
    """Freeze Display just writes out the dependencies in same format at pip freeze"""

    @classmethod
    def display(_cls, dependency_tree: typing.Mapping[str, typing.Sequence[str]]):
        pkgs = dependency_tree.keys()
        dep_ver = requtils.get_dependency_versions(pkgs)
        sorted_list = sorted(list(dep_ver.items()), key=lambda x: x[0])
        print("\n".join(["{0}".format(v) for _, v in sorted_list]))


class TreeDisplay:
    """This displays Dependencies as a tree"""
    _INDENT_LEVEL = 0

    @classmethod
    def display(_cls, dependency_tree: typing.Mapping[str, typing.Sequence[str]]):
        pkgs = dependency_tree.keys()
        dep_ver = requtils.get_dependency_versions(pkgs)
        sorted_list = sorted(list(dep_ver.items()), key=lambda x: x[0])

        # TODO: this will double print trees
        for pkg in sorted_list:
            _cls._print_tree(pkg, dependency_tree)

    @classmethod
    def _print_tree(_cls, name, tree):
        if not _cls._INDENT_LEVEL:
            print(f"- {name}")
        else:
            # Print pkg with indent, and tree marker
            print(f"{'  '*_cls._INDENT_LEVEL}|- {name}")
        children = tree[name]
        if children:
            _cls._INDENT_LEVEL += 1
            for child in children:
                _cls._print_tree(child, tree)
            _cls._INDENT_LEVEL -= 1
