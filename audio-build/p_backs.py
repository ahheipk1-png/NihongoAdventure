# -*- coding: utf-8 -*-
u"""Back buttons where there were dead ends, and the grown-up gets to play.

The complaint was fair: several places could only be left by refreshing.

  * /admin had no way back to the game at all. A "Back to the game" link now
    sits at the top, on the sign-in screen and inside.
  * The player editor's only exits were Save and a Cancel at the bottom; a
    plain Back now sits at the top where a hand looks first.
  * The admin card on the home screen was a one-way door to /admin. It now has
    two buttons: Manage (the parents' page) and Play - and playing as the
    grown-up opens every topic and every level, because the person who checks
    the children's work should be able to jump straight to any level.

"Open every level" rides the existing unlockAll flag, so it is not a special
case for one name: any player a parent ticks "skip the order" for can now play
ahead on the level list and the ladder, not just across topics.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
MIRROR = r"C:\JapaneseLearning\index.html"
PAGE = r"C:\JapaneseLearning\functions\admin.js"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- 1. every level open for unlockAll players: the level list ------
    rep("""    const past = i < cur.index;
    const here = i === cur.index;
    const star = !!perfect[i];
    const shown = info.kana.slice(0, 6).join(" ") + (info.kana.length > 6 ? " …" : "");
    const state = past ? "past" : here ? "here" : "locked";
    const tag = past || here ? "button" : "span";
    const right = star ? '<span class="lvlrow-star" title="Cleared without a mistake">★</span>'
                : here ? '<span class="lvlrow-go">Play ›</span>'
                : past ? '<span class="lvlrow-go">Again ›</span>'
                : '<span class="lvlrow-lock" aria-hidden="true">🔒</span>';
    const tip = star
      ? "Level " + (i + 1) + " — already cleared without a mistake. Play it again?"
      : past ? "Level " + (i + 1) + " — play it again; clear it with no mistakes for a ★"
      : here ? "Level " + (i + 1) + " — where you are now. Tap to play it."
      : "Level " + (i + 1) + " — not open yet; reach it by passing the levels before it";
    rows.push('<' + tag + ' class="lvlrow ' + state + '" title="' + esc(tip) + '"' +
      (past || here ? ' data-lv="' + i + '"' : ' aria-disabled="true"') + '>' +""",
        """    const past = i < cur.index;
    const here = i === cur.index;
    const star = !!perfect[i];
    // "Skip the order" opens the levels ahead as well as the topics.
    const ahead = !past && !here && !!p.unlockAll;
    const canPlay = past || here || ahead;
    const shown = info.kana.slice(0, 6).join(" ") + (info.kana.length > 6 ? " …" : "");
    const state = here ? "here" : canPlay ? "past" : "locked";
    const tag = canPlay ? "button" : "span";
    const right = star ? '<span class="lvlrow-star" title="Cleared without a mistake">★</span>'
                : here ? '<span class="lvlrow-go">Play ›</span>'
                : past ? '<span class="lvlrow-go">Again ›</span>'
                : ahead ? '<span class="lvlrow-go">Play ›</span>'
                : '<span class="lvlrow-lock" aria-hidden="true">🔒</span>';
    const tip = star
      ? "Level " + (i + 1) + " — already cleared without a mistake. Play it again?"
      : past ? "Level " + (i + 1) + " — play it again; clear it with no mistakes for a ★"
      : here ? "Level " + (i + 1) + " — where you are now. Tap to play it."
      : ahead ? "Level " + (i + 1) + " — ahead of the ladder, but every level is open for you"
      : "Level " + (i + 1) + " — not open yet; reach it by passing the levels before it";
    rows.push('<' + tag + ' class="lvlrow ' + state + '" title="' + esc(tip) + '"' +
      (canPlay ? ' data-lv="' + i + '"' : ' aria-disabled="true"') + '>' +""", "levels open")

    # ---- 2. ...and the ladder rungs on the menu ------------------------
    rep("""    const cls = i < lv.index ? "learned" : i === lv.index ? "current" : "";
    const flawless = !!perfect[i];
    const past = i < lv.index;
    const tag = past ? "button" : "span";""",
        """    const cls = i < lv.index ? "learned" : i === lv.index ? "current" : "";
    const flawless = !!perfect[i];
    const past = i < lv.index;
    // Every rung is a door for a player whose order is unlocked.
    const canGo = past || (!!p.unlockAll && i !== lv.index);
    const tag = canGo ? "button" : "span";""", "rungs canGo")

    rep("""        ? "Level " + (i + 1) + " — play it again; no mistakes earns a green star"
        : i === lv.index ? "You are here" : "Not open yet";""",
        """        ? "Level " + (i + 1) + " — play it again; no mistakes earns a green star"
        : canGo ? "Level " + (i + 1) + " — open for you; tap to play it"
        : i === lv.index ? "You are here" : "Not open yet";""", "rung tip")

    rep("""           (flawless ? " perfect" : "") + (past ? " replay" : "") + '"' +
           (past ? ' data-replay="' + i + '"' : '') +""",
        """           (flawless ? " perfect" : "") + (canGo ? " replay" : "") + '"' +
           (canGo ? ' data-replay="' + i + '"' : '') +""", "rung replay attr")

    # ---- 3. the checkbox says what it now does -------------------------
    rep("'Open every topic now (skip the order)</label>'",
        "'Open every topic and every level (skip the order)</label>'", "checkbox label")

    # ---- 4. the admin card: Manage AND Play ----------------------------
    rep("""    if (isAdmin) {
      return '<div class="pslot">' +
               '<button class="profile admincard" data-open="' + p.id + '">' +
                 '<span class="profile-face" aria-hidden="true">🔑</span>' +
                 '<span class="profile-name">' + esc(p.name) + '</span>' +
                 '<span class="profile-meta">Grown-ups’ page</span>' +
                 '<span class="profile-meta">Tap to manage players →</span>' +
               '</button>' +
             '</div>';
    }""",
        """    if (isAdmin) {
      return '<div class="pslot">' +
               '<div class="profile admincard">' +
                 '<span class="profile-face" aria-hidden="true">🔑</span>' +
                 '<span class="profile-name">' + esc(p.name) + '</span>' +
                 '<span class="profile-meta">The grown-up</span>' +
                 '<div class="row" style="gap:6px;justify-content:center;margin-top:4px">' +
                   '<button class="btn btn-sm btn-primary" data-adminmanage="' + p.id + '" ' +
                     'title="Approve players, reset passwords, edit anything">Manage</button>' +
                   '<button class="btn btn-sm" data-adminplay="' + p.id + '" ' +
                     'title="Play the game as the grown-up — every topic and level open">Play</button>' +
                 '</div>' +
               '</div>' +
             '</div>';
    }""", "admin card two doors")

    rep("""  screenEl.querySelectorAll("[data-open]").forEach(function (b) {""",
        """  screenEl.querySelectorAll("[data-adminmanage]").forEach(function (b) {
    b.onclick = function () { location.href = location.origin + "/admin"; };
  });
  screenEl.querySelectorAll("[data-adminplay]").forEach(function (b) {
    b.onclick = function () {
      audio.prime();
      const who = state.profiles.find(function (x) { return x.id === b.getAttribute("data-adminplay"); });
      if (!who) return;
      // The grown-up sees everything; the flag persists and syncs.
      if (!who.unlockAll) { who.unlockAll = true; save(); }
      if (who.pending) { window.alert("This player is still waiting for approval — open Manage first."); return; }
      openPlayer(who);
    };
  });
  screenEl.querySelectorAll("[data-open]").forEach(function (b) {""", "wire admin buttons")

    rep(".profile.admincard { border-color: var(--ai); background: var(--ai-wash); }",
        ".profile.admincard { border-color: var(--ai); background: var(--ai-wash); cursor: default; }",
        "admincard css")

    # ---- 5. the player editor gets a Back at the top -------------------
    rep("""  screenEl.innerHTML =
    '<div class="stack">' +
      '<div class="sheet stack">' +
        '<span class="eyebrow">' + (isNew ? "New player" : "Player settings") + '</span>' +""",
        """  screenEl.innerHTML =
    '<div class="stack">' +
      '<div class="row"><button class="btn btn-ghost btn-sm" id="backP" ' +
        'title="Leave without saving">\u2190 Back</button></div>' +
      '<div class="sheet stack">' +
        '<span class="eyebrow">' + (isNew ? "New player" : "Player settings") + '</span>' +""", "editor back button")

    rep("""  document.getElementById("cancelP").onclick = function () {
    draft = null;
    if (isNew) { state.activeId = null; go("home"); } else { go("menu"); }
  };""",
        """  const leave = function () {
    draft = null;
    if (isNew) { state.activeId = null; go("home"); } else { go("menu"); }
  };
  document.getElementById("cancelP").onclick = leave;
  document.getElementById("backP").onclick = leave;""", "wire editor back")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    # ---- 6. /admin gets a way back to the game -------------------------
    f = io.open(PAGE, encoding="utf-8").read()
    a = "<h1>Nihongo Adventure</h1>"
    b = '<a class="backlink" href="/">\u2190 Back to the game</a>\n  <h1>Nihongo Adventure</h1>'
    assert f.count(a) == 1, "admin h1: %d" % f.count(a)
    f = f.replace(a, b, 1)
    c = "  h1 { font-size: 21px; margin: 0 0 2px; }"
    d = """  h1 { font-size: 21px; margin: 0 0 2px; }
  .backlink { display: inline-block; margin: 0 0 12px; color: var(--ai); font-weight: 700;
              font-size: 13px; text-decoration: none; }
  .backlink:hover { text-decoration: underline; }"""
    assert f.count(c) == 1, "admin css: %d" % f.count(c)
    f = f.replace(c, d, 1)
    io.open(PAGE, "w", encoding="utf-8").write(f)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("game syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
    r2 = subprocess.run(["node", "--input-type=module", "--check"], input=f, capture_output=True, text=True)
    print("admin page syntax:", "OK" if r2.returncode == 0 else r2.stderr[:400])


if __name__ == "__main__":
    main()
