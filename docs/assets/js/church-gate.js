/* Church Notes — build-time password gate.
 *
 * The page body is PBKDF2(SHA-256) -> AES-GCM encrypted at build time, so the notes are
 * unreadable without the passphrase *even from view-source*. An obfuscated (base64) gate
 * would leave the content exposed in the source and at raw.githubusercontent.com.
 *
 * Honest limits: there is no server, so the ciphertext is public and a weak passphrase is
 * brute-forceable offline. This deters casual readers, link-sharers and crawlers; it is
 * not confidentiality against someone who wants in. One shared password: no per-user
 * identity, no revocation.
 *
 * The unlocked passphrase is cached in sessionStorage for the tab's lifetime, so moving
 * between gated pages does not re-prompt. It is cleared when the tab closes.
 */
(function () {
  var node = document.getElementById('cn-payload');
  if (!node) { return; }

  var payload;
  try { payload = JSON.parse(node.textContent); } catch (e) { return; }

  var input = document.getElementById('cn-pass');
  var form  = document.getElementById('cn-form');
  var err   = document.getElementById('cn-err');
  var out   = document.getElementById('cn-root');
  var lock  = document.getElementById('cn-lock');
  var STORE = 'cn-key';

  function b64(s) {
    var raw = atob(s), a = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) { a[i] = raw.charCodeAt(i); }
    return a;
  }
  function say(m) { if (err) { err.textContent = m; err.style.display = 'block'; } }
  function clearSay() { if (err) { err.textContent = ''; err.style.display = 'none'; } }
  function store(v) { try { sessionStorage.setItem(STORE, v); } catch (e) {} }
  function unstore() { try { sessionStorage.removeItem(STORE); } catch (e) {} }
  function cached() { try { return sessionStorage.getItem(STORE); } catch (e) { return null; } }

  /* Decrypted markup goes in via innerHTML, so <script> inside it does NOT execute. The
     fragment is our own build output, never user input, and it carries its own interactive
     JS (the Bible-lands map, the sermons search filter, the theme toggle), so the script
     nodes are re-created here to make them run. Only ever applied to our own ciphertext. */
  function activate(root) {
    var scripts = root.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
      var old = scripts[i], live = document.createElement('script');
      for (var j = 0; j < old.attributes.length; j++) {
        live.setAttribute(old.attributes[j].name, old.attributes[j].value);
      }
      if (old.src) { live.src = old.src; } else { live.textContent = old.textContent; }
      old.parentNode.replaceChild(live, old);
    }
  }

  function reveal(plain) {
    out.innerHTML = new TextDecoder().decode(plain);
    /* Unhide BEFORE the scripts run. Anything in the fragment that measures layout on
       init (the Bible-lands map reads clientWidth/clientHeight) sees 0x0 while the
       container is display:none, and then renders nothing — the page looks fine but the
       map is blank until something forces a re-measure. Order matters here. */
    out.hidden = false;
    if (lock) { lock.style.display = 'none'; }
    activate(out);
    /* Belt and braces for anything that initialises on load/resize instead: it missed
       both events (the document is already loaded). Re-measure on the next frame. */
    requestAnimationFrame(function () { window.dispatchEvent(new Event('resize')); });
    document.title = (payload.title ? payload.title + ' \u00b7 ' : '') + 'Church Notes';
  }

  function attempt(pw, silent) {
    if (!(window.crypto && window.crypto.subtle)) {
      say('Decryption needs a secure address. On a local alias such as '
        + 'church.peterjaycox.com:' + (location.port || '8042') + ', open '
        + 'http://localhost:' + (location.port || '8042') + ' or http://127.0.0.1:'
        + (location.port || '8042') + ' instead \u2014 browsers only allow this on https, '
        + 'localhost and 127.0.0.1. On a published site this means it is not being served over https.');
      return;
    }
    clearSay();
    var enc = new TextEncoder();
    crypto.subtle.importKey('raw', enc.encode(pw), { name: 'PBKDF2' }, false, ['deriveKey'])
      .then(function (base) {
        return crypto.subtle.deriveKey(
          { name: 'PBKDF2', salt: b64(payload.kdf.salt),
            iterations: payload.kdf.iterations, hash: 'SHA-256' },
          base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
      })
      .then(function (key) {
        return crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(payload.iv) }, key, b64(payload.ct));
      })
      .then(function (plain) { store(pw); reveal(plain); })
      .catch(function () {
        unstore();                       // a cached value that no longer decrypts is stale
        if (silent) { if (input) { input.focus(); } } else { say('Incorrect password.'); }
      });
  }

  if (!payload.ct) {
    /* Fail-closed build: no passphrase was configured, so no ciphertext was shipped.
       Nothing here can ever be unlocked — say so plainly instead of offering a dead form. */
    say('This page is locked, and no site password has been configured yet.');
    if (form) { form.style.display = 'none'; }
    return;
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var pw = input ? input.value : '';
      if (!pw) { say('Enter the password.'); return; }
      attempt(pw, false);
    });
  }

  var saved = cached();
  if (saved) { attempt(saved, true); }
  else if (input) { input.focus(); }
})();
