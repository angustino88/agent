#!/usr/bin/env python3
"""
ed25519_key.py

Generate, encrypt, and decrypt Ed25519 private keys using Python's cryptography library.
Compatible with OpenSSL 3.x PKCS#8 format.

Usage:
    python ed25519_key.py generate [priv_out] [pub_out]
    python ed25519_key.py encrypt [priv_in] [enc_out]
    python ed25519_key.py decrypt [enc_in] [dec_out]
"""

import sys
import os
from pathlib import Path
from getpass import getpass
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def generate_ed25519_keypair(priv_path: Path, pub_path: Path):
    """Generate a new Ed25519 private and public key pair."""
    print("🔐 Generating Ed25519 key pair...")

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path.write_bytes(priv_bytes)
    pub_path.write_bytes(pub_bytes)

    try:
        os.chmod(priv_path, 0o600)
    except Exception:
        pass

    print(f"✅ Private key saved: {priv_path}")
    print(f"✅ Public key saved:  {pub_path}")
    return private_key, public_key

def encrypt_private_key(priv_in: Path, enc_out: Path = None):
    """Encrypt an existing Ed25519 private key."""
    if not priv_in.is_file():
        print(f"❌ Private key not found: {priv_in}")
        sys.exit(1)

    if enc_out is None:
        enc_out = priv_in.with_name(priv_in.stem + "_encrypted.pem")

    print(f"🔒 Encrypting private key → {enc_out.name}")

    password = getpass("Enter password to encrypt: ").strip()
    if not password:
        print("❌ No password entered. Aborting.")
        sys.exit(2)

    private_key = serialization.load_pem_private_key(priv_in.read_bytes(), password=None)

    enc_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )
    enc_out.write_bytes(enc_bytes)

    print(f"✅ Encrypted private key saved: {enc_out}")

def decrypt_private_key(enc_path: Path, out_path: Path = None):
    """Decrypt an encrypted Ed25519 private key and optionally save PEM."""
    if not enc_path.is_file():
        print(f"❌ Encrypted key not found: {enc_path}")
        sys.exit(1)

    if out_path is None:
        out_path = enc_path.with_name(enc_path.stem + "_decrypted.pem")

    print(f"🔓 Decrypting key → {out_path.name}")
    password = getpass("Enter password to decrypt private key: ").strip()
    if not password:
        print("❌ No password entered. Aborting.")
        sys.exit(2)

    enc_bytes = enc_path.read_bytes()
    private_key = serialization.load_pem_private_key(enc_bytes, password=password.encode())

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    out_path.write_bytes(priv_bytes)
    try:
        os.chmod(out_path, 0o600)
    except Exception:
        pass

    print(f"✅ Decrypted private key saved: {out_path}")
    return private_key

def print_help():
    print(__doc__)

def main():
    args = sys.argv[1:]
    base = Path(".")

    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == "generate":
        priv_out = Path(args[1]) if len(args) > 1 else base / "ed25519_priv.pem"
        pub_out = Path(args[2]) if len(args) > 2 else base / "ed25519_pub.pem"
        generate_ed25519_keypair(priv_out, pub_out)

    elif cmd == "encrypt":
        priv_in = Path(args[1]) if len(args) > 1 else Path("ed25519_priv.pem")
        enc_out = Path(args[2]) if len(args) > 2 else None
        encrypt_private_key(priv_in, enc_out)

    elif cmd == "decrypt":
        enc_in = Path(args[1]) if len(args) > 1 else Path("ed25519_priv_encrypted.pem")
        dec_out = Path(args[2]) if len(args) > 2 else Path("ed25519_priv.pem")
        decrypt_private_key(enc_in, dec_out)

    else:
        print(f"❌ Unknown command: {cmd}")
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()