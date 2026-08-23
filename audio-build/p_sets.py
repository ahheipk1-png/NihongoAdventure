# -*- coding: utf-8 -*-
"""Complete a set - a kana row, a group of five words, a kanji group - and get
paid. The sets are the groups the game already has; nothing new is invented."""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note, count=1):
    global s
    n = s.count(a)
    assert n == count, "expected %d of (%s), found %d" % (count, note, n)
    s = s.replace(a, b, count)


rep("""function cardHome(key) { return CARD_HOME[key] || "hiragana"; }""",
"""function cardHome(key) { return CARD_HOME[key] || "hiragana"; }

/* A set is one of the groups of five the game already has - a kana row, a
   group of five words, a kanji group - each with the label it was written
   with. Built once; the data never changes at runtime. */
const CARD_SETS = (function () {
  const out = [];
  COURSE_ORDER.forEach(function (cid) {
    const c = COURSES[cid];
    c.units.concat(c.extraUnits || []).forEach(function (u, i) {
      if (u.keys.length) out.push({ id: cid + ":" + i, label: u.label || ("Set " + (i + 1)), course: cid, keys: u.keys.slice() });
    });
  });
  KANJI_GROUPS.forEach(function (g, i) {
    out.push({ id: "kanji:" + i, label: "\\u6f22\\u5b57 \\u00b7 " + g.label, course: "kanji", keys: KANJI_KEYS[i].slice() });
  });
  return out;
})();

// Ten times what the cards are worth, rounded up to a round hundred.
function setBonus(set) {
  const v = set.keys.reduce(function (n, k) { return n + cardValue(k); }, 0);
  return Math.ceil(v * 10 / 100) * 100;
}

function setOwned(p, set) {
  return set.keys.filter(function (k) { return !!cards(p)[k]; }).length;
}

/* Pay for every newly completed set. Returns what was paid so the caller can
   say so. Idempotent: setsPaid remembers, so a sixth copy pays nothing and the
   boot check can run every load. The caller saves. */
function checkSets(p) {
  if (!p.setsPaid) p.setsPaid = {};
  const paid = [];
  CARD_SETS.forEach(function (set) {
    if (p.setsPaid[set.id]) return;
    if (setOwned(p, set) < set.keys.length) return;
    const bonus = setBonus(set);
    addMoney(p, bonus);
    p.setsPaid[set.id] = true;
    paid.push({ id: set.id, label: set.label, bonus: bonus });
  });
  return paid;
}""", "set helpers")

rep("""  room.prize = { key: key, already: already,
                 perfect: !!(room.wheel && room.wheel.perfect),
                 gain: cardValue(key) };
  room.wheel = null;
  save();""",
"""  room.prize = { key: key, already: already,
                 perfect: !!(room.wheel && room.wheel.perfect),
                 gain: cardValue(key), sets: checkSets(p) };
  room.wheel = null;
  save();""", "landCard pays sets")

rep("""    if (!p.setsPaid || typeof p.setsPaid !== "object") p.setsPaid = {};""",
"""    if (!p.setsPaid || typeof p.setsPaid !== "object") p.setsPaid = {};
    checkSets(p);          // sets completed before bonuses existed are paid once, here""",
    "boot pays old sets")

rep("""            '<strong>' + cash(balance(p)) + '</strong> to spend now.</p>' +
        '</div>' +""",
"""            '<strong>' + cash(balance(p)) + '</strong> to spend now.</p>' +
        '</div>' +
        (room.prize.sets && room.prize.sets.length
          ? room.prize.sets.map(function (st) {
              return '<div class="setwin">' +
                       '<span class="setwin-icon" aria-hidden="true">\\U0001f389</span>' +
                       '<span><strong>' + esc(st.label) + ' complete</strong> \\u2014 every card in the set. ' +
                       '<strong>+' + cash(st.bonus) + '</strong> set bonus.</span>' +
                     '</div>';
            }).join("")
          : '') +""", "prize set panel")

