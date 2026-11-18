from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import report


def sign_exe(exe_path: str | Path, priv_key_path: str | Path, sig_path: str | Path):
    """
    Sign a file using an Ed25519 private key (OpenSSL 3.x compatible).
    """
    exe_path = Path(exe_path)
    priv_key_path = Path(priv_key_path)
    sig_path = Path(sig_path)

    if not exe_path.is_file():
        raise FileNotFoundError(f"File to sign not found: {exe_path}")
    if not priv_key_path.is_file():
        raise FileNotFoundError(f"Private key not found: {priv_key_path}")

    report.info(f'Signing {exe_path.name} -> {sig_path.name}')

    # Load the private key (unencrypted or encrypted PEM)
    pem_data = priv_key_path.read_bytes()
    private_key = serialization.load_pem_private_key(pem_data, password=None)

    # Read file and sign
    data = exe_path.read_bytes()
    signature = private_key.sign(data)
    sig_path.write_bytes(signature)

    report.ok(f'Signature written to {sig_path}')


def verify_exe_signature(exe_path: str | Path, pub_key_path: str | Path, sig_path: str | Path) -> bool:
    """
    Verify the signature of a file using an Ed25519 public key (OpenSSL 3.x compatible).
    Returns True if valid.
    """
    exe_path = Path(exe_path)
    pub_key_path = Path(pub_key_path)
    sig_path = Path(sig_path)

    for f, label in [(exe_path, "data file"), (pub_key_path, "public key"), (sig_path, "signature")]:
        if not f.is_file():
            raise FileNotFoundError(f"Missing {label}: {f}")

    report.info(f'Verifying {exe_path.name} using {pub_key_path.name}')

    # Load public key
    pub_key = serialization.load_pem_public_key(pub_key_path.read_bytes())

    # Verify signature
    try:
        pub_key.verify(sig_path.read_bytes(), exe_path.read_bytes())
        report.ok('Signature verified')
        return True
    except Exception as e:
        report.fail(f'Signature verification failed: {e}')
        return False