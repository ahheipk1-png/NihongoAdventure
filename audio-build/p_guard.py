# -*- coding: utf-8 -*-
"""Guessing should not pass a level.

Measured before this: a child tapping at random passed EVERY Sprout game 100%
of the time, even at a deliberate two seconds a tap, and Word Building fell to
random tapping 56% of the time on Explorer. Tapping fast beat tapping slowly
everywhere, because a wrong answer cost a fixed penalty while the clock ran in
seconds - so spamming was the winning strategy.

Four rules, applied to every game:
  1. every answer costs a little power, right or wrong, so speed cannot be farmed
  2. two tries at a question, then the answer is shown and it is lost
  3. a question got wrong never advances the quota, in any game
  4. Word Building scores the word, not the letter
"""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note, count=1):
    global s
    n = s.count(a)
    assert n == count, "expected %d of (%s), found %d" % (count, note, n)
    s = s.replace(a, b, count)


# ---------------------------------------------------------------- 1. every answer costs
rep("""function powerInit(p, mode) {
  const base = tierOf(p).power;
  session.cfg = {
    quota: base.quota,
    drain: base.drain * (DRAIN_RATE[mode] || 0.75) * paceOf(p),
    refill: base.refill,
    penalty: base.penalty
  };""",
"""/* Every answer costs a little power, right or wrong. Without it the clock runs
   in seconds while a wrong answer costs a flat penalty, so the cheapest way
   through a level is to tap as fast as possible - measured, tapping every 0.7s
   beat tapping every 2s in every game. Charging the answer rather than only
   the second makes guessing cost something no matter how fast it is done. */
const ANSWER_COST = 3;

function powerInit(p, mode) {
  const base = tierOf(p).power;
  session.cfg = {
    quota: base.quota,
    drain: base.drain * (DRAIN_RATE[mode] || 0.75) * paceOf(p),
    refill: base.refill,
    penalty: base.penalty,
    cost: ANSWER_COST
  };""", "answer cost config")

rep("""function powerGain(p) {
  session.power = Math.min(100, session.power + session.cfg.refill);
  session.score += 1;""",
"""// `n` scores more than one - Word Building completes a whole word at once.
function powerGain(p, n) {
  session.power = Math.min(100, session.power + session.cfg.refill - session.cfg.cost);
  session.score += (n || 1);""", "powerGain cost")

rep("""function powerLose(p) {
  session.wrongs += 1;
  session.wrongHere = true;
  session.power = Math.max(0, session.power - session.cfg.penalty);""",
"""function powerLose(p) {
  session.wrongs += 1;
  session.wrongHere = true;
  session.power = Math.max(0, session.power - session.cfg.penalty - session.cfg.cost);""",
    "powerLose cost")

# a refill that is not a scored answer still pays the cost of the tap
rep("""      session.power = Math.min(100, session.power + session.cfg.refill / 2);""",
"""      session.power = Math.min(100, session.power + session.cfg.refill / 2 - session.cfg.cost);""",
    "half refill cost")

# ---------------------------------------------------------------- 2. two tries, then it is lost
rep("""    firstTry: 0, wrongs: 0, wrongHere: false, tips: 0, tipHere: false,""",
    """    firstTry: 0, wrongs: 0, wrongHere: false, tips: 0, tipHere: false, triesHere: 0,""",
    "tries counter")

rep("""  session.answeredWrongHere = false;
  session.tipHere = false;""",
"""  session.answeredWrongHere = false;
  session.triesHere = 0;
  session.tipHere = false;""", "match resets tries")

