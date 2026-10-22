#!/usr/bin/env python3
"""Church Notes — build-time password gate.

Every content page ships as ciphertext. The passphrase never enters the repo or the
built site: it is read at build time from `~/.hermes/secrets/church-gate.txt` (0600).

Why encryption rather than the obfuscated (base64) gate used on the flashcards page:
this site is intended to be served from a public host. A base64 gate leaves the page
body readable in the source and at `raw.githubusercontent.com`, which defeats the point.
PBKDF2-HMAC-SHA256 -> AES-256-GCM is standard and available in every current browser
via WebCrypto.

Honest limits: there is no server, so the ciphertext is public and a weak passphrase is
brute-forceable offline. This deters casual readers, link-sharers and crawlers. It is not
confidentiality against someone who wants in, and one shared password means no per-user
identity and no revocation.

If the secret file is missing the site still builds, but every page is locked with NO
payload: a build cannot leak because nobody configured the gate.
"""
import base64
import hashlib
import json
import os
import re

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SECRET = os.path.expanduser("~/.hermes/secrets/church-gate.txt")
_GATE_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "church-gate.js")
ITERATIONS = 200_000
KEYLEN = 32
DOMAIN = b"cn-gate-v1|"


def passphrase():
    """The site passphrase, or None when the gate has not been configured.

    Read-only and never logged: the value must not appear in build output, in git,
    or in any transcript.
    """
    try:
        with open(SECRET, encoding="utf-8") as fh:
            value = fh.read().strip()
        return value or None
    except FileNotFoundError:
        return None


def _b64(raw):
    return base64.b64encode(raw).decode("ascii")


def _nonce_material(pw, text):
    """Deterministic salt + IV derived from the passphrase and the plaintext.

    These payloads re-encrypt on every build. `os.urandom()` salt/IV made every page
    differ on every run even when nothing changed, so each build showed up as churn.
    Deriving both from SHA-256(domain | passphrase | plaintext) makes the build
    reproducible: identical input produces identical ciphertext.

    Uniqueness — what AES-GCM actually depends on — still holds: a different
    passphrase or a different plaintext yields a different salt (64 bits) and IV
    (96 bits), so no two distinct messages are ever encrypted under the same
    key+nonce pair. Both values ship inside the payload anyway, so deriving them
    reveals nothing the payload does not already carry.
    """
    return hashlib.sha256(
        DOMAIN + pw.encode("utf-8") + b"|" + text.encode("utf-8")
    ).digest()


def encrypt(text, pw, title):
    """Encrypt one page fragment into the JSON payload the browser gate decrypts."""
    material = _nonce_material(pw, text)
    salt, iv = material[:16], material[16:28]
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEYLEN, salt=salt,
                     iterations=ITERATIONS).derive(pw.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, text.encode("utf-8"), None)
    payload = json.dumps({
        "v": 1,
        "title": title,
        "kdf": {"name": "PBKDF2", "hash": "SHA-256",
                "iterations": ITERATIONS, "salt": _b64(salt)},
        "alg": "AES-GCM",
        "iv": _b64(iv),
        "ct": _b64(ct),
    }, separators=(",", ":"))
    # A title could in principle contain "</" — it must not close the script element early.
    return payload.replace("</", "<\\/")


def unconfigured_payload():
    """No passphrase set: ship no ciphertext at all, so nothing can be cracked."""
    return json.dumps({"v": 1, "unconfigured": True}, separators=(",", ":"))


