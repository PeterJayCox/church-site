# Church Notes Site

Private static site generator for the Obsidian **Church/Wiki** (sermon notes,
Bible study, theology), rendered in the **Stained-Glass** theme.

## Status — LOCAL SCAFFOLD
- [x] Generator reads the real `Church/Wiki` markdown (36 pages)
- [x] Stained-Glass themed output + `<meta robots=noindex>` on every page
- [x] `robots.txt` blocks all crawlers (private site)
- [ ] GitHub repo + Pages
- [ ] Custom domain / subdomain DNS (Hostinger)
- [ ] Deploy script with git push

**The site is intentionally private.** Every page carries
`<meta name="robots" content="noindex, nofollow">` and `robots.txt` is
`Disallow: /`. Do not publish without keeping those in place.

## Build
```bash
~/.hermes/hermes-agent/venv/bin/python3 build_site.py
# output -> ./site/   (open site/index.html to preview)
```
Or: `bash scripts/church-site-build.sh`

Use the **hermes venv python** (system 3.9 picks up a stale `PYTHONPATH`).

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

## Next steps (when you're ready to publish)
1. Pick a host: subdomain `church.peterjaycox.com` (recommended, clean + easy
   to block), subpath `/church/`, or GitHub Pages only.
2. `gh repo create church-notes-site --private|public` and enable Pages.
3. Point DNS (Hostinger) / add `CNAME` (see `site/CNAME.example`).
4. Fill in the git push block in `scripts/church-site-build.sh`.

## Files
| Path | Purpose |
|------|---------|
| `build_site.py` | Generator (theme + parser + renderer) |
| `scripts/church-site-build.sh` | Local build script (staged for deploy) |
| `site/` | Generated output (gitignore-able; rebuilt) |
| `~/Desktop/Hermes/church-notes-rich-stainedglass.html` | Designed homepage mockup (the target look) |
