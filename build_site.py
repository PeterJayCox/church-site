#!/usr/bin/env python3
"""
Church Notes static site generator — Stained-Glass theme, rich homepage.
Reads the Obsidian Church/Wiki markdown and emits a themed static site with a
data-driven landing page (hero, study of the season, browse grid, series,
concepts, people, recent sermons, by-the-book).

PASSWORD-GATED SITE: every page is emitted as ciphertext behind one shared passphrase
(scripts/church_gate.py — PBKDF2-HMAC-SHA256 -> AES-256-GCM, decrypted in the browser).
The passphrase lives outside the repo at ~/.hermes/secrets/church-gate.txt (0600); with no
passphrase set, every page still builds but locked with no payload (fail-closed). Pages also
carry <meta name="robots" content="noindex,nofollow,noarchive,nosnippet"> and robots.txt
disallows everything. Run with the hermes venv python:
    ~/.hermes/hermes-agent/venv/bin/python3 build_site.py
Set or change the passphrase with scripts/set-gate-password.py (it rebuilds afterwards).
"""
import os, re, sys, datetime

HOME = os.path.expanduser("~")
WIKI   = os.path.join(HOME, "Library/Mobile Documents/iCloud~md~obsidian/Documents/Peter's Vault/Church/Wiki")
# CHURCH_OUT lets a build go somewhere other than the live output (dry runs, tests).
# `docs/` is the published artifact: GitHub Pages serves main:/docs (see
# ~/.hermes/scripts/church-site-deploy.sh).
OUT    = os.environ.get("CHURCH_OUT") or os.path.join(HOME, "Desktop/Hermes/Church Site/docs")
SITE_NAME = "Church Notes"
SITE_TAG  = "a private theology &amp; sermon wiki"
MAP_HTML  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map-block.html")

# Reusable bible-map library (sermon-focus maps), importable without side effects.
_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    import build_map as _bmap
except Exception:
    _bmap = None

# Password gate: every page is emitted as ciphertext (see scripts/church_gate.py).
# GATE_PW is set once in main(); None means unconfigured, and every page then ships
# locked with no payload rather than in the clear.
try:
    import church_gate as _gate
except Exception as _gate_err:            # never let a gate import failure ship plaintext
    _gate = None
    _GATE_IMPORT_ERROR = _gate_err
GATE_PW = None

