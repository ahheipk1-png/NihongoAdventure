# -*- coding: utf-8 -*-
"""The rest of the review fixes: the page, the sweep, and the held answer.

Anchors here are deliberately short and free of backslashes - the page is a
template literal full of \\u escapes, and matching those through two layers of
quoting is how the first attempt at this went wrong.
"""
import io, os, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
PAGE = r"C:\JapaneseLearning\functions\admin.js"
SYNC = r"C:\JapaneseLearning\functions\api\sync.js"


def patch(path, edits):
    s = io.open(path, encoding="utf-8").read()
    for old, new, note in edits:
        if s.count(old) == 0 and new in s:
            print("  (already there: %s)" % note)
            continue
        assert s.count(old) == 1, "%s / %s: found %d" % (os.path.basename(path), note, s.count(old))
        s = s.replace(old, new, 1)
    io.open(path, "w", encoding="utf-8").write(s)


NUM_HELPER = '''/* Everything the page shows came out of a save, and a save came from a request
   nobody had to authenticate. A field called `stars` is a number only because
   the game happened to write it; a stranger can write anything. */
function n(v, blank) {
  var x = Number(v);
  return (v == null || !isFinite(x)) ? (blank === undefined ? "-" : blank) : String(x);
}
function stamp(t)'''

CSP = '''/* A nonce, and a policy that allows nothing else.

   Escaping is the fix for injected markup and this is the belt to its braces:
   under `script-src 'nonce-...'` an `onerror=` that slipped through would sit
   in the page inert, because an inline event handler is not a nonced script. */
export async function onRequestGet() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let nonce = "";
  for (let i = 0; i < bytes.length; i++) nonce += bytes[i].toString(16).padStart(2, "0");
  return new Response(PAGE.split("__NONCE__").join(nonce), {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex, nofollow",
      "referrer-policy": "no-referrer",
      "content-security-policy":
        "default-src 'none'; script-src 'nonce-" + nonce + "'; style-src 'nonce-" + nonce + "'; " +
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    }
  });
}'''

TYPED = '''    /* The boxes above and the JSON below are two views of one save, and a
       parent who edited the JSON meant it. So a box only overrules the text if
       the box itself was changed. */
    function typed(id, was) {
      var el = document.getElementById(id);
      return el && el.value !== String(was) ? el.value : null;
    }
    var nm = typed("eName", p.name); if (nm !== null && nm.trim()) next.name = nm.trim();
    var fc = typed("eFace", p.face); if (fc !== null && fc.trim()) next.face = fc.trim();
    var mn = typed("eMoney", n(p.money)); if (mn !== null) next.money = Number(mn) || 0;
    var sp = typed("eSpent", n(p.spent)); if (sp !== null) next.spent = Number(sp) || 0;
    Array.prototype.forEach.call(document.querySelectorAll("[data-level]"), function (i) {
      var cid = i.getAttribute("data-level");
      if (i.value === i.getAttribute("data-was")) return;
      if (next.progress && next.progress[cid]) {
        next.progress[cid].level = Math.max(0, (Number(i.value) || 1) - 1);
      }
    });'''

SIGNOUT = '''    if (!d.ok) {
      // Only a refused session sends you back to the door. "Slow down" and a
      // dropped connection are not reasons to throw the parent out.
      if (d._status === 401) {
        TOKEN = ""; sessionStorage.removeItem("nihongo-admin");
        document.getElementById("main").hidden = true;
        document.getElementById("gate").hidden = false;
        say("gateMsg", d.error || "sign in again", "bad");
      } else {
        say("mainMsg", d.error || "could not load", "bad");
      }
      return;
    }'''


