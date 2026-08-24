# -*- coding: utf-8 -*-
"""What the admin page needs the game and the sync endpoint to record.

Two small things, both written by the game because the game is the only thing
that knows what a level or a card is worth:

  - `opens`: the last ten times a child tapped their own name. There is no such
    thing as a login here, and this is the nearest honest equivalent.
  - `stat`: a summary - topic, level, stars, mastered, money, cards, places -
    recomputed whenever a push goes out. Without it the admin page would have
    to carry a copy of COURSES, CARD_SETS and ECONOMY, and the copy would rot.
"""
import io, os, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
FUNC = r"C:\JapaneseLearning\functions\api\sync.js"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- the game records an open, and a summary ------------------------
    rep("""function newProfile(name, face, tier) {""",
        """/* A child tapping their own name is the only thing here that resembles a
   login, so it is what gets remembered - the last ten, which is enough to see
   who has been playing and who has quietly stopped. */
function noteOpen(p) {
  if (!p) return;
  const had = Array.isArray(p.opens) ? p.opens : [];
  p.opens = [Date.now()].concat(had).slice(0, 10);
}

function newProfile(name, face, tier) {""", "noteOpen")

    rep("""    b.onclick = function () { audio.prime(); state.activeId = b.getAttribute("data-open"); go("menu"); };""",
        """    b.onclick = function () {
      audio.prime();
      state.activeId = b.getAttribute("data-open");
      noteOpen(currentProfile());
      save();
      go("menu");
    };""", "record the open")

    rep("""  // What the device is not entitled to send: its own sync bookkeeping.
  function outgoing(p) {
    const copy = {};
    Object.keys(p).forEach(function (k) { if (k !== "sync") copy[k] = p[k]; });
    return copy;
  }""",
        """  /* A summary of where this child has got to, recomputed on the way out.

     It rides along because the parents' page has no business owning a second
     copy of COURSES, CARD_SETS and ECONOMY - it would drift the first time a
     topic was added, and then quietly report the wrong thing forever. Cheap:
     it is worked out once every few seconds at most, never during a round. */
  function summary(p) {
    const rows = allRows(p);
    const items = rows.reduce(function (n, r) { return n + r.keys.length; }, 0);
    const known = learnedKana(p).filter(function (k) { return box(p, k) >= MASTERED; }).length;
    return {
      topic: courseOf(p).title, level: (prog(p).level || 0) + 1, levels: ladderFor(p).length,
      stars: greenStars(p), mastered: known, items: items,
      balance: balance(p), cards: cardCount(p),
      sights: Object.keys(p.landmarks || {}).length, at: Date.now()
    };
  }

  // What the device is not entitled to send: its own sync bookkeeping.
  function outgoing(p) {
    const copy = {};
    Object.keys(p).forEach(function (k) { if (k !== "sync") copy[k] = p[k]; });
    try { copy.stat = summary(p); } catch (e) { /* never block a save over a number */ }
    return copy;
  }""", "summary")

    # `stat.at` moves every push, which would make every profile look changed;
    # the fingerprint must ignore it.
    rep("""  function mark(text) {""",
        """  function mark(text) {
    // `stat.at` ticks on every call, so fingerprinting it would push a save
    // that has not changed, every four seconds, forever.
    text = text.replace(/"at":\\d+/g, '"at":0');""", "fingerprint ignores the clock")

    # a merged profile keeps whichever list of opens is longer, and boot tidies
    rep("""  // A face is picked from a list. Anything else arrived by another route.
  if (FACES.indexOf(p.face) === -1) p.face = FACES[0];""",
        """  // A face is picked from a list. Anything else arrived by another route.
  if (FACES.indexOf(p.face) === -1) p.face = FACES[0];
  if (!Array.isArray(p.opens)) p.opens = [];
  p.opens = p.opens.filter(function (t) { return typeof t === "number" && isFinite(t) && t > 0; })
                   .sort(function (a, b) { return b - a; }).slice(0, 10);""", "opens tidy")

    io.open(GAME, "w", encoding="utf-8").write(s)

    # ---- the merge carries both ------------------------------------------
    f = io.open(FUNC, encoding="utf-8").read()

    def frep(old, new, note):
        nonlocal f
        assert f.count(old) == 1, "%s: found %d" % (note, f.count(old))
        f = f.replace(old, new, 1)

    frep("""function mergeProfile(server, client, base) {""",
         """/* The last ten opens, from either computer, newest first. Two devices see
   different halves of the same week and both halves are worth keeping. */
function mergeOpens(a, b) {
  const all = (Array.isArray(a) ? a : []).concat(Array.isArray(b) ? b : []);
  const seen = {}, out = [];
  all.map(num).filter(function (t) { return t > 0; })
     .sort(function (x, y) { return y - x; })
     .forEach(function (t) { if (!seen[t]) { seen[t] = 1; out.push(t); } });
  return out.slice(0, 10);
}

function mergeProfile(server, client, base) {""", "mergeOpens")

    frep("""    wipe: Math.max(sw, cw),
    touched: Math.max(st, ct)""",
         """    opens: mergeOpens(server.opens, client.opens),
    // Derived, not authoritative: whichever side is fresher describes itself.
    stat: newer.stat || server.stat || client.stat || null,
    wipe: Math.max(sw, cw),
    touched: Math.max(st, ct)""", "opens and stat in the merge")

    frep(""" *   name, face, course    from whichever side was touched last.""",
         """ *   name, face, course    from whichever side was touched last.
 *   opens                 the last ten, from either computer - it is what the
 *                         parents' page at /admin shows as "last played".""", "header")

    io.open(FUNC, "w", encoding="utf-8").write(f)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("game syntax:", "OK" if r.returncode == 0 else r.stderr[:600])
    for path in (FUNC, r"C:\JapaneseLearning\functions\api\admin.js", r"C:\JapaneseLearning\functions\admin.js"):
        src = io.open(path, encoding="utf-8").read()
        rr = subprocess.run(["node", "--input-type=module", "--check"], input=src, capture_output=True, text=True)
        print("%-28s %s" % (os.path.basename(path), "OK" if rr.returncode == 0 else rr.stderr[:400]))


if __name__ == "__main__":
    main()
