"""
Interactive version bumper.

Updates APP_VERSION and CHANGELOG in version_config.py and optionally
creates a git commit for the change.

Usage:
  bump_version.py                   # interactive
  bump_version.py --patch           # bump patch (1.2.3 → 1.2.4)
  bump_version.py --minor           # bump minor (1.2.3 → 1.3.0)
  bump_version.py --major           # bump major (1.2.3 → 2.0.0)
  bump_version.py --version 3.0.0   # set explicit version
  bump_version.py --patch --no-commit
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import report

_ROOT_DIR = Path(__file__).resolve().parents[3]
VERSION_CONFIG = _ROOT_DIR / 'prj' / 'config' / 'version' / 'version_config.py'
INDEX_JSON    = _ROOT_DIR / 'prj' / 'config' / 'version' / 'index.json'


# ── Version helpers ───────────────────────────────────────────────────────────

def _parse_version(content: str) -> tuple[int, int, int]:
    m = re.search(r"APP_VERSION\s*=\s*'(\d+)\.(\d+)\.(\d+)'", content)
    if not m:
        report.fail('Could not parse APP_VERSION from version_config.py')
        sys.exit(1)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _bump(version: tuple, bump_type: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if bump_type == 'major': return (major + 1, 0, 0)
    if bump_type == 'minor': return (major, minor + 1, 0)
    if bump_type == 'patch': return (major, minor, patch + 1)
    raise ValueError(f'Unknown bump type: {bump_type}')


def _ver_str(v: tuple) -> str:
    return '.'.join(str(x) for x in v)


# ── CHANGELOG collection ──────────────────────────────────────────────────────

def _collect_changelog() -> list[str]:
    """Collect changelog entries interactively, one per line."""
    print()
    print(f'  {report.BOLD}Changelog entries{report.RST}  {report.DIM}(one per line, blank line to finish){report.RST}')
    entries: list[str] = []
    while True:
        try:
            line = input(f'  {report.CYN}▶{report.RST} ').strip()
        except EOFError:
            break
        if not line:
            break
        entries.append(line)
    return entries


def _suggest_from_git(since_tag: str | None) -> list[str]:
    """Return a list of git commit subjects since the given tag (or last 20)."""
    try:
        if since_tag:
            cmd = ['git', '-C', str(_ROOT_DIR), 'log', f'{since_tag}..HEAD',
                   '--oneline', '--no-merges']
        else:
            cmd = ['git', '-C', str(_ROOT_DIR), 'log', '-20',
                   '--oneline', '--no-merges']
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return [line.split(' ', 1)[1] for line in out.splitlines() if ' ' in line]
    except Exception:
        return []


# ── version_config.py rewrite ─────────────────────────────────────────────────

def _update_file(content: str, new_version: str, changelog: list[str]) -> str:
    # Bump version
    content = re.sub(
        r"APP_VERSION\s*=\s*'[\d.]+'",
        f"APP_VERSION = '{new_version}'",
        content,
    )
    # Replace CHANGELOG list (handles multi-line)
    if changelog:
        entries = ',\n        '.join(f'"{e}"' for e in changelog)
        new_log = f'CHANGELOG = [\n        {entries},\n    ]'
    else:
        new_log = 'CHANGELOG = []'

    content = re.sub(
        r'CHANGELOG\s*=\s*\[.*?\]',
        new_log,
        content,
        flags=re.DOTALL,
    )
    return content


# ── Git helpers ───────────────────────────────────────────────────────────────

def _latest_tag() -> str | None:
    try:
        tag = subprocess.check_output(
            ['git', '-C', str(_ROOT_DIR), 'describe', '--tags', '--abbrev=0'],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return tag or None
    except Exception:
        return None


def _update_index_template(new_version: str) -> bool:
    """Add *new_version* entry to the committed index.json template.

    The signature is cleared — it will be re-computed and written to the
    build artifact (prj/build/app/index.json) during the build step.
    The template itself is only ever updated here, during the version bump.
    """
    if not INDEX_JSON.exists():
        return False
    try:
        data = json.loads(INDEX_JSON.read_text(encoding='utf-8'))
        versions = data.setdefault('versions', [])
        if not any(v['version'] == new_version for v in versions):
            versions.append({
                'version': new_version,
                'metadata_url': f'{new_version}/meta.json',
            })
            data['latest'] = new_version
        # Clear stale signature — template is unsigned; build re-signs the artifact
        data.pop('signature', None)
        INDEX_JSON.write_text(
            json.dumps(data, sort_keys=True, indent=2) + '\n', encoding='utf-8'
        )
        return True
    except Exception as exc:
        report.warn(f'Could not update index.json template: {exc}')
        return False


def _git_commit(version: str) -> None:
    try:
        subprocess.check_call(
            ['git', '-C', str(_ROOT_DIR), 'add', str(VERSION_CONFIG)],
        )
        # Stage index.json template if it was modified alongside the bump
        if INDEX_JSON.exists():
            subprocess.check_call(
                ['git', '-C', str(_ROOT_DIR), 'add', str(INDEX_JSON)],
            )
        subprocess.check_call(
            ['git', '-C', str(_ROOT_DIR), 'commit', '-m', f'chore: bump version to {version}'],
        )
        report.ok(f'Committed: chore: bump version to {version}')
    except subprocess.CalledProcessError as e:
        report.warn(f'Git commit failed: {e}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]
    no_commit = '--no-commit' in args
    args = [a for a in args if a != '--no-commit']

    content     = VERSION_CONFIG.read_text(encoding='utf-8')
    current     = _parse_version(content)
    current_str = _ver_str(current)
    bump_label  = ''

    # — Header
    print()
    report.box_top('VERSION BUMPER')
    report.box_blank()
    report.box_row('Current version', f'{report.DIM}{current_str}{report.RST}')

    # — Determine new version
    if args:
        arg = args[0].lstrip('-')
        if arg in ('major', 'minor', 'patch'):
            new_version = _bump(current, arg)
            bump_label  = arg
        elif re.match(r'^\d+\.\d+\.\d+$', arg):
            new_version = tuple(int(x) for x in arg.split('.'))
            bump_label  = 'explicit'
        else:
            report.box_bot()
            report.fail(f'Unknown argument: {args[0]}')
            print(__doc__)
            sys.exit(1)
    else:
        report.box_blank()
        report.box_row(f'{report.DIM}[1]{report.RST} patch  — bug fix')
        report.box_row(f'{report.DIM}[2]{report.RST} minor  — new feature(s)')
        report.box_row(f'{report.DIM}[3]{report.RST} major  — breaking change / new architecture')
        report.box_blank()
        report.box_bot()
        try:
            choice = input(f'  {report.CYN}▶{report.RST} Select [1/2/3]: ').strip()
        except EOFError:
            sys.exit(0)
        mapping = {'1': 'patch', '2': 'minor', '3': 'major'}
        if choice not in mapping:
            report.fail('Invalid choice.')
            sys.exit(1)
        bump_label  = mapping[choice]
        new_version = _bump(current, bump_label)
        print()
        report.box_top('VERSION BUMPER')
        report.box_blank()
        report.box_row('Current version', f'{report.DIM}{current_str}{report.RST}')

    new_str = _ver_str(new_version)
    report.box_row('New version',
        f'{report.GRN}{report.BOLD}{new_str}{report.RST}  '
        f'{report.DIM}({bump_label} bump){report.RST}')
    report.box_blank()
    report.box_bot()

    # — Suggest changelog entries from git history
    last_tag    = _latest_tag()
    suggestions = _suggest_from_git(last_tag)
    if suggestions:
        since_label = last_tag or 'beginning'
        report.section(f'Recent commits since {report.CYN}{since_label}{report.RST}')
        total = len(suggestions)
        max_show = 15
        shown = min(total, max_show)
        for i, s in enumerate(suggestions[:shown], 1):
            print(f'  {report.DIM}{i:>2}.{report.RST}  {s}')
        if total > shown:
            more = total - shown
            plural = 's' if more != 1 else ''
            report.info(f'  ... and {more} more commit{plural} not shown. Use git to view full history.')

    changelog = _collect_changelog()
    if not changelog:
        print()
        report.warn('No changelog entries — meta.json will have empty release notes.')

    # — Write file
    new_content = _update_file(content, new_str, changelog)
    VERSION_CONFIG.write_text(new_content, encoding='utf-8')
    print()
    rel_path = VERSION_CONFIG.relative_to(_ROOT_DIR)
    report.ok(f'{report.WHT}{rel_path}{report.RST}  updated  '
              f'{report.DIM}{current_str}{report.RST} → '
              f'{report.GRN}{report.BOLD}{new_str}{report.RST}')

    # — Update index.json template (unsigned; build will sign the artifact)
    if _update_index_template(new_str):
        idx_rel = INDEX_JSON.relative_to(_ROOT_DIR)
        report.ok(f'{report.WHT}{idx_rel}{report.RST}  version entry added  '
                  f'{report.DIM}(signature cleared — re-signed at build time){report.RST}')

    # — Commit
    if not no_commit and shutil.which('git'):
        try:
            ans = input(f'\n  {report.CYN}▶{report.RST} Commit the change? [Y/n]: ').strip().lower()
        except EOFError:
            ans = 'n'
        if ans in ('', 'y', 'yes'):
            _git_commit(new_str)

    print()


if __name__ == '__main__':
    main()
