"""Hashing and verification utilities."""
from __future__ import annotations

import hashlib
import hmac


class HashUtil:
    """Utility for hashing and verifying data or files using hashlib/hmac.

    Supported algorithms: https://docs.python.org/3/library/hashlib.html
    """

    _CHUNK_SIZE = 8192  # 8 KiB for streaming reads

    @staticmethod
    def hash_data(data: str | bytes, algo: str, key: str | bytes | None = None) -> str:
        """Hash *data* with optional HMAC *key*.  Returns a hex digest."""
        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        if key is not None:
            key_bytes = key if isinstance(key, bytes) else key.encode('utf-8')
            return hmac.new(key_bytes, data_bytes, getattr(hashlib, algo)).hexdigest()
        return getattr(hashlib, algo)(data_bytes).hexdigest()

    @staticmethod
    def verify_data(data: str | bytes, hash_value: str, algo: str, key: str | bytes | None = None) -> bool:
        """Verify *data* against *hash_value* using constant-time comparison."""
        computed = HashUtil.hash_data(data, algo, key)
        return hmac.compare_digest(computed, str(hash_value))

    @staticmethod
    def hash_file(file_path: str, algo: str, key: str | bytes | None = None) -> str:
        """Hash the contents of a file.  Streams in chunks to handle large files."""
        if key is not None:
            key_bytes = key if isinstance(key, bytes) else key.encode('utf-8')
            h = hmac.new(key_bytes, digestmod=getattr(hashlib, algo))
        else:
            h = getattr(hashlib, algo)()
        with open(file_path, 'rb') as f:
            while chunk := f.read(HashUtil._CHUNK_SIZE):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify_file(file_path: str, hash_value: str, algo: str, key: str | bytes | None = None) -> bool:
        """Verify a file hash using constant-time comparison."""
        computed = HashUtil.hash_file(file_path, algo, key)
        return hmac.compare_digest(computed, str(hash_value))

    @staticmethod
    def available_algorithms() -> list[str]:
        """List all available hash algorithms."""
        return sorted(hashlib.algorithms_available)

    @staticmethod
    def compare_digest(a: str | bytes, b: str | bytes) -> bool:
        """Securely compare two digests (constant time)."""
        if isinstance(a, str):
            a = a.encode('utf-8')
        if isinstance(b, str):
            b = b.encode('utf-8')
        return hmac.compare_digest(a, b)

    @staticmethod
    def md5(data: str | bytes) -> str:
        """Quick MD5 hex digest."""
        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        return hashlib.md5(data_bytes).hexdigest()

    @staticmethod
    def sha256(data: str | bytes) -> str:
        """Quick SHA-256 hex digest."""
        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        return hashlib.sha256(data_bytes).hexdigest()

    @staticmethod
    def sha512(data: str | bytes) -> str:
        """Quick SHA-512 hex digest."""
        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        return hashlib.sha512(data_bytes).hexdigest()

    @staticmethod
    def md5_file(file_path: str) -> str:
        """Quick MD5 of a file (streaming)."""
        return HashUtil.hash_file(file_path, 'md5')

    @staticmethod
    def sha256_file(file_path: str) -> str:
        """Quick SHA-256 of a file (streaming)."""
        return HashUtil.hash_file(file_path, 'sha256')
