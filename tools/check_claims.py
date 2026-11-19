#!/usr/bin/env python3
"""Check the numbers in this profile's table against the repositories they name.

    python3 tools/check_claims.py README.md <repos-root>

`<repos-root>` holds `karg/`, `bitlane/`, `sift/` and `turnstile/`, cloned or
checked out. The profile is the only page in the account whose claims live in
other people's trees, so it is measured against a copy of those trees rather
than against a remembered one.

Every check prefers the file that holds the fact to the prose that quotes it: a
case is a line in a test source, a header is a path, a dependency is a parsed
TOML section, a benchmark second is a line in a committed transcript. Where a
number can only be read from the repository that measures it, the source column
says so — "this was matched against its own badge, not re-derived here" is a
thing the output should say out loud instead of leaving the reader to guess.

Exit status is 0 only when every check agrees.
"""

import ast
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from sys import stdlib_module_names
from urllib.request import Request, urlopen

WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
         8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}

CPP_STANDARD_HEADERS = {
    "algorithm", "array", "atomic", "barrier", "bit", "cassert", "clocale",
    "cmath", "codecvt", "compare", "concepts", "cstddef", "cstdint", "cstdio",
    "cstdlib", "cstring", "ctime", "charconv", "execution", "filesystem",
    "format", "forward_list", "fstream", "functional", "initializer_list",
    "iomanip", "iosfwd", "iostream", "istream", "iterator", "latch", "limits",
    "list", "map", "memory", "memory_resource", "numbers", "optional", "queue",
    "ranges", "scoped_allocator", "set", "shared_mutex", "source_location",
    "span", "spanstream", "sstream", "stack", "stacktrace", "stdexcept",
    "stop_token", "streambuf", "string", "string_view", "syncstream", "thread",
    "tuple", "typeindex", "typeinfo", "type_traits", "unordered_map",
    "unordered_set", "utility", "valarray", "variant", "vector", "version",
}

# The three packages turnstile's own import-allowlist job permits.
JAVA_ALLOWLIST = {"java.lang.invoke", "java.util", "java.util.concurrent"}

# `__future__` is a compiler directive, not a module the process links at run
# time, so it does not belong in a list of imports a README enumerates.
NON_MODULES = {"__future__"}


def read(path):
    return Path(path).read_text(encoding="utf-8")


def badge_number(markdown, name, suffix):
    hit = re.search(r"/badge/" + re.escape(name) + r"-(\d+)" + re.escape(suffix), markdown)
    return hit and int(hit.group(1))


def table_cells(profile_text):
    """The third column of the profile's table, keyed by repository name."""
    cells = {}
    for line in profile_text.splitlines():
        columns = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(columns) != 3:
            continue
        name = re.search(r"\[\*\*(\w+)\*\*\]", columns[0])
        if name and name.group(1) != "What":
            cells[name.group(1)] = columns[2]
    return cells


def python_imports(root):
    found = set()
    for path in Path(root).rglob("*.py"):
        for node in ast.walk(ast.parse(read(path), filename=str(path))):
            if isinstance(node, ast.Import):
                found.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level:
                found.add(node.module.split(".")[0])
    return found - NON_MODULES


def angle_includes(root):
    found = set()
    for path in Path(root).rglob("*.hpp"):
        found.update(re.findall(r"^\s*#include\s*<([\w.]+)>", read(path), re.MULTILINE))
    return found


def java_roots(root):
    """The package prefix each `import` in the tree is drawn from, to the depth
    the allowlist works at (two or three segments)."""
    roots = set()
    for path in Path(root).rglob("*.java"):
        for name in re.findall(r"^\s*import (?:static )?([\w.]+);", read(path), re.MULTILINE):
            if not name.startswith("java."):
                roots.add(name)
                continue
            parts = name.split(".")
            for depth in (3, 2):
                candidate = ".".join(parts[:depth])
                if candidate in JAVA_ALLOWLIST:
                    roots.add(candidate)
                    break
            else:
                roots.add(name)
    return roots


def count_lines(path):
    return read(path).count("\n")


WORDS_TO_NUMBER = {word: number for number, word in WORDS.items()}


def as_number(token):
    """The profile writes five and ten in words and 32 and 231 in digits, the way
    a sentence does. Read whichever it used, so a measurement is compared with a
    number rather than with a string that happens to look like one."""
    token = token.strip().rstrip(".")
    if token.isdigit():
        return int(token)
    return WORDS_TO_NUMBER.get(token.lower(), token)


