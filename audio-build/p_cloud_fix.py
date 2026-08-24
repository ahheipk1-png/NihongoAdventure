# -*- coding: utf-8 -*-
"""Corrections to cloud save, from a round of adversarial review.

Four of them are real defects rather than polish:

  - a profile arriving from another computer skipped boot's whole
    normalisation pass, so a save written by an older build landed raw. The
    pass is now a named function that both boot and the merge call.
  - the level clamp only ever checked the course that happened to be open,
    because `ladderFor(p)` reads `p.course`. Every course is checked now,
    through a stub, the way ECONOMY already does it.
  - `p.face` reaches innerHTML unescaped in three places. That was harmless
    while a face could only come from the picker; it is not harmless once a
    face can arrive from another computer.
  - a push read the row, merged, and wrote it back with nothing stopping the
    other computer from writing in between. The write is now conditional on
    the revision it merged against, and retries against whatever it finds.

Deliberately NOT adopted from the review: deriving money from green stars and
set bonuses instead of merging it. It is exact today and would silently
re-price history tomorrow - `cardValue` depends on which topic owns a card,
and CARD_HOME is first-wins across COURSE_ORDER, so inserting a topic can move
a card's home, change a set's bonus and quietly take money off a child who
earned it. The delta merge can only ever be generous; derivation can subtract.
"""
import io, os, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
FUNC = r"C:\JapaneseLearning\functions\api\sync.js"


