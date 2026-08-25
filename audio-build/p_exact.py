# -*- coding: utf-8 -*-
"""The Learn sheet shows exactly what the level asks - no more, no less.

A Word Building level asks the child to spell five words. The sheet was showing
those five words AND the ten individual letters they are built from - so a level
that asks いえ / あお / いけ / きく / こえ had a Learn button listing あ い う え
お か き く け こ on top. The letters are not asked there; you spell words, you
do not pick single kana. The sheet now shows the five words and only the five
words, each with its meaning, its picture and the tiles it is made of - the same
five the game will ask, drawn from the same wordsForLevel() so they cannot drift
apart.

The Play-through walked the ten letters for the same reason; it now walks the
five words, and the slide for a word finds its meaning and picture in the course
word list rather than in the item table, where a word does not live.
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

    # ---- the sheet: only the words on a word level ----------------------
    rep("""function studySheetHTML(p, lv) {
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
}""",
        """/* The list of things this level actually asks about, and nothing else.

   On a Word Building level the questions are whole words, so the sheet is those
   words - not the letters they are spelled from, which are never asked there.
   Everywhere else the questions are the board's own items plus whatever it is
   borrowing back for review. */
function studyItems(p, lv) {
  if (lv.game === "word" && courseOf(p).kind === "kana") {
    return wordsForLevel(p).map(function (x) { return x.w; });
  }
  return studyKeys(p, lv).all;
}

function studySheetHTML(p, lv) {
  // Word Building asks for the words themselves, so the sheet is exactly those
  // words - the same five the game will ask, no letters listed on top of them.
  if (lv.game === "word" && courseOf(p).kind === "kana") {
    const words = wordsForLevel(p);
    if (words.length) return '<div class="study-list">' + studyWordsHTML(p, words) + '</div>';
  }
  const keys = studyKeys(p, lv);
  let out = '<div class="study-list">' + studyRowsHTML(p, lv, keys.own) + '</div>';
  if (keys.extra.length) {
    out += '<div class="study-again">Also on this board \\u2014 met before, due for another look</div>' +
           '<div class="study-list">' + studyRowsHTML(p, lv, keys.extra) + '</div>';
  }
  return out;
}""", "studySheetHTML exact")

    # ---- the play-through walks the same list ---------------------------
    rep("""  const items = studyKeys(p, lv).all;
  studyPlayer.paused = false;""",
        """  const items = studyItems(p, lv);
  studyPlayer.paused = false;""", "play-through items")

    # ---- a word slide finds its meaning and picture in the word list ----
    rep("""  } else if (lv.game === "word") {
    body = '<div class="slide-jp" lang="ja">' + esc(key) + '</div>' +
           '<div class="spell-row">' + key.split("").map(function (ch) {
             return '<span class="spell-tile">' + esc(ch) + '</span>';
           }).join('<span class="spell-plus" aria-hidden="true">+</span>') + '</div>' +
           '<div class="slide-en">' + esc(showForm(p, key, forms[forms.length - 1])) + '</div>';
  }""",
        """  } else if (lv.game === "word") {
    // A word is not an item of a kana course, so its meaning lives in the word
    // list, not in itemOf(); fall back to that before the raw key.
    const w = (c.words || []).filter(function (x) { return x.w === key; })[0] || {};
    const mean = w.en || showForm(p, key, forms[forms.length - 1]);
    body = '<div class="slide-jp" lang="ja">' + esc(key) + '</div>' +
           '<div class="spell-row">' + key.split("").map(function (ch) {
             return '<span class="spell-tile">' + esc(ch) + '</span>';
           }).join('<span class="spell-plus" aria-hidden="true">+</span>') + '</div>' +
           '<div class="slide-en">' + esc(mean) + '</div>';
  }""", "word slide meaning")

    # the word slide's picture: emoji from the word list when there is no photo
    rep("""  const pic = picFor(key) ? picImg(key, "slide-img")
            : (it.pic && !isGrammar ? '<span class="slide-pic" aria-hidden="true">' + it.pic + '</span>' : '');""",
        """  const wpic = (lv.game === "word"
    ? ((c.words || []).filter(function (x) { return x.w === key; })[0] || {}).pic
    : null);
  const pic = picFor(key) ? picImg(key, "slide-img")
            : (wpic ? '<span class="slide-pic" aria-hidden="true">' + wpic + '</span>'
            : (it.pic && !isGrammar ? '<span class="slide-pic" aria-hidden="true">' + it.pic + '</span>' : ''));""",
        "word slide picture")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])


if __name__ == "__main__":
    main()
