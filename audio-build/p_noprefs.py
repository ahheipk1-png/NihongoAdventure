# -*- coding: utf-8 -*-
"""No settings to get wrong.

The pace control and the typing option were the last two dials. Both were
choices made before a child knows what they mean, and the pace one could turn
the clock off entirely - which quietly undid the thing every game is balanced
around. One speed, tapping only. Making a new player is a name and a face.
"""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note):
    global s
    n = s.count(a)
    assert n == 1, "expected 1 of (%s), found %d" % (note, n)
    s = s.replace(a, b, 1)


# ---------------------------------------------------------------- pace
rep("""// A hard clock is an accessibility barrier as much as a difficulty setting.
const PACE = { normal: 1, gentle: 0.45, off: 0 };
function paceOf(p) { return PACE[p.pace] !== undefined ? PACE[p.pace] : 1; }""",
"""/* One speed. A dial that could switch the clock off entirely undid the thing
   every game is balanced around, and it was a choice made before a child knew
   what it meant. The clock is gentle enough on its own: a right answer buys
   about six seconds, and a round needs ten of them. */
function paceOf(p) { return 1; }""", "one pace")

rep("""        '<span class="eyebrow">Speed of the power bar</span>' +
        '<div class="paces">' +
          [["normal","Normal"],["gentle","Gentle"],["off","No timer"]].map(function (o) {
            return '<button class="pace" data-pace="' + o[0] + '" aria-pressed="' +
                   (draft.pace === o[0]) + '">' + o[1] + '</button>';
          }).join("") +
        '</div>' +
""", "", "drop the pace picker")

rep("""  screenEl.querySelectorAll("[data-pace]").forEach(function (b) {
    b.onclick = function () { draft.pace = b.getAttribute("data-pace"); renderProfileEditor(p); };
  });
""", "", "drop the pace handler")

rep("""      pace: (p && p.pace) || "normal"
""", "", "drop the pace draft")

rep("""      tier: ONE_TIER, typing: p ? !!p.typing : false,
      unlockAll: p ? !!p.unlockAll : false,
""", """      tier: ONE_TIER, unlockAll: p ? !!p.unlockAll : false
""", "draft fields")

rep("""    // Hold after the sound: long enough to look, longer for a gentle pace.
    const hold = p.pace === "gentle" ? 1000 : 500;""",
"""    // Hold after the sound, long enough to look at what was just said.
    const hold = 600;""", "learn hold")

# ---------------------------------------------------------------- typing
rep("""        '<label class="row" style="gap:8px;font-weight:700;font-size:14.5px;cursor:pointer">' +
          '<input type="checkbox" id="typingIn"' + (draft.typing ? " checked" : "") + ' style="width:19px;height:19px">' +
          'Type the answer in Match instead of tapping</label>' +
""", "", "drop the typing checkbox")

rep("""  const typingIn = document.getElementById("typingIn");
  if (typingIn) typingIn.onchange = function () { draft.typing = typingIn.checked; };
""", "", "drop the typing handler")

rep("""      np.typing = draft.typing; np.unlockAll = draft.unlockAll; np.pace = draft.pace;""",
    """      np.unlockAll = draft.unlockAll;""", "save new profile")

rep("""      p.name = name; p.face = draft.face; p.tier = draft.tier; p.typing = draft.typing; p.unlockAll = draft.unlockAll; p.pace = draft.pace;""",
    """      p.name = name; p.face = draft.face; p.tier = draft.tier; p.unlockAll = draft.unlockAll;""",
    "save existing profile")

rep("""    typing: false, cards: {}, money: 0, spent: 0, landmarks: {}, setsPaid: {}""",
    """    cards: {}, money: 0, spent: 0, landmarks: {}, setsPaid: {}""", "new profile fields")

rep("""  const typing = p.typing && courseOf(p).kind === "kana" && fm.to === "romaji";
""", "", "no typing question")

rep("""  return { answer: answer, from: fm.from, to: fm.to, typing: typing, options: options };""",
    """  return { answer: answer, from: fm.from, to: fm.to, options: options };""", "question shape")

rep("""    p.tier = ONE_TIER;                    // tiers are gone; everyone plays the same game""",
"""    p.tier = ONE_TIER;                    // tiers are gone; everyone plays the same game
    delete p.pace; delete p.typing;       // ...and so are the two dials""",
    "migrate away the dials")

io.open(f, "w", encoding="utf-8").write(s)
print("pace and typing removed")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])
