#!/usr/bin/env python3
# Copyright 2020-2022, Tyler Calder
"""Real Requirements

Parses through the list of installed packages and explores your source code to
identify what the real requirements of your software are.

The entirety of the implementation is considered private and shouldn't be relied
on for as a stable interface.
"""
import argparse
import enum
import json
import pathlib
import re
import subprocess
import typing


IMPORT_RE = re.compile(
    r"(from )?(?(1)(?P<from>[a-zA-Z0-9._]*)|import (?P<import>[a-zA-Z0-9+._]*))"
)

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


class ParsedShowOutput(typing.NamedTuple):
    name: str
    deps: typing.List[str]


class RealReq:
    """Main Application

    This will be a CLI tool used to gather information about the requirements
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
        self._args = self.parser.parse_args()

    def __call__(self):
        # Gather imports
        # Find dependencies
        # Find Dependency versions
        pkgs = search_source(self._args.source, aliases=self._read_aliases())
        if self._args.deep:
            pkgs = build_dep_list(pkgs)
        dep_ver = get_dependency_versions(pkgs)
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


def search_source(source, aliases=ALIASES):
    """Go through the source directory and identify all modules"""
    source_files = list(pathlib.Path(source).rglob("*.[Pp][Yy]"))

    imports = []
    for file_ in source_files:
        with file_.open() as f:
            lines = f.readlines()
        for line in lines:
            module = scan_for_imports(line)
            if module:
                imports.append(module)

    # Now we want to clean out the imports that we have
    # 1. Eliminate the imports which start with `.` These are relative
    #   imports, and so don't matter for pip requirements
    # 2. Split imports on `.` we only want the top level module name
    # 3. Remove STD LIB imports
    # 4. Remove imports whose name begins with the same name as `source` these
    #   are local modules, not modules being installed from pip
    # 5. Rename imports who have an Alias record
    imports = [m for m in imports if not m.startswith(".")]
    imports = [m.split(".")[0] for m in imports]
    imports = [m for m in imports if m not in STD_LIBS]
    imports = set(imports)

    source_module = pathlib.Path(source).stem
    imports.discard(source_module)
    for import_name, install_name in aliases.items():
        if import_name in imports:
            imports.remove(import_name)
            imports.add(install_name)

    return imports


def scan_for_imports(line):
    """Scans line for import syntax, returning the name of the module imported"""
    lm = IMPORT_RE.match(line)
    if lm:
        module = (
            lm.groupdict()["from"]
            if lm.groupdict()["from"]
            else lm.groupdict()["import"]
        )
        return module
    else:
        return ""


def build_dep_list(pkgs):
    """Builds list of dependencies"""
    errs = []
    pkgs_ = set(pkgs)
    dependencies = {}

    while pkgs_:
        try:
            results = subprocess.run(
                [
                    "pip",
                    "show",
                ]
                + list(pkgs_),
                stdout=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError:
            errs.append(pkg)
            continue

        found_deps = set()
        for out in results.stdout.decode().split("---\n"):
            p = get_deps_from_output(out)
            dependencies[p.name] = p.deps
            found_deps |= set(p.deps)

        # Clean up pkgs_ to only be new dependencies that need to be searched
        pkgs_ = found_deps - pkgs_
    return list(dependencies.keys())


def get_deps_from_output(out: str) -> ParsedShowOutput:
    out_text = out.split("\n")
    deps = []
    for line in out_text:
        if line.startswith("Name"):
            name = line[5:].strip()
        elif line.startswith("Requires"):
            # Requires: is 9 chars long
            deps = line[9:].strip().split(",")
            deps = [_.strip() for _ in deps if _ != ""]
    return ParsedShowOutput(name=name, deps=deps)


def get_dependency_versions(dependencies):
    """Gets versions of dependencies"""
    results = subprocess.run(["pip", "freeze"], stdout=subprocess.PIPE, check=True)
    versions = parse_versions(results.stdout)
    dep_ver = dict(filter(lambda i: i[0] in dependencies, versions.items()))
    return dep_ver


def parse_versions(freeze_out: bytes) -> typing.Dict[str, str]:
    out_text = freeze_out.decode("utf-8").strip().split("\n")
    versions = {}
    for line in out_text:
        if "==" in line:
            dep, _ = line.split("==")
        else:
            dep, _ = line.split(" ", maxsplit=1)
        versions[dep] = line
    return versions


if __name__ == "__main__":
    main()
