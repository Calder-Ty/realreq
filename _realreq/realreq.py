#!/usr/bin/env python3
# Copyright 2020-2022, Tyler Calder
"""Real Requirements

Parses through the list of installed packages and explores your source code to
identify what the real requirements of your software are.

The entirety of the implementation is considered private and shouldn't be relied
on for as a stable interface.
"""
import argparse
import json
import pathlib
import typing

import _realreq.requtils as requtils
import _realreq.display as display


HERE_PATH = pathlib.Path(__file__).resolve().parent.absolute()

# Convert pathlib.Path to str for python 3.5 compatability
with open(str(HERE_PATH / "std_lib.json")) as fi:
    STD_LIBS = json.load(fi)["libs"]


with open(str(HERE_PATH / "aliases.json")) as fi:
    ALIASES = json.load(fi)


def main():
    """Application entry point"""
    app = RealReq()
    app()


class RealReq:
    """Main Application

    This wll be a CLI tool used to gather information about the requirements
    actually used in your source code
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            epilog="A command line tool for gathering the actual requirements from your python source code."
        )
        self.parser.add_argument(
            "-d",
            "--deep",
            action="store_true",
            help="Conduct a recursive search to completely define your dependencies (recommended for executable distributions).",
        )
        self.parser.add_argument(
            "-s",
            "--source",
            default=pathlib.Path("."),
            type=pathlib.Path,
            help="Path to your source file (Defaults to the current directory).",
        )
        self.parser.add_argument(
            "-a",
            "--alias",
            action="append",
            help="Set an alias for package names in <import name>=<install name> format. Can be specified multiple times.",
        )
        self.parser.add_argument(
            "--alias-file",
            type=pathlib.Path,
            help="Path to text file containing aliases in <import name>=<install name> format",
        )
        self.parser.add_argument(
            "-i",
            "--invert",
            action="store_true",
            help="Display dependencies in inverted tree format",
        )

        self._args = self.parser.parse_args()

    def __call__(self):
        pkgs = search_source(self._args.source, aliases=self._read_aliases())

        if self._args.deep or self._args.invert:
            tree = requtils.build_dep_tree(pkgs)
            if self._args.invert:
                display.TreeDisplay.display(tree.invert())
            else:
                display.FreezeDisplay.display(tree)

        # TODO: Shallow search doesn't generate a tree, but a list so for now
        # We handle seperately, lets unify the handling
        else:
            dep_ver = requtils.get_dependency_versions(pkgs)
            sorted_list = sorted(list(dep_ver.items()), key=lambda x: x[0])
            print("\n".join(["{0}".format(v) for _, v in sorted_list]))

    def _read_aliases(self) -> typing.Dict[str, str]:
        # Split user_aliases
        cli_aliases = {}
        file_aliases = {}

        if not (self._args.alias or self._args.alias_file):
            return ALIASES
        if self._args.alias:
            cli_aliases = split_aliases(self._args.alias)
        if self._args.alias_file:
            with self._args.alias_file.open() as fi:
                file_aliases = split_aliases(fi.readlines())

        return {**ALIASES, **file_aliases, **cli_aliases}


def split_aliases(aliases: typing.List[str]) -> typing.Dict[str, str]:
    res = [a.strip().split("=") for a in aliases]
    if any([len(_) != 2 for _ in res]):
        raise ValueError("Aliases must be in format of 'IMPORT_ALIAS'='PKG_NAME'")
    return dict(res)


def search_source(source: pathlib.Path, aliases: typing.Dict = ALIASES):
    """Go through the source directory and identify all modules"""
    source_files = find_all_source_files(source)
    imports = find_imports(source_files)
    imports = clean_imports(imports, source)

    for import_name, install_name in aliases.items():
        if import_name in imports:
            imports.remove(import_name)
            imports.add(install_name)

    return imports


def find_all_source_files(source: pathlib.Path):
    """Generates a list of all source files"""
    if is_module(source):
        return [source]
    else:
        return list(source.rglob("*.[Pp][Yy]"))


def is_module(path: pathlib.Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".py"


def find_imports(source_files: typing.List[pathlib.Path]) -> typing.List[str]:
    imports = []
    for file_ in source_files:
        with file_.open() as f:
            lines = f.readlines()
        for line in lines:
            module = requtils.scan_for_imports(line)
            if module:
                imports.append(module)
    return imports


def clean_imports(imports: typing.List[str], source: pathlib.Path) -> typing.Set[str]:
    """Clean out the imports that we have to what we need

    Eliminates Relative imports, reorganizes to only the top level module, removes std_lib modules
    and removes local modules.
    """
    imports = filter_relative_imports(imports)
    imports = filter_to_top_level_package(imports)
    imports = filter_std_libs(imports)
    # 4. Remove imports whose name begins with the same name as `source` these
    #   are local modules, not modules being installed from pip
    imports = set(imports)
    filter_local(imports, source)
    return imports


def filter_relative_imports(imports: typing.List[str]) -> typing.List[str]:
    return [m for m in imports if not m.startswith(".")]


def filter_to_top_level_package(imports: typing.List[str]) -> typing.List[str]:
    return [m.split(".")[0] for m in imports]


def filter_std_libs(imports: typing.List[str]) -> typing.List[str]:
    return [m for m in imports if m not in STD_LIBS]


def filter_local(imports: typing.Set[str], source: pathlib.Path):
    source_module = source.resolve().parent.stem if is_module(source) else source.stem
    imports.discard(source_module)


if __name__ == "__main__":
    main()
