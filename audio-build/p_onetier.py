# -*- coding: utf-8 -*-
"""One difficulty, chosen by nobody.

Three tiers meant three sets of numbers to keep honest, three blurbs that had
to stay true, and a choice a child makes before they know anything about the
game - Sprout looked friendly and was the one that could be passed by tapping
at random. There is one setting now, tuned once and measured once, and no
picker. Everyone keeps the pace control and the typing option, which are
preferences rather than a difficulty.
"""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note):
    global s
    n = s.count(a)
    assert n == 1, "expected 1 of (%s), found %d" % (note, n)
    s = s.replace(a, b, 1)


# ---------------------------------------------------------------- one tier
rep("""const TIERS = {
  sprout: {
    label:"Sprout", blurb:"Three choices, a gentle clock, and a second try when you slip.",
    choices:3, reverse:0, retry:true, roundLen:8,
    power:{ quota:10, drain:2.6, refill:24, penalty:6 },
    modes:["match","listen","pairs","fruit","word"], dakuten:false
  },
  explorer: {
    label:"Explorer", blurb:"Four choices, both directions, and streaks to chase.",
    choices:4, reverse:0.35, retry:false, roundLen:12,
    power:{ quota:10, drain:4.0, refill:18, penalty:8 },
    modes:["match","listen","pairs","fruit","word","fish"], dakuten:false
  },
  ninja: {
    label:"Ninja", blurb:"Six choices, optional typing, and が/ざ/だ/ば/ぱ once the basics are solid.",
    choices:6, reverse:0.4, retry:false, roundLen:15,
    power:{ quota:14, drain:4.2, refill:18, penalty:8 },
    modes:["match","listen","pairs","fruit","word","fish"], dakuten:true
  }
};""",
"""/* One setting for everybody. Four choices, both directions, a second try when
   you slip, and every game. It sits where Explorer sat - so nobody's ladder
   moves under them - with Sprout's kindness about a slip, which the two-tries
   rule now makes safe: guessing was measured at nought to four per cent
   against it, and a child who knows the material passes every time. */
const TIERS = {
  player: {
    label:"Player", blurb:"Four choices, both directions, and a second try when you slip.",
    choices:4, reverse:0.35, retry:true, roundLen:12,
    power:{ quota:10, drain:3.6, refill:20, penalty:8 },
    modes:["match","listen","pairs","fruit","word","fish"], dakuten:false
  }
};
const ONE_TIER = "player";""", "single tier")

rep("""function tierOf(p) { return TIERS[p.tier] || TIERS.explorer; }""",
"""// There is one tier; a saved profile naming an old one still finds it.
function tierOf(p) { return TIERS[ONE_TIER]; }""", "tierOf")

# ---------------------------------------------------------------- the editor
rep("""  const tiers = Object.keys(TIERS).map(function (key) {
    const t = TIERS[key];
    return '<button class="tier" data-tier="' + key + '" aria-pressed="' + (draft.tier === key) + '">' +
             '<span class="tier-name">' + t.label + '</span>' +
             '<span class="tier-sub">' + esc(t.blurb) + '</span></button>';
  }).join("");

""", "", "drop the tier buttons")

rep("""        '<span class="eyebrow">Level</span>' +
        '<div class="tiers">' + tiers + '</div>' +
        '<span class="eyebrow">Speed of the power bar</span>' +""",
    """        '<span class="eyebrow">Speed of the power bar</span>' +""", "drop the picker")

rep("""        (draft.tier === "ninja"
          ? '<label class="row" style="gap:8px;font-weight:700;font-size:14.5px;cursor:pointer">' +
              '<input type="checkbox" id="typingIn"' + (draft.typing ? " checked" : "") + ' style="width:19px;height:19px">' +
              'Type the answer in Match instead of tapping</label>'
          : "") +""",
"""        '<label class="row" style="gap:8px;font-weight:700;font-size:14.5px;cursor:pointer">' +
          '<input type="checkbox" id="typingIn"' + (draft.typing ? " checked" : "") + ' style="width:19px;height:19px">' +
          'Type the answer in Match instead of tapping</label>' +""", "typing for everyone")

rep("""  screenEl.querySelectorAll("[data-tier]").forEach(function (b) {
    b.onclick = function () { draft.tier = b.getAttribute("data-tier"); renderProfileEditor(p); };
  });
""", "", "drop the tier handler")

rep("""      tier: p ? p.tier : "explorer", typing: p ? !!p.typing : false,""",
    """      tier: ONE_TIER, typing: p ? !!p.typing : false,""", "draft tier")

# typing was gated behind the dakuten tier; with one tier it is just a setting
rep("""  const typing = p.typing && t.dakuten && courseOf(p).kind === "kana" && fm.to === "romaji";""",
    """  const typing = p.typing && courseOf(p).kind === "kana" && fm.to === "romaji";""", "typing gate")

# ---------------------------------------------------------------- saved profiles
rep("""    delete p.stars;                       // the points counter is gone""",
"""    delete p.stars;                       // the points counter is gone
    p.tier = ONE_TIER;                    // tiers are gone; everyone plays the same game""",
    "migrate saved tiers")

rep("""    course: "hiragana", progress: { hiragana: { level: 0, boxes: {}, perfect: {} } },""",
    """    course: "hiragana", progress: { hiragana: { level: 0, boxes: {}, perfect: {} } },""",
    "new profile untouched")

io.open(f, "w", encoding="utf-8").write(s)
print("one tier, no picker")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])