LOCK_CSS = """
#cn-lock{max-width:450px;margin:13vh auto 0;padding:0 24px}
.cn-card{background:var(--surface);border:1px solid var(--border);border-radius:16px;
padding:30px 32px;box-shadow:0 26px 60px rgba(0,0,0,.45)}
.cn-mark{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:21px;
color:#F1EDE3;background:linear-gradient(135deg,var(--ruby),var(--violet));
box-shadow:0 0 18px rgba(142,36,52,.5);margin-bottom:16px}
.cn-card h1{font-family:'Cormorant Garamond',serif;font-size:27px;font-weight:600;margin:0 0 6px;line-height:1.2}
.cn-card p{color:var(--text-muted);font-size:13.5px;margin:0 0 20px}
#cn-pass{width:100%;padding:12px 14px;border-radius:10px;border:1px solid var(--border);
background:var(--surface2);color:var(--text);font-size:15px;font-family:inherit}
#cn-pass:focus{outline:none;border-color:var(--amber);box-shadow:0 0 0 3px rgba(200,155,60,.16)}
#cn-form button{margin-top:14px;width:100%;padding:12px;border-radius:10px;
border:1px solid rgba(200,155,60,.45);background:rgba(200,155,60,.14);color:var(--candle);
font-weight:600;font-size:14.5px;font-family:inherit;cursor:pointer;transition:.15s}
#cn-form button:hover{background:rgba(200,155,60,.24)}
#cn-err{display:none;margin-top:11px;font-size:12.5px;color:#E2798A}
.cn-note{margin-top:18px;padding-top:14px;border-top:1px solid var(--border);
font-size:11.5px;color:var(--text-dim);line-height:1.55}
#cn-root[hidden]{display:none}
"""

LOCK_UI = """<section id="cn-lock"><div class="cn-card">
  <div class="cn-mark">&#10013;</div>
  <h1>Church Notes</h1>
  <p>A private theology &amp; sermon wiki. Enter the password to read it.</p>
  <form id="cn-form" autocomplete="off">
    <input type="password" id="cn-pass" placeholder="Password" autocomplete="current-password"
           autocapitalize="off" spellcheck="false" aria-label="Site password">
    <button type="submit">Unlock</button>
    <div id="cn-err" role="alert"></div>
  </form>
  <div class="cn-note">&#128274; Encrypted page &mdash; the text is unreadable without the
  password, including in the page source. <noscript>JavaScript is required to unlock this page.</noscript></div>
</div></section>
<div id="cn-root" hidden></div>
<script type="application/json" id="cn-payload">__PAYLOAD__</script>
<script src="__PREFIX__assets/js/church-gate.js" defer></script>
</body></html>"""


def gate_page(html, title, prefix="", pw=None):
    """Wrap a fully-rendered page in the locked shell.

    The head, nav and brand stay readable (a locked door should say what it is); every
    byte from `<main>` onwards — the actual notes, the footer, and any inline script
    that renders them — is encrypted. The real title is carried inside the ciphertext
    so the page titles do not leak the contents either.
    """
    i = html.find("<main")
    if i == -1:
        raise ValueError("gate_page: no <main> found — refusing to emit the page ungated")
    pre, rest = html[:i], html[i:]
    tail = "</body></html>"
    if not rest.rstrip().endswith(tail):
        raise ValueError("gate_page: unexpected page shape — refusing to emit it ungated")
    rest = rest.rstrip()[:-len(tail)]

    payload = unconfigured_payload() if pw is None else encrypt(rest, pw, title)
    pre = re.sub(r"<title>.*?</title>", "<title>Church Notes</title>", pre,
                 count=1, flags=re.S)
    pre = pre.replace("</head>", "<style>" + LOCK_CSS + "</style>\n</head>", 1)
    return pre + LOCK_UI.replace("__PAYLOAD__", payload).replace("__PREFIX__", prefix)


def write_assets(out_dir):
    """Emit the gate script into the built site. Called from the build, so a clean
    build regenerates it rather than losing a hand-dropped copy."""
    dst = os.path.join(out_dir, "assets", "js")
    os.makedirs(dst, exist_ok=True)
    with open(_GATE_JS, encoding="utf-8") as fh:
        src = fh.read()
    with open(os.path.join(dst, "church-gate.js"), "w", encoding="utf-8") as fh:
        fh.write(src)
    return os.path.join(dst, "church-gate.js")