def live_job_count(repo):
    """Jobs in the most recent completed `main` run, read from the API.

    A job count is the one claim in the profile that lives in the run list and
    not in a file, so it is checked there when the environment allows it. None
    means it was not measured — no token, no network, no finished run — which is
    reported as a skip rather than as a disagreement, because a claim this
    script could not look at has not been shown to be wrong.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return None
    request = Request(
        f"https://api.github.com/repos/fj-8/{repo}/actions/runs"
        "?branch=main&status=completed&event=push&per_page=10",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    try:
        with urlopen(request, timeout=30) as response:
            runs = json.load(response)["workflow_runs"]
        for run in runs:
            # A queued main run that a newer push replaced finishes with no jobs
            # at all; it is not a record of how many jobs the workflow has.
            with urlopen(Request(run["jobs_url"] + "?per_page=100", headers=request.headers),
                         timeout=30) as response:
                total = json.load(response)["total_count"]
            if total:
                return total
        return None
    except (OSError, KeyError, ValueError):
        return None


class Report:
    """Rows of two kinds: a `number` compares a quoted figure with a measured one,
    a `fact` says whether the file the claim points at contains what the claim
    says it does. `skip` is a third state for a claim the script could not look at,
    which is neither agreement nor disagreement."""

    def __init__(self):
        self.rows = []

    def number(self, repo, label, quoted, measured, source):
        self.rows.append((repo, label, str(quoted), str(measured), source, "number"))

    def fact(self, repo, label, ok, source):
        self.rows.append((repo, label, "claimed", "confirmed" if ok else "NOT FOUND",
                          source, "fact"))

    def skip(self, repo, label, quoted, source):
        self.rows.append((repo, label, str(quoted), "not measured", source, "skip"))

    def render(self, profile_path):
        width = max(len(r[1]) for r in self.rows) + 1
        print(f"profile {profile_path}\n")
        failures = skips = 0
        for repo, label, quoted, measured, source, kind in self.rows:
            if kind == "skip":
                flag, skipped = "skip", True
            else:
                skipped = False
                agrees = measured == "confirmed" if kind == "fact" else quoted == measured
                flag = "ok  " if agrees else "FAIL"
            failures += 0 if skipped or flag == "ok  " else 1
            skips += 1 if skipped else 0
            print(f"{flag} {repo:<10} {label:<{width}} {quoted:>9} / {measured:>12}"
                  f"   {source}")
        checked = len(self.rows) - skips
        print(f"\n{checked - failures}/{checked} of the claims this script could measure "
              f"match the repositories they describe; {skips} skipped.")
        return 1 if failures else 0


def check_karg(root, claim, prose, out):
    repo = root / "karg"
    readme = read(repo / "README.md")
    cargo = tomllib.loads(read(repo / "Cargo.toml"))
    out.number("karg", "tests", re.search(r"\b(\d+) tests", claim).group(1),
               badge_number(readme, "tests", "%20passing"),
               "karg's badge; cargo adds the doc tests, so karg's CI is the measurer")
    out.number("karg", "MSRV", re.search(r"MSRV ([\d.]+)", claim).group(1),
               cargo["package"]["rust-version"], "Cargo.toml package.rust-version")
    out.fact("karg", "unsafe_code = forbid",
             "#![forbid(unsafe_code)]" in read(repo / "src" / "lib.rs"), "src/lib.rs")
    out.fact("karg", "both dep tables empty",
             not cargo.get("dependencies") and not cargo.get("dev-dependencies"),
             "Cargo.toml, parsed")


def check_bitlane(root, claim, prose, out):
    repo = root / "bitlane"
    readme = read(repo / "README.md")
    cases = sum(len(re.findall(r"^\s*TEST\(", read(p), re.MULTILINE))
                for p in (repo / "tests").glob("*.cpp"))
    out.number("bitlane", "ctest cases", re.search(r"\b(\d+) `ctest` cases", claim).group(1),
               cases, "TEST( registrations in tests/*.cpp")
    out.number("bitlane", "  its badge says", badge_number(readme, "tests", "%20passing"),
               cases, "badge against the same measurement")
    headers = list((repo / "include" / "bitlane").glob("*.hpp"))
    out.number("bitlane", "headers", as_number(re.search(r"\b(\w+) headers", claim).group(1)),
               len(headers), "include/bitlane/*.hpp")
    out.number("bitlane", "  its badge says", badge_number(readme, "header--only", "%20files"),
               len(headers), "badge against the same count")
    foreign = sorted(angle_includes(repo / "include") - CPP_STANDARD_HEADERS)
    out.fact("bitlane", "one SSE2 lane, nothing else", foreign == ["emmintrin.h"],
             f"non-standard <angle> includes: {foreign}")
    codec = read(repo / "include" / "bitlane" / "codec.hpp")
    out.fact("bitlane", "FNV-1a-64 over the frame", "fnv1a" in codec
             and "1469598103934665603" in codec, "fnv1a and its offset basis in codec.hpp")


def check_sift(root, claim, prose, out):
    repo = root / "sift"
    readme = read(repo / "README.md")
    cases = sum(len(re.findall(r"^\s*def test_", read(p), re.MULTILINE))
                for p in (repo / "tests").rglob("*.py"))
    out.number("sift", "unittest cases", re.search(r"\b(\d+) `unittest` cases", claim).group(1),
               cases, "def test_ methods in tests/")
    out.number("sift", "  its badge says", badge_number(readme, "tests", "%20passing"), cases,
               "badge against the same count")
    imports = python_imports(repo / "src" / "sift")
    out.number("sift", "  third-party", len(imports - set(stdlib_module_names)), 0,
               "ast over src/sift against sys.stdlib_module_names")
    named = {m.strip() for m in re.search(r"imports only stdlib modules — ([^—]+) —", prose)
             .group(1).replace("`", "").split(",")}
    out.fact("sift", "that list is exact", named == imports,
             f"prose names {len(named)}, src/sift imports {len(imports)}"
             + (f", difference {sorted(named ^ imports)}" if named != imports else ""))
    out.fact("sift", "test_package.py guards it",
             "stdlib_module_names" in read(repo / "tests" / "test_package.py"),
             "tests/test_package.py")
    transcript = read(repo / "bench" / "bench-full.txt")
    seconds = float(re.search(r"total ([\d.]+) s", transcript).group(1))
    out.number("sift", "benchmark seconds", re.search(r"a (\d+) s benchmark", claim).group(1),
               round(seconds), f"bench/bench-full.txt totals {seconds} s")
    ratios = {float(r) for r in re.findall(r"([\d.]+)x slower", transcript)}
    loss = re.search(r"is ([\d.]+)×–([\d.]+)× slower", prose)
    for quoted in loss.groups() if loss else ():
        out.fact("sift", f"the {quoted}x loss it quotes", float(quoted) in ratios,
                 "bench/bench-full.txt, as a measured row")


def check_turnstile(root, claim, prose, out):
    repo = root / "turnstile"
    readme = read(repo / "README.md")
    suite = read(repo / "src" / "test" / "java" / "turnstile" / "TurnstileTest.java")
    cases = len(re.findall(r"Harness\.test\(", suite))
    out.number("turnstile", "cases", re.search(r"\b(\d+) cases", claim).group(1), cases,
               "Harness.test( registrations")
    out.number("turnstile", "  its badge says", badge_number(readme, "tests", "%20passing"),
               cases, "badge against the same count")
    jobs = live_job_count("turnstile")
    quoted_jobs = as_number(re.search(r"(\w+) CI jobs", claim).group(1))
    if jobs is None:
        out.skip("turnstile", "CI jobs", quoted_jobs,
                 "the run list, which needs an API token and a finished run")
    else:
        out.number("turnstile", "CI jobs", quoted_jobs, jobs,
                   "jobs in the most recent completed main run")
    out.number("turnstile", "Harness.java lines",
               re.search(r"(\d+) lines of `Harness\.java`", prose).group(1),
               count_lines(repo / "src" / "test" / "java" / "turnstile" / "Harness.java"),
               "the file itself")
    bench = len(list((repo / "bench").glob("bench-run-*.txt")))
    stride = len(list((repo / "bench").glob("stride-run-*.txt")))
    quoted_bench, quoted_stride = (as_number(g) for g in re.search(
        r"(\w+) bench launches and (\w+) of the padding", claim).groups())
    out.number("turnstile", "bench transcripts", quoted_bench, bench, "bench/bench-run-*.txt")
    out.number("turnstile", "padding A/B transcripts", quoted_stride, stride,
               "bench/stride-run-*.txt")
    out.number("turnstile", "  committed in all",
               as_number(re.search(r"(\w+) committed transcripts", claim).group(1)),
               bench + stride, "both kinds together")
    roots = java_roots(repo / "src" / "main")
    out.fact("turnstile", "nothing outside the JDK", roots == JAVA_ALLOWLIST,
             "imports in src/main, three packages"
             + ("" if roots == JAVA_ALLOWLIST else f", difference {sorted(roots ^ JAVA_ALLOWLIST)}"))


CHECKS = {"karg": check_karg, "bitlane": check_bitlane, "sift": check_sift,
          "turnstile": check_turnstile}


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    profile, root = Path(argv[1]), Path(argv[2])
    text = read(profile)
    cells = table_cells(text)
    if set(cells) != set(CHECKS):
        print(f"expected the table to hold {sorted(CHECKS)}, found {sorted(cells)}")
        return 2
    out = Report()
    for name, check in CHECKS.items():
        check(root, cells[name], text, out)
    return out.render(profile)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
