# -*- coding: utf-8 -*-
u"""Six fixes from the parent actually using it, plus a static Back to levels.

1. Four buttons carried a JS "\\U0001f50a" escape, which JavaScript does not
   understand, so they printed the raw text "U0001f50a" instead of the speaker,
   the light bulb, the book and the party popper. Real characters now.
2. Listening asked for romaji - hearing "ka" and picking "ka" is no test. It
   answers with the character now.
3. The wheel span too fast to aim and did two extra turns after the tap; it now
   turns slowly and settles onto the slice under the pin when STOP was pressed.
4. "0 of 69 mastered" beside "Level 1" was two counting systems; the home card
   shows one now, "Level 1 of 36".
5. The cloud panel is a quiet line, code and join folded behind a link.
6. A static "Back to levels" button in the top bar, on every in-game screen.
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

    # ---- 1. broken emoji escapes: literal backslash-U -> the real glyph -
    for bad, ch in [("\\U0001f4a1", u"\U0001f4a1"), ("\\U0001f50a", u"\U0001f50a"),
                    ("\\U0001f4d6", u"\U0001f4d6"), ("\\U0001f389", u"\U0001f389")]:
        assert s.count(bad) == 1, "emoji %s found %d" % (bad, s.count(bad))
        s = s.replace(bad, ch, 1)

    # ---- 2. listening answers with the character, never romaji ---------
    rep("""  const answer = nextKana(p, session.pool, lastPrompt);
  lastPrompt = answer;
  const fm = pickForms(p);""",
        """  const answer = nextKana(p, session.pool, lastPrompt);
  lastPrompt = answer;
  let fm = pickForms(p);
  // Hearing a sound and choosing its romaji is no test - the romaji IS the
  // sound written down. A listening round answers with the character instead.
  if (session.mode === "listen" && fm.to === "romaji") {
    const ff = (session.level && session.level.forms) || courseOf(p).forms;
    const glyph = ff.indexOf("jp") !== -1 ? "jp"
      : (ff.filter(function (f) { return f !== "romaji"; })[0] || "jp");
    fm = { from: "romaji", to: glyph };
  }""", "listen answers in kana")

    # ---- 3. the wheel: slow, and settles where you stopped ------------
    rep(".wheel.spinning { animation: wheelspin 1300ms linear infinite; }",
        ".wheel.spinning { animation: wheelspin 3600ms linear infinite; }", "slow wheel")
    rep("""          const target = cur + ((360 - ((cur + idx * slice + slice / 2) % 360)) % 360) + 720;
          el.style.transform = "rotate(" + target + "deg)";""",
        """          // Centre the very slice under the pin when STOP was pressed - no extra
          // turns, or it looks as though the tap was ignored.
          const target = cur + ((360 - ((cur + idx * slice + slice / 2) % 360)) % 360);
          el.style.transform = "rotate(" + target + "deg)";""", "settle no extra turns")

    # ---- 4. the home card shows one counting system -------------------
    rep("""               '<span class="profile-meta">' + courseOf(p).title + ' · ' + lv.label + '</span>' +
               '<span class="profile-meta">' + done + ' of ' + total + ' mastered</span>' +
               '<span class="profile-bar"><i style="width:' + pct + '%"></i></span>' +""",
        """               '<span class="profile-meta">' + esc(courseOf(p).title) + '</span>' +
               '<span class="profile-meta">' + esc(lv.label + ' of ' + lv.total) + '</span>' +
               '<span class="profile-bar"><i style="width:' +
                 (lv.total ? Math.round((lv.number / lv.total) * 100) : 0) + '%"></i></span>' +""",
        "home card level progress")

    # ---- 5. the cloud panel becomes a quiet line ---------------------
    a = s.index("""function cloudSheet() {
  if (!cloud.ready()) return "";
  const c = cloud.code();""")
    b = s.index("\nfunction wireCloud() {", a)
    new_sheet = '''function cloudSheet() {
  if (!cloud.ready()) return "";
  const c = cloud.code();

  /* Automatic, so this is quiet. A child never needs it; a parent linking a
     second computer taps "Play on another computer" for the code and join box. */
  if (c) {
    return '<div class="cloudbar">' +
             '<span class="cloudbar-note">\\u2601 Progress saves automatically</span> ' +
             '<button class="linkish" id="cloudMore">Play on another computer</button>' +
             '<div class="cloudbar-detail" id="cloudDetail" hidden>' +
               '<p class="fineprint">On the other computer, open the game and type this code:</p>' +
               '<div class="row" style="justify-content:center">' +
                 '<span class="code-box">' + esc(c.slice(0, 4)) + '<i>-</i>' + esc(c.slice(4)) + '</span>' +
                 '<button class="btn btn-sm" id="cloudCopy" title="Copy the family code">Copy</button>' +
               '</div>' +
               '<p class="fineprint">Already have a code from another computer? ' +
                 '<button class="linkish" id="cloudJoinToggle">Enter it here</button> ' +
                 '\\u00b7 <button class="linkish" id="cloudOff">Stop saving on this computer</button></p>' +
               '<div class="row" id="cloudJoinRow" style="justify-content:center" hidden>' +
                 '<input class="code-in" id="cloudCode" maxlength="9" placeholder="CODE" aria-label="Family code" />' +
                 '<button class="btn btn-sm" id="cloudJoin">Use this code</button>' +
               '</div>' +
               '<span class="grow-label" id="cloudMsg">' + esc(cloud.note()) + '</span>' +
             '</div>' +
           '</div>';
  }

  /* No code yet - a fresh second computer, or one where saving was stopped.
     The one thing worth offering is joining an existing family. */
  return '<div class="cloudbar">' +
           '<span class="cloudbar-note">' +
             (state.profiles.length ? '\\u2601 Progress saves automatically'
                                    : 'Already playing on another computer?') + '</span>' +
           '<div class="row" style="justify-content:center">' +
             '<input class="code-in" id="cloudCode" maxlength="9" placeholder="CODE" ' +
               'title="The eight-letter code from the computer you already set up" aria-label="Family code" />' +
             '<button class="btn btn-sm" id="cloudJoin" title="Bring that family\\'s players onto this computer">Use this code</button>' +
             (cloud.stopped() ? '<button class="btn btn-sm" id="cloudOn" title="Turn saving back on for this computer">Turn saving on</button>' : '') +
           '</div>' +
           '<span class="grow-label" id="cloudMsg">' + esc(cloud.note()) + '</span>' +
         '</div>';
}
'''
    s = s[:a] + new_sheet + s[b + 1:]

    rep("""  const toggle = document.getElementById("cloudJoinToggle");
  if (toggle) toggle.onclick = function () {
    const row = document.getElementById("cloudJoinRow");
    if (row) { row.hidden = !row.hidden; const i = document.getElementById("cloudCode"); if (i && !row.hidden) i.focus(); }
  };""",
        """  const more = document.getElementById("cloudMore");
  if (more) more.onclick = function () {
    const d = document.getElementById("cloudDetail");
    if (d) d.hidden = !d.hidden;
  };

  const toggle = document.getElementById("cloudJoinToggle");
  if (toggle) toggle.onclick = function () {
    const row = document.getElementById("cloudJoinRow");
    if (row) { row.hidden = !row.hidden; const i = document.getElementById("cloudCode"); if (i && !row.hidden) i.focus(); }
  };""", "wire cloudMore")

    rep(".cloud-pill {",
        """.cloudbar { text-align: center; margin: 2px 0 4px; color: var(--ink-faint); font-size: 12px; }
.cloudbar-note { font-weight: 700; }
.cloudbar-detail {
  margin: 8px auto 0; max-width: 440px; padding: 12px 14px;
  background: var(--paper); border: 1.5px solid var(--rule); border-radius: 14px;
}
.cloudbar-detail .fineprint { margin: 0 0 8px; }
.cloud-pill {""", "cloudbar css")

    # ---- 6. a static "Back to levels" in the top bar -----------------
    # It sits right after the player's name, on every in-game screen, so there
    # is always one fixed way back to the level picker.
    rep("""    html += '<button class="who" id="toMenu" title="' + esc(p.name) +
              ' — back to the topic menu">' +
              '<span class="who-face" aria-hidden="true">' + esc(p.face) + '</span>' +
              '<span class="who-name">' + esc(p.name) + '</span></button>' +""",
        """    html += '<button class="who" id="toMenu" title="' + esc(p.name) +
              ' — back to the topic menu">' +
              '<span class="who-face" aria-hidden="true">' + esc(p.face) + '</span>' +
              '<span class="who-name">' + esc(p.name) + '</span></button>' +
            (screen !== "levels"
              ? '<button class="purse levels" id="toLevels" title="Back to the level list — pick which level to play">\\u2190 Levels</button>'
              : '') +""", "levels button markup")

    rep("""  const menu = document.getElementById("toMenu");
  if (menu) menu.onclick = function () { stopLoops(); go("menu"); };""",
        """  const menu = document.getElementById("toMenu");
  if (menu) menu.onclick = function () { stopLoops(); go("menu"); };
  const lvl = document.getElementById("toLevels");
  if (lvl) lvl.onclick = function () { stopLoops(); go("levels"); };""", "levels button wire")

    rep(".purse.sound, .purse.vol { font-size: 15px; padding: 6px 10px; }",
        """.purse.sound, .purse.vol { font-size: 15px; padding: 6px 10px; }
.purse.levels { font-size: 13px; font-weight: 700; }""", "levels button css")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    left = re.findall(r"\\U[0-9a-fA-F]{8}", js)
    print("remaining broken \\U escapes in main script:", len(left))
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])


if __name__ == "__main__":
    main()