def main():
    # ---------------- the game -------------------------------------------
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # 1. boot's backfill becomes a function the merge can call too
    head = "  state.profiles.forEach(function (p) {          // backfill older saves\n"
    tail = "\n  });\n  if (state.resetAt !== RECORDS_RESET) {"
    i = s.index(head)
    j = s.index(tail, i)
    body = s[i + len(head):j]
    dedented = "\n".join(l[2:] if l.startswith("  ") else l for l in body.split("\n"))
    s = s[:i] + "  state.profiles.forEach(backfill);" + s[j + len("\n  });"):]

    backfill = '''
/* Everything a save has to be put through before the game can trust it.

   Boot has always done this to whatever came out of localStorage. The cloud
   made it something a merged profile needs too: a save written by an older
   build, or by a computer that has not reloaded since the last deploy, arrives
   in that build's shape and would otherwise go straight into play. */
function backfill(p) {
%s
  /* Every course, not only the one that happens to be open. `ladderFor` reads
     the profile's current course, so this clamp has never once looked at the
     others - a stub asks the question properly, the way ECONOMY does. */
  Object.keys(p.progress).forEach(function (cid) {
    const top = ladderFor({ course: cid, unlockAll: p.unlockAll }).length - 1;
    p.progress[cid].level = Math.max(0, Math.min(p.progress[cid].level || 0, Math.max(0, top)));
  });
  // A face is picked from a list. Anything else arrived by another route.
  if (FACES.indexOf(p.face) === -1) p.face = FACES[0];
}
''' % dedented.rstrip()

    rep("(function boot() {", backfill.lstrip("\n") + "\n(function boot() {", "backfill function")

    # 2. a merged profile goes through it as well
    rep("""    state.profiles.forEach(function (p) {
      lastSent[p.id] = mark(JSON.stringify(outgoing(p)));
      if (typeof checkSets === "function") checkSets(p);
    });""",
        """    state.profiles.forEach(function (p) {
      // The fingerprint is of what the server holds, not of what this device
      // makes of it: a correction below has to be pushed once, and then the
      // two agree and it is never pushed again.
      lastSent[p.id] = mark(JSON.stringify(outgoing(p)));
      backfill(p);
      checkSets(p);
    });""", "backfill on merge")

    # 3. a face from elsewhere is not markup
    rep("""              '<span class="who-face" aria-hidden="true">' + p.face + '</span>' +""",
        """              '<span class="who-face" aria-hidden="true">' + esc(p.face) + '</span>' +""", "topbar face")
    rep("""               '<span class="profile-face" aria-hidden="true">' + p.face + '</span>' +""",
        """               '<span class="profile-face" aria-hidden="true">' + esc(p.face) + '</span>' +""", "home face")
    rep("""'<h1>Hi ' + esc(p.name) + ' ' + p.face + '</h1>'""",
        """'<h1>Hi ' + esc(p.name) + ' ' + esc(p.face) + '</h1>'""", "menu face")

    # 4. the Artifact never asks
    rep("""  const ENDPOINT = "/api/sync";
  const DEBOUNCE = 4000;""",
        """  const ENDPOINT = "/api/sync";
  const DEBOUNCE = 4000;
  /* The Artifact build is served from a Claude domain and its CSP forbids
     every outside request. Asking anyway would log a violation on every load
     and buy nothing, so on those hosts the feature is simply not there. */
  const HOSTED = !/(^|\\.)(claude\\.ai|claudeusercontent\\.com|anthropic\\.com)$/i.test(location.hostname);""",
        "hosted test")

    rep("""  let reachable = null;            // null until the first call answers""",
        """  let reachable = HOSTED ? null : false;   // null until the first call answers""", "reachable init")

    # 5. a tab being hidden is the last chance to push; keep the request alive
    rep("""  function post(body) {
    return fetch(ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (res) {""",
        """  function post(body, closing) {
    const text = JSON.stringify(body);
    return fetch(ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/json" },
      // A plain request dies with the page. `keepalive` outlives it, but only
      // up to 64 KB, and a family of maxed-out players is bigger than that -
      // so it is used when it fits and skipped when it would fail outright.
      keepalive: !!closing && text.length < 60000,
      body: text
    }).then(function (res) {""", "keepalive")

    rep("""  function run(full) {
    if (!on() || reachable === false) return Promise.resolve(false);""",
        """  function run(full, closing) {
    if (!on() || reachable === false) return Promise.resolve(false);""", "run signature")

    rep("""    return post(body).then(function (res) {
      reachable = true;""",
        """    return post(body, closing).then(function (res) {
      reachable = true;""", "post closing")

    rep("""  function queue(full) {
    chain = chain.catch(function () { return false; }).then(function () { return run(full); });
    return chain;
  }""",
        """  function queue(full, closing) {
    chain = chain.catch(function () { return false; }).then(function () { return run(full, closing); });
    return chain;
  }""", "queue closing")

    rep("""    flush: function () {
      if (timer) { window.clearTimeout(timer); timer = null; }
      return queue(false);
    },""",
        """    flush: function (closing) {
      if (timer) { window.clearTimeout(timer); timer = null; }
      return queue(false, closing);
    },""", "flush closing")

    rep("""    if (document.visibilityState === "hidden") cloud.flush();""",
        """    if (document.visibilityState === "hidden") cloud.flush(true);""", "hidden flush")

    io.open(GAME, "w", encoding="utf-8").write(s)

    # ---------------- the endpoint ---------------------------------------
    f = io.open(FUNC, encoding="utf-8").read()

    def frep(old, new, note):
        nonlocal f
        assert f.count(old) == 1, "%s: found %d" % (note, f.count(old))
        f = f.replace(old, new, 1)

    frep("""function newCode(len) {
  const bytes = new Uint8Array(len || CODE_LEN);
  crypto.getRandomValues(bytes);
  let out = "";
  for (let i = 0; i < bytes.length; i++) out += ALPHABET[bytes[i] % ALPHABET.length];
  return out;
}""",
         """/* 256 does not divide by 30, so a plain modulo would make the first sixteen
   letters of the alphabet a shade likelier than the rest. Drawing again on the
   remainder costs nothing and keeps every code equally likely. */
function newCode(len) {
  const want = len || CODE_LEN;
  const ceiling = 256 - (256 % ALPHABET.length);
  let out = "";
  while (out.length < want) {
    const bytes = new Uint8Array(want * 2);
    crypto.getRandomValues(bytes);
    for (let i = 0; i < bytes.length && out.length < want; i++) {
      if (bytes[i] < ceiling) out += ALPHABET[bytes[i] % ALPHABET.length];
    }
  }
  return out;
}""", "rejection sampling")

    frep("""  const pushed = {};
  for (let i = 0; i < profiles.length; i++) {
    const p = profiles[i];
    pushed[p.id] = true;
    const row = await env.DB.prepare(
      "SELECT data, rev, deleted FROM saves WHERE code = ?1 AND pid = ?2"
    ).bind(code, p.id).first();
    if (row && row.deleted) continue;            // it was deleted elsewhere
    let server = null;
    if (row && row.data) {
      try { server = JSON.parse(row.data); } catch (e) { server = null; }
    }
    const merged = mergeProfile(server, p, bases[p.id]);
    await env.DB.prepare(
      "INSERT INTO saves (code, pid, data, rev, updated, deleted) VALUES (?1, ?2, ?3, 1, ?4, 0) " +
      "ON CONFLICT(code, pid) DO UPDATE SET data = ?3, updated = ?4, rev = saves.rev + 1"
    ).bind(code, p.id, JSON.stringify(merged), now).run();
  }""",
         """  for (let i = 0; i < profiles.length; i++) {
    await store(env, code, profiles[i], bases[profiles[i].id], now);
  }""", "store loop")

    frep("""/* ---------- the endpoint ---------- */""",
         """/* Read, merge, write - with the write conditional on the row not having moved
   in between. Two computers syncing the same child in the same second would
   otherwise each merge against the same old row and the second would erase the
   first. On a clash it simply reads what landed and merges on top of that. */
async function store(env, code, p, base, now) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const row = await env.DB.prepare(
      "SELECT data, rev, deleted FROM saves WHERE code = ?1 AND pid = ?2"
    ).bind(code, p.id).first();
    if (row && row.deleted) return;              // deleted on purpose, elsewhere
    if (!row) {
      const ins = await env.DB.prepare(
        "INSERT INTO saves (code, pid, data, rev, updated, deleted) VALUES (?1, ?2, ?3, 1, ?4, 0) " +
        "ON CONFLICT(code, pid) DO NOTHING"
      ).bind(code, p.id, JSON.stringify(p), now).run();
      if (ins && ins.meta && ins.meta.changes === 1) return;
      continue;                                  // someone got there first
    }
    let server = null;
    if (row.data) {
      try { server = JSON.parse(row.data); } catch (e) { server = null; }
    }
    const merged = mergeProfile(server, p, base);
    const upd = await env.DB.prepare(
      "UPDATE saves SET data = ?1, rev = rev + 1, updated = ?2 WHERE code = ?3 AND pid = ?4 AND rev = ?5"
    ).bind(JSON.stringify(merged), now, code, p.id, row.rev).run();
    if (upd && upd.meta && upd.meta.changes === 1) return;
  }
}

/* ---------- the endpoint ---------- */""", "store function")

    io.open(FUNC, "w", encoding="utf-8").write(f)

    # ---------------- only /api/* goes through the Worker -----------------
    routes = os.path.join(os.path.dirname(GAME), "audio-build", "dist", "_routes.json")
    io.open(routes, "w", encoding="utf-8").write(
        '{\n  "version": 1,\n  "include": ["/api/*"],\n  "exclude": []\n}\n')

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = os.path.join(os.path.dirname(GAME), "audio-build", "_check.js")
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("game syntax:", "OK" if r.returncode == 0 else r.stderr[:800])
    r2 = subprocess.run(["node", "--input-type=module", "--check"], input=f, capture_output=True, text=True)
    print("worker syntax:", "OK" if r2.returncode == 0 else r2.stderr[:800])


if __name__ == "__main__":
    main()
