import sys
import json
import base64
import shutil
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
import report

def canonical_bytes(data: dict) -> bytes:
    """Return canonicalized JSON bytes (excluding the signature)."""
    payload = {k: v for k, v in data.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sign_index(priv_key_path: Path, data: dict) -> None:
    """Sign data using Ed25519 private key."""
    priv_key_path = Path(priv_key_path)
    priv = serialization.load_pem_private_key(priv_key_path.read_bytes(), password=None)
    if not isinstance(priv, ed25519.Ed25519PrivateKey):
        raise TypeError("Provided key is not an Ed25519 private key.")

    sig = priv.sign(canonical_bytes(data))
    data["signature"] = base64.b64encode(sig).decode()

def update_index(
    version: str,
    priv_key_path: Path,
    index_path: Path,
    dist_dir: Path,
    metadata_url: str = None,
    output_path: Path = None,
):
    """Update and sign the version index.

    Parameters
    ----------
    index_path  : Path to the *input* index (template).  Never modified.
    output_path : Where to write the signed result.  Defaults to ``dist_dir/index.json``.
                  Pass an explicit path to keep the committed template untouched.
    """
    priv_key_path = Path(priv_key_path)
    index_path = Path(index_path)
    dist_dir = Path(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the output path (default: dist_dir/index.json)
    out_path = Path(output_path) if output_path else (dist_dir / "index.json")

    if not index_path.exists():
        report.fail(f'index.json not found at {index_path}')
        sys.exit(1)

    # Load JSON
    data = json.loads(index_path.read_text(encoding="utf-8"))
    versions = data.setdefault("versions", [])

    # Use provided metadata_url or default
    if metadata_url is None:
        metadata_url = f"{version}/meta.json"

    # Append if missing
    if not any(v["version"] == version for v in versions):
        versions.append({
            "version": version,
            "metadata_url": metadata_url
        })
        data["latest"] = version
        report.ok(f'Added version {version} to index.json')
    else:
        report.info(f'Version {version} already exists; re-signing only.')

    # Sign in-memory, write to output path only — template (index_path) is never modified
    sign_index(priv_key_path, data)
    out_path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    report.ok(f'Signed index.json written to {out_path} (signature length={len(data["signature"])})')

    # Copy to dist/ if the output landed elsewhere
    dist_out = dist_dir / "index.json"
    if out_path.resolve() != dist_out.resolve():
        shutil.copy2(out_path, dist_out)
        report.info(f'Copied signed index.json to {dist_out}')