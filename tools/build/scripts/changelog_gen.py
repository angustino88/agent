"""
CHANGELOG.md generator.

Reads git tag history and generates a structured CHANGELOG.md with one
section per version, listing the commit subjects between consecutive tags.
An [Unreleased] section is prepended when commits exist after the newest tag.

Output: CHANGELOG.md in the repository root.

Usage:
  changelog_gen.py               # write to <repo-root>/CHANGELOG.md
  changelog_gen.py --stdout      # print to stdout instead
  changelog_gen.py --since v1.0  # include only v1.0 and newer
  changelog_gen.py --max 20      # cap at the last N version tags
"""
import argparse
import subprocess
import sys
from pathlib import Path

import report

_ROOT_DIR = Path(__file__).resolve().parents[3]
_OUTPUT   = _ROOT_DIR / 'CHANGELOG.md'
_MAX_TAGS = 50   # safety cap


# ── Git helpers ───────────────────────────────────────────────────────────────

def _run(*args) -> str:
    return subprocess.check_output(
        list(args), cwd=str(_ROOT_DIR), stderr=subprocess.DEVNULL
    ).decode().strip()


def _tags() -> list[str]:
    """All version tags, newest first."""
    try:
        raw = _run('git', 'tag', '--sort=-version:refname')
        return [t for t in raw.splitlines() if t.strip()]
    except Exception:
        return []


def _tag_date(tag: str) -> str:
    try:
        return _run('git', 'log', '-1', '--format=%as', tag)  # YYYY-MM-DD
    except Exception:
        return '????-??-??'


def _commits_between(older: str | None, newer: str) -> list[str]:
    """Commit subjects in (older, newer] — oldest first."""
    try:
        ref = f'{older}..{newer}' if older else newer
        raw = _run('git', 'log', ref, '--oneline', '--no-merges', '--reverse')
        return [
            line.split(' ', 1)[1]
            for line in raw.splitlines()
            if ' ' in line
        ]
    except Exception:
        return []


# ── Generator ─────────────────────────────────────────────────────────────────

def generate(
    since: str | None = None,
    max_tags: int = _MAX_TAGS,
    to_stdout: bool = False,
) -> None:
    tags = _tags()
    if not tags:
        report.warn('No git tags found. Create a tag first:  git tag v1.0.0')
        return

    tags = tags[:max_tags]

    if since:
        if since in tags:
            tags = tags[: tags.index(since) + 1]   # include *since* and newer
        else:
            report.warn(f'Tag "{since}" not found — including all {len(tags)} tags.')

    lines: list[str] = [
        '# Changelog',
        '',
        'All notable changes are documented here.',
        'Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).',
        '',
        '---',
        '',
    ]

    # Unreleased section
    unreleased = _commits_between(tags[0], 'HEAD')
    if unreleased:
        lines += ['## [Unreleased]', '']
        lines += [f'- {c}' for c in unreleased]
        lines.append('')

    # One section per tag
    for i, tag in enumerate(tags):
        date    = _tag_date(tag)
        older   = tags[i + 1] if i + 1 < len(tags) else None
        commits = _commits_between(older, tag)
        lines  += [f'## [{tag}] — {date}', '']
        if commits:
            lines += [f'- {c}' for c in commits]
        else:
            lines.append('_No recorded commits in this release._')
        lines.append('')

    content = '\n'.join(lines)

    if to_stdout:
        print(content)
    else:
        _OUTPUT.write_text(content, encoding='utf-8')
        print()
        report.ok(
            f'{report.WHT}CHANGELOG.md{report.RST}  written  '
            f'{report.DIM}→  {_OUTPUT.relative_to(_ROOT_DIR)}{report.RST}'
        )
        report.info(
            f'{len(tags)} version tag(s)  |  '
            f'{len(unreleased)} unreleased commit(s)'
        )
        print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate CHANGELOG.md from git tags and commit history.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--stdout', action='store_true',
                        help='Print to stdout instead of writing CHANGELOG.md')
    parser.add_argument('--since',  metavar='TAG',
                        help='Include only tags >= TAG')
    parser.add_argument('--max',    type=int, default=_MAX_TAGS, metavar='N',
                        help=f'Max number of version tags (default: {_MAX_TAGS})')
    args = parser.parse_args()
    generate(since=args.since, max_tags=args.max, to_stdout=args.stdout)


if __name__ == '__main__':
    main()
