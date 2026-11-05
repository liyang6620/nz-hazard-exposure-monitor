"""Generate a local encrypted RSA key pair; never print private material."""

from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / ".local/snowflake")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to((ROOT / ".local").resolve()):
        raise ValueError("Keys must stay under ignored .local/")
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or secrets.token_urlsafe(36)
    if len(passphrase) < 16:
        raise ValueError("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE must have at least 16 characters")
    private = directory / "rsa_key.p8"
    public = directory / "rsa_key.pub"
    public_b64 = directory / "rsa_key.pub.b64"
    saved_passphrase = directory / "key_passphrase.txt"
    if any(path.exists() for path in (private, public, public_b64, saved_passphrase)):
        raise FileExistsError("Key pair already exists; rotation must be explicit")
    directory.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(passphrase.encode()),
        )
    )
    public.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    public_b64.write_text(
        "".join(public.read_text(encoding="ascii").splitlines()[1:-1]), encoding="ascii"
    )
    saved_passphrase.write_text(passphrase, encoding="ascii")
    fingerprint = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    digest = hashes.Hash(hashes.SHA256())
    digest.update(fingerprint)
    print(f"Key pair created under {directory}; public-key SHA-256: {digest.finalize().hex()}")


if __name__ == "__main__":
    main()
