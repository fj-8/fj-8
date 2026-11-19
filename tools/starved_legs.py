#!/usr/bin/env python3
"""Print the recent `main` runs of the repositories this profile describes, and
which legs of each never got a runner.

    GITHUB_TOKEN=… python3 tools/starved_legs.py [repo …]        # default: all four

The paragraph in README.md about a badge that is not green is a claim about the
run list, and the run list is the only part of the account that moves without
anybody pushing anything: a queued run can be replaced, a starved leg can be
re-run, and the prose says nothing about either. So the prose quotes a closed
range of commits, and this is the command that produced it and can produce the
next one. It prints what happened, in newest-first order, and does not decide
whether a page should be edited — the range in the prose stays true either way,
and the only thing that can go stale is a sentence that says "the most recent".

A leg is called `starved` when it ended `cancelled` having never been given a
runner: no steps, no start time, nothing to read. A run that finishes holding no
jobs at all is a different thing — it was still queued when a newer push replaced
it, so nothing was tested and nothing failed. The API token is read from the same
place `check_claims.py` reads it, because the two scripts ask the same host the
same question and only differ in what they print.
"""

import sys
from check_claims import api_json

HOST = "https://api.github.com"
REPOS = ["karg", "bitlane", "sift", "turnstile"]
LIMIT = 15


def completed_runs(repo):
    """The last `LIMIT` `main` runs that reached a verdict, newest first."""
    data = api_json(f"/repos/fj-8/{repo}/actions/runs?branch=main&event=push&per_page=50")
    if not data:
        return None
    runs = []
    for run in data["workflow_runs"]:
        if run["status"] != "completed":
            continue
        jobs = api_json(run["jobs_url"].removeprefix(HOST) + "?per_page=100") or {}
        runs.append((run["head_sha"][:7], run["conclusion"], jobs.get("jobs", [])))
        if len(runs) == LIMIT:
            break
    return runs


def describe(job):
    if job["conclusion"] != "cancelled":
        return job["conclusion"] or job["status"]
    return "starved" if not job["steps"] else "cancelled mid-run"


def main(argv):
    repos = argv[1:] or REPOS
    unreadable = False
    for repo in repos:
        runs = completed_runs(repo)
        print(f"== {repo}")
        if runs is None:
            print("  not measured: the API needs a token and an answer\n")
            unreadable = True
            continue
        for sha, verdict, jobs in runs:
            if not jobs:
                # Nothing ran, so nothing can be reported about the code.
                print(f"{sha}  {verdict:<9} no job started   (0 jobs)")
                continue
            odd = [f"{describe(j)} {j['name']}" for j in jobs if j["conclusion"] != "success"]
            print(f"{sha}  {verdict:<9} {', '.join(odd) or 'every job green'}"
                  f"   ({len(jobs)} jobs)")
        starved = sum(1 for _, _, jobs in runs
                      for j in jobs if describe(j) == "starved")
        green = sum(1 for _, _, jobs in runs if jobs and not
                    [j for j in jobs if j["conclusion"] != "success"])
        nothing = sum(1 for _, _, jobs in runs if not jobs)
        print(f"  {starved} legs starved and {green} runs fully green across "
              f"{len(runs)} completed runs, {nothing} of them finishing with no "
              f"job started\n")
    return 1 if unreadable else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
