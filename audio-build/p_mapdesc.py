# -*- coding: utf-8 -*-
u"""Three requests from looking at the map and the ladder.

1. A passed level and a flawless one were the same green. Passed-but-not-perfect
   is a paler green now; a green star keeps the full green (and the star).

2. The prefecture tiles floated on plain blue. They now sit on a soft island
   shape - not an accurate map, but built FROM the tiles themselves: a blurred
   blob under each one, merged into one landmass, so it always matches wherever
   the tiles are and scales with them (it is an SVG, so resizing is free).

3. The photo panel showed five pictures and no words. A short description of the
   place - from Wikipedia, in English - now sits under them.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
MIRROR = r"C:\JapaneseLearning\index.html"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- 1. paler green for passed, full green for perfect --------------
    rep(".rung.learned { color: var(--wakakusa); border-color: var(--wakakusa); background: var(--wakakusa-wash); }",
        """/* Passed, but not flawless: a paler green than a green-star level. */
.rung.learned {
  color: #6aa15a; border-color: #c2ddb3; background: #eef6e6;
  color: color-mix(in srgb, var(--wakakusa) 58%, var(--ink-faint));
  border-color: color-mix(in srgb, var(--wakakusa) 42%, var(--rule));
  background: color-mix(in srgb, var(--wakakusa-wash) 45%, var(--paper));
}""", "pale learned")

    rep(".rung.perfect { position: relative; border-color: var(--wakakusa); }",
        """.rung.perfect { position: relative;
  color: var(--wakakusa); border-color: var(--wakakusa); background: var(--wakakusa-wash); }""",
        "full green perfect")

    # ---- 2. the island silhouette under the tiles ----------------------
    rep(""".japan {
  display: grid; grid-template-columns: repeat(13, 66px); grid-auto-rows: 66px; gap: 7px;
  padding: 22px; width: max-content;
}""",
        """.japan {
  position: relative;
  display: grid; grid-template-columns: repeat(13, 66px); grid-auto-rows: 66px; gap: 7px;
  padding: 22px; width: max-content;
}
/* Built from the tiles, so it always underlays them and scales with them. */
.japan-bg { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; }
.japan-land  { fill: rgba(150, 190, 120, .5); }
.japan-coast { fill: rgba(228, 216, 176, .45); }
.japan > .ptile, .japan > .sea-deco { position: relative; z-index: 1; }""", "japan-bg css")

    # the generator, placed next to mapHTML
    rep("function mapHTML(p) {",
        """/* A soft island under the prefecture tiles. Not a real map: a blurred circle
   at each tile's own grid position, all merged by a gooey filter into one
   continuous landmass. Because it is drawn from the tile positions it always
   sits under them, and because it is an SVG stretched to the grid box it costs
   nothing to resize. */
function japanBg() {
  const W = 986, H = 1132;                     // the grid's own pixel box
  const cx = function (c) { return 55 + c * 73; };
  const cy = function (r) { return 55 + r * 73; };
  const dots = PREFS.map(function (r) {
    return '<circle cx="' + cx(r.col) + '" cy="' + cy(r.row) + '" r="55"/>';
  }).join("");
  const goo = function (id, dev, aa, bb) {
    return '<filter id="' + id + '"><feGaussianBlur in="SourceGraphic" stdDeviation="' + dev +
      '" result="b"/><feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 ' +
      aa + ' ' + bb + '"/></filter>';
  };
  return '<svg class="japan-bg" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" aria-hidden="true">' +
           '<defs>' + goo("gLand", 16, 20, -10) + goo("gCoast", 26, 16, -8) + '</defs>' +
           '<g class="japan-coast" filter="url(#gCoast)">' + dots + '</g>' +
           '<g class="japan-land" filter="url(#gLand)">' + dots + '</g>' +
         '</svg>';
}

