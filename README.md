# Church Notes Site

Private static site generator for the Obsidian **Church/Wiki** (sermon notes,
Bible study, theology), rendered in the **Stained-Glass** theme.

## Status — PUBLISHED (gated)
- [x] Generator reads the real `Church/Wiki` markdown (58 pages)
- [x] Stained-Glass themed output + `<meta robots=noindex>` on every page
- [x] `robots.txt` blocks all crawlers (private site)
- [x] GitHub repo + Pages — `PeterJayCox/church-site` (PUBLIC repo, **ciphertext only**)
- [x] Custom domain `church.peterjaycox.com` (CNAME → `peterjaycox.github.io`)
- [x] Deploy script: `~/.hermes/scripts/church-site-deploy.sh`

**The site is private by *encryption*, not by host.** Every content page is
emitted as AES-256-GCM ciphertext and the browser decrypts it with the shared
passphrase (WebCrypto), so a public repo and public host expose nothing but
ciphertext. Keep `noindex`/`robots.txt` AND the gate in place.

**Honest limits of the gate** (there is no server):
- The ciphertext is public, so a weak passphrase is brute-forceable offline.
- Page **titles** and the page count/section names remain readable in the
  payload metadata and the nav.
- One shared passphrase: no per-user identity, no revocation.

## Build
```bash
~/.hermes/hermes-agent/venv/bin/python3 build_site.py
# output -> ./docs/   (open docs/index.html to preview — it needs an http origin
#                      for WebCrypto, so prefer scripts/serve-local.sh)
```
Or: `bash scripts/church-site-build.sh`

## Deploy
```bash
bash ~/.hermes/scripts/church-site-deploy.sh   # build -> verify gated -> push main
```
GitHub Pages serves `main:/docs`. It refuses to deploy without a gate
passphrase, and aborts if any page lacks a ciphertext payload.

## How it works
- Walks `Church/Wiki/**/*.md`, parses YAML frontmatter (`type`, `title`,
  `church`, `tags`, `date`, `preacher`, `passage`).
- Renders each page to `./site/<slug>.html` in the Stained-Glass theme.
- Resolves `[[wikilinks]]` (including `|display` and nested-bracket variants)
  to relative hrefs; unresolved links degrade to plain text (see limitations).
- **Rich homepage** (`index.html`) is fully data-driven from live wiki data:
  hero stats, Study of the Season (biggest series), browse grid, sermon
  series, concept chips, people & churches, recent sermons (by date), and a
  by-the-book index — no hand-typed content.
- **"The Bible Lands" interactive satellite map** (built by `scripts/build_map.py`
  into `map-block.html`, injected into the homepage) — self-contained, no CDN,
  works on `file://`. ESRI World Imagery tiles stream in on demand with
  drag-to-pan (cursor-follow), scroll / pinch / double-click zoom, `+`/`−`/`⟳`
  controls, and an OT / NT / All era toggle. 29 markers, Exodus & NT routes and
  region labels are reprojected live in Web Mercator from true lat/lon.
- **Per-sermon geography maps** — every sermon / passage page (and the
  homepage's overview) gets its own pannable/zoomable map. A `BOOKS` table
  (19 entries) maps each biblical book to its relevant region: Romans→Rome,
  Ephesians→Ephesus, Colossians→Colossae, Galatians→the Galatian cities,
  1 Peter→Asia Minor, Psalms & Nehemiah→Jerusalem, **Acts→Paul's whole
  Mediterranean mission network with his journey & voyage-to-Rome lines**,
  Exodus→Egypt to Sinai (with the route),
  Hebrews→the temple, Corinthians→Corinth, Philippians→Philippi,
  Thessalonians→Thessalonica, Timothy→Ephesus, Titus→Crete, Philemon→
  Colossae, Revelation→Patmos & the seven churches, the four Gospels→Galilee
  to Jerusalem, and Genesis→the patriarchs' route (Ur→Haran→Canaan→Egypt).
- **Sermons index + navigation** — a dedicated `sermons/index.html` page lists
  all talks grouped by book (with dates, passages, preachers); the navbar
  "Sermons" links to it, and every sermon page carries an "← All sermons ·
  ← Home" nav with a proper breadcrumb.

## Known limitations
- **Pathological wikilinks:** the corpus contains a few deeply-nested / malformed
  links (e.g. `../raw/sermons/[[equip-2-[[stephen-mcalpine-17-aug-2025]].md|…]]`).
  These degrade to plain text rather than breaking the build. Can be added to
  the resolver if you need them.
- **Flat output:** pages are currently emitted as `<slug>.html` in one folder
  (originally grouped by `type` is not directory-preserved yet).
- **Provenance markers** (`^[raw/sermons/…]`) are stripped; the raw-formatted
  (`Church/2025/…`) reference links are not resolved.

## Publishing notes
- Host: GitHub Pages, repo `PeterJayCox/church-site`, source `main:/docs`,
  custom domain `church.peterjaycox.com` (DNS CNAME → `peterjaycox.github.io`,
  record managed at Hostinger).
- The passphrase lives **only** at `~/.hermes/secrets/church-gate.txt` (0600).
  Never commit it; never put it in a command line or a transcript.
- Change it with `scripts/set-gate-password.py` (prompts, then rebuilds).

## Files
| Path | Purpose |
|------|---------|
| `build_site.py` | Generator (theme + parser + renderer) |
| `scripts/church-gate.js` | In-browser WebCrypto unlock |
| `scripts/church_gate.py` | Build-time encryption (passphrase → ciphertext) |
| `scripts/church-site-build.sh` | Local build only (no push) |
| `scripts/serve-local.sh` | Local preview server on 127.0.0.1:8042 |
| `~/.hermes/scripts/church-site-deploy.sh` | Build + gate check + push |
| `docs/` | Published output (committed; regenerated each build) |