# ---------------------------------------------------------------- theme
CSS = """
:root{--bg:#19181E;--surface:#211F28;--surface2:#2C2A35;--surface3:#36333F;
--text:#F1EDE3;--text-muted:#A7A09A;--text-dim:#7A746E;--border:#373442;--border-l:#46424F;
--ruby:#9A2A3E;--ruby-l:#B93C52;--amber:#C89B3C;--candle:#F2C879;--violet:#4C3A8A;
--violet-l:#6A55B5;--moss:#5F7A55;--teal:#2E7D78;--radius:16px;
--header-bg:rgba(25,24,30,.85);--body-text:#E6E1D6}
[data-theme="light"]{--bg:#F3EEE1;--surface:#FBF7EC;--surface2:#EEE7D5;--surface3:#E3DAC3;
--text:#2B2620;--text-muted:#5D5648;--text-dim:#877C6A;--border:#DBD2BB;--border-l:#C2B492;
--header-bg:rgba(243,238,225,.9);--body-text:#39332A}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh;display:flex;flex-direction:column;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px;width:100%}
a{color:inherit}
.serif{font-family:'Cormorant Garamond',serif}
header{position:sticky;top:0;z-index:20;background:var(--header-bg);backdrop-filter:saturate(160%) blur(10px);-webkit-backdrop-filter:saturate(160%) blur(10px);border-bottom:1px solid var(--border)}
.topbar{display:flex;align-items:center;justify-content:space-between;height:62px;gap:20px}
.brand{display:flex;align-items:center;gap:11px;text-decoration:none}
.brand .mark{width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,var(--ruby),var(--violet));display:grid;place-items:center;font-size:15px;color:#F1EDE3;box-shadow:0 0 14px rgba(142,36,52,.5)}
.brand .nm{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:20px;line-height:1}
.brand .sb{font-size:11px;color:var(--text-dim);letter-spacing:.03em}
nav{display:flex;gap:3px;align-items:center;flex:1;justify-content:center}
nav a{font-size:13.5px;color:var(--text-muted);text-decoration:none;padding:8px 13px;border-radius:999px;transition:.15s;white-space:nowrap}
nav a:hover{color:var(--text);background:var(--surface2)}
.hero{text-align:center;padding:64px 24px 32px;position:relative;overflow:hidden;background:radial-gradient(ellipse at 50% -10%,rgba(200,155,60,.12),transparent 60%),radial-gradient(ellipse at 85% 15%,rgba(142,36,52,.14),transparent 55%),radial-gradient(ellipse at 12% 20%,rgba(76,58,138,.16),transparent 55%)}
[data-theme="light"] .hero{background:radial-gradient(ellipse at 50% -10%,rgba(200,155,60,.16),transparent 60%),radial-gradient(ellipse at 85% 15%,rgba(154,42,62,.10),transparent 55%),radial-gradient(ellipse at 12% 20%,rgba(76,58,138,.10),transparent 55%)}
.season{display:inline-flex;align-items:center;gap:8px;background:rgba(95,122,85,.16);border:1px solid rgba(95,122,85,.45);color:var(--moss);font-size:11.5px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;padding:6px 14px;border-radius:999px}
.season i{width:8px;height:8px;border-radius:50%;background:var(--moss);display:inline-block;box-shadow:0 0 8px var(--moss)}
.verse{font-family:'Cormorant Garamond',serif;font-size:clamp(25px,4.2vw,40px);font-weight:500;line-height:1.35;max-width:720px;margin:22px auto 0}
.verse .qmark{font-size:1.6em;line-height:0;vertical-align:-.35em;color:var(--amber);opacity:.55;font-weight:700}
.verse .ref{display:inline-block;color:var(--candle);font-weight:600;font-style:normal;margin-top:10px;padding-top:10px;border-top:1px solid var(--amber);min-width:120px}
[data-theme="light"] .verse .ref{color:#8A6A1F}
.verse-sub{color:var(--amber);font-size:12px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;margin-top:14px}
.tagline{max-width:580px;margin:12px auto 0;color:var(--text-muted);font-size:15px;line-height:1.6}
.hero-stats{display:flex;justify-content:center;gap:26px;margin:26px auto 0;flex-wrap:wrap}
.hstat{text-align:center}
.hstat b{display:block;font-family:'Cormorant Garamond',serif;font-size:24px;font-weight:700;color:var(--candle)}
[data-theme="light"] .hstat b{color:#8A6A1F}
.hstat span{font-size:11px;color:var(--text-dim);letter-spacing:.04em;text-transform:uppercase}
.privbar{display:inline-flex;align-items:center;gap:7px;margin-top:22px;background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:6px 15px;font-size:11.5px;color:var(--text-muted)}
main{padding:40px 0 60px;flex:1}
.section{margin-bottom:46px}
.sec-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.sec-head .left{display:flex;align-items:center;gap:11px}
.sec-head h2{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:26px;margin:0}
.sec-head .bar{width:28px;height:3px;background:linear-gradient(90deg,var(--ruby),var(--amber));border-radius:2px}
.sec-head .more{font-size:12.5px;color:var(--text-muted);text-decoration:none;border-bottom:1px dotted var(--border)}
.sec-head .more:hover{color:var(--candle)}
[data-theme="light"] .sec-head .more:hover{color:#8A6A1F}
.ornament{display:flex;align-items:center;justify-content:center;gap:10px;margin:38px auto}
.ornament .seg{height:2px;border-radius:1px}
.ornament .s1{width:44px;background:var(--ruby)}
.ornament .s2{width:22px;background:var(--amber)}
.ornament .s3{width:8px;height:8px;border-radius:50%;background:radial-gradient(circle at 35% 30%,var(--violet-l),var(--violet));transform:none}
.ornament .s4{width:22px;background:var(--amber)}
.ornament .s5{width:44px;background:var(--teal)}
.featured{display:grid;grid-template-columns:1.15fr .85fr;gap:20px}
.featured .main{background:linear-gradient(150deg,var(--surface) 0%,var(--surface2) 100%);border:1px solid var(--border);border-left:4px solid var(--amber);border-radius:var(--radius);padding:30px}
.featured .k{font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--amber);font-weight:600}
.featured .main h3{font-family:'Cormorant Garamond',serif;font-size:28px;font-weight:700;margin:10px 0 8px}
.featured .lede{color:var(--text-muted);font-size:14px;line-height:1.65}
.featured .meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.tag{font-size:11.5px;padding:5px 11px;border-radius:999px;background:var(--surface3);color:var(--text-muted);border:1px solid var(--border)}
.featured .main a.cta{display:inline-block;margin-top:20px;font-size:13px;font-weight:600;color:var(--candle);text-decoration:none}
[data-theme="light"] .featured .main a.cta{color:#8A6A1F}
.featured .main a.cta:hover{text-decoration:underline}
.sidestack{display:flex;flex-direction:column;gap:20px}
.sidestack .sub{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:22px;flex:1}
.sidestack .sub .k{font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;font-weight:600;color:var(--ruby-l)}
.sidestack .sub h4{font-family:'Cormorant Garamond',serif;font-size:19px;margin:8px 0 6px}
.sidestack .sub p{font-size:13px;color:var(--text-muted);line-height:1.55}
.browse{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.cat{display:flex;flex-direction:column;gap:14px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:22px;text-decoration:none;transition:transform .18s;position:relative;overflow:hidden}
.cat:hover{transform:translateY(-3px);border-color:var(--border-l)}
.cat::before{content:"";position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,var(--cc-a),var(--cc-b));opacity:.9}
.cat .ic{width:40px;height:40px;border-radius:11px;display:grid;place-items:center;font-size:19px;background:var(--surface2);border:1px solid var(--border)}
.cat h3{font-family:'Cormorant Garamond',serif;font-size:20px;font-weight:600}
.cat p{font-size:13px;color:var(--text-muted);line-height:1.55;flex:1}
.cat .num{font-size:12px;color:var(--text-dim)}
.cat .num b{color:var(--candle);font-weight:600}
.series{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.srs{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:22px;text-decoration:none;display:flex;flex-direction:column;gap:9px;transition:transform .18s}
.srs:hover{transform:translateY(-3px);border-color:var(--border-l)}
.srs .book{font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:700;color:var(--amber)}
[data-theme="light"] .srs .book{color:#8A6A1F}
.srs .bar{height:4px;border-radius:2px;background:linear-gradient(90deg,var(--sc-a,var(--ruby)),var(--sc-b,var(--amber)))}
.srs h4{font-size:14.5px;font-weight:600}
.srs p{font-size:12.5px;color:var(--text-muted);line-height:1.5;flex:1}
.srs .n{font-size:11.5px;color:var(--text-dim)}
.srs .n b{color:var(--candle)}
[data-theme="light"] .srs .n b{color:#8A6A1F}
.concept-chips{display:flex;flex-wrap:wrap;gap:10px}
.chip{display:inline-flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:9px 16px;text-decoration:none;font-size:13px;color:var(--text-muted);transition:.15s}
.chip b{color:var(--text);font-weight:600}
.chip i{width:8px;height:8px;border-radius:50%;background:var(--cc,var(--amber));box-shadow:0 0 8px var(--cc,var(--amber))}
.chip:hover{color:var(--text);border-color:var(--border-l);background:var(--surface2)}
.people{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.person{display:flex;gap:16px;align-items:flex-start;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px}
.person .avatar{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;font-family:'Cormorant Garamond',serif;font-weight:700;font-size:17px;color:#F1EDE3;flex-shrink:0}
.person h4{font-size:14.5px;font-weight:600}
.person .role{font-size:11.5px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.04em}
.person p{font-size:12.5px;color:var(--text-muted);line-height:1.5;margin-top:5px}
.person .church{font-size:11.5px;color:var(--text-muted);margin-top:7px}
.person .church b{color:var(--moss)}
.sermon-list{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.srow{display:flex;align-items:center;gap:16px;padding:15px 22px;border-bottom:1px solid var(--border);text-decoration:none;transition:background .15s}
.srow:last-child{border-bottom:none}
.srow:hover{background:var(--surface2)}
.srow .d{background:var(--surface2);border:1px solid var(--border);border-radius:11px;min-width:56px;text-align:center;padding:9px 6px}
.srow .d b{display:block;font-family:'Cormorant Garamond',serif;font-size:24px;line-height:1;color:var(--candle)}
[data-theme="light"] .srow .d b{color:#8A6A1F}
.srow .d span{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-dim)}
.srow .t{flex:1;min-width:0}
.srow .t .meta{font-size:11px;color:var(--text-dim);letter-spacing:.03em}
.srow .t h4{font-size:15px;font-weight:600;margin:2px 0}
.srow .t p{font-size:12.5px;color:var(--text-muted)}
.srow .ref{font-family:'Cormorant Garamond',serif;font-size:16px;color:var(--text-muted);white-space:nowrap}
.books{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.bk{background:var(--surface);border:1px solid var(--border);border-radius:11px;padding:14px;text-decoration:none;transition:.15s}
.bk:hover{background:var(--surface2);border-color:var(--border-l)}
.bk .b{font-family:'Cormorant Garamond',serif;font-size:19px;font-weight:700;color:var(--amber)}
[data-theme="light"] .bk .b{color:#8A6A1F}
.bk span{display:block;font-size:11px;color:var(--text-dim);margin-top:3px}
.crumbs{font-size:12px;color:var(--text-dim);padding:18px 0 0}
.crumbs a{color:var(--text-muted)}
.crumbs a:hover{color:var(--candle);text-decoration:none}
.pg-nav{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;margin:10px 0 4px}
.pg-nav a{color:var(--candle);text-decoration:none;border-bottom:1px dotted var(--border-l)}
[data-theme="light"] .pg-nav a{color:#8A6A1F}
.pg-nav a:hover{text-decoration:underline;border-bottom-style:solid}
.wiki-body h3 .n,.ser .n{display:inline-block;min-width:22px;text-align:center;font-size:11.5px;
  color:var(--candle);background:var(--surface3);border-radius:999px;padding:1px 7px;vertical-align:2px}
[data-theme="light"] .wiki-body h3 .n,[data-theme="light"] .ser .n{color:#8A6A1F}
.pg-meta{color:var(--text-dim);font-size:12px}
.pg-count{color:var(--text-dim);font-size:12px;font-weight:400}
.wiki-body h1{font-family:'Cormorant Garamond',serif;font-size:34px;line-height:1.2;margin:6px 0 18px}
.wiki-body h2{font-family:'Cormorant Garamond',serif;font-size:24px;margin:26px 0 10px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.wiki-body h3{font-size:17px;margin:20px 0 8px;color:var(--candle)}
.wiki-body p{margin:10px 0;color:var(--body-text)}
.wiki-body>p:first-of-type:first-letter{font-family:'Cormorant Garamond',serif;font-size:3.1em;font-weight:600;color:var(--candle);float:left;line-height:.82;padding:4px 8px 0 0}
[data-theme="light"] .wiki-body>p:first-of-type:first-letter{color:#8A6A1F}
.wiki-body ul,.wiki-body ol{margin:10px 0 10px 22px;color:var(--body-text)}
.wiki-body li{margin:5px 0}
.wiki-body blockquote{position:relative;border-left:3px solid var(--amber);background:var(--surface);padding:14px 18px 14px 44px;margin:14px 0;border-radius:0 12px 12px 0;color:var(--text-muted);font-style:italic}
.wiki-body blockquote::before{content:"\\201C";position:absolute;left:12px;top:2px;font-family:'Cormorant Garamond',serif;font-size:44px;line-height:1;color:var(--amber);opacity:.55}
.wiki-body strong{color:var(--text)}
.wiki-body em{color:var(--candle)}
[data-theme="light"] .wiki-body h3,[data-theme="light"] .wiki-body em{color:#8A6A1F}
.wiki-body hr{border:none;border-top:1px solid var(--border);margin:24px 0}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0}
.meta-line{font-size:12.5px;color:var(--text-dim);border:1px solid var(--border);background:var(--surface);border-radius:12px;padding:10px 14px;margin-bottom:14px}
.meta-line strong{color:var(--text-muted)}
.meta-line a.passage{color:var(--candle);font-weight:600;font-variant:small-caps;letter-spacing:.03em;text-decoration:none;border-bottom:1px dotted var(--border-l)}
.meta-line a.passage:hover{border-bottom-style:solid;color:var(--text)}
[data-theme="light"] .meta-line a.passage{color:#8A6A1F}
.scripture{font-variant:small-caps;letter-spacing:.03em;color:var(--amber);font-weight:600}
[data-theme="light"] .scripture{color:#8A6A1F}
.srow .go{color:var(--text-dim);font-size:16px;opacity:0;transition:opacity .15s;flex-shrink:0}
.srow:hover .go{opacity:1}
.srow .mapflag{font-size:12px;margin-left:6px;opacity:.85}
.sfilter{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 16px}
.sfilter input[type="search"]{flex:1;min-width:220px;background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:10px 18px;color:var(--text);font-size:13.5px;font-family:'Inter',sans-serif;outline:none}
.sfilter input[type="search"]:focus{border-color:var(--violet-l)}
.sfilter select{background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:10px 14px;color:var(--text);font-size:13px;font-family:'Inter',sans-serif;outline:none;cursor:pointer}
.sfilter .fcount{font-size:12px;color:var(--text-dim);white-space:nowrap}
.bgroup{border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);padding:20px 24px;margin-bottom:16px}
.bgroup h3.ser{margin:0 0 10px;font-family:'Cormorant Garamond',serif;font-size:21px;color:var(--amber);border:none;padding:0}
[data-theme="light"] .bgroup h3.ser{color:#8A6A1F}
.bgroup ul{list-style:none;margin:0}
.bgroup li{padding:8px 0;border-bottom:1px solid var(--border)}
.bgroup li:last-child{border-bottom:none}
.bgroup li a{color:var(--text);font-weight:500;text-decoration:none}
.bgroup li a:hover{color:var(--candle);text-decoration:underline}
[data-theme="light"] .bgroup li a:hover{color:#8A6A1F}
.theme-toggle{background:var(--surface2);border:1px solid var(--border);color:var(--text-muted);border-radius:999px;width:34px;height:34px;display:grid;place-items:center;cursor:pointer;font-size:15px;transition:.15s;flex-shrink:0}
.theme-toggle:hover{color:var(--candle);border-color:var(--border-l)}
[data-theme="light"] .theme-toggle:hover{color:#8A6A1F}
.theme-toggle .tt-auto,.theme-toggle .tt-light{display:none}
.theme-toggle .tt-dark{display:inline}
html[data-theme-mode="auto"] .theme-toggle .tt-dark{display:none}
html[data-theme-mode="auto"] .theme-toggle .tt-auto{display:inline}
html[data-theme-mode="light"] .theme-toggle .tt-dark{display:none}
html[data-theme-mode="light"] .theme-toggle .tt-light{display:inline}
.mnav{display:none;gap:6px;padding:0 0 12px;flex-wrap:wrap}
.mnav a{font-size:12.5px;color:var(--text-muted);text-decoration:none;padding:6px 12px;border-radius:999px;background:var(--surface);border:1px solid var(--border)}
.mnav a:hover{color:var(--text)}
footer{border-top:1px solid var(--border);padding:28px 0;background:var(--surface)}
.foot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--text-dim)}
.priv-badge{background:var(--surface2);border:1px solid var(--border);padding:5px 12px;border-radius:999px;font-size:11px;color:var(--text-muted)}
@media(max-width:900px){.browse,.series,.people{grid-template-columns:repeat(2,1fr)}.books{grid-template-columns:repeat(3,1fr)}.featured{grid-template-columns:1fr}}
@media(max-width:640px){.browse,.series,.people,.books{grid-template-columns:1fr}nav{display:none}.mnav{display:flex}.srow .ref{display:none}.srow .go{display:none}}
"""

