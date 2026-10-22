#!/usr/bin/env python3
"""Set (or change) the Church Notes site password.

Run this YOURSELF in your own terminal — it prompts with echo off, so the value never
enters a chat, a shell history, or a build log:

    ~/.hermes/hermes-agent/venv/bin/python3 \
        ~/Desktop/Hermes/Church\\ Site/scripts/set-gate-password.py

It writes ~/.hermes/secrets/church-gate.txt (0600) and then re-runs the site build so
every page is re-encrypted with the new passphrase.

Length matters. There is no server: the ciphertext ships to the browser, so an attacker
can guess offline, as fast as their hardware allows. Twelve characters is the floor; a
passphrase (several words) is better than a short complicated string.
"""
import getpass
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET = os.path.expanduser("~/.hermes/secrets/church-gate.txt")
MIN_LEN = 12


def main() -> int:
    print("Church Notes — set the site password")
    print("(not echoed; nothing is written to your shell history)")
    print()
    pw = getpass.getpass(f"New password (min {MIN_LEN} chars): ")
    if pw != pw.strip():
        print("\nRefused: leading or trailing whitespace. It is invisible and easy to mistype.")
        return 1
    if len(pw) < MIN_LEN:
        print(f"\nRefused: {len(pw)} characters. Use at least {MIN_LEN}.")
        return 1
    again = getpass.getpass("Confirm: ")
    if pw != again:
        print("\nRefused: the two entries differ.")
        return 1

    os.makedirs(os.path.dirname(SECRET), exist_ok=True)
    with open(SECRET, "w", encoding="utf-8") as fh:
        fh.write(pw + "\n")
    os.chmod(SECRET, 0o600)
    print(f"\nStored (0600): {SECRET}")

    if "--no-build" in sys.argv:
        print("Skipped the build (--no-build). Re-run the build to re-encrypt the site.")
        return 0

    print("\nRe-building the site with the new password…")
    build = os.path.join(os.path.dirname(HERE), "build_site.py")
    return subprocess.call([sys.executable, build])


if __name__ == "__main__":
    sys.exit(main())
