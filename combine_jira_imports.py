"""
combine_jira_imports.py
-----------------------
Combines multiple Jira Cloud import JSON files into a single file.

Dog tag
-------
  Name     : combine_jira_imports.py
  Project  : jira-data-generator
  Repo     : https://github.com/emretoptanci/jira-data-generator
  Author   : Emre Toptancı (https://github.com/emretoptanci)
  Version  : 1.0.0
  Updated  : 2026-10-12
  Requires : Python 3.9+ (standard library only)
  Input    : Two or more Jira Cloud JSON importer files (e.g. from generate_jira_import.py)
  Output   : A single Jira Cloud JSON importer file (users + projects/issues/history)

Merging rules
-------------
  users    — deduplicated by accountId; first occurrence of each accountId wins.
  projects — grouped by project key; issues from every file are concatenated in
             the order the files are supplied; project-level metadata (name,
             description, lead, type) is taken from the first file that defines
             each project key.

Usage
-----
python combine_jira_imports.py FILE [FILE ...] [--output OUTPUT]

Examples
--------
# Combine all demo_import_*.json files (shell glob)
python combine_jira_imports.py demo_import_*.json

# Explicit file list with a custom output path
python combine_jira_imports.py a.json b.json c.json --output combined.json
"""

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def _merge_users(all_users: list[list[dict]]) -> list[dict]:
    """
    Flatten and deduplicate users from multiple files.
    Deduplication key: accountId. First occurrence wins.
    """
    seen: dict[str, dict] = {}
    for users in all_users:
        for user in users:
            aid = user["accountId"]
            if aid not in seen:
                seen[aid] = user
    return list(seen.values())


def _merge_projects(all_projects: list[list[dict]]) -> list[dict]:
    """
    Merge project lists from multiple files, keyed on project key.

    - Project-level metadata (name, description, lead, type) comes from the
      first file that defines each project key.
    - Issues from all files that share the same project key are concatenated
      in the order the files were supplied.
    """
    meta: dict[str, dict]        = {}   # project key → non-issues fields
    issues: dict[str, list[dict]] = {}  # project key → accumulated issues

    for projects in all_projects:
        for project in projects:
            key = project["key"]
            if key not in meta:
                meta[key] = {k: v for k, v in project.items() if k != "issues"}
                issues[key] = []
            issues[key].extend(project.get("issues", []))

    result = []
    for key, project_meta in meta.items():
        entry = dict(project_meta)
        entry["issues"] = issues[key]
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Top-level combiner
# ---------------------------------------------------------------------------

def combine(paths: list[str]) -> dict:
    """Load each file and merge their contents into a single document."""
    datasets: list[dict] = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            datasets.append(json.load(f))

    return {
        "users":    _merge_users   ([d.get("users",    []) for d in datasets]),
        "projects": _merge_projects([d.get("projects", []) for d in datasets]),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine multiple Jira Cloud import JSON files into one.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Input JSON files to combine (at least two)",
    )
    parser.add_argument(
        "--output", "-o",
        default="combined_import.json",
        metavar="PATH",
        help="Output file path",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if len(args.files) < 2:
        print("[error] At least two input files are required.", file=sys.stderr)
        sys.exit(1)

    missing = [f for f in args.files if not Path(f).exists()]
    if missing:
        for f in missing:
            print(f"[error] File not found: {f}", file=sys.stderr)
        sys.exit(1)

    print(f"[info] Combining {len(args.files)} file(s): {', '.join(args.files)}")

    data = combine(args.files)

    total_users    = len(data["users"])
    total_projects = len(data["projects"])
    total_issues   = sum(len(p["issues"]) for p in data["projects"])

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(
        f"[info] Written {total_users} user(s), {total_projects} project(s), "
        f"{total_issues} issue(s) -> {args.output}"
    )


if __name__ == "__main__":
    main()
