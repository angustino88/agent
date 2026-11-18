#!/usr/bin/env python3
"""
Generate or update prj/config/version/index.json with Git metadata.

This script lives under `tools/build/scripts` so build tooling can invoke it
consistently from build and deploy scripts.

Usage:
  python tools/build/scripts/generate_version.py --output prj/config/version/index.json
  python tools/build/scripts/generate_version.py --output prj/config/version/index.json --print-version
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

import report


def run_cmd(args, cwd=None):
    try:
        return subprocess.check_output(args, cwd=cwd, text=True).strip()
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate version metadata file with git commit SHA.")
    parser.add_argument("--output", "-o", default="prj/config/version/index.json", help="Output JSON path")
    parser.add_argument("--template", "-t", default=None, help="Optional template JSON to merge")
    parser.add_argument("--print-version", action="store_true",
                        help="Print the 'latest' version from the output file and exit (no write)")
    args = parser.parse_args()

    if args.print_version:
        try:
            with open(args.output, "r", encoding="utf-8") as f:
                print(json.load(f).get("latest", ""))
        except Exception as exc:
            report.fail(f'Could not read version from {args.output}: {exc}')
            sys.exit(1)
        return

    cwd = os.getcwd()

    full = run_cmd(["git", "rev-parse", "HEAD"], cwd)
    short = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd)
    branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    commit_date = run_cmd(["git", "show", "-s", "--format=%cI", "HEAD"], cwd)

    data = {}
    src = args.template if args.template else args.output
    if os.path.exists(src):
        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    if short:
        data["gitCommit"] = short
    if full:
        data["gitCommitFull"] = full
    if branch:
        data["gitBranch"] = branch
    if commit_date:
        data["gitCommitDate"] = commit_date

    data["buildTimeUtc"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    data["generator"] = "tools/build/scripts/generate_version.py"

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    report.ok(f'Wrote {args.output}')


if __name__ == "__main__":
    main()