rep("""  if (!session.answeredWrongHere) { credit(p, q.answer, false); powerLose(p); session.answeredWrongHere = true; }

  if (t.retry) {                     // Sprout keeps trying so they end on a win
    if (btn) { btn.classList.add("wrong", "dim"); btn.disabled = true; }
    return;
  }""",
"""  session.triesHere = (session.triesHere || 0) + 1;
  if (!session.answeredWrongHere) { credit(p, q.answer, false); session.answeredWrongHere = true; }
  powerLose(p);                      // every wrong answer costs, not just the first

  /* Sprout gets a second try rather than an unlimited one. Unlimited retries
     with no penalty meant a child tapping at random passed every level -
     measured at 100%, even tapping slowly. Two tries still means a wrong
     answer is not the end of the question; it just is not free. */
  if (t.retry && session.triesHere < 2) {
    if (btn) { btn.classList.add("wrong", "dim"); btn.disabled = true; }
    return;
  }""", "two tries on match")

# ---------------------------------------------------------------- 3. a missed question never scores
# fruit: the fruit itself remembers
rep("""    if (it.kana === want) {
      audio.good();
      if (speech.can(it.kana)) speech.say(it.kana);
      it.placed = true;
      session.boardMatched += 1;
      credit(p, it.kana, true);
      if (powerGain(p)) { audio.star(); renderFruit(p); setTimeout(function () { finish(p); }, 420); return; }""",
"""    if (it.kana === want) {
      audio.good();
      if (speech.can(it.kana)) speech.say(it.kana);
      it.placed = true;
      session.boardMatched += 1;
      credit(p, it.kana, true);
      // A fruit that was already dropped in the wrong bag still goes home, but
      // it does not move the quota - the question was got wrong.
      if (it.missed) {
        session.power = Math.min(100, session.power + session.cfg.refill / 2 - session.cfg.cost);
        drawPower();
        if (session.boardMatched >= session.boardPairs) { audio.done(); refreshPool(p); setupFruit(p); }
        renderFruit(p);
        return;
      }
      if (powerGain(p)) { audio.star(); renderFruit(p); setTimeout(function () { finish(p); }, 420); return; }""",
    "fruit no score after a miss")

rep("""    } else {
      audio.bad();
      credit(p, it.kana, false);
      powerLose(p);
      fruitEl.classList.add("nope");""",
"""    } else {
      audio.bad();
      if (!it.missed) credit(p, it.kana, false);
      it.missed = true;
      powerLose(p);
      fruitEl.classList.add("nope");""", "fruit marks the miss")

# pairs: the pair remembers
rep("""  if (a.kana === b.kana && a.kind !== b.kind) {
    audio.good();
    if (speech.can(a.kana)) speech.say(a.kana);
    a.done = true; b.done = true;
    session.boardMatched += 1;
    credit(p, a.kana, true);
    const filled = powerGain(p);""",
"""  if (a.kana === b.kana && a.kind !== b.kind) {
    audio.good();
    if (speech.can(a.kana)) speech.say(a.kana);
    a.done = true; b.done = true;
    session.boardMatched += 1;
    credit(p, a.kana, true);
    // Found after a wrong guess: the pair still clears, but it does not count
    // towards the quota - otherwise turning cards at random fills it.
    const wasMissed = !!(session.missedPairs && session.missedPairs[a.kana]);
    if (wasMissed) session.power = Math.min(100, session.power + session.cfg.refill / 2 - session.cfg.cost);
    const filled = wasMissed ? false : powerGain(p);""", "pairs no score after a miss")

rep("""    const tested = a.open ? b : a;      // the hidden card is the one being identified
    credit(p, tested.kana, false);
    powerLose(p);""",
"""    const tested = a.open ? b : a;      // the hidden card is the one being identified
    credit(p, tested.kana, false);
    if (!session.missedPairs) session.missedPairs = {};
    session.missedPairs[a.kana] = true;
    session.missedPairs[b.kana] = true;
    powerLose(p);""", "pairs marks the miss")

rep("""  session.boardMatched = 0;
  session.boardPairs = session.pool.length;
  session.boards += 1;
  session.tipHere = false;
}""",
"""  session.boardMatched = 0;
  session.boardPairs = session.pool.length;
  session.boards += 1;
  session.tipHere = false;
  session.missedPairs = {};
}""", "pairs resets misses")

