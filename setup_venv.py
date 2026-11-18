import os
import subprocess
import sys
from pathlib import Path

ENV_NAME = ".venv"
PROXY = "http://example-proxy:8080"  # ← replace with your proxy if needed
MIN_UV_VERSION = (0, 4, 0)


def check_python_version():
    print(f"Python version: {sys.version}")
    if sys.version_info[:2] != (3, 12):
        print("❌ Python 3.12.x is required.")
        sys.exit(1)


def env_with_proxy() -> dict:
    env = os.environ.copy()
    env["HTTP_PROXY"] = PROXY
    env["HTTPS_PROXY"] = PROXY
    env["UV_SYSTEM_CERTS"] = "1"
    env["VIRTUAL_ENV"] = str(Path(ENV_NAME).resolve())  # ← hint uv to use our venv
    return env


def run(cmd: list, env=None, quiet=False):
    kwargs = dict(env=env)
    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    subprocess.check_call(cmd, **kwargs)


def ensure_uv():
    """Install uv if missing, validate minimum version."""
    try:
        result = subprocess.check_output(
            [sys.executable, "-m", "uv", "--version"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # result: "uv 0.4.10"
        version_str = result.strip().split()[-1]
        version = tuple(int(x) for x in version_str.split("."))
        if version < MIN_UV_VERSION:
            print(f"⚠️  uv {version_str} is too old, upgrading...")
            raise RuntimeError("uv too old")
        return
    except Exception:
        pass

    print("📦 Bootstrapping uv via pip...")
    env = env_with_proxy()

    try:
        run([sys.executable, "-m", "ensurepip", "--upgrade"], env=env)
    except subprocess.CalledProcessError:
        print("⚠️  ensurepip failed — continuing anyway")

    try:
        run([sys.executable, "-m", "pip", "install", "uv", "--proxy", PROXY], env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install uv: {e}")
        sys.exit(e.returncode)


def sync_workspace():
    print("🔧 Syncing workspace with uv...")
    env = env_with_proxy()
    env["UV_PROJECT_ENVIRONMENT"] = str(Path(ENV_NAME).resolve())

    lock_exists = Path("uv.lock").exists()

    cmd = [
        sys.executable, "-m", "uv", "sync",
        "--python", "3.12",
        "--all-packages",       # ← installs ALL workspace members
    ]

    if lock_exists:
        cmd.append("--frozen")
    else:
        print("ℹ️  No uv.lock found — generating one now...")

    try:
        run(cmd, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ uv sync failed: {e}")
        print("💡 Try: delete uv.lock and re-run to regenerate")
        sys.exit(e.returncode)


def print_activation_hint():
    if os.name == "nt":
        print(f"👉 Activate: .\\{ENV_NAME}\\Scripts\\activate")
    else:
        print(f"👉 Activate: source ./{ENV_NAME}/bin/activate")


def main():
    check_python_version()
    ensure_uv()
    sync_workspace()
    print(f"\n✅ Done! Environment ready in ./{ENV_NAME}")
    print_activation_hint()


if __name__ == "__main__":
    main()