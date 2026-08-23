# -*- coding: utf-8 -*-
"""Numbers on one scale, and a map worth working for.

The three income streams had drifted onto different scales. A green star paid
1000 x the level number, which grows with the square of a topic's length - so
a late N5 level paid $43,000 while a card was worth $30 and a whole prefecture
cost $11,000. Money stopped meaning anything long before the end.

Everything is re-based so the four things a child does are comparable:

  a level's green star   $300 (level 1) rising to about $4,200
  a card                 $50 to $275, so a Card Room run is worth a fair slice
                         of a level
  a completed set        about a level's pay
  a sight to build       $150 x its place in the prefecture, $8,250 a
                         prefecture, half that again to gild it

Sized against a child who green-stars every level, collects every card once
and completes every set - about $540,000. Building all 470 sights, which is
what all 47 prefecture cards means, costs 72% of that: not trivial, and
reachable without a perfect run. Gilding all of Japan costs 144% of it, so it
stays out of reach of anything but obsession.
"""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note):
    global s
    n = s.count(a)
    assert n == 1, "expected 1 of (%s), found %d" % (note, n)
    s = s.replace(a, b, 1)


# ---------------------------------------------------------------- cards
rep("""const COURSE_CARD_VALUE = {
  hiragana: 10, katakana: 12, kanamix: 16, numbers: 18, animals: 22,
  weekdays: 22, verbs: 26, nouns: 26, adjectives: 30, greetings: 30,
  n5: 40, grammar: 55, kanji: 45
};""",
"""/* On the same scale as everything else: a common kana card is $50, a grammar
   sentence $275. A Card Room run of fifteen questions is then worth roughly a
   fifth of a level, which is about what a quarter of an hour should buy. */
const COURSE_CARD_VALUE = {
  hiragana: 50, katakana: 60, kanamix: 80, numbers: 90, animals: 110,
  weekdays: 110, verbs: 130, nouns: 130, adjectives: 150, greetings: 150,
  n5: 200, grammar: 275, kanji: 225
};""", "card values")

rep("""  v += Math.max(0, key.length - 1) * 5;          // longer items are harder
  if (home === "grammar") v += 10;               // whole sentences""",
"""  v += Math.max(0, key.length - 1) * 25;         // longer items are harder
  if (home === "grammar") v += 50;               // whole sentences""", "length bonus")

rep("""  return v >= 60 ? "legendary" : v >= 40 ? "epic" : v >= 24 ? "rare" : "common";""",
    """  return v >= 300 ? "legendary" : v >= 200 ? "epic" : v >= 120 ? "rare" : "common";""",
    "rarity thresholds")

rep("""  if (home === "pref") return 100;               // legendary, and only ever earned""",
    """  if (home === "pref") return 500;               // legendary, and only ever earned""",
    "prefecture card value")

# ---------------------------------------------------------------- levels
rep("""const STAR_PAY = 1000;
function starPay(idx) { return STAR_PAY * ((idx || 0) + 1); }""",
"""/* A level pays a flat $200 plus $100 a rung. Flat 1000-a-rung grew with the
   square of a topic's length, so finishing hiragana paid two thirds of a
   million and nothing after it mattered. This keeps a late level worth about
   fourteen times an early one rather than forty. */
const STAR_BASE = 200, STAR_STEP = 100;
function starPay(idx) { return STAR_BASE + STAR_STEP * ((idx || 0) + 1); }""", "star pay")

# ---------------------------------------------------------------- sets
rep("""function setBonus(set) {
  const v = set.keys.reduce(function (n, k) { return n + cardValue(k); }, 0);
  return Math.ceil(v * 10 / 100) * 100;
}""",
"""// A completed set is worth about what a level is: the cards over again.
function setBonus(set) {
  const v = set.keys.reduce(function (n, k) { return n + cardValue(k); }, 0);
  return Math.ceil(v / 100) * 100;
}""", "set bonus")

# ---------------------------------------------------------------- the map
rep("""function stagePrice(k, stage) { return (stage === 1 ? 450 : 225) * k; }""",
"""/* $150 a step up a prefecture's list to build, half that to light and to
   gild. A prefecture costs $8,250 to build and $16,500 to finish, so a card
   is five or six levels' work - and all 47 come to $388,000 against the
   $540,000 a child earns by doing everything, which is the margin that makes
   it hard but not hopeless. */
function stagePrice(k, stage) { return (stage === 1 ? 150 : 75) * k; }""", "stage prices")

# ---------------------------------------------------------------- tips
rep("""function tipPrice(lv) { return 100 * ((lv && lv.number) || 1); }""",
"""/* A tenth of what the level pays. The real price of a tip is the green star
   it forfeits - the whole level's money - so the cash on top is a token. */
function tipPrice(lv) {
  return Math.max(50, Math.round(starPay(((lv && lv.number) || 1) - 1) / 10 / 10) * 10);
}""", "tip price")

io.open(f, "w", encoding="utf-8").write(s)
print("economy re-based")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:500])
