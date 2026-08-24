# -*- coding: utf-8 -*-
"""Teach the words Word Building asks for, and put the boost back.

TWO THINGS.

1. "It asked あか, but the Learn button never taught it."

   On a kana topic, Word Building shows a picture and an English word and asks
   the child to assemble あか out of tiles. The study sheet for that level lists
   the level's ten kana - あ い う え お か き く け こ - and nothing else.
   Nowhere in the game is a child ever told that "red" is あか. There is no
   audio prompt either, so there is nothing to spell from: only a guess.

   Measured on hiragana level 3, the sheet showed the ten kana while the game
   asked for うえ, こえ, きく, かお and あお.

   The sheet now shows the words themselves - the word, its meaning, its
   picture, a speaker where there is a clip, and the very tiles the child will
   be handed. For that to be honest the sheet and the game have to name the
   same five words, so the choice is made once by wordsForLevel() and
   remembered, exactly the way the board pool already is.

   Vocabulary topics are untouched: there the word IS the item, so it was
   always on the sheet.

2. The pronunciation boost, restored on top of the volume pill.

   An <audio> element cannot be turned past 1.0 and these clips are quiet, so
   +20% needs a gain node. The pill's three steps now scale that gain rather
   than the element, and the element's own volume goes back to 1 - otherwise
   the two multiply and the loud step is capped at exactly the level the boost
   exists to get past.
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

    # ---- 1. one list of words, drawn once ------------------------------
    rep("""function setupWord(p) {
  const learned = learnedKana(p);
  const count = rowsIntroduced(p);
  const LIST = courseOf(p).words || [];
  const isVocab = courseOf(p).kind !== "kana";
""",
        """/* The five words this level will ask, decided once.

   The study sheet has to promise the same five the game then asks, and the
   choice involves a shuffle - so it is made once per player per level and
   remembered, the way levelPool already remembers the board. Advancing a
   level, or changing topic, draws a new five. */
let wordMemo = null;

function wordsForLevel(p) {
  const key = [p && p.id, p && p.course, prog(p).level || 0].join("|");
  if (wordMemo && wordMemo.key === key) return wordMemo.words.slice();

  const learned = learnedKana(p);
  const count = rowsIntroduced(p);
  const LIST = courseOf(p).words || [];
  const isVocab = courseOf(p).kind !== "kana";

  // On a kana course a word is playable once every character in it is known.
  // On a vocabulary course the word itself is the item, so ask about the word.
  let usable = LIST.filter(function (x) {
    if (x.row >= count) return false;
    return isVocab
      ? learned.indexOf(x.w) !== -1
      : x.w.split("").every(function (k) { return learned.indexOf(k) !== -1; });
  });
  if (!usable.length) {
    // Nothing is fully spellable yet - prefer the words needing the fewest
    // characters the player has not met, rather than the first five in the list.
    usable = LIST.slice().sort(function (a, b) {
      function miss(x) {
        return x.w.split("").filter(function (ch) { return learned.indexOf(ch) === -1; }).length;
      }
      return miss(a) - miss(b);
    }).slice(0, 5);
  }

  /* Favour words that exercise the board this level is built on. The board
     pool rather than the round's own five: the five are drawn when the round
     starts, and the sheet has to be able to say all this beforehand. */
  const weak = levelPool(p);
  function relevance(x) {
    return isVocab
      ? (weak.indexOf(x.w) !== -1 ? 1 : 0)
      : x.w.split("").filter(function (k) { return weak.indexOf(k) !== -1; }).length;
  }
  const ranked = shuffle(usable).sort(function (a, b) { return relevance(b) - relevance(a); });
  const words = ranked.slice(0, Math.min(5, ranked.length));
  wordMemo = { key: key, words: words };
  return words.slice();
}

function setupWord(p) {
""", "wordsForLevel")

    # the old body of setupWord goes; it now just takes the memoised list
    rep("""  // On a kana course a word is playable once every character in it is known.
  // On a vocabulary course the word itself is the item, so ask about the word.
  let usable = LIST.filter(function (x) {
    if (x.row >= count) return false;
    return isVocab
      ? learned.indexOf(x.w) !== -1
      : x.w.split("").every(function (k) { return learned.indexOf(k) !== -1; });
  });
  if (!usable.length) {
    // Nothing is fully spellable yet - prefer the words needing the fewest
    // characters the player has not met, rather than the first five in the list.
    usable = LIST.slice().sort(function (a, b) {
      function miss(x) {
        return x.w.split("").filter(function (ch) { return learned.indexOf(ch) === -1; }).length;
      }
      return miss(a) - miss(b);
    }).slice(0, 5);
  }

  // Favour words that exercise this board's weak five.
  const weak = session.pool;
  function relevance(x) {
    return isVocab
      ? (weak.indexOf(x.w) !== -1 ? 1 : 0)
      : x.w.split("").filter(function (k) { return weak.indexOf(k) !== -1; }).length;
  }
  const ranked = shuffle(usable).sort(function (a, b) { return relevance(b) - relevance(a); });

  session.words = ranked.slice(0, Math.min(5, ranked.length));
  session.wi = 0;""",
        """  session.words = wordsForLevel(p);
  session.wi = 0;""", "setupWord body")

    # ---- 2. the sheet teaches them --------------------------------------
    rep("""function studySheetHTML(p, lv) {
  const keys = studyKeys(p, lv);
  let out = '<div class="study-list">' + studyRowsHTML(p, lv, keys.own) + '</div>';
  if (keys.extra.length) {
    out += '<div class="study-again">Also on this board \\u2014 met before, due for another look</div>' +
           '<div class="study-list">' + studyRowsHTML(p, lv, keys.extra) + '</div>';
  }
  return out;
}""",
        """/* A word on a kana topic is not one of the topic's items - the items are
   letters, and the word is made of them - so nothing on the sheet ever named
   it. That is how a child could be asked to spell あか having been taught あ
   and か and never once told that あか means red. */
function studyWordsHTML(p, words) {
  return words.map(function (x) {
    const tiles = x.w.split("").map(function (ch) {
      return '<span class="spell-tile">' + esc(ch) + '</span>';
    }).join('<span class="spell-plus" aria-hidden="true">+</span>');
    return '<div class="study-row spell">' +
             '<div class="spell-head">' +
               (picFor(x.w) ? picImg(x.w, "study-img")
                 : x.pic ? '<span class="study-pic" aria-hidden="true">' + x.pic + '</span>' : '') +
               '<div class="spell-meta">' +
                 '<span class="study-part kana">' + esc(x.w) + '</span>' +
                 '<span class="study-en-inline">' + esc(x.en) + '</span>' +
               '</div>' + speakerBtn(p, x.w, null) +
             '</div>' +
             '<div class="spell-row">' + tiles + '</div>' +
           '</div>';
  }).join("");
}

function studySheetHTML(p, lv) {
  const keys = studyKeys(p, lv);
  let out = '<div class="study-list">' + studyRowsHTML(p, lv, keys.own) + '</div>';
  if (keys.extra.length) {
    out += '<div class="study-again">Also on this board \\u2014 met before, due for another look</div>' +
           '<div class="study-list">' + studyRowsHTML(p, lv, keys.extra) + '</div>';
  }
  // On a vocabulary topic the words are the items and are already above.
  if (lv.game === "word" && courseOf(p).kind === "kana") {
    const words = wordsForLevel(p);
    if (words.length) {
      out += '<div class="study-again">The words you will build \\u2014 the letters you know, ' +
             'put together</div>' +
             '<div class="study-list">' + studyWordsHTML(p, words) + '</div>';
    }
  }
  return out;
}""", "studyWordsHTML")

    # ---- 3. the boost, scaled by the pill --------------------------------
    rep("""          if (!el) { el = new Audio(); el.preload = "auto"; }
          // Set every time: the pill can move between one word and the next.
          el.volume = volLevel();
          el.pause(); el.src = src; el.currentTime = 0;""",
        """          if (!el) { el = new Audio(); el.preload = "auto"; }
          louder();
          el.pause(); el.src = src; el.currentTime = 0;""", "louder call")

    rep("""  function clip(key) { return (window.AUDIO && window.AUDIO[key]) || null; }
""",
        """  function clip(key) { return (window.AUDIO && window.AUDIO[key]) || null; }

  /* An <audio> element stops at 1.0, and these clips are quiet - 32 kbps mono
     out of a system voice, recorded well below full scale - so the way to make
     the Japanese louder than it was recorded is a gain node in front of it.

     The pill's three steps scale that gain rather than the element, because
     doing both would multiply: el.volume would cap the loud step at exactly
     the level the boost exists to get past. Wired once, and only when there is
     a running context to wire into - an element connected to a context that
     never resumes makes no sound at all, which is worse than a quiet one. */
  const SAY_BOOST = 1.2;
  let amp = null, wired = false;

  function louder() {
    const ctx = audio.context();
    if (!ctx) return;
    if (ctx.state === "suspended") { try { ctx.resume(); } catch (e) { /* no-op */ } }
    if (!wired && ctx.state === "running") {
      wired = true;
      try {
        const node = ctx.createMediaElementSource(el);
        amp = ctx.createGain();
        node.connect(amp).connect(ctx.destination);
      } catch (e) { amp = null; }
    }
    // Set every time: the pill can move between one word and the next.
    if (amp) { amp.gain.value = SAY_BOOST * volLevel(); el.volume = 1; }
    else el.volume = volLevel();
  }
""", "louder")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)   # index.html is the tracked copy

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])


if __name__ == "__main__":
    main()
