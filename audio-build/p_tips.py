# -*- coding: utf-8 -*-
"""Tips: a nudge that costs money. It speaks the item or shows its picture -
a reminder, never the answer - and where even that would give the answer
away, it greys out one wrong option instead. A round with a tip in it cannot
earn a green star."""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note, count=1):
    global s
    n = s.count(a)
    assert n == count, "expected %d of (%s), found %d" % (count, note, n)
    s = s.replace(a, b, count)


# ---------------------------------------------------------------- session
rep("""    firstTry: 0, wrongs: 0, wrongHere: false,""",
    """    firstTry: 0, wrongs: 0, wrongHere: false, tips: 0, tipHere: false,""", "session fields")

rep("""    session.perfect = !!session.won && session.wrongs === 0;""",
    """    session.perfect = !!session.won && session.wrongs === 0 && !session.tips;""", "no star with a tip")

# a tip is once per question or board
rep("""function advanceMatch(p) {
  session.locked = false;
  session.paused = false;
  session.answeredWrongHere = false;""",
"""function advanceMatch(p) {
  session.locked = false;
  session.paused = false;
  session.answeredWrongHere = false;
  session.tipHere = false;""", "match resets tip")

rep("""    session.missedTarget = false;""",
    """    session.missedTarget = false;
    session.tipHere = false;""", "fish resets tip")

rep("""  session.boardMatched = 0;
  session.boardPairs = session.pool.length;
  session.boards += 1;
}""",
"""  session.boardMatched = 0;
  session.boardPairs = session.pool.length;
  session.boards += 1;
  session.tipHere = false;
}""", "pairs resets tip")

rep("""  session.boards += 1;
  session.picked = null;
}""",
"""  session.boards += 1;
  session.picked = null;
  session.tipHere = false;
}""", "fruit resets tip")

rep("""  session.filled = letters.map(function () { return null; });""",
"""  session.filled = letters.map(function () { return null; });
  session.tipHere = false;""", "word resets tip")

# ---------------------------------------------------------------- the nudge
rep("""/* Wired by every game that draws a boardTag. Kept in one place so a new game
   cannot forget it. */
function wireBoardTag(p) {""",
"""/* ------------------------------------------------------------
   TIPS - a nudge for money.
   A tip speaks the item or shows its picture: a reminder, never the
   answer. The reveal rules that hide a speaker or a picture wherever it
   would give the answer away apply here too, and where both are hidden
   the tip narrows instead - one wrong option greyed out. One per
   question or board; a round with a tip in it cannot earn a green star.
   ------------------------------------------------------------ */

function tipPrice(lv) { return 100 * ((lv && lv.number) || 1); }

// What the board is about right now: the item and the form being answered.
function tipTarget(p) {
  if (!session) return null;
  const m = session.mode;
  if (m === "match" || m === "listen") {
    return session.q ? { key: session.q.answer, form: session.q.to } : null;
  }
  if (m === "pairs") {
    const up = session.up && session.up.length ? session.cards[session.up[0]] : null;
    const first = up || (session.cards || []).filter(function (c) { return !c.done; })[0];
    return first ? { key: first.kana, form: session.toForm } : null;
  }
  if (m === "fruit") {
    let it = null;
    if (session.picked) it = session.items[parseInt(session.picked.getAttribute("data-f"), 10)];
    if (!it || it.placed) it = (session.items || []).filter(function (x) { return !x.placed; })[0];
    return it ? { key: it.kana, form: session.toForm } : null;
  }
  if (m === "word") {
    const w = session.words && session.words[session.wi];
    return w ? { key: w.w, form: null, noPic: true } : null;   // spelling: hearing it is the nudge
  }
  if (m === "fish") {
    return session.target ? { key: session.target, form: session.toForm } : null;
  }
  return null;
}

function nudgeFor(p, key, form, noPic) {
  return {
    say: speech.can(key) && audioOK(p, form),
    pic: !noPic && !!picFor(key) && artOK(form)
  };
}

function tipKind(p) {
  const t = tipTarget(p);
  if (!t) return null;
  const n = nudgeFor(p, t.key, t.form, t.noPic);
  return n.say ? "hear" : n.pic ? "see" : "narrow";
}

function tipBtnHTML(p) {
  if (!session || !session.level) return "";
  const price = tipPrice(session.level);
  const kind = tipKind(p);
  if (!kind) return "";
  const label = kind === "hear" ? "Hear it" : kind === "see" ? "See it" : "Narrow it";
  const used = !!session.tipHere;
  const short = balance(p) < price;
  const why = used ? "One tip per question \\u2014 the next one is a fresh chance"
            : short ? cash(price) + " \\u2014 you have " + cash(balance(p))
            : kind === "hear" ? "Hear it said for " + cash(price) + ". Counts as a tip: no green star this round."
            : kind === "see" ? "See its picture for " + cash(price) + ". Counts as a tip: no green star this round."
            : "Hearing or seeing it would give it away, so this greys out one wrong option for " + cash(price) + ".";
  return '<button class="btn btn-sm tipbtn" id="tipBtn"' + ((used || short) ? ' disabled' : '') +
         ' title="' + esc(why) + '">\\U0001f4a1 ' + label + ' \\u00b7 ' + cash(price) + '</button>';
}

// A picture, shown beside the board for a moment and then gone.
function showNudgePic(key) {
  const old = document.getElementById("nudgePic");
  if (old && old.parentNode) old.parentNode.removeChild(old);
  const el = document.createElement("div");
  el.id = "nudgePic";
  el.className = "nudge-pic";
  el.innerHTML = picImg(key, "nudge-img");
  document.body.appendChild(el);
  setTimeout(function () { el.classList.add("out"); }, 2000);
  setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 2500);
}

// Grey out one wrong option, in whatever shape this game's options take.
function narrowOne(p, key) {
  const m = session.mode;
  if (m === "match" || m === "listen") {
    const wrong = Array.prototype.filter.call(screenEl.querySelectorAll(".ans"), function (b) {
      return b.getAttribute("data-k") !== key && !b.disabled;
    });
    if (wrong.length) { const b = pick(wrong); b.classList.add("wrong", "dim"); b.disabled = true; }
    return;
  }
  if (m === "pairs") {
    const idx = [];
    session.cards.forEach(function (c, i) { if (!c.open && !c.done && c.kana !== key) idx.push(i); });
    if (idx.length) {
      const i = pick(idx);
      const b = screenEl.querySelector('[data-i="' + i + '"]');
      if (b) { b.classList.add("dim"); b.disabled = true; }
    }
    return;
  }
  if (m === "fruit") {
    const bags = Array.prototype.filter.call(screenEl.querySelectorAll("[data-b]"), function (b) {
      return b.getAttribute("data-k") !== key && !b.classList.contains("filled") && !b.disabled;
    });
    if (bags.length) { const b = pick(bags); b.classList.add("dim"); b.disabled = true; }
    return;
  }
  if (m === "fish") {
    const wrong = (session.fishes || []).filter(function (f) { return !f.dead && f.kana !== key; });
    if (wrong.length) {
      const f = pick(wrong);
      f.dead = true;
      f.el.style.setProperty("--fx", f.x + "px");
      f.el.style.setProperty("--fy", f.y + "px");
      f.el.classList.add("miss");
      setTimeout(function () { if (f.el.parentNode) f.el.parentNode.removeChild(f.el); }, 340);
    }
  }
}

function useTip(p) {
  if (!session || session.tipHere) return;
  const t = tipTarget(p);
  if (!t) return;
  const price = tipPrice(session.level);
  if (!pay(p, price)) { audio.bad(); return; }
  session.tips += 1;
  session.tipHere = true;
  const n = nudgeFor(p, t.key, t.form, t.noPic);
  if (n.say) speech.say(t.key);
  if (n.pic) showNudgePic(t.key);
  if (!n.say && !n.pic) narrowOne(p, t.key);
  if (n.say || n.pic) audio.good();
  renderTopbar();
  const b = document.getElementById("tipBtn");
  if (b) { b.disabled = true; b.title = "One tip per question \\u2014 the next one is a fresh chance"; }
  announce("Tip used. " + cash(price) + " spent.");
  save();
}

function wireTip(p) {
  const b = document.getElementById("tipBtn");
  if (b) b.onclick = function () { audio.prime(); useTip(p); };
}

/* Wired by every game that draws a boardTag. Kept in one place so a new game
   cannot forget it. */
function wireBoardTag(p) {""", "tip machinery")

