# -*- coding: utf-8 -*-
"""A "Real photos" button on every prefecture and every place on the map.

The map already teaches 47 prefectures and 470 famous places by name - 金閣寺,
兼六園, 首里城 - but a child spelling 首里城 has never seen it. This puts real
photographs one tap away.

Not embedded. Five photos each for 517 places would be hundreds of megabytes;
the page is 5.6 MB and must stay a thing a phone can load. Instead the button
asks Wikimedia Commons at the moment it is tapped and shows what comes back.

Wikimedia Commons on purpose, and not a plain image search: everything on
Commons is freely licensed, and the API hands back the licence and the
photographer with each picture, so every photo can be shown WITH its credit,
which is what makes using it honest. Confirmed from the live site: the API
answers cross-origin, the images hotlink, and a search for 浅草寺 returns
"Sensoji 2023" and an Unsplash shot of the temple, not woodblock prints once
the non-photographs are filtered out.

It queries by the Japanese name, which is the most precise - 松本城 finds
Matsumoto Castle and nothing else - and falls back to the English name if the
Japanese one is thin. Results are kept in memory, so opening a place twice is
one request, not two.

Where there is no network - the Artifact build, whose CSP forbids the request,
or a plane - it says so and offers nothing broken.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
MIRROR = r"C:\JapaneseLearning\index.html"

MODULE = r'''
/* ============================================================
   16b. REAL PHOTOS
   ============================================================ */

/* Freely-licensed photographs of a place, fetched from Wikimedia Commons when
   the button is tapped - never embedded, never without a credit. See
   audio-build/p_photos.py for why Commons and why not a file. */
const realpix = (function () {
  const API = "https://commons.wikimedia.org/w/api.php";
  const WANT = 5;
  const cache = {};                 // query -> array of photos, or "none"
  let reachable = null;             // null until the first call answers

  // Non-photographs that a name search drags in: maps, seals, flags, diagrams.
  const NOTAPHOTO = /(\.svg|map of|map,|diagram|seal of|coat of arms|\bflag\b|\blogo\b|icon|floor plan|\bplan of|chart|blazon|emblem|logotype|stamp of)/i;

  function strip(html) {
    const d = document.createElement("div");
    d.innerHTML = String(html || "");
    return (d.textContent || "").replace(/\s+/g, " ").trim();
  }

  function url(term) {
    return API + "?origin=*&format=json&action=query&generator=search" +
      "&gsrnamespace=6&gsrlimit=24&gsrsearch=" + encodeURIComponent(term) +
      "&prop=imageinfo&iiprop=url|mime|size|extmetadata&iiurlwidth=640";
  }

  function usable(page) {
    const ii = (page.imageinfo || [])[0];
    if (!ii || !ii.thumburl) return null;
    if (["image/jpeg", "image/png", "image/webp"].indexOf(ii.mime) === -1) return null;
    if ((ii.width || 0) < 500) return null;
    if (NOTAPHOTO.test(page.title)) return null;
    const meta = ii.extmetadata || {};
    return {
      thumb: ii.thumburl,
      page: ii.descriptionurl || "",
      by: strip((meta.Artist && meta.Artist.value) || "").slice(0, 80) || "Wikimedia Commons",
      lic: strip((meta.LicenseShortName && meta.LicenseShortName.value) || "")
    };
  }

  function search(term) {
    return fetch(url(term)).then(function (r) {
      if (!r.ok) throw new Error("bad status");
      return r.json();
    }).then(function (j) {
      reachable = true;
      const pages = (j.query && j.query.pages) ? Object.keys(j.query.pages).map(function (k) {
        return j.query.pages[k];
      }) : [];
      pages.sort(function (a, b) { return (a.index || 0) - (b.index || 0); });
      const out = [];
      for (let i = 0; i < pages.length && out.length < WANT; i++) {
        const ph = usable(pages[i]);
        if (ph) out.push(ph);
      }
      return out;
    });
  }

  function fetchFor(query, backup) {
    if (cache[query]) return Promise.resolve(cache[query] === "none" ? [] : cache[query]);
    return search(query).then(function (list) {
      if (list.length < 2 && backup && backup !== query) {
        return search(backup).then(function (more) {
          const seen = {}, all = list.concat(more).filter(function (ph) {
            if (seen[ph.thumb]) return false; seen[ph.thumb] = 1; return true;
          }).slice(0, WANT);
          cache[query] = all.length ? all : "none";
          return all;
        });
      }
      cache[query] = list.length ? list : "none";
      return list;
    });
  }

  function close() {
    const el = document.getElementById("pixOverlay");
    if (el && el.parentNode) el.parentNode.removeChild(el);
    document.removeEventListener("keydown", onKey);
  }
  function onKey(e) { if (e.key === "Escape") close(); }

  function shell(title, sub, body) {
    return '<div class="study-panel pix-panel">' +
             '<div class="pix-head">' +
               '<div><div class="pix-title" lang="ja">' + esc(title) + '</div>' +
                 (sub ? '<div class="pix-sub">' + esc(sub) + '</div>' : '') + '</div>' +
               '<button class="btn btn-ghost btn-sm" id="pixClose">Close</button>' +
             '</div>' + body +
             '<p class="pix-credit-note">Real photographs from Wikimedia Commons, ' +
               'shown with their licence. Tap one to see it there.</p>' +
           '</div>';
  }

  function draw(title, sub, inner) {
    let wrap = document.getElementById("pixOverlay");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "study-overlay pix-overlay";
      wrap.id = "pixOverlay";
      document.body.appendChild(wrap);
      document.addEventListener("keydown", onKey);
      wrap.addEventListener("click", function (e) { if (e.target === wrap) close(); });
    }
    wrap.innerHTML = shell(title, sub, inner);
    document.getElementById("pixClose").onclick = close;
  }

  function gallery(list) {
    return '<div class="pix-grid">' + list.map(function (ph) {
      return '<a class="pix-cell" href="' + esc(ph.page) + '" target="_blank" rel="noopener noreferrer" ' +
             'title="' + esc(ph.by + (ph.lic ? " · " + ph.lic : "")) + '">' +
               '<img src="' + esc(ph.thumb) + '" alt="" loading="lazy">' +
               '<span class="pix-by">' + esc(ph.by) + (ph.lic ? ' · ' + esc(ph.lic) : '') + '</span>' +
             '</a>';
    }).join("") + '</div>';
  }

  return {
    // Whether the button should appear at all: hidden only once we know the
    // request cannot be made (the Artifact build).
    ready: function () { return reachable !== false; },

    open: function (title, sub, query, backup) {
      draw(title, sub, '<div class="pix-note">Looking for photos…</div>');
      fetchFor(query, backup).then(function (list) {
        if (!document.getElementById("pixOverlay")) return;   // already closed
        if (!list.length) {
          draw(title, sub, '<div class="pix-note">No photos found for this one.</div>');
        } else {
          draw(title, sub, gallery(list));
        }
      }).catch(function () {
        if (reachable === null) reachable = false;
        if (!document.getElementById("pixOverlay")) return;
        draw(title, sub, '<div class="pix-note">Photos need the online game — ' +
          'open it at nihongoadventure.pages.dev.</div>');
      });
    }
  };
})();

'''

CSS = '''.pix-panel { width: min(760px, 100%); gap: 12px; }
.pix-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.pix-title { font-family: var(--font-kana); font-weight: 800; font-size: 20px; }
.pix-sub { color: var(--ink-soft); font-size: 13px; margin-top: 2px; }
.pix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.pix-cell {
  position: relative; display: block; border-radius: 10px; overflow: hidden;
  background: var(--ground-deep); text-decoration: none; aspect-ratio: 4 / 3;
}
.pix-cell img { width: 100%; height: 100%; object-fit: cover; display: block; }
.pix-by {
  position: absolute; left: 0; right: 0; bottom: 0;
  font-size: 10px; line-height: 1.25; color: #fff; padding: 8px 6px 4px;
  background: linear-gradient(transparent, rgba(0,0,0,.72));
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pix-note { padding: 26px 8px; text-align: center; color: var(--ink-soft); }
.pix-credit-note { font-size: 11px; color: var(--ink-faint); text-align: center; margin: 0; }
.pix-btn {
  border: 1.5px solid var(--rule); background: var(--paper); color: var(--ink-soft);
  border-radius: 999px; padding: 3px 9px; font-size: 12px; font-weight: 700; cursor: pointer;
  white-space: nowrap;
}
.pix-btn:hover { border-color: var(--ai); color: var(--ai); }
.pref-photos { border: 1.5px solid var(--ai); color: var(--ai); background: var(--ai-wash); }
.stop-photos { margin-left: 4px; }
'''


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # the module goes just before the existing photos slideshow module
    rep("const photos = (function () {\n  const data = window.PHOTOS;",
        MODULE.strip("\n") + "\n\nconst photos = (function () {\n  const data = window.PHOTOS;",
        "realpix module")

    # ---- the prefecture gets a photos button in its header --------------
    rep("""      speakerBtn(p, r.kana, null).replace('class="say"', 'class="say big"') +
    '</div>' +""",
        """      speakerBtn(p, r.kana, null).replace('class="say"', 'class="say big"') +
      (realpix.ready()
        ? '<button class="pix-btn pref-photos" data-pref-pix="' + esc(r.kanji) + '" ' +
          'data-pref-en="' + esc(r.romaji) + '" title="See real photographs of ' + esc(r.romaji) +
          '">\\ud83d\\udcf7 Real photos</button>' : '') +
    '</div>' +""", "pref photos button")

    # ---- and every place gets a small one -------------------------------
    rep("""        '<span class="stop-sub">' + esc(sg.kana) + ' · ' + esc(sg.en) + '</span>' + pips +
      '</span>' +""",
        """        '<span class="stop-sub">' + esc(sg.kana) + ' · ' + esc(sg.en) + '</span>' + pips +
        (realpix.ready()
          ? '<button class="pix-btn stop-photos" data-pix="' + esc(sg.jp) + '" ' +
            'data-pix-en="' + esc(sg.en) + '" title="See real photographs of ' + esc(sg.en) +
            '">\\ud83d\\udcf7 Photos</button>' : '') +
      '</span>' +""", "sight photos button")

    # ---- wire both, in the same place the rest of the map is wired -------
    rep("""  const jump = host.querySelector("#mapJump");
  if (jump) jump.onclick = function () { const c = closestPref(p); if (c) { mapSel = c.id; again(); } };""",
        """  const jump = host.querySelector("#mapJump");
  if (jump) jump.onclick = function () { const c = closestPref(p); if (c) { mapSel = c.id; again(); } };
  Array.prototype.forEach.call(host.querySelectorAll("[data-pix]"), function (b) {
    b.onclick = function (e) {
      e.stopPropagation();
      const sg = SIGHT_BY_JP[b.getAttribute("data-pix")];
      realpix.open(sg ? sg.jp : b.getAttribute("data-pix"),
                   sg ? sg.kana + " · " + sg.en : b.getAttribute("data-pix-en"),
                   b.getAttribute("data-pix"), b.getAttribute("data-pix-en"));
    };
  });
  Array.prototype.forEach.call(host.querySelectorAll("[data-pref-pix]"), function (b) {
    b.onclick = function (e) {
      e.stopPropagation();
      const kanji = b.getAttribute("data-pref-pix"), en = b.getAttribute("data-pref-en");
      realpix.open(kanji, en, kanji, en);
    };
  });""", "wire photos buttons")

    # ---- css -------------------------------------------------------------
    rep(""".pref-photos { border: 1.5px solid var(--ai); color: var(--ai); background: var(--ai-wash); }""",
        """.pref-photos { border: 1.5px solid var(--ai); color: var(--ai); background: var(--ai-wash); }""",
        "css-guard") if False else None
    rep(".study-overlay {\n  position: fixed; inset: 0; z-index: 90;",
        CSS.rstrip() + "\n.study-overlay {\n  position: fixed; inset: 0; z-index: 90;", "css")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
    import os
    print("page: %.1f MB" % (os.path.getsize(GAME) / 1048576.0))


if __name__ == "__main__":
    main()
