import hashlib

from cryptography.hazmat.primitives.serialization import load_der_public_key

from src.core.agent_api.signing import AgentKey, b64url, b64url_decode, enrollment_message, request_message


def test_request_message_matches_backend_layout():
    message = request_message(
        backend_id="dept_a",
        agent_uid="u-1",
        method="post",
        path="/agent/heartbeat",
        timestamp="1700000000",
        nonce="bm9uY2U",
        body=b"{}",
    )
    assert message == b"\0".join(
        [
            b"labmango-agent-request-v1",
            b"dept_a",
            b"u-1",
            b"POST",
            b"/agent/heartbeat",
            b"1700000000",
            b"bm9uY2U",
            hashlib.sha256(b"{}").hexdigest().encode(),
        ]
    )


def test_enrollment_proof_verifies_with_published_public_key():
    key = AgentKey.generate()
    message = enrollment_message(backend_id="dept_a", agent_uid="u-1", grant="eg_x", public_key_der=key.public_key_der)
    assert message.split(b"\0")[3] == hashlib.sha256(b"eg_x").hexdigest().encode()

    public = load_der_public_key(b64url_decode(key.public_key_b64url))
    public.verify(b64url_decode(key.sign(message)), message)  # raises on mismatch


def test_base64url_is_unpadded_and_key_round_trips():
    key = AgentKey.generate()
    assert "=" not in key.public_key_b64url and "=" not in b64url(b"\x00")
    assert AgentKey.from_private_bytes(key.private_bytes).public_key_der == key.public_key_der
    assert key.private_bytes.hex() not in repr(key)