# fish: missedTarget already exists
rep("""    if (f.kana === session.target) {
      audio.good();
      if (speech.can(f.kana)) speech.say(f.kana);
      f.el.classList.add("caught");
      credit(p, f.kana, true);
      setTimeout(function () { if (f.el.parentNode) f.el.parentNode.removeChild(f.el); }, 340);
      if (powerGain(p)) { audio.star(); finish(p); return; }
      newTarget();
      return;""",
"""    if (f.kana === session.target) {
      audio.good();
      if (speech.can(f.kana)) speech.say(f.kana);
      f.el.classList.add("caught");
      credit(p, f.kana, true);
      setTimeout(function () { if (f.el.parentNode) f.el.parentNode.removeChild(f.el); }, 340);
      // Caught after grabbing the wrong fish: it counts as caught, not as a
      // point, so tapping every fish in the pond gets nowhere.
      if (session.missedTarget) {
        session.power = Math.min(100, session.power + session.cfg.refill / 2 - session.cfg.cost);
        drawPower();
        newTarget();
        return;
      }
      if (powerGain(p)) { audio.star(); finish(p); return; }
      newTarget();
      return;""", "fish no score after a miss")

# ---------------------------------------------------------------- 4. Word Building scores the word
rep("""    const items = courseOf(p).items;
    if (items[t.k]) credit(p, t.k, true); else scoreOnly(p);
    const filled = powerGain(p);
    const solved = session.filled.indexOf(null) === -1;
    if (solved && !items[t.k] && items[entry.w]) credit(p, entry.w, true);""",
"""    const items = courseOf(p).items;
    if (items[t.k]) credit(p, t.k, true); else scoreOnly(p);
    /* A letter tops the power up but does not score. Scoring per letter made a
       four-letter word worth four questions, which is why random tile-dropping
       passed this game 56% of the time on Explorer while every other game held
       under 25%. The word is the question; it is worth two. */
    const solved = session.filled.indexOf(null) === -1;
    let filled = false;
    if (solved && !session.wordMissed) {
      filled = powerGain(p, 2);
    } else {
      session.power = Math.min(100, session.power + session.cfg.refill / 2 - session.cfg.cost);
      drawPower();
    }
    if (solved && !items[t.k] && items[entry.w]) credit(p, entry.w, true);""",
    "word scores the word")

rep("""  } else {
    session.streak = 0;
  }
  powerLose(p);
  const tileEl = screenEl.querySelector('[data-t="' + ti + '"]');""",
"""  } else {
    session.streak = 0;
  }
  session.wordMissed = true;        // this word will not score, however it ends
  powerLose(p);
  const tileEl = screenEl.querySelector('[data-t="' + ti + '"]');""",
    "word marks the miss")

rep("""  session.filled = letters.map(function () { return null; });
  session.tipHere = false;""",
"""  session.filled = letters.map(function () { return null; });
  session.tipHere = false;
  session.wordMissed = false;""", "word resets the miss")

# ---------------------------------------------------------------- the reward runs
rep("""  const runId = room.id;
  const strict = room.kind === "room";""",
"""  const runId = room.id;
  // Two tries at a question in both runs; only the paid room strikes you out.
  const strict = true;
  const strikesOut = room.kind === "room";""", "draw gets two tries")

rep("""      if (!strict || q.wrongs < ROOM_TRIES) {
        if (strict) {""",
"""      if (q.wrongs < ROOM_TRIES) {
        if (strict) {""", "two tries in both runs")

rep("""      q.answered = true;
      room.marks.push("miss");
      room.strikes += 1;""",
"""      q.answered = true;
      room.marks.push("miss");
      if (strikesOut) room.strikes += 1;""", "strikes only in the room")

rep("""        if (room.strikes >= ROOM_STRIKES) room.over = true;""",
"""        if (strikesOut && room.strikes >= ROOM_STRIKES) room.over = true;""",
    "only the room can blow up")

io.open(f, "w", encoding="utf-8").write(s)
print("anti-guessing policy applied")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