# ---------------------------------------------------------------- the button, in every game
rep("""'<div class="row"><button class="btn btn-sm" id="learnBtn">📖 Learn · restarts</button><button class="btn btn-ghost btn-sm" id="quit">End round</button></div>' +""",
    """'<div class="row">' + tipBtnHTML(p) + '<button class="btn btn-sm" id="learnBtn">📖 Learn · restarts</button><button class="btn btn-ghost btn-sm" id="quit">End round</button></div>' +""",
    "tip button in five games", count=5)

rep("""  wireBoardTag(p);""", """  wireBoardTag(p);
  wireTip(p);""", "wire tip in five games", count=5)

# ---------------------------------------------------------------- the result
rep("""                        ' along the way.' : '') + '</p>'""",
"""                        ' along the way.' : '') +
            (s.tips ? ' ' + s.tips + ' tip' + (s.tips > 1 ? 's' : '') + ' used \\u2014 ' +
                      cash(s.tips * tipPrice(s.level)) + ', and no green star this round.' : '') + '</p>'""",
    "result tips line")

# ---------------------------------------------------------------- the look
rep(""".laddernote { font-size: 12.5px; color: var(--ink-faint); margin: 2px 0 0; }""",
""".laddernote { font-size: 12.5px; color: var(--ink-faint); margin: 2px 0 0; }
.tipbtn { border-color: var(--yamabuki); color: var(--yamabuki); }
.tipbtn[disabled] { opacity: .5; }
.nudge-pic {
  position: fixed; right: 14px; bottom: 96px; z-index: 60;
  border: 3px solid var(--yamabuki); border-radius: var(--r-lg); background: var(--paper);
  padding: 8px; box-shadow: var(--shadow); animation: settle .45s cubic-bezier(.2,1.3,.4,1) both;
  transition: opacity .5s ease;
}
.nudge-pic.out { opacity: 0; }
.nudge-img { width: 150px; height: 150px; object-fit: cover; border-radius: 12px; display: block; }""",
    "tip css")

io.open(f, "w", encoding="utf-8").write(s)
print("tips applied")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