FAVICON_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
    "<stop offset='0' stop-color='#9A2A3E'/><stop offset='1' stop-color='#4C3A8A'/>"
    "</linearGradient></defs>"
    "<rect width='64' height='64' rx='16' fill='url(#g)'/>"
    "<text x='32' y='45' font-size='36' text-anchor='middle' fill='#F1EDE3' "
    "font-family='Georgia,serif'>&#10013;</text></svg>")

THEME_HEAD = """<script>
(function(){var d=document.documentElement;
function sys(){try{return (window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)?'light':'dark';}catch(e){return 'dark';}}
function saved(){try{var s=localStorage.getItem('cn-theme2');return (s==='light'||s==='dark')?s:null;}catch(e){return null;}}
function mode(){return saved()||'auto';}
function save(m){try{if(m==='auto'){localStorage.removeItem('cn-theme2');}else{localStorage.setItem('cn-theme2',m);}}catch(e){}}
function label(m){var b=document.querySelector('.theme-toggle');if(!b){return;}
var t={auto:'Appearance: auto \\u2014 follows your system ('+sys()+'). Click to cycle auto \\u2192 parchment \\u2192 stained glass.',
light:'Appearance: parchment (pinned). Shift-click to follow your system again.',
dark:'Appearance: stained glass (pinned). Shift-click to follow your system again.'}[m];
if(t){b.setAttribute('title',t);b.setAttribute('aria-label',t);}}
function apply(){var m=mode();d.setAttribute('data-theme',m==='auto'?sys():m);d.setAttribute('data-theme-mode',m);label(m);}
function cycle(ev){var m=mode();
if(ev&&ev.shiftKey){save('auto');}
else if(m==='auto'){save(sys()==='dark'?'light':'dark');}
else if(m===sys()){save('auto');}
else{save(m==='light'?'dark':'light');}
apply();}
function followSystem(){if(!saved()){apply();}}
try{localStorage.removeItem('cn-theme');}catch(e){}
window.__cnTheme={cycle:cycle,apply:apply,mode:mode,setAuto:function(){save('auto');apply();}};
apply();
try{var mq=window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)');
if(mq&&mq.addEventListener){mq.addEventListener('change',followSystem);}}catch(e){}
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',apply);}
})();
</script>"""

THEME_TOGGLE = ('<button class="theme-toggle" id="theme-toggle" type="button"'
    ' aria-label="Appearance" title="Appearance"'
    ' onclick="window.__cnTheme.cycle(event)"'
    " onkeydown=\"if(event.key==='Enter'||event.key===' '){event.preventDefault();window.__cnTheme.cycle(event)}\">"
    '<span class="tt-auto" aria-hidden="true">\U0001f317</span>'
    '<span class="tt-light" aria-hidden="true">\U0001fa9f</span>'
    '<span class="tt-dark" aria-hidden="true">\U0001f56f\ufe0f</span></button>')


def head(title, prefix=""):
    import base64
    fav = "data:image/svg+xml;base64," + base64.b64encode(FAVICON_SVG.encode()).decode()
    return f"""<!DOCTYPE html>
<html lang="en-AU" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · {SITE_NAME}</title>
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<link rel="icon" type="image/svg+xml" href="{fav}">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
{THEME_HEAD}
</head>
<body>
<header><div class="wrap topbar">
  <a class="brand" href="{prefix}index.html"><span class="mark">✝</span><span><span class="nm">{SITE_NAME}</span><br><span class="sb">{SITE_TAG}</span></span></a>
  <nav>
    <a href="{prefix}index.html">Home</a>
    <a href="{prefix}index.html#series">Series</a>
    <a href="{prefix}sermons/index.html">Sermons</a>
    <a href="{prefix}index.html#concepts">Concepts</a>
    <a href="{prefix}index.html#people">People</a>
    <a href="{prefix}index.html#books">By the Book</a>
    <a href="https://peterjaycox.com">Hub</a>
  </nav>
  {THEME_TOGGLE}
</div>
<div class="wrap"><nav class="mnav" aria-label="Mobile navigation">
  <a href="{prefix}index.html">Home</a>
  <a href="{prefix}sermons/index.html">Sermons</a>
  <a href="{prefix}index.html#series">Series</a>
  <a href="{prefix}index.html#concepts">Concepts</a>
  <a href="{prefix}index.html#books">By the Book</a>
  <a href="https://peterjaycox.com">Hub</a>
</nav></div>
</header>
"""

def foot():
    return f"""<footer><div class="wrap foot">
  <span>© {datetime.date.today().year} {SITE_NAME} — private theology &amp; sermon wiki</span>
  <span class="priv-badge">🔒 Private · password protected</span>
</div></footer>
</body></html>"""

