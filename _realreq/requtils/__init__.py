"""Real Req Utilities"""
import re
import subprocess
import typing
from . import dependency_tree as dep_graph


IMPORT_RE = re.compile(
    r"(from )?(?(1)(?P<from>[a-zA-Z0-9._]*)|import (?P<import>[a-zA-Z0-9+._]*))"
)
PIP_SHOW_SEP = "---\n"


class ParsedShowOutput(typing.NamedTuple):
    name: str
    deps: typing.List[str]


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
    return build_dep_tree(pkgs).nodes()


def build_dep_tree(pkgs: typing.List[str]) -> dep_graph.DependencyGraph:
    pkgs_ = set(pkgs)
    dependencies = dep_graph.DependencyGraph()
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
            # FIXME: No Error message or tracking happening
            continue

        found_deps = set()
        for out in results.stdout.decode().split(PIP_SHOW_SEP):
            p = get_deps_from_output(out)
            dependencies.add_node(p.name)
            for dep in p.deps:
                dependencies.add_dependency(dep, p.name)
            found_deps |= set(p.deps)

        # Clean up pkgs_ to only be new dependencies that need to be searched
        pkgs_ = found_deps - pkgs_
    return dependencies


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

    deps: typing.List[str]
