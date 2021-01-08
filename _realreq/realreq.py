#!/usr/bin/env python3
"""Real Requirements

Parses through the list of installed packages and explores your source code to
identify what the real requirements of your software are.
"""
import argparse
import json
import pathlib
import re
import subprocess


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
    app = _RealReq()
    app()


class _RealReq:
    """Main Application

    This will be a CLI tool used to gather information about the requirements
    actually used in your source code
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument(
            "-s", "--source", default=pathlib.Path("."), type=pathlib.Path
        )

    def __call__(self):
        # Gather imports
        # Find dependencies
        # Find Dependency versions
        args = self.parser.parse_args()
        pkgs = _search_source(args.source)
        deps = _build_dep_list(pkgs)
        dep_ver = _get_dependency_versions(deps)
        print("\n".join(["{0}=={1}".format(k, v) for k, v in dep_ver.items()]))


def _search_source(source):
    """Go through the source directory and identify all modules"""
    source_files = list(pathlib.Path(source).rglob("*.[Pp][Yy]"))

    imports = []
    for file_ in source_files:
        with file_.open() as f:
            lines = f.readlines()
        for line in lines:
            module = _scan_for_imports(line)
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

    # FIXME: This will only work if source is the name of the project. I.E
    # If source is a path (as it probably is, since that is what we expect to be
    # passed into the CLI
    source_module = pathlib.Path(source).stem
    print(source)
    print(source_module)
    imports.discard(source_module)
    for import_name, install_name in ALIASES.items():
        if import_name in imports:
            imports.remove(import_name)
            imports.add(install_name)

    return imports


def _scan_for_imports(line):
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


def _build_dep_list(pkgs):
    """Builds list of dependencies"""
    errs = []
    pkgs_ = list(pkgs)
    dependencies = {}

    while pkgs_:
        pkg = pkgs_.pop()
        if pkg in dependencies:
            # We've seen this already, lets not duplicate it
            # or it is in the standard library, and won't be found by pip show
            continue
        try:
            results = subprocess.run(
                ["pip", "show", pkg], stdout=subprocess.PIPE, check=True
            )
        except subprocess.CalledProcessError:
            errs.append(pkg)
            continue

        out_text = results.stdout.decode("utf-8").split("\n")
        for line in out_text:
            if line.startswith("Requires"):
                # Requires: is 9 chars long
                p = line[9:].strip().split(",")
                p = [_.strip() for _ in p if _ != ""]
                dependencies[pkg] = p
                pkgs_.extend(p)
    return list(dependencies.keys())


def _get_dependency_versions(dependencies):
    """Gets versions of dependencies"""
    results = subprocess.run(["pip", "freeze"], stdout=subprocess.PIPE, check=True)
    out_text = results.stdout.decode("utf-8").strip().split("\n")
    dep_ver = {}
    for line in out_text:
        dep, ver = line.split("==")
        if dep in dependencies:
            dep_ver[dep] = ver
    return dep_ver


if __name__ == "__main__":
    main()
