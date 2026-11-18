"""
Build history recorder and viewer.

Records each build run to prj/build/log/build_history.json.
Every entry captures: version, git info, duration, outcome, package metadata.

Usage:
  build_history.py               # list last 10 builds
  build_history.py -n 20         # list last 20 builds
  build_history.py --stats       # aggregate statistics
  build_history.py --clear [-y]  # clear history (prompts unless -y)

Called automatically by build.py at the end of each build run.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import report

_ROOT_DIR     = Path(__file__).resolve().parents[3]
_HISTORY_FILE = _ROOT_DIR / 'prj' / 'build' / 'log' / 'build_history.json'
_DEFAULT_N    = 10


# ── Entry schema ──────────────────────────────────────────────────────────────
# {
#   "timestamp":  "2026-07-15T14:32:10",
#   "version":    "1.2.3",
#   "git_sha":    "a1b2c3d",
#   "git_branch": "main",
#   "duration_s": 48.3,
#   "outcome":    "success" | "failure",
#   "package":    "AppName-1.2.3.zip",   # or null
#   "size_mb":    97.6,                   # or null
#   "sha256":     "abc...",               # or null
# }

def record(entry: dict) -> None:
    """Append *entry* to the history file (creates it when missing)."""
    entry.setdefault('timestamp', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
    history = _load()
    history.append(entry)
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding='utf-8')


def _load() -> list:
    if not _HISTORY_FILE.exists():
        return []
    try:
        return json.loads(_HISTORY_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_row(n: int, entry: dict) -> str:
    outcome  = entry.get('outcome', '?')
    ic       = report.OK_IC if outcome == 'success' else report.FAIL_IC
    version  = entry.get('version', '?')
    ts       = entry.get('timestamp', '')[:16].replace('T', ' ')
    dur_s    = entry.get('duration_s') or 0
    dur      = f'{dur_s:.0f}s'
    size_mb  = entry.get('size_mb')
    size     = f'{size_mb:.1f} MB' if size_mb else '—'
    sha      = entry.get('git_sha', '')[:7] or '—'
    num      = f'{report.DIM}{n:>2}{report.RST}'
    ver_fmt  = f'{report.BOLD}{version:<9}{report.RST}'
    sha_fmt  = f'{report.DIM}{sha:<7}{report.RST}'
    return (
        f'  {num}  {ic}  {ver_fmt}{ts}  '
        f'{report.DIM}{dur:>5}  {size:>8}  {sha_fmt}{report.RST}'
    )


def _fmt_header() -> str:
    b, r, d = report.BOLD, report.RST, report.DIM
    return (
        f'  {b}{"#":>2}{"":2}{"":2}{"version":<9}{"date & time":<16}'
        f'  {"dur":>5}  {"size":>8}  {"sha":<7}{r}'
    )


# ── Commands ──────────────────────────────────────────────────────────────────

def list_history(n: int = _DEFAULT_N) -> None:
    history = _load()
    if not history:
        print()
        report.info('No build history found.')
        print()
        return

    total  = len(history)
    recent = history[-n:][::-1]          # most recent first

    print()
    report.box_top('BUILD HISTORY')
    report.box_blank()
    report.box_line(_fmt_header())
    report.box_sep()
    for i, entry in enumerate(recent, 1):
        report.box_line(_fmt_row(i, entry))
    report.box_blank()
    if total > n:
        note = (
            f'  {report.DIM}Showing {len(recent)} of {total} entries'
            f'   ({_HISTORY_FILE.name}){report.RST}'
        )
        report.box_line(note)
    report.box_bot()
    print()


def stats() -> None:
    history = _load()
    if not history:
        print()
        report.info('No build history found.')
        print()
        return

    total     = len(history)
    n_success = sum(1 for e in history if e.get('outcome') == 'success')
    n_fail    = total - n_success
    rate      = n_success / total * 100 if total else 0
    durs      = [e['duration_s'] for e in history if e.get('duration_s')]
    avg_dur   = sum(durs) / len(durs) if durs else 0
    min_dur   = min(durs, default=0)
    max_dur   = max(durs, default=0)
    first_ts  = history[0].get('timestamp', '')[:10]
    last_ts   = history[-1].get('timestamp', '')[:10]

    print()
    report.box_top('BUILD STATISTICS')
    report.box_blank()
    report.box_row('Total builds',  f'{report.BOLD}{total}{report.RST}')
    report.box_row('Period',        f'{report.DIM}{first_ts}  →  {last_ts}{report.RST}')
    report.box_blank()
    report.box_sep()
    report.box_blank()
    report.box_row('Success',
        f'{report.GRN}{n_success}{report.RST}  {report.DIM}({rate:.0f}%){report.RST}')
    report.box_row('Failure',
        f'{report.RED}{n_fail}{report.RST}' if n_fail
        else f'{report.DIM}0{report.RST}')
    report.box_blank()
    report.box_sep()
    report.box_blank()
    report.box_row('Avg duration',  report.format_duration(avg_dur))
    report.box_row('Fastest',       report.format_duration(min_dur))
    report.box_row('Slowest',       report.format_duration(max_dur))
    report.box_blank()
    report.box_bot()
    print()


def clear(confirmed: bool = False) -> None:
    if not _HISTORY_FILE.exists():
        report.info('History file does not exist — nothing to clear.')
        return
    if not confirmed:
        try:
            ans = input(
                f'  {report.YLW}⚠{report.RST}  Delete ALL build history? [y/N]: '
            ).strip().lower()
        except EOFError:
            ans = 'n'
        if ans not in ('y', 'yes'):
            report.info('Cancelled.')
            return
    _HISTORY_FILE.unlink(missing_ok=True)
    report.ok('Build history cleared.')


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='View or manage the build history log.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '-n', type=int, default=_DEFAULT_N, metavar='N',
        help=f'Number of recent entries to show (default: {_DEFAULT_N})',
    )
    parser.add_argument('--stats', action='store_true', help='Show aggregate statistics')
    parser.add_argument('--clear', action='store_true', help='Clear the history file')
    parser.add_argument('-y',      action='store_true', help='Skip confirmation for --clear')
    args = parser.parse_args()

    if args.clear:
        clear(confirmed=args.y)
    elif args.stats:
        stats()
    else:
        list_history(n=args.n)


if __name__ == '__main__':
    main()