def emit(path, html, title, prefix=""):
    """Write one page, behind the password gate.

    Every content page goes through here. If the gate module or the passphrase is
    missing, gate_page() still emits a locked shell with no payload — the site is
    unusable until it is configured, which is the safe direction to fail in.
    """
    if _gate is not None:
        html = _gate.gate_page(html, title, prefix=prefix, pw=GATE_PW)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)


def build_sermons_index(pages):
    """A dedicated sermons index page, grouped by book, with client-side search/filter."""
    from collections import OrderedDict
    raw = [p for p in pages if p["rel"].startswith("raw/sermons/")]
    def sdate(p): return scalar(p["meta"].get("date","")) or "0000"
    groups = OrderedDict()
    for p in sorted(raw, key=sdate, reverse=True):
        book = _bmap.detect_book(scalar(p["meta"].get("passage")) or page_title(p)) if _bmap else None
        key = book_label(book) if book else "Other"
        groups.setdefault(key, []).append(p)
    # canonical book order, then Other
    canon = [k for k in _bmap.BOOKS if k.title() in groups] if _bmap else []
    order = [k.title() for k in canon if k.title() in groups]
    order += [k for k in groups if k not in order]
    rows = ""
    for key in order:
        n = len(groups[key])
        items = ""
        for p in groups[key]:
            has_map = False
            if _bmap:
                try:
                    has_map = bool(_bmap.detect_book(scalar(p["meta"].get("passage")) or page_title(p)))
                except Exception:
                    has_map = False
            flag = '<span class="mapflag" title="This talk includes a Bible-lands focus map">🗺️</span>' if has_map else ""
            items += (f'<li data-title="{escape_html(page_title(p).lower())}" '
                      f'data-preacher="{escape_html(scalar(p["meta"].get("preacher")).lower())}" '
                      f'data-church="{escape_html(church_display(p["meta"].get("church")).lower())}">'
                      f'<a href="../{p["out_rel"]}">{page_title(p)}</a>{flag}'
                      f' <span class="pg-meta">({sdate(p)}'
                      + (f' · {scalar(p["meta"].get("passage"))}' if scalar(p["meta"].get("passage")) else '')
                      + (f' · {scalar(p["meta"].get("preacher"))}' if scalar(p["meta"].get("preacher")) else '')
                      + ')</span></li>\n')
        rows += (f'<div class="bgroup" data-book="{key.lower()}"><h3 class="ser">{key}'
                 f' <span class="pg-count">· {n} talk{"s" if n!=1 else ""}</span></h3><ul>{items}</ul></div>')
    preachers = sorted({scalar(p["meta"].get("preacher")) for p in raw if scalar(p["meta"].get("preacher"))})
    church_opts = sorted({church_display(p["meta"].get("church")) for p in raw})
    popts = "".join(f'<option value="{escape_html(x.lower())}">{escape_html(x)}</option>' for x in preachers)
    copts = "".join(f'<option value="{escape_html(x.lower())}">{escape_html(x)}</option>' for x in church_opts)
    filter_ui = f"""
<div class="sfilter">
  <input type="search" id="ssearch" placeholder="Search titles, passages, text…" aria-label="Search sermons">
  <select id="spreacher" aria-label="Filter by preacher"><option value="">All preachers</option>{popts}</select>
  <select id="schurch" aria-label="Filter by church"><option value="">All churches</option>{copts}</select>
  <span class="fcount" id="scount">{len(raw)} talks</span>
</div>"""
    os.makedirs(os.path.join(OUT, "sermons"), exist_ok=True)
    h = head("Sermons", prefix="../")
    h += ('<main class="wrap"><div class="crumbs"><a href="../index.html">Home</a> / Sermons</div><div class="wiki-body">'
          f'<h1>Sermons</h1><p>Every recorded sermon, grouped by book. In total, {len(raw)} talks.</p>'
          + filter_ui + rows
          + '</div></main>'
          + """<script>
(function(){
  var q=document.getElementById('ssearch'), pr=document.getElementById('spreacher'),
      ch=document.getElementById('schurch'), cnt=document.getElementById('scount');
  var groups=[].slice.call(document.querySelectorAll('.bgroup'));
  function apply(){
    var t=(q.value||'').toLowerCase().trim(), p=pr.value, c=ch.value, shown=0;
    groups.forEach(function(g){
      var vis=0;
      [].slice.call(g.querySelectorAll('li')).forEach(function(li){
        var ok=true;
        if(p && li.getAttribute('data-preacher')!==p) ok=false;
        if(c && li.getAttribute('data-church')!==c) ok=false;
        if(t && (li.textContent.toLowerCase().indexOf(t)===-1)) ok=false;
        li.style.display=ok?'':'none'; if(ok) vis++;
      });
      g.style.display=vis?'':'none';
      shown+=vis;
    });
    cnt.textContent = shown + ' talk' + (shown===1?'':'s') + ' shown';
  }
  [q,pr,ch].forEach(function(el){ el.addEventListener('input',apply); });
})();
</script>""") + foot()
    emit(os.path.join(OUT, "sermons", "index.html"), h, "Sermons", prefix="../")
    print(f"[church-build] wrote sermons index ({len(raw)} talks, searchable, gated)")

# ---------------------------------------------------------------- helpers
def parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 4)
        if end != -1:
            fm = text[4:end]; body = text[end+4:]
            for line in fm.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":"); v = v.strip().strip('"').strip("'")
                    if v.startswith("["):
                        v = [x.strip().strip('"') for x in v.strip("[]").split(",") if x.strip()]
                    meta[k.strip().lower()] = v
            return meta, body
    return meta, text

def scalar(v):
    """Collapse a parsed YAML value that may be a list to a plain string."""
    if isinstance(v, (list, tuple)):
        v = v[0] if v else ""
    if v is None:
        return ""
    v = str(v)
    return "" if v.strip().lower() in ("null","none","nil","") else v

def first_sentence(body):
    # collapse wikilinks to their display text so snippets read cleanly
    body = re.sub(r"\[\[[^\]]*\|([^\]]*)\]\]", r"\1", body)   # [[path|disp]] -> disp
    body = re.sub(r"\[\[([^\]]*)\]\]", r"\1", body)           # [[name]] -> name
    body = re.sub(r"\^?\[[^\]]*?\]", "", body)                 # provenance markers
    body = re.sub(r"[\[\]]", "", body)
    m = re.search(r"[A-Za-z].*?[.!?]", body)
    if m:
        s = m.group(0).strip()
        s = _tidy_snippet(s)
        return s[:150] + ("…" if len(s) > 150 else "")
    return _tidy_snippet(body[:110])

def _tidy_snippet(s):
    """Repair snippets left dangling by a collapsed wikilink (e.g. 'Minister at .')."""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([.,;:])", r"\1", s)                       # 'word .' -> 'word.'
    s = re.sub(r"\b(at|of|in|from|with|alongside|to)\s*$", "", s).strip()
    s = re.sub(r"[,\s]+$", "", s)
    if s and s[-1] not in ".!?…":
        s += "."
    return s

