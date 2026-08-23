# -*- coding: utf-8 -*-
"""Pin the kanji to their courses, and let the economy price itself.

Two changes that have to land before any new topic does.

1. kanjiOffset summed the ladder lengths of every PRECEDING course, so slotting
   a topic into the middle of the order shifted which kanji group every later
   topic teaches. A child sitting on a kanji rung would find five characters
   they had never met, and a level they had passed would quietly un-pass. The
   offsets are pinned to exactly today's values instead, so the order of topics
   becomes something that can be changed freely.

2. The map's prices were hand-tuned against a fixed amount of content, and went
   stale the moment levels were added. They are computed from the content now:
   whatever the game grows to, all 47 prefecture cards cost about 65% of what a
   perfect run pays.
"""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note):
    global s
    n = s.count(a)
    assert n == 1, "expected 1 of (%s), found %d" % (note, n)
    s = s.replace(a, b, 1)


# ---------------------------------------------------------------- 1. pin the kanji
rep("""// The whole ladder, computed the same way every time - no randomness, so
// "Level 7" means the same thing for every player at the same tier.
// Kanji carries on from topic to topic rather than restarting, so each course
// starts where the one before it left off.
function kanjiOffset(courseId) {
  let n = 0;
  for (let i = 0; i < COURSE_ORDER.length; i++) {
    const id = COURSE_ORDER[i];
    if (id === courseId) break;
    n += Math.floor(baseLadderLength(id) / 4);
  }
  return n;
}""",
"""/* The whole ladder, computed the same way every time - no randomness, so
   "Level 7" means the same thing for every player.

   Which kanji group a topic starts on used to be derived by summing the ladder
   lengths of everything before it, which meant inserting a topic anywhere in
   the order silently changed the kanji taught by every topic after it - a
   child on a kanji rung would meet five characters they had never seen, and a
   passed level would un-pass. These are those same numbers, frozen, so the
   order of topics is now free to change. A new topic takes the next value.

   (The old sum ignored extraUnits, so hiragana runs seven kanji levels but
   only advanced the cursor four, and katakana re-teaches groups 4-6. Freezing
   keeps that quirk rather than fixing it: fixing it would move kanji levels
   that children have already passed.) */
const KANJI_START = {
  hiragana: 0, katakana: 4, kanamix: 8,
  numbers: 12, animals: 13, weekdays: 14, verbs: 14, nouns: 15,
  adjectives: 16, greetings: 17, n5: 18, grammar: 5
};

function kanjiOffset(courseId) {
  const at = KANJI_START[courseId];
  if (at !== undefined) return at;
  // A topic added later: carry on past the highest pinned start.
  let top = 0;
  Object.keys(KANJI_START).forEach(function (k) { if (KANJI_START[k] > top) top = KANJI_START[k]; });
  let n = top + 1;
  for (let i = 0; i < COURSE_ORDER.length; i++) {
    const id = COURSE_ORDER[i];
    if (id === courseId) break;
    if (KANJI_START[id] === undefined) n += Math.max(1, Math.floor(baseLadderLength(id) / 4));
  }
  return n % KANJI_GROUPS.length;
}""", "pin the kanji")

# ---------------------------------------------------------------- 2. derive the economy
rep("""function ladderFor(p) {
  const rows = allRows(p);
  const base = [];""",
"""/* What the whole game is worth, and what the map should therefore cost.

   Computed from the content rather than written down, because it was written
   down twice and went stale twice: add a topic and the map re-prices itself to
   keep the same shape - all 47 prefecture cards costing about 65% of what a
   perfect run pays, so they are hard but reachable without one, and gilding
   every sight staying out of reach of anything but obsession. */
const ECONOMY = (function () {
  let stars = 0;
  COURSE_ORDER.forEach(function (cid) {
    const stub = { course: cid };
    const n = ladderFor(stub).length;
    for (let i = 0; i < n; i++) stars += starPay(i);
  });
  const sets = CARD_SETS.reduce(function (n, st) { return n + setBonus(st); }, 0);
  const cards = Object.keys(CARD_HOME).reduce(function (n, k) { return n + cardValue(k); }, 0);
  const income = stars + sets + cards;
  // 55 is 1+2+...+10 - the shape of one prefecture's ten sights.
  const per = 55 * Math.max(1, PREFS.length);
  const unit = Math.max(50, Math.round(income * 0.65 / per / 10) * 10);
  return { stars: stars, sets: sets, cards: cards, income: income, unit: unit };
})();

function ladderFor(p) {
  const rows = allRows(p);
  const base = [];""", "economy")

rep("""/* $150 a step up a prefecture's list to build, half that to light and to
   gild. A prefecture costs $8,250 to build and $16,500 to finish, so a card
   is five or six levels' work - and all 47 come to $388,000 against the
   $540,000 a child earns by doing everything, which is the margin that makes
   it hard but not hopeless. */
function stagePrice(k, stage) { return (stage === 1 ? 150 : 75) * k; }""",
"""/* A step up a prefecture's list to build, half that to light and to gild. The
   unit is not written here: ECONOMY works it out from how much the game pays,
   so adding topics re-prices the map instead of leaving it behind. */
function stagePrice(k, stage) {
  return (stage === 1 ? ECONOMY.unit : ECONOMY.unit / 2) * k;
}""", "stage price")

io.open(f, "w", encoding="utf-8").write(s)
print("kanji pinned, economy derived")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])
