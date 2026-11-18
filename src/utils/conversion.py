"""Numeric and binary conversion utilities."""
from __future__ import annotations

import struct


class ConversionUtil:
    """Low-level type conversion helpers for embedded/automotive data."""

    # ------------------------------------------------------------------
    # Signed / unsigned
    # ------------------------------------------------------------------

    @staticmethod
    def unsigned_to_signed(val: int, bits: int) -> int:
        """Convert an unsigned integer to a signed integer of given *bits* width."""
        mask = 1 << bits
        val %= mask
        if val >= mask >> 1:
            val -= mask
        return val

    @staticmethod
    def signed_to_unsigned(val: int, bits: int) -> int:
        """Convert a signed integer to its unsigned representation of *bits* width."""
        mask = 1 << bits
        return val % mask

    # ------------------------------------------------------------------
    # Float ↔ unsigned
    # ------------------------------------------------------------------

    @staticmethod
    def unsigned_to_float32(val: int) -> float:
        """Reinterpret a 32-bit unsigned integer as IEEE 754 float32."""
        return struct.unpack('f', struct.pack('I', val))[0]

    @staticmethod
    def float32_to_unsigned(val: float) -> int:
        """Reinterpret an IEEE 754 float32 as a 32-bit unsigned integer."""
        return struct.unpack('I', struct.pack('f', val))[0]

    @staticmethod
    def unsigned_to_float64(val: int) -> float:
        """Reinterpret a 64-bit unsigned integer as IEEE 754 float64."""
        return struct.unpack('d', struct.pack('Q', val))[0]

    @staticmethod
    def float64_to_unsigned(val: float) -> int:
        """Reinterpret an IEEE 754 float64 as a 64-bit unsigned integer."""
        return struct.unpack('Q', struct.pack('d', val))[0]

    # ------------------------------------------------------------------
    # int ↔ bytes
    # ------------------------------------------------------------------

    @staticmethod
    def int_to_bytes(val: int, length: int, byteorder: str = 'little', signed: bool = False) -> bytes:
        """Convert an integer to *length* bytes."""
        return val.to_bytes(length, byteorder=byteorder, signed=signed)

    @staticmethod
    def bytes_to_int(b: bytes, byteorder: str = 'little', signed: bool = False) -> int:
        """Convert bytes to an integer."""
        return int.from_bytes(b, byteorder=byteorder, signed=signed)

    # ------------------------------------------------------------------
    # Hex string helpers
    # ------------------------------------------------------------------

    @staticmethod
    def hexstr_to_int(hex_str: str) -> int:
        """Convert a hex string (e.g. ``'0x1A'``) to an integer."""
        return int(hex_str, 16)

    @staticmethod
    def int_to_hexstr(val: int, prefix: str = '0x', width: int = 0) -> str:
        """Convert an integer to a hex string, optionally zero-padded to *width* nibbles."""
        hex_digits = f"{val:X}" if width == 0 else f"{val:0{width}X}"
        return f"{prefix}{hex_digits}"

    @staticmethod
    def hexstr_to_bytes(hex_str: str) -> bytes:
        """Convert a hex string (with or without ``0x`` prefix) to bytes."""
        hex_str = hex_str.removeprefix('0x').removeprefix('0X')
        return bytes.fromhex(hex_str)

    @staticmethod
    def bytes_to_hexstr(b: bytes, prefix: str = '', separator: str = '') -> str:
        """Convert bytes to a hex string with optional prefix and separator."""
        return separator.join(f"{prefix}{byte:02X}" for byte in b)

    # ------------------------------------------------------------------
    # Binary string helpers
    # ------------------------------------------------------------------

    @staticmethod
    def int_to_binstr(val: int, bits: int = 0) -> str:
        """Convert an integer to a binary string, optionally zero-padded to *bits*."""
        if bits:
            return f"0b{val:0{bits}b}"
        return f"0b{val:b}"

    @staticmethod
    def binstr_to_int(bin_str: str) -> int:
        """Convert a binary string (e.g. ``'0b1010'``) to an integer."""
        return int(bin_str, 2)

    # ------------------------------------------------------------------
    # Scaling (raw ↔ physical)
    # ------------------------------------------------------------------

    @staticmethod
    def raw_to_physical(raw: int | float, scale: float, offset: float) -> float:
        """Apply linear scaling: ``physical = raw * scale + offset``."""
        return raw * scale + offset

    @staticmethod
    def physical_to_raw(physical: float, scale: float, offset: float) -> float:
        """Inverse linear scaling: ``raw = (physical - offset) / scale``."""
        if scale == 0:
            raise ZeroDivisionError("scale must not be zero")
        return (physical - offset) / scale