rep("""      (owned.length
        ? '<div class="wgrid">' + grid + '</div>'
        : '<div class="note">No cards yet. Pass a level and the lucky draw opens.</div>') +
      '<div class="row">' +
        (roomCanOpen(p)""",
"""      (owned.length
        ? '<div class="wgrid">' + grid + '</div>'
        : '<div class="note">No cards yet. Pass a level and the lucky draw opens.</div>') +
      setsHTML(p) +
      '<div class="row">' +
        (roomCanOpen(p)""", "wallet sets section")

rep("""function renderWallet(p) {""",
"""/* The wallet's checklist of sets: only from topics that have been started,
   so the list grows with the journey rather than opening as a wall. */
function setsHTML(p) {
  const started = Object.keys(p.progress || {});
  const rows = CARD_SETS.filter(function (set) {
    return set.course === "kanji" ? setOwned(p, set) > 0 : started.indexOf(set.course) !== -1;
  }).map(function (set) {
    const have = setOwned(p, set), all = set.keys.length, done = !!(p.setsPaid || {})[set.id];
    const chips = set.keys.map(function (k) {
      return '<span class="setchip' + (cards(p)[k] ? ' have' : '') + '" title="' +
             esc(cardFace(p, k).jp + ' \\u2014 ' + cardFace(p, k).en + (cards(p)[k] ? '' : ' \\u00b7 not yet')) + '">' +
             esc(cardFace(p, k).jp) + '</span>';
    }).join("");
    return '<div class="setrow' + (done ? ' done' : '') + '" title="' +
             esc(set.label + ': ' + have + ' of ' + all + (done ? ' \\u2014 bonus paid' : ' \\u2014 collect all ' + all + ' for ' + cash(setBonus(set)))) + '">' +
             '<div class="setrow-head">' +
               '<span class="setrow-label">' + esc(set.label) + '</span>' +
               '<span class="setrow-n">' + have + ' / ' + all + '</span>' +
               '<span class="setrow-bonus">' + (done ? '\\u2713 ' + cash(setBonus(set)) : cash(setBonus(set)) + ' when complete') + '</span>' +
             '</div>' +
             '<div class="setchips">' + chips + '</div>' +
           '</div>';
  });
  if (!rows.length) return "";
  const paidN = CARD_SETS.filter(function (st) { return !!(p.setsPaid || {})[st.id]; }).length;
  return '<div class="sheet stack">' +
           '<span class="eyebrow">Sets \\u00b7 ' + paidN + ' complete</span>' +
           '<p style="margin:0;font-size:13px">Collect every card in a group and it pays a bonus \\u2014 ten times what the cards are worth.</p>' +
           '<div class="setlist">' + rows.join("") + '</div>' +
         '</div>';
}

function renderWallet(p) {""", "setsHTML")

rep(""".wcard.legendary { border-color: var(--shu); }""",
""".wcard.legendary { border-color: var(--shu); }
.setlist { display: flex; flex-direction: column; gap: 8px; }
.setrow { border: 1.5px solid var(--rule); border-radius: var(--r-md); padding: 10px 12px; background: var(--paper); }
.setrow.done { border-color: var(--wakakusa); background: var(--wakakusa-wash); }
.setrow-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.setrow-label { font-weight: 800; font-size: 14px; }
.setrow-n { font-family: var(--font-kana); font-weight: 700; color: var(--ink-soft); font-size: 13px; }
.setrow-bonus { margin-left: auto; font-size: 12.5px; font-weight: 800; color: var(--yamabuki); }
.setrow.done .setrow-bonus { color: var(--wakakusa); }
.setchips { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 7px; }
.setchip {
  font-family: var(--font-kana); font-weight: 700; font-size: 13px;
  border: 1.5px solid var(--rule); border-radius: 8px; padding: 3px 8px;
  color: var(--ink-faint); opacity: .6;
}
.setchip.have { color: var(--ink); border-color: var(--wakakusa); background: var(--paper); opacity: 1; }
.setwin {
  display: flex; align-items: center; gap: 12px;
  border: 1.5px solid var(--yamabuki); background: var(--yamabuki-wash);
  border-radius: var(--r-lg); padding: 12px 16px; font-size: 14px; line-height: 1.45;
}
.setwin-icon { font-size: 24px; line-height: 1; }""", "sets css")

io.open(f, "w", encoding="utf-8").write(s)
print("set bonuses applied")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
