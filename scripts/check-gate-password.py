#!/usr/bin/env python3
"""Check whether a candidate passphrase opens the gated pages on the Church site.

Run it YOURSELF in your own terminal — it prompts with echo off, so the value never
enters a chat, a shell history, or a log:

    ~/.hermes/hermes-agent/venv/bin/python3 \
        ~/Desktop/Hermes/Church\\ Site/scripts/check-gate-password.py

It reports whether the candidate equals the stored secret, and whether it actually
decrypts the built pages on disk (the test that matters). Neither the stored secret nor
your candidate is ever printed.
"""
import base64
import getpass
import hashlib
import json
import pathlib
import re
import sys

SITE = pathlib.Path.home() / "Desktop/Hermes/Church Site/site"
SECRET = pathlib.Path.home() / ".hermes/secrets/church-gate.txt"
PAYLOAD_RE = re.compile(r'id="cn-payload"[^>]*>(.*?)</script>', re.S)


def pages():
    out = []
    idx = SITE / "index.html"
    if idx.exists():
        out.append(("home", idx))
    srm = SITE / "sermons" / "index.html"
    if srm.exists():
        out.append(("sermons index", srm))
    others = sorted(p for p in SITE.glob("*.html") if p.name != "index.html")
    for p in others[:3]:
        out.append((p.stem, p))
    return out


def main() -> int:
    if not SECRET.exists():
        print(f"No stored passphrase at {SECRET} — nothing to compare against.")
        return 1
    stored = SECRET.read_text(encoding="utf-8")
    cand = getpass.getpass("Type the passphrase you have been trying: ")
    same = cand == stored
    print(f"1. Candidate == stored secret: {'YES' if same else 'NO'}")
    if not same:
        if cand.strip() == stored.strip():
            print("   -> they differ ONLY by leading/trailing whitespace. That is your bug.")
        elif cand.lower() == stored.lower():
            print("   -> they differ ONLY by letter case. That is your bug.")

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    b = base64.b64decode
    print("\n2. Decrypting built pages with your candidate:")
    tested = 0
    for label, page in pages():
        m = PAYLOAD_RE.search(page.read_text(encoding="utf-8"))
        if not m or not m.group(1).strip():
            print(f"   {label}: no payload block")
            continue
        d = json.loads(m.group(1).replace("<\\/", "</"))
        if d.get("unconfigured"):
            print(f"   {label}: built WITHOUT a passphrase (fail-closed, no ciphertext)")
            continue
        key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b(d["kdf"]["salt"]),
                         iterations=d["kdf"]["iterations"]).derive(cand.encode())
        try:
            pt = AESGCM(key).decrypt(b(d["iv"]), b(d["ct"]), None)
            print(f"   {label}: OPENS ({len(pt)} bytes) <- this passphrase is correct")
        except Exception:
            print(f"   {label}: FAILS (wrong passphrase for this ciphertext)")
        tested += 1
    if not tested:
        print("   nothing on disk to test against")
    return 0


if __name__ == "__main__":
    sys.exit(main())
