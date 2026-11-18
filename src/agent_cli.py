"""Lab Mango agent command line (docs/agent-platform/agent-cli.md in lab-mango).

    labmango-agent enroll --url <backend-origin> --agent-uid <uuid> [--grant <grant>] [--unattended]
    labmango-agent status [--json]
    labmango-agent unenroll [--yes]

Exit codes for ``enroll``: 0 enrolled, 2 invalid or expired grant, 3 key proof rejected,
4 already enrolled / conflict, 5 backend unreachable, 1 anything else.
``status`` exits 0 only when a heartbeat to the backend succeeds right now.

Runs without Qt. The packaged app forwards these sub-commands here from ``main.py``.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.agent_api import (  # noqa: E402
    AgentApiClient,
    AlreadyEnrolled,
    IdentityStore,
    default_agent_home,
    enroll,
    errors,
    load_credentials,
)

COMMANDS = ("enroll", "status", "unenroll")
GRANT_ENV = "LABMANGO_AGENT_GRANT"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_GRANT = 2
EXIT_PROOF = 3
EXIT_CONFLICT = 4
EXIT_UNREACHABLE = 5


def _agent_version() -> str:
    try:
        from prj.config.version.version_config import VersionConfig

        return str(VersionConfig.APP_VERSION)
    except Exception:
        return "0.0.0"


def _fingerprint() -> str:
    try:
        from src.utils.fingerprint import get_hardware_fingerprint

        return get_hardware_fingerprint()
    except Exception:
        return ""


def _tls_verify(args: argparse.Namespace) -> bool | str:
    if getattr(args, "insecure", False):
        return False
    return args.ca_bundle or True


def _store(args: argparse.Namespace) -> IdentityStore:
    return IdentityStore(args.home or default_agent_home())


def _read_grant(args: argparse.Namespace) -> Optional[str]:
    grant = args.grant or os.environ.get(GRANT_ENV)
    if grant:
        return grant.strip()
    if args.unattended or not sys.stdin.isatty():
        return None
    return getpass.getpass("Enrollment grant: ").strip() or None


def cmd_enroll(args: argparse.Namespace) -> int:
    grant = _read_grant(args)
    if not grant:
        print(f"No grant given: use --grant, {GRANT_ENV} or run interactively.", file=sys.stderr)
        return EXIT_GRANT
    if args.url.startswith("http://") and not args.insecure:
        print("Refusing a plain-HTTP backend URL; use HTTPS (or --insecure for local testing).", file=sys.stderr)
        return EXIT_ERROR
    store = _store(args)
    try:
        identity = enroll(
            store,
            backend_url=args.url,
            agent_uid=args.agent_uid,
            grant=grant,
            agent_version=_agent_version(),
            fingerprint="" if args.no_fingerprint else _fingerprint(),
            verify=_tls_verify(args),
        )
    except ValueError as error:
        print(f"Enrollment failed: {error}", file=sys.stderr)
        return EXIT_ERROR
    except AlreadyEnrolled as error:
        print(f"Enrollment failed: {error.args[0]}", file=sys.stderr)
        return EXIT_CONFLICT
    except errors.EnrollmentRejected as error:
        # The backend answers 400 for both bad grant and bad proof; a locally made proof is
        # correct by construction, so 400 almost always means the grant.
        print(f"Enrollment rejected (grant invalid, expired or used): {error}", file=sys.stderr)
        return EXIT_GRANT if "proof" not in str(error).lower() else EXIT_PROOF
    except errors.EnrollmentConflict as error:
        print(f"Enrollment conflict: {error}", file=sys.stderr)
        return EXIT_CONFLICT
    except errors.BackendUnreachable as error:
        print(f"Backend unreachable: {error}", file=sys.stderr)
        return EXIT_UNREACHABLE
    except errors.AgentApiError as error:
        print(f"Enrollment failed: {error}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        grant = None  # best effort: drop the grant reference

    _save_tls(store, args)
    print(f"Enrolled agent {identity.agent_uid} with backend {identity.backend_key} ({identity.key_storage} key).")
    return EXIT_OK


def _save_tls(store: IdentityStore, args: argparse.Namespace) -> None:
    identity = store.load()
    if identity is None:
        return
    extra = dict(identity.extra)
    extra["tls_verify"] = _tls_verify(args)
    from dataclasses import replace

    store.save(replace(identity, extra=extra))


def cmd_status(args: argparse.Namespace) -> int:
    store = _store(args)
    identity, key = load_credentials(store)
    report: dict = {
        "enrolled": bool(identity and identity.is_enrolled),
        "state": identity.state if identity else "not_enrolled",
        "agent_uid": identity.agent_uid if identity else None,
        "backend_url": identity.backend_url if identity else None,
        "backend_key": identity.backend_key if identity else None,
        "key_storage": identity.key_storage if identity else None,
        "key_available": key is not None,
        "agent_home": str(store.directory),
        "heartbeat": None,
    }
    exit_code = EXIT_ERROR
    if identity and identity.is_enrolled and key is not None:
        verify = identity.extra.get("tls_verify", True)
        client = AgentApiClient(identity.backend_url, identity=identity, key=key, verify=verify, timeout=10)
        try:
            beat = client.heartbeat()
            report["heartbeat"] = {
                "ok": True,
                "status": beat.status,
                "last_seen_at": beat.last_seen_at.isoformat() if beat.last_seen_at else None,
            }
            exit_code = EXIT_OK
        except errors.AgentApiError as error:
            report["heartbeat"] = {"ok": False, "error": str(error)}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for name, value in report.items():
            print(f"{name:14} {value}")
    return exit_code


def cmd_unenroll(args: argparse.Namespace) -> int:
    store = _store(args)
    identity = store.load()
    if identity is None:
        print("Not enrolled.")
        return EXIT_OK
    if not args.yes:
        if not sys.stdin.isatty():
            print("Refusing to unenroll without --yes in a non-interactive session.", file=sys.stderr)
            return EXIT_ERROR
        answer = input(f"Delete the local identity and key of agent {identity.agent_uid}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            return EXIT_ERROR
    store.clear()
    print(
        f"Removed local identity {identity.agent_uid}. Ask an operator to revoke or decommission it "
        "in Lab Mango; the backend still lists it until then."
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labmango-agent", description="Lab Mango agent enrollment and status")
    parser.add_argument("--home", help="agent state folder (default: machine-wide, or LABMANGO_AGENT_HOME)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_enroll = sub.add_parser("enroll", help="enroll this computer with a one-time grant")
    p_enroll.add_argument("--url", required=True, help="backend origin, including any Router prefix")
    p_enroll.add_argument("--agent-uid", required=True, help="the pending agent created by the operator")
    p_enroll.add_argument("--grant", help=f"one-time grant (eg_...); also read from {GRANT_ENV}")
    p_enroll.add_argument("--unattended", action="store_true", help="never prompt; fail if no grant is given")
    p_enroll.add_argument("--ca-bundle", help="CA bundle used to verify the backend's TLS certificate")
    p_enroll.add_argument("--insecure", action="store_true", help="allow http:// and skip TLS verification (testing only)")
    p_enroll.add_argument("--no-fingerprint", action="store_true", help="do not send the hardware fingerprint")
    p_enroll.set_defaults(func=cmd_enroll)

    p_status = sub.add_parser("status", help="show identity and send a heartbeat")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_unenroll = sub.add_parser("unenroll", help="delete the local identity and key")
    p_unenroll.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    p_unenroll.set_defaults(func=cmd_unenroll)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
