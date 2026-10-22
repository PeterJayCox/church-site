#!/usr/bin/env bash
# Church Notes — local preview server.
# Serves ./docs on http://127.0.0.1:8042  (private to this Mac only).
# Usage:  ./scripts/serve-local.sh   [port]
#
# Threaded on purpose: `python3 -m http.server` is single-threaded, so one
# keep-alive connection from a browser (or a half-open socket) blocks every
# later request — the port stays open, connections are accepted, and clients
# get an empty reply (curl exit 52) until the server is restarted.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${1:-8042}"
if lsof -i :"$PORT" >/dev/null 2>&1; then
  echo "Port $PORT already in use — is a server already running?"
  echo "Open http://localhost:$PORT in your browser."
  exit 0
fi
echo "Serving Church Notes at  http://localhost:$PORT"
echo "Private to this Mac. Ctrl-C to stop."
echo
echo "Browse http://localhost:$PORT or http://127.0.0.1:$PORT — NOT the"
echo "church.peterjaycox.com alias. The pages are password-gated with WebCrypto,"
echo "which browsers allow only on https, localhost and 127.0.0.1; on the alias"
echo "the gate reports 'needs https' instead of showing the password form."
exec python3 -c '
import functools, sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

class Server(ThreadingHTTPServer):
    daemon_threads = True

handler = functools.partial(SimpleHTTPRequestHandler, directory="docs")
Server(("127.0.0.1", int(sys.argv[1])), handler).serve_forever()
' "$PORT"