def role_line(body):
    """Prefer a person's '**Role:' line as their card bio — never truncated mid-thought."""
    m = re.search(r"\*\*\s*Role\s*:?\*\*\s*(.+)", body)
    if not m:
        return None
    t = m.group(1)
    t = re.sub(r"\[\[[^\]]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", lambda mm: mm.group(1).split("/")[-1].replace("-"," ").title(), t)
    t = re.sub(r"[\[\]]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or None

def escape_html(t):
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# Bible Gateway deep link for a passage in the ESV. Normalises en/em dashes to a
# plain hyphen (Bible Gateway's range separator) and keeps colons/semicolons so
# multi-reading passages (e.g. "Colossians 1:2-8; 4:2-6") open as one search.
def bible_gateway_url(passage):
    if passage is None:
        return ""
    psg = str(passage)
    for d in ("\u2013", "\u2014", "\u2012", "\u2011", "\u2212"):
        psg = psg.replace(d, "-")
    psg = re.sub(r"\s*;\s*", "; ", psg).strip()
    if not psg:
        return ""
    from urllib.parse import quote
    return "https://www.biblegateway.com/passage/?search=" + quote(psg, safe=":;,") + "&version=ESV"

# The reading to open on Bible Gateway for a sermon: an explicit `study_readings`
# field (a Growth Group study-schedule passage) wins; else the sermon `passage`.
def study_readings(meta):
    return scalar(meta.get("study_readings")) or scalar(meta.get("passage"))

# tolerant obsidian wikilink resolver ------------------------------------
def resolve_wikilinks(text, slug_map, out_rel):
    text = re.sub(r"\^?\[raw/sermons/\[\[([^\]]*?)\]\]\.md\]", r"[[\1]]", text)
    text = re.sub(r"\^?\[raw/sermons/[^\]]*?\.md\]", "", text)
    def repl(m):
        inner = m.group(1)
        if "|" in inner:
            target, disp = inner.rsplit("|", 1); disp = disp.strip()
        else:
            target, disp = inner, None
        t = re.sub(r"\[|\]", "", target).strip().rstrip("/")
        t = re.sub(r"\.md$", "", t).strip()   # strip literal '.md', not a char set
        slug = os.path.basename(t.rstrip("/"))
        href = slug_map.get(slug) or slug_map.get(os.path.normpath(t.replace(" ","-")))
        if href:
            rel = os.path.relpath(href, os.path.dirname(out_rel)) if out_rel else href
            label = disp or slug.replace("-"," ").title()
            return f'<a href="{rel}">{label}</a>'
        return disp or target
    return re.sub(r"\[\[+([^\]]*?)\]\]", repl, text)

def md_to_html(md):
    try:
        import markdown
        return markdown.markdown(md, extensions=["extra"])
    except Exception:
        return "<p>" + escape_html(md).replace("\n","</p><p>") + "</p>"

def slugify(name):
    return re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")

def page_title(p):
    t = p["meta"].get("title")
    if t:
        if isinstance(t, (list, tuple)):
            t = t[0] if t else ""
        else:
            t = str(t)
        return re.sub(r"[\[\]]", "", t).strip()
    m = re.search(r"^#\s+(.+)$", p["body"], re.M)
    if m:
        t = re.sub(r"\[|\]|\|.*", "", m.group(1)).strip()
        return t or p["slug"].replace("-"," ").title()
    return p["slug"].replace("-"," ").title()

def initials(name):
    words = re.findall(r"[A-Za-z]", str(name))
    return (words[0] + (words[1] if len(words) > 1 else "")).upper() if words else "·"

# Friendly display names for raw slugs that were leaking into the UI.
CHURCH_NAMES = {
    "st-james": "St James Turramurra",
    "pm-baptist": "Port Macquarie Baptist",
    "st-james-turramurra": "St James Turramurra",
}
def church_display(v):
    v = scalar(v)
    return CHURCH_NAMES.get(v.strip().lower(), v)

BOOK_LABELS = {"1-peter": "1 Peter", "1-peter-series": "1 Peter", "2-corinthians": "2 Corinthians"}
def book_label(slugish):
    s = (slugish or "").strip()
    return BOOK_LABELS.get(s, s.replace("-", " ").title())

# Stable per-concept accent: same concept keeps its colour across rebuilds.
CHIP_PALETTE = ["#6A55B5", "#B93C52", "#C89B3C", "#5F7A55", "#2E7D78", "#F2C879", "#9A2A3E"]
def concept_color(name):
    h = 0
    for ch in str(name):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return CHIP_PALETTE[h % len(CHIP_PALETTE)]

# Per-series accent colours — one gradient per book, echoed on series cards,
# sermon pages and their focus maps for instant wayfinding.
SERIES_ACCENTS = {
    "romans":      ("var(--ruby)", "var(--amber)"),
    "galatians":   ("var(--violet-l)", "var(--teal)"),
    "colossians":  ("var(--teal)", "var(--moss)"),
    "ephesians":   ("var(--violet)", "var(--violet-l)"),
    "1 peter":     ("var(--moss)", "var(--candle)"),
    "psalm":       ("var(--amber)", "var(--candle)"),
    "acts":        ("var(--ruby-l)", "var(--violet)"),
    "exodus":      ("var(--amber)", "var(--ruby)"),
    "nehemiah":    ("var(--moss)", "var(--amber)"),
}
def series_accent_for_slug(slug):
    """Pick an accent pair from the series slug (e.g. '1-peter-series')."""
    key = slug.replace("-series", "").replace("1-peter", "1 peter")
    return SERIES_ACCENTS.get(key, ("var(--ruby)", "var(--amber)"))

# Scripture reference pattern — wrap refs in small-caps amber chips.
_REF_RE = re.compile(r"\b((?:[1-3]\s?)?(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalm|Psalms|Proverbs|Ecclesiastes|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation)\.?\s\d+(?::\d+(?:[–\-—]\d+)?)?(?:,\s*\d+(?::\d+)*)*)")
def style_scripture_refs(html_fragment):
    # Only touch text outside tags; skip anything already inside an <a>.
    parts = re.split(r"(<[^>]+>)", html_fragment)
    out = []
    in_a = 0
    for part in parts:
        if part.startswith("<"):
            low = part.lower()
            if low.startswith("<a"): in_a += 1
            elif low.startswith("</a"): in_a = max(0, in_a - 1)
            out.append(part)
            continue
        if not in_a:
            part = _REF_RE.sub(lambda m: f'<span class="scripture">{m.group(1)}</span>', part)
        out.append(part)
    return "".join(out)

# Australian English for rendered content (house rule) — applied to visible text only.
_AU_WORDS = [
    (r"\brecognizable\b", "recognisable"), (r"\bRecognizable\b", "Recognisable"),
    (r"\brecognize\b", "recognise"), (r"\bRecognize\b", "Recognise"),
    (r"\brecognized\b", "recognised"), (r"\brecognized\b", "recognised"),
    (r"\borganize\b", "organise"), (r"\borganized\b", "organised"),
    (r"\borganization\b", "organisation"), (r"\bOrganization\b", "Organisation"),
    (r"\bcenter\b", "centre"), (r"\bCenter\b", "Centre"), (r"\bcenters\b", "centres"),
    (r"\bcolor\b", "colour"), (r"\bColor\b", "Colour"), (r"\bcolors\b", "colours"),
    (r"\bhonor\b", "honour"), (r"\bhonor\b", "honour"),
    (r"\bbehavior\b", "behaviour"), (r"\bBehavior\b", "Behaviour"),
    (r"\bfavor\b", "favour"), (r"\bneighbor\b", "neighbour"),
    (r"\blabor\b", "labour"), (r"\btraveled\b", "travelled"),
    (r"\bfulfill\b", "fulfil"), (r"\bskillful\b", "skilful"),
    (r"\bcanceling\b", "cancelling"), (r"\bmodeling\b", "modelling"),
]
_AU_RES = [(re.compile(p), r) for p, r in _AU_WORDS]
def au_english(html_fragment):
    parts = re.split(r"(<[^>]+>)", html_fragment)
    out = []
    for part in parts:
        if part.startswith("<"):
            out.append(part)
            continue
        for rx, rep in _AU_RES:
            part = rx.sub(rep, part)
        out.append(part)
    return "".join(out)

# ---------------------------------------------------------------- transcript layout
TRANSCRIPT_CSS = """
.transcript{margin-top:22px}
.watch,.transcript .watch{display:inline-flex;align-items:center;gap:8px;margin:4px 0 26px;font-size:13px;font-weight:600;color:var(--candle);text-decoration:none;border:1px solid var(--border);border-radius:999px;padding:7px 16px}
.watch:hover,.transcript .watch:hover{border-color:var(--candle)}
.transcript .tlinks{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:4px 0 26px}
.transcript .tlinks .watch{margin:0}
.transcript .read{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--teal);text-decoration:none;border:1px solid var(--border);border-radius:999px;padding:7px 16px}
.transcript .read:hover{border-color:var(--teal);color:var(--text)}
[data-theme="light"] .transcript .read{color:#1F6B63}
.transcript .pane{position:relative;margin:0 0 30px;padding:6px;background:linear-gradient(150deg,var(--surface) 0%,var(--surface2) 100%);border:1px solid var(--border-l);border-radius:18px;box-shadow:0 0 0 1px rgba(200,155,60,.08),inset 0 0 34px rgba(200,155,60,.05)}
.transcript .pane::before{content:"";position:absolute;inset:9px;border:1px solid rgba(200,155,60,.28);border-radius:13px;pointer-events:none}
.transcript .pane-inner{position:relative;padding:30px 38px 26px}
.transcript .pane .stamp{display:flex;align-items:center;gap:12px;margin-bottom:16px;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--amber);font-weight:600}
.transcript .pane .stamp .t{font-variant-numeric:tabular-nums;color:var(--candle)}
.transcript .pane .stamp .rule{flex:1;height:1px;background:linear-gradient(90deg,rgba(200,155,60,.4),transparent)}
.transcript .pane .stamp .cross{color:var(--ruby-l);font-size:14px;line-height:1}
.transcript .sermon{font-family:'Cormorant Garamond',serif;font-size:20px;line-height:1.85;color:var(--text);font-weight:500}
.transcript .sermon .drop::first-letter{float:left;font-size:58px;line-height:.8;padding:5px 12px 0 0;color:var(--candle);font-weight:700}
.transcript .sermon p{margin-bottom:14px}
.transcript .sermon p:last-child{margin-bottom:0}
.transcript .note{margin:-4px 0 36px}
.transcript .note-inner{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--violet-l);border-radius:12px;padding:16px 20px}
.transcript .note .tag{display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--violet-l);font-weight:600;margin-bottom:8px}
.transcript .note p{font-size:14px;color:var(--text-muted);line-height:1.6}
.transcript .note p+p{margin-top:8px}
.transcript .study{margin-top:46px}
.transcript .study .head{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.transcript .study .head h2{font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:700;margin:0;color:var(--text)}
.transcript .study .head .bar{width:28px;height:3px;background:linear-gradient(90deg,var(--teal),var(--amber));border-radius:2px}
.transcript .study .lede{color:var(--text-dim);font-size:13px;margin-bottom:18px}
.transcript .qlist{display:flex;flex-direction:column;gap:12px}
.transcript .q{display:flex;gap:14px;align-items:flex-start;background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--teal);border-radius:12px;padding:15px 18px}
.transcript .q .num{font-family:'Cormorant Garamond',serif;font-size:22px;font-weight:700;color:var(--teal);line-height:1;min-width:24px}
.transcript .q p{font-size:14px;color:var(--text-muted);line-height:1.6;margin:0}
.transcript .related{margin-top:-16px}
.transcript .rl{display:flex;flex-wrap:wrap;gap:8px}
.transcript .rl a{font-size:13.5px;font-weight:600;color:var(--candle);text-decoration:none;border:1px solid var(--border);background:var(--surface);border-radius:999px;padding:5px 13px;display:inline-block}
.transcript .rl a:hover{border-color:var(--candle)}
"""
CSS = CSS + TRANSCRIPT_CSS

def transcript_to_html(body, meta):
    """Render a `layout: transcript` body: sacred panes + delta commentary + study questions."""
    panes = []          # [{t, title, paras, notes}]
    questions = []
    related = []
    in_questions = False
    in_rel = False
    cur = None
    started = False
    for line in body.split("\n"):
        st = line.strip()
        if not started:
            if st == "" or st.startswith("# "):
                continue
            started = True
        if st.startswith("## "):
            head_text = st[3:].strip()
            low = head_text.lower()
            if low.startswith("study questions"):
                in_questions = True; in_rel = False; cur = None; continue
            if low.startswith("related"):
                in_rel = True; in_questions = False; cur = None; continue
            m = re.match(r'^(\d{1,2}:\d{2})\s*[—–-]\s*(.*)$', head_text)
            if m:
                panes.append({"t": m.group(1), "title": m.group(2).strip(), "paras": [], "notes": []})
                cur = panes[-1]; in_questions = False; in_rel = False
            continue
        if in_rel:
            if st:
                related.append(st)
            continue
        if in_questions:
            m = re.match(r'^\s*\d+\.\s+(.*)$', st)
            if m:
                questions.append(m.group(1).strip())
            continue
        if cur is None:
            continue
        if st.startswith(">"):
            cur["notes"].append(st[1:].strip())
        elif st:
            cur["paras"].append(st)

    out = ['<div class="transcript">']
    vid = scalar(meta.get("video_id")); ts = scalar(meta.get("video_timestamp"))
    links = []
    if vid:
        label = ts
        try:
            sec = int(ts); label = f"{sec//60}:{sec%60:02d}"
        except Exception:
            pass
        frag = f"&t={ts}s" if ts else ""
        links.append(f'<a class="watch" href="https://www.youtube.com/watch?v={vid}{frag}">▶ Watch from the sermon · {label}</a>')
    psg = study_readings(meta)
    if psg:
        links.append(f'<a class="read" href="{bible_gateway_url(psg)}" target="_blank" rel="noopener">📖 Read {escape_html(psg)} in the ESV →</a>')
    if links:
        out.append('<div class="tlinks">' + "".join(links) + '</div>')

    for p in panes:
        out.append('<section class="pane"><div class="pane-inner">')
        out.append(f'<div class="stamp"><span class="cross">†</span><span>{escape_html(p["title"])}</span><span class="rule"></span><span class="t">{p["t"]}</span></div>')
        out.append('<div class="sermon">')
        for i, para in enumerate(p["paras"]):
            cls = ' class="drop"' if i == 0 else ''
            out.append(f'<p{cls}>{au_english(escape_html(para))}</p>')
        out.append('</div></div></section>')
        if p["notes"]:
            out.append('<div class="note"><div class="note-inner"><div class="tag">✎ Commentary</div>')
            for n in p["notes"]:
                out.append(au_english(md_to_html(n)))
            out.append('</div></div>')

    if questions:
        out.append('<section class="study"><div class="head"><span class="bar"></span><h2>Study Questions</h2></div>')
        out.append('<p class="lede">Drawn from the companion notes — for small groups and personal reflection.</p><div class="qlist">')
        for i, q in enumerate(questions, 1):
            out.append(f'<div class="q"><span class="num">{i}</span>{au_english(md_to_html(q))}</div>')
        out.append('</div></section>')

    if related:
        out.append('<section class="study related"><div class="head"><span class="bar"></span><h2>Related</h2></div><div class="rl">')
        for r in related:
            # strip a leading "- " bullet; content is already resolved wikilinks
            r = re.sub(r'^-\s*', '', r)
            out.append(f'{md_to_html(r)}&nbsp; ')
        out.append('</div></section>')

    out.append('</div>')
    return "".join(out)

# ---------------------------------------------------------------- build
def main():
    # Regenerate the satellite map + overlay first (graceful if offline: keep
    # the previous map-block.html / satellite.webp, still build the site).
    import subprocess
    try:
        subprocess.run([sys.executable, os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "scripts", "build_map.py")],
            check=True, timeout=240)
    except Exception as e:
        print(f"[church-build] ⚠ satellite map skipped ({e}); using previous block if present")

    global GATE_PW
    if _gate is None:
        # Refuse to build rather than write the notes to disk in the clear.
        print(f"[church-build] ✗ password-gate module unavailable ({_GATE_IMPORT_ERROR}).")
        print("[church-build]   Refusing to build — pages would be written UNENCRYPTED.")
        return 1
    os.makedirs(OUT, exist_ok=True)
    _gate.write_assets(OUT)
    GATE_PW = _gate.passphrase()
    if GATE_PW is None:
        print("[church-build] ⚠ NO PASSWORD SET — pages will be locked with NO payload.")
        print("[church-build]   Set one with scripts/set-gate-password.py, then rebuild.")
    pages = []
    for root, dirs, files in os.walk(WIKI):
        dirs[:] = [d for d in dirs if d not in (".obsidian",)]
        for f in files:
            if not f.endswith(".md") or f in ("index.md","SCHEMA.md","log.md"): continue
            src = os.path.join(root, f); rel = os.path.relpath(src, WIKI)
            text = open(src, encoding="utf-8").read()
            meta, body = parse_frontmatter(text)
            slug = slugify(os.path.splitext(f)[0])
            out = os.path.join(OUT, slug + ".html")
            pages.append({"slug":slug,"rel":rel,"meta":meta,"body":body,"out":out,
                          "type":meta.get("type") or "page",
                          "out_rel":os.path.relpath(out,OUT)})
    slug_map = {p["slug"]: p["out_rel"] for p in pages}
    for p in pages:
        slug_map[p["rel"].replace(".md","")] = p["out_rel"]

    # render detail pages
    for p in pages:
        is_transcript = scalar(p["meta"].get("layout")) == "transcript"
        body = resolve_wikilinks(p["body"], slug_map, p["out_rel"])
        if is_transcript:
            html_body = transcript_to_html(body, p["meta"])
        else:
            html_body = md_to_html(body)
            html_body = style_scripture_refs(html_body)
            html_body = au_english(html_body)
        title = page_title(p)
        tags = p["meta"].get("tags") or []
        tag_html = "".join(f'<span class="tag">#{t}</span>' for t in tags)
        ml = []
        for key, label in (("preacher","Preacher"),("date","Date"),
                           ("passage","Passage"),("church","Church")):
            v = scalar(p["meta"].get(key))
            if v:
                if key == "church": v = church_display(v)
                if key == "passage":
                    rd = study_readings(p["meta"])
                    u = bible_gateway_url(rd)
                    v = (f'<a class="passage" href="{u}" target="_blank" rel="noopener" '
                         f'title="Open these readings on Bible Gateway (ESV)">{escape_html(rd)}</a>')
                ml.append(f'{label}: <strong>{v}</strong>')
        meta_html = (f'<div class="meta-line">' + " &nbsp;·&nbsp; ".join(ml) + "</div>") if ml else ""
        # breadcrumb target + label
        if p["rel"].startswith("raw/sermons/") or p["type"] == "sermon":
            crumb_url, crumb = "sermons/index.html", "Sermon"
        elif p["rel"].startswith("sermons/"):
            crumb_url, crumb = "index.html#series", "Series"
        else:
            cmap = {"concept":("index.html#concepts","Concepts"),
                    "entity":("index.html#people","People"),
                    "passage":("index.html#books","Passages")}
            crumb_url, crumb = cmap.get(p["type"], ("", "Home"))
        # Per-book geography map for sermon / passage pages (skipped on transcript layout)
        map_html = ""
        if not is_transcript and _bmap is not None:
            try:
                _book = _bmap.detect_book(scalar(p["meta"].get("passage")) or title)
                if _book and _book in _bmap.BOOKS:
                    map_html = _bmap.sermon_map_block(_book)
            except Exception as _e:
                map_html = ""
        # Per-series accent: tint the map section header + meta line to the book colour
        if map_html and _bmap is not None:
            try:
                _bk = _bmap.detect_book(scalar(p["meta"].get("passage")) or title)
                _c1, _c2 = SERIES_ACCENTS.get(_bk, (None, None))
                if _c1:
                    map_html = map_html.replace('class="mapsection map-focus"',
                        f'class="mapsection map-focus" style="--sc-a:{_c1};--sc-b:{_c2}"', 1)
            except Exception:
                pass
        # Watch button on plain (non-transcript) sermon notes that carry a video_id
        watch_html = ""
        if not is_transcript:
            _vid = scalar(p["meta"].get("video_id"))
            if _vid:
                _ts = scalar(p["meta"].get("video_timestamp"))
                _frag = f"&t={_ts}s" if _ts else ""
                _lab = _ts
                try:
                    _sec = int(_ts); _lab = f"{_sec//60}:{_sec%60:02d}"
                except Exception:
                    pass
                if _ts:
                    _lbl = f"▶ Watch from the sermon · {_lab}"
                else:
                    _lbl = "▶ Watch the service"
                watch_html = f'<div class="tlinks"><a class="watch" href="https://www.youtube.com/watch?v={_vid}{_frag}">{_lbl}</a></div>'

        h = head(title)
        h += f'<main class="wrap"><div class="crumbs"><a href="index.html">Home</a> / '
        if crumb_url:
            h += f'<a href="{crumb_url}">{crumb}</a>'
        else:
            h += crumb
        h += '</div><div class="pg-nav">'
        h += '<a href="sermons/index.html">← All sermons</a>&nbsp;·&nbsp;' if crumb == "Sermon" else ''
        h += f'<a href="index.html">← Home</a>'
        h += '</div><div class="wiki-body">'
        h += f'<h1>{title}</h1>{meta_html}{watch_html}{map_html}{html_body}{tag_html}</div></main>' + foot()
        emit(p["out"], h, title)

    build_sermons_index(pages)   # dedicated sermons index page (grouped by book)

    # ------------------------- RICH HOMEPAGE -------------------------
    concepts  = [p for p in pages if p["rel"].startswith("concepts/")]
    entities  = [p for p in pages if p["rel"].startswith("entities/")]
    people_p  = [p for p in entities if p["rel"].startswith("entities/people/")]
    churches  = [p for p in entities if p["rel"].startswith("entities/churches/")]
    series_p  = [p for p in pages if p["rel"].startswith("sermons/") and ("series" in (p["meta"].get("tags") or []))]
    raw       = [p for p in pages if p["rel"].startswith("raw/sermons/")]
    passages  = [p for p in pages if p["rel"].startswith("passages/")]

    def sdate(p): return p["meta"].get("date","") or ""
    raw_sorted = sorted(raw, key=sdate, reverse=True)

    # series with sermon counts from their body
    for s in series_p:
        s["_count"] = len(re.findall(r"^###\s+\d+\.", s["body"], re.M))

    # by-the-book aggregation from raw sermon passages
    book_map = {}
    for p in raw:
        psg = scalar(p["meta"].get("passage")).strip()
        if psg:
            book = re.split(r"\s+\d+", psg)[0].strip()
            book_map.setdefault(book, []).append(p)
    for p in passages:  # dedicated passage pages count as their book too
        book_map.setdefault(page_title(p).split("—")[0].strip(), [])

    # ---- hero
    def stat(n, lbl):
        # singularise the label for counts of one ('1 passage', not '1 passages')
        if n == 1 and lbl.endswith("s") and not lbl.endswith("ss"):
            lbl = lbl[:-1]
        return f'<div class="hstat"><b>{n}</b><span>{lbl}</span></div>'
    stats = "".join([
        stat(len(series_p),"series"), stat(len(raw),"sermons"),
        stat(len(concepts),"concepts"), stat(len(people_p),"people"),
        stat(len(passages),"passages")])

    # ---- study of the season = biggest series
    study = max(series_p, key=lambda s: s["_count"]) if series_p else None
    study_html = ""
    side_html = ""
    if study:
        ov = re.search(r"## Overview\s*$", study["body"], re.M)
        lede = first_sentence(study["body"].split("## Overview")[1] if "## Overview" in study["body"] else study["body"])
        tags = (study["meta"].get("tags") or [])[:3]
        tgs = "".join(f'<span class="tag">{t}</span>' for t in tags)
        study_html = f"""<div class="featured">
          <div class="main">
            <div class="k">Study of the Season</div>
            <h3>{page_title(study)} — top series by sermons</h3>
            <p class="lede">{lede}</p>
            <div class="meta">{tgs}<span class="tag">{study['_count']} sermons</span></div>
            <a class="cta" href="{study['out_rel']}">Explore the series →</a>
          </div>
          <div class="sidestack">
            <div class="sub"><div class="k">Newest sermon</div><h4>{page_title(raw_sorted[0]) if raw_sorted else '—'}</h4><p>{scalar(raw_sorted[0]['meta'].get('passage','')) if raw_sorted else ''} · {scalar(raw_sorted[0]['meta'].get('date','')) if raw_sorted else ''}</p></div>
            <div class="sub"><div class="k">Concept of note</div><h4>{page_title(concepts[0]) if concepts else '—'}</h4><p>{first_sentence(concepts[0]['body']) if concepts else ''}</p></div>
          </div>
        </div>"""

    # ---- browse cards
    # ---- browse cards (churches card points at the actual churches pages)
    browse_cards = [
        ("Sermon Series","🕊️","var(--ruby)","var(--violet)",len(series_p),"Verse-by-verse walks through whole books.",'#series'),
        ("Sermons","📖","var(--amber)","var(--candle)",len(raw),"Individual talks from across the corpus.","sermons/index.html"),
        ("Theological Concepts","💡","var(--violet)","var(--teal)",len(concepts),"Doctrine and themes traced across the sermons.",'#concepts'),
        ("People","👤","var(--moss)","var(--teal)",len(people_p),"Pastors and speakers behind the notes.",'#people'),
        ("Churches","⛪","var(--teal)","var(--violet)",len(churches),"The congregations the notes come from.",(churches[0]["out_rel"] if churches else '#people')),
        ("By the Book","🗂️","var(--candle)","var(--ruby)",len(book_map),"Index everything through a single book.",'#books'),
    ]
    browse = "".join(
        f'<a class="cat" href="{a}" style="--cc-a:{ca};--cc-b:{cb}"><div class="ic">{ic}</div><h3>{t}</h3><p>{d}</p><div class="num"><b>{n}</b></div></a>'
        for t,ic,ca,cb,n,d,a in browse_cards)

    # ---- series
    srs = ""
    for s in series_p:  # include the "next" tile blank instead of count overflow
        sc1, sc2 = series_accent_for_slug(s["slug"])
        srs += (f'<a class="srs" href="{s["out_rel"]}" style="--sc-a:{sc1};--sc-b:{sc2}">'
                f'<div class="book">{book_label(s["slug"].replace("-series",""))}</div><div class="bar"></div>'
                f'<h4>{page_title(s)}</h4><p>{au_english(first_sentence(s["body"]))}</p>'
                f'<div class="n"><b>{s["_count"]}</b> sermons</div></a>')
    # fill to 4 tiles
    while series_p and len(series_p) < 4:
        srs += '<div class="srs" style="border-style:dashed;justify-content:center;align-items:center;color:var(--text-dim);font-size:12.5px">More series as they&#39;re preached</div>'
        break

    # ---- concepts (stable colour per concept — hashed from the name)
    chips = ""
    for c in concepts:
        cc = concept_color(page_title(c))
        chips += f'<a class="chip" href="{c["out_rel"]}" style="--cc:{cc}"><i></i><b>{page_title(c)}</b></a>'

    # ---- people
    av_colors = [("var(--ruby)","var(--violet)"),("var(--amber)","var(--candle)"),
                 ("var(--teal)","var(--moss)"),("var(--violet)","var(--ruby)"),
                 ("var(--moss)","var(--teal)"),("var(--candle)","var(--ruby)")]
    ppl = ""
    for i, q in enumerate(people_p[:6]):
        c1,c2 = av_colors[i % len(av_colors)]
        church = church_display(q["meta"].get("church",""))
        bio = role_line(q["body"]) or first_sentence(q["body"])
        ppl += (f'<div class="person"><div class="avatar" style="background:linear-gradient(135deg,{c1},{c2})">{initials(page_title(q))}</div>'
                f'<div><h4>{page_title(q)}</h4><div class="role">{(q["meta"].get("tags") or [""])[0].replace("-"," ")}</div>'
                f'<p>{bio}</p><div class="church"><b>{church}</b></div></div></div>')
    if churches:
        ctxt = " &amp; ".join(page_title(c) for c in churches[:2])
        clink = churches[0]["out_rel"]
        ppl += f'<a class="person" href="{clink}" style="text-decoration:none;align-items:center;justify-content:center;color:var(--text-muted);border:1px dashed var(--border-l)"><span>⛪ {ctxt}</span></a>'

    # ---- recent sermons
    rows = ""
    for p in raw_sorted[:6]:
        d = scalar(p["meta"].get("date",""))
        dy, mo = "", ""
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
        if m:
            y,mm,dd = m.groups()
            mo = datetime.date(int(y),int(mm),int(dd)).strftime("%b")
            dy = str(int(dd))
        elif "/" in d:
            parts = d.split("/")
            if len(parts)==3: mo,dy = parts[1][:3], str(int(parts[0]))
        else:
            mo,dy = d, ""
        ref = scalar(p["meta"].get("passage",""))
        preacher = scalar(p["meta"].get("preacher",""))
        y = d[:4]
        has_map = bool(_bmap.detect_book(ref or page_title(p))) if _bmap else False
        flag = '<span class="mapflag">🗺️</span>' if has_map else ""
        rows += (f'<a class="srow" href="{p["out_rel"]}"><div class="d"><b>{dy}</b><span>{mo}</span></div>'
                 f'<div class="t"><div class="meta">{preacher}{" · "+y if y else ""}</div><h4>{page_title(p)}{flag}</h4>'
                 f'<p>{au_english(first_sentence(p["body"]))}</p></div><span class="ref">{ref}</span><span class="go">→</span></a>')

    # ---- by the book
    # Map book name -> a real destination: matching series page, else sermons index.
    series_by_book = {}
    for s in series_p:
        series_by_book[book_label(s["slug"].replace("-series","")).lower()] = s["out_rel"]
    books_html = ""
    for bk, items in sorted(book_map.items(), key=lambda kv:-len(kv[1])):
        detail = f"{len(items)} sermon" + ("s" if len(items)!=1 else "") if items else "study"
        href = series_by_book.get(bk.lower(), "sermons/index.html")
        books_html += f'<a class="bk" href="{href}"><div class="b">{bk}</div><span>{detail}</span></a>'

    index = head("Home")
    index += f"""<section class="hero"><div class="wrap">
        <span class="season"><i></i>Season after Trinity &nbsp;·&nbsp; green</span>
        <div class="verse"><span class="qmark">“</span>I beseech you therefore, brethren, by the mercies of God, that ye present your bodies a living sacrifice, holy, acceptable unto God, which is your reasonable service.<span class="qmark">”</span><br><span class="ref">— Romans 12:1</span></div>
        <div class="verse-sub">The Romans series</div>
        <p class="tagline">Sermon notes, Bible study and theology gathered from St James Turramurra &amp; Port Macquarie Baptist — a quiet wiki for reflection and teaching.</p>
        <div class="hero-stats">{stats}</div>
        <span class="privbar">🔒 Private — password protected</span>
      </div></section>"""
    index += "<main class='wrap'>"
    ORN = '<div class="ornament" aria-hidden="true"><span class="seg s1"></span><span class="seg s2"></span><span class="seg s3"></span><span class="seg s4"></span><span class="seg s5"></span></div>'
    # Bible Lands historical map — injected verbatim (self-contained SVG+JS)
    if os.path.exists(MAP_HTML):
        index += open(MAP_HTML, encoding="utf-8").read()
    if study_html: index += f'<div class="section">{study_html}</div>'
    index += f'<div class="section"><div class="sec-head"><div class="left"><span class="bar"></span><h2>Browse the notes</h2></div></div><div class="browse">{browse}</div></div>'
    if srs:
        index += f'{ORN}<div class="section" id="series"><div class="sec-head"><div class="left"><span class="bar"></span><h2>Sermon series</h2></div><a class="more" href="#books">Browse by book →</a></div><div class="series">{srs}</div></div>'
    if chips:
        index += f'{ORN}<div class="section" id="concepts"><div class="sec-head"><div class="left"><span class="bar"></span><h2>Theological concepts</h2></div><a class="more" href="index.html">All →</a></div><div class="concept-chips">{chips}</div></div>'
    if ppl:
        index += f'{ORN}<div class="section" id="people"><div class="sec-head"><div class="left"><span class="bar"></span><h2>People &amp; places</h2></div></div><div class="people">{ppl}</div></div>'
    if rows:
        index += f'{ORN}<div class="section" id="sermons"><div class="sec-head"><div class="left"><span class="bar"></span><h2>Recent sermons</h2></div><a class="more" href="sermons/index.html">All sermons →</a></div><div class="sermon-list">{rows}</div></div>'
    if books_html:
        index += f'{ORN}<div class="section" id="books"><div class="sec-head"><div class="left"><span class="bar"></span><h2>By the book</h2></div><a class="more" href="sermons/index.html">Browse by book →</a></div><div class="books">{books_html}</div></div>'
    index += "</main>" + foot()
    emit(os.path.join(OUT, "index.html"), index, "Home")

    open(os.path.join(OUT,"robots.txt"),"w",encoding="utf-8").write("User-agent: *\nDisallow: /\n")
    # Custom domain + Pages plumbing. The passphrase is NOT here: every page is ciphertext.
    open(os.path.join(OUT,"CNAME"),"w",encoding="utf-8").write("church.peterjaycox.com\n")
    open(os.path.join(OUT,".nojekyll"),"w",encoding="utf-8").write("")
    state = "encrypted" if GATE_PW else "LOCKED (no password set)"
    print(f"[church-build] Wrote {len(pages)} pages + rich index + robots.txt -> {OUT}  [{state}]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