function mapHTML(p) {""", "japanBg fn")

    rep("""'<div class="mapwrap"><div class="japan" role="group" aria-label="Map of Japan">' + tiles +""",
        """'<div class="mapwrap"><div class="japan" role="group" aria-label="Map of Japan">' + japanBg() + tiles +""",
        "inject japanBg")

    # ---- 3. a description under the five photos ------------------------
    # realpix gains a Wikipedia lookup and shows it beneath the gallery.
    rep("""  const cache = {};                 // query -> array of photos, or "none"
  let reachable = null;             // null until the first call answers""",
        """  const cache = {};                 // query -> array of photos, or "none"
  const descCache = {};             // query -> description text, or "none"
  let reachable = null;             // null until the first call answers""", "descCache")

    rep("""  function gallery(list) {""",
        """  /* A couple of sentences about the place, from Wikipedia, in English so a
     parent can read it too. The English name finds the best article; the
     Japanese name is the fallback, and Japanese Wikipedia the last resort. */
  function wiki(host, term) {
    const u = host + "/w/api.php?origin=*&format=json&action=query&generator=search&gsrlimit=1" +
      "&gsrsearch=" + encodeURIComponent(term) +
      "&prop=extracts&exintro=1&explaintext=1&exsentences=2";
    return fetch(u).then(function (r) { return r.json(); }).then(function (j) {
      const pg = (j.query && j.query.pages) ? Object.keys(j.query.pages).map(function (k) {
        return j.query.pages[k]; })[0] : null;
      return (pg && pg.extract) ? pg.extract : "";
    });
  }

  function describe(enTerm, jpTerm) {
    const key = enTerm || jpTerm || "";
    if (descCache[key]) return Promise.resolve(descCache[key] === "none" ? "" : descCache[key]);
    return wiki("https://en.wikipedia.org", enTerm || jpTerm)
      .then(function (t) { return t || (jpTerm ? wiki("https://en.wikipedia.org", jpTerm) : ""); })
      .then(function (t) { return t || (jpTerm ? wiki("https://ja.wikipedia.org", jpTerm) : ""); })
      .then(function (t) { descCache[key] = t || "none"; return t; })
      .catch(function () { return ""; });
  }

  function gallery(list) {""", "wiki+describe")

    rep("""    open: function (title, sub, query, backup) {
      draw(title, sub, '<div class="pix-note">Looking for photos…</div>');
      fetchFor(query, backup).then(function (list) {
        if (!document.getElementById("pixOverlay")) return;   // already closed
        if (!list.length) {
          draw(title, sub, '<div class="pix-note">No photos found for this one.</div>');
        } else {
          draw(title, sub, gallery(list));
        }
      }).catch(function () {""",
        """    open: function (title, sub, query, backup) {
      draw(title, sub, '<div class="pix-note">Looking for photos…</div>');
      // The description rides in behind the photos, whenever it lands.
      describe(backup, query).then(function (text) {
        const box = document.getElementById("pixDesc");
        if (box && text) box.textContent = text;
        else if (box) box.parentNode && box.remove();
      });
      fetchFor(query, backup).then(function (list) {
        if (!document.getElementById("pixOverlay")) return;   // already closed
        if (!list.length) {
          draw(title, sub, '<div class="pix-note">No photos found for this one.</div>' + descSlot());
        } else {
          draw(title, sub, gallery(list) + descSlot());
        }
      }).catch(function () {""", "open with desc")

    # the slot the description fills into, and its style
    rep("""  function gallery(list) {
    return '<div class="pix-grid">' + list.map(function (ph) {""",
        """  function descSlot() {
    return '<p class="pix-desc" id="pixDesc"></p>';
  }

  function gallery(list) {
    return '<div class="pix-grid">' + list.map(function (ph) {""", "descSlot fn")

    rep(""".pix-note { padding: 26px 8px; text-align: center; color: var(--ink-soft); }""",
        """.pix-note { padding: 26px 8px; text-align: center; color: var(--ink-soft); }
.pix-desc { margin: 4px 0 0; font-size: 13.5px; line-height: 1.5; color: var(--ink-soft); }
.pix-desc:empty { display: none; }""", "pix-desc css")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])


if __name__ == "__main__":
    main()
