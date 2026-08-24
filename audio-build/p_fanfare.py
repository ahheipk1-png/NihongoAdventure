# -*- coding: utf-8 -*-
"""Sounds that tell a child which thing just happened.

The game had four tones and used them for everything: the same little rise
meant "you won the round", "you drew a card" and "you finished a prefecture",
and three real achievements - a green star, a completed collection, an item
finally mastered - made no sound at all.

So: one sound per event, differing by shape rather than only pitch, because a
six-year-old across the room hears rhythm before they hear frequency.

  right      two notes up, bright and short
  wrong      one low note, gentle - being wrong twice in a row is not a punishment
  pass       a three-note major arpeggio, the moment the quota fills
  perfect    the green star: the arpeggio again, higher, with a sparkle on top
  card       a fast shimmer up four notes
  set        a warm held chord - a collection is a slower kind of win
  build      a low-to-high swell, something being raised
  mastered   a soft descending chime, quiet enough not to interrupt a round
  finished   a topic completed: six notes, the longest thing in the game

Also here, because it came out of the same review: on the homophones the study
sheet could miss a word the board was about to ask. keepFamilies deliberately
reaches past the level pool to fetch a word's relatives - that is what makes
橋/箸/端 a drill rather than a picture quiz - but the sheet only knew the pool,
so level 27 listed 上る 登る 昇る 早い 鳴く and then asked 泣く.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
MIRROR = r"C:\JapaneseLearning\index.html"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note, count=1):
        nonlocal s
        assert s.count(old) == count, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, count)

    # ---- 1. the sheet knows about the relatives the board can fetch ------
    rep("""function studyKeys(p, lv) {
  const own = (lv.kana || []).slice();
  const extra = levelPool(p).filter(function (k) { return own.indexOf(k) === -1; });
  return { own: own, extra: extra, all: own.concat(extra) };
}""",
        """function studyKeys(p, lv) {
  const own = (lv.kana || []).slice();
  const extra = levelPool(p).filter(function (k) { return own.indexOf(k) === -1; });

  /* keepFamilies deliberately reaches past the pool to fetch a word's
     relatives - that is what makes 橋 against 箸 and 端 a drill rather than a
     picture quiz - so the sheet has to know about them too, or it lists 町 and
     the board asks 街. Bounded: a family is three words at most. */
  const c = courseOf(p);
  if (c.homophone) {
    const confuse = c.confuse || {}, met = {};
    learnedKana(p).forEach(function (k) { met[k] = 1; });
    own.concat(extra).forEach(function (k) {
      (confuse[k] || []).forEach(function (rel) {
        if (met[rel] && own.indexOf(rel) === -1 && extra.indexOf(rel) === -1) extra.push(rel);
      });
    });
  }
  return { own: own, extra: extra, all: own.concat(extra) };
}""", "sheet knows the family")

    # ---- 2. the palette --------------------------------------------------
    rep("""    good:  function () { tone(587.33, 0, .13, "sine", .14); tone(880, .09, .22, "sine", .13); },
    bad:   function () { tone(196, 0, .2, "triangle", .1); },
    star:  function () { [523.25, 659.25, 783.99, 1046.5].forEach(function (f, i) { tone(f, i * .075, .22, "sine", .12); }); },
    done:  function () { [523.25, 659.25, 783.99].forEach(function (f, i) { tone(f, i * .1, .3, "sine", .13); }); }""",
        """    /* One sound per thing that can happen, told apart by shape more than by
       pitch: a child across the room hears the rhythm first. */
    good:  function () { tone(587.33, 0, .13, "sine", .16); tone(880, .09, .22, "sine", .15); },
    bad:   function () { tone(196, 0, .2, "triangle", .12); },

    // The quota fills: three notes up, and that is the round won.
    pass:  function () {
      [523.25, 659.25, 783.99].forEach(function (f, i) { tone(f, i * .08, .26, "sine", .15); });
    },
    // A green star. The same shape an octave up, with a sparkle over the top,
    // because flawless is the rarest thing a level can be.
    perfect: function () {
      [523.25, 659.25, 783.99, 1046.5].forEach(function (f, i) { tone(f, i * .085, .3, "sine", .15); });
      tone(1318.51, .36, .5, "sine", .1);
      tone(1567.98, .44, .55, "sine", .07);
    },
    // A card out of the wheel: a fast shimmer, over before it is thought about.
    card:  function () {
      [880, 1108.73, 1318.51, 1760].forEach(function (f, i) { tone(f, i * .05, .2, "triangle", .09); });
    },
    // A set completed. A collection is a slower kind of win, so: a held chord.
    set:   function () {
      [261.63, 329.63, 392, 523.25].forEach(function (f, i) { tone(f, i * .03, .55, "sine", .1); });
      tone(1046.5, .18, .5, "sine", .07);
    },
    // Something raised on the map: low to high, like a thing going up.
    build: function () { tone(196, 0, .18, "triangle", .12); tone(392, .1, .32, "sine", .13); },
    // An item reaching the top box mid-round. Quiet on purpose - it must not
    // sound like the answer was wrong, and it must not stop the round.
    mastered: function () { tone(1046.5, 0, .16, "sine", .08); tone(783.99, .1, .26, "sine", .07); },
    // A whole topic finished: the longest sound in the game, and the rarest.
    finished: function () {
      [523.25, 659.25, 783.99, 1046.5, 1318.51, 1567.98].forEach(function (f, i) {
        tone(f, i * .09, .38, "sine", .14);
      });
    },

    // Older names, kept so nothing that still calls them falls silent.
    star:  function () { this.pass(); },
    done:  function () { [523.25, 659.25, 783.99].forEach(function (f, i) { tone(f, i * .1, .3, "sine", .12); }); }""",
        "palette")

    # ---- 3. the quota filling is a pass, not a star ----------------------
    s = s.replace("if (powerGain(p)) { audio.star();", "if (powerGain(p)) { audio.pass();")
    s = s.replace("if (filled) { audio.star(); finish(p); return; }",
                  "if (filled) { audio.pass(); finish(p); return; }")
    s = s.replace("if (filled) { audio.star(); setTimeout(function () { finish(p); }, 620); return; }",
                  "if (filled) { audio.pass(); setTimeout(function () { finish(p); }, 620); return; }")

    # ---- 4. the green star gets its own fanfare on the result screen -----
    rep("""  if (s.levelUp) audio.star();""",
        """  /* The round already chimed when the quota filled, so this is only for the
     thing that has not been heard yet: a green star, first time. */
  if (s.perfectNew) audio.perfect();
  else if (s.levelUp) audio.pass();""", "result fanfare")

    # ---- 5. a card, and a set, sound like themselves ---------------------
    rep("""  renderTopbar();          // the badges are about to be read against the prize
  audio.star();""",
        """  renderTopbar();          // the badges are about to be read against the prize
  // A completed collection is the bigger news of the two.
  if (room.prize.sets && room.prize.sets.length) audio.set(); else audio.card();""", "draw sound")

    # ---- 6. the map: a place raised, a prefecture completed --------------
    rep("""        audio.star();""", """        audio.card();""", "prefecture card")
    rep("""      } else {
        audio.good();
        mapToast = { pref: sg.pref, card: false,""",
        """      } else {
        audio.build();
        mapToast = { pref: sg.pref, card: false,""", "building raised")

    # ---- 7. an item reaching the top box, and a topic finished ----------
    rep("""function bump(p, k, right) {
  const rec = boxRec(p, k);
  const now = Date.now();
  let b = rec.b;""",
        """function bump(p, k, right) {
  const rec = boxRec(p, k);
  const now = Date.now();
  const was = rec.b;
  let b = rec.b;""", "bump was")

    rep("""  prog(p).boxes[k] = { b: b, t: now };
}""",
        """  prog(p).boxes[k] = { b: b, t: now };
  // Mastery happens mid-round, so it gets its own quiet chime rather than the
  // round's - and it is the only place in the game that sound is heard.
  if (b >= MASTERED && was < MASTERED) audio.mastered();
}""", "mastered chime")

    rep("""    if (!prog(p).done) prog(p).done = true;""",
        """    if (!prog(p).done) { prog(p).done = true; audio.finished(); }""", "topic finished")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])


if __name__ == "__main__":
    main()