def main():
    patch(PAGE, [
        # --- the nonce goes on both inline blocks -------------------------
        ("<style>", '<style nonce="__NONCE__">', "style nonce"),
        ("<script>\nvar TOKEN", '<script nonce="__NONCE__">\nvar TOKEN', "script nonce"),

        # --- a coercing helper, next to the other formatters --------------
        ("function stamp(t)", NUM_HELPER, "n() helper"),

        # --- every summary field, in the table ----------------------------
        ("""' <span class="muted">' + st.level + " / " + st.levels + '</span>'""",
         """' <span class="muted">' + n(st.level) + " / " + n(st.levels) + '</span>'""", "table level"),
        ("""st.stars) + '</td>'""", """n(st.stars)) + '</td>'""", "table stars"),
        ("""'<div class="bar" title="' + st.mastered + " of " + st.items +""",
         """'<div class="bar" title="' + n(st.mastered) + " of " + n(st.items) +""", "table mastered"),
        ("""(st.cards == null ? "-" : st.cards) + '</td>'""",
         """n(st.cards) + '</td>'""", "table cards"),

        # --- and in the editor -------------------------------------------
        ("""'</b><span>level ' + (st.level || "?") +
        ' of ' + (st.levels || "?") + '</span></div>'""",
         """'</b><span>level ' + n(st.level, "?") +
        ' of ' + n(st.levels, "?") + '</span></div>'""", "editor level"),
        ("""(st.stars == null ? "-" : st.stars) + '</b><span>green stars</span></div>'""",
         """n(st.stars) + '</b><span>green stars</span></div>'""", "editor stars"),
        ("""'<div class="stat"><b>' + (st.mastered == null ? "-" : st.mastered) + '</b><span>of ' +
        (st.items || "?") + ' mastered</span></div>'""",
         """'<div class="stat"><b>' + n(st.mastered) + '</b><span>of ' +
        n(st.items, "?") + ' mastered</span></div>'""", "editor mastered"),
        ("""(st.cards == null ? "-" : st.cards) + '</b><span>cards</span></div>'""",
         """n(st.cards) + '</b><span>cards</span></div>'""", "editor cards"),
        ("""(st.sights == null ? "-" : st.sights) + '</b><span>places built</span></div>'""",
         """n(st.sights) + '</b><span>places built</span></div>'""", "editor sights"),

        # --- the two money boxes carry a save's raw fields ----------------
        ("""'<input id="eMoney" type="number" value="' + (p.money || 0) + '"></div>'""",
         """'<input id="eMoney" type="number" value="' + n(p.money, "0") + '"></div>'""", "money box"),
        ("""'<input id="eSpent" type="number" value="' + (p.spent || 0) + '"></div>'""",
         """'<input id="eSpent" type="number" value="' + n(p.spent, "0") + '"></div>'""", "spent box"),
        ("""data-level="' + esc(cid) + '" value="' +
        ((g.level || 0) + 1) + '">""",
         """data-level="' + esc(cid) + '" value="' +
        (n(g.level, 0) + 1) + '" data-was="' + (n(g.level, 0) + 1) + '">""", "level boxes"),

        # --- the numbers are the game's, not ours -------------------------
        ("""    '<label>Last few times this player was opened</label>'""",
         """    '<p class="muted" style="font-size:12px;margin:0 0 14px">The six numbers above are what ' +
      'the game itself last reported. They catch up the next time this player is opened on a ' +
      'computer, not the moment you save here.</p>' +
    '<label>Last few times this player was opened</label>'""", "freshness note"),

        # --- only a refused session signs you out -------------------------
        ("""    if (!d.ok) {
      TOKEN = ""; sessionStorage.removeItem("nihongo-admin");
      document.getElementById("main").hidden = true;
      document.getElementById("gate").hidden = false;
      say("gateMsg", d.error || "sign in again", "bad");
      return;
    }""", SIGNOUT, "sign out on 401 only"),

        # --- the form only overrules what was typed -----------------------
        ("""    next.name = document.getElementById("eName").value.trim() || next.name;
    next.face = document.getElementById("eFace").value.trim() || next.face;
    next.money = Number(document.getElementById("eMoney").value) || 0;
    next.spent = Number(document.getElementById("eSpent").value) || 0;
    Array.prototype.forEach.call(document.querySelectorAll("[data-level]"), function (i) {
      var cid = i.getAttribute("data-level");
      if (next.progress && next.progress[cid]) {
        next.progress[cid].level = Math.max(0, (Number(i.value) || 1) - 1);
      }
    });""", TYPED, "typed only"),

        ("""api({ action: "put", code: PICK.code, pid: PICK.pid, data: next })""",
         """api({ action: "put", code: PICK.code, pid: PICK.pid, data: next, rev: PICK.rev })""", "send rev"),

        # --- and the page is served under a policy ------------------------
        ("""export async function onRequestGet() {
  return new Response(PAGE, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex, nofollow",
      "referrer-policy": "no-referrer"
    }
  });
}""", CSP, "csp"),
    ])

    patch(SYNC, [
        ('Math.floor(minute / 1440), NEW_PER_DAY',
         'minute - (minute % 1440), NEW_PER_DAY', "day bucket scale"),
        ('    if (await tooMany(env, key + ":n", minute - (minute % 1440), NEW_PER_DAY)) {',
         '''    /* The same column as the per-minute counter, so it has to be on the same
       scale: a day bucket numbered in the twenty-thousands looked ancient to a
       sweep measuring in minutes and was deleted on sight, which quietly reset
       the daily limit every time it ran. */
    if (await tooMany(env, key + ":n", minute - (minute % 1440), NEW_PER_DAY)) {''', "day bucket note"),
    ])

    patch(GAME, [
        ("""    // Called when a round ends and it is safe to change what is on screen.
    settle: function () {
      if (!held) return false;
      const data = held;
      held = null;
      apply(data);
      return true;
    },""",
         """    /* Called when a round ends and it is safe to change what is on screen.

       The answer that arrived mid-round is thrown away rather than applied: it
       was merged against the save as it stood before the last few questions,
       and adopting it now would quietly roll them back. Asking again costs one
       request and merges against what the child actually has. */
    settle: function () {
      if (!held) return false;
      held = null;
      queue(false);
      return true;
    },""", "settle re-syncs"),
    ])

    s = io.open(GAME, encoding="utf-8").read()
    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("game syntax:", "OK" if r.returncode == 0 else r.stderr[:600])
    for path in (SYNC, r"C:\JapaneseLearning\functions\api\admin.js", PAGE):
        src = io.open(path, encoding="utf-8").read()
        rr = subprocess.run(["node", "--input-type=module", "--check"], input=src, capture_output=True, text=True)
        print("%-14s %s" % (os.path.basename(path), "OK" if rr.returncode == 0 else rr.stderr[:400]))


if __name__ == "__main__":
    main()
