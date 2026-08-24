# -*- coding: utf-8 -*-
"""Make "What this level asks" tell the truth.

A board is not just the level's own items. boardPool tops it up with up to two
overdue items pulled from everything learned - that is the spacing, and it is
deliberate - and pads with older material when the level is short. The study
sheet only ever listed the level's own items, so the board could ask two or
three things the Learn button never showed. On a reading game a child can still
work it out from the character in front of them; on a listening level they get
a voice saying a word they were never taught, which is where this was noticed.

So the sheet now shows the whole board: the level's own items first, then what
is arriving again for revision, under its own heading so the two are not
confused. Play-through walks all of it.

For the sheet and the board to agree they have to be the same list, and
boardPool is not deterministic - it picks at random and asks what is due right
now. It is therefore drawn once per player per level and remembered, so opening
the sheet, failing the level and trying again all show the board that is
actually coming. Advancing a level, or switching topic, draws a new one.

One extra guard: on a listening level the extras have to be sayable too. An
overdue item with no clip was previously able to arrive on a board where the
only question is what you can hear.
"""
import io, re, shutil, subprocess

GAME  = r"C:\JapaneseLearning\kana-quest.html"
INDEX = r"C:\JapaneseLearning\index.html"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- 1. the extras must be audible on a listening level -------------
    rep("""  const asks = function (k) { return !shared[k] && tellsApart(p, k, forms); };""",
        """  const asks = function (k) { return !shared[k] && tellsApart(p, k, forms); };
  /* A listening board's only question is what you can hear, so anything it
     borrows from earlier has to have a voice. The level's own items were
     already checked by gameFitsLevel; the borrowed ones never were. */
  const audible = info.game === "listen"
    ? function (k) { return speech.can(k); }
    : function () { return true; };""", "audible")

    rep("""  const overdue = learnedKana(p).filter(function (k) {
    return kana.indexOf(k) === -1 && box(p, k) > 0 && isDue(p, k, now) && asks(k);
  });""",
        """  const overdue = learnedKana(p).filter(function (k) {
    return kana.indexOf(k) === -1 && box(p, k) > 0 && isDue(p, k, now) && asks(k) && audible(k);
  });""", "overdue audible")

    rep("""    const older = learnedKana(p).filter(function (k) {
      return kana.indexOf(k) === -1 && asks(k);
    });""",
        """    const older = learnedKana(p).filter(function (k) {
      return kana.indexOf(k) === -1 && asks(k) && audible(k);
    });""", "older audible")

    # ---- 2. one pool, drawn once, shared by the sheet and the board -----
    rep("""/* Rebuild a board so relatives travel together.""",
        """/* The sheet and the board have to be looking at the same list, and boardPool
   is not deterministic: it picks at random and asks what is due at this
   moment. Drawn once per player per level and kept, so studying, failing and
   retrying all show the board that is really coming. The key carries the topic
   as well as the level number - level 3 of hiragana is not level 3 of verbs. */
let poolMemo = null;

function levelPool(p) {
  const key = [p && p.id, p && p.course, prog(p).level || 0].join("|");
  if (poolMemo && poolMemo.key === key) return poolMemo.pool.slice();
  poolMemo = { key: key, pool: boardPool(p).slice() };
  return poolMemo.pool.slice();
}

/* What the sheet shows: the level's own items, then whatever the board is
   borrowing back from earlier. Split rather than merged - "here is the new
   material" and "here is what is coming round again" are different promises. */
function studyKeys(p, lv) {
  const own = (lv.kana || []).slice();
  const extra = levelPool(p).filter(function (k) { return own.indexOf(k) === -1; });
  return { own: own, extra: extra, all: own.concat(extra) };
}

function studySheetHTML(p, lv) {
  const keys = studyKeys(p, lv);
  let out = '<div class="study-list">' + studyRowsHTML(p, lv, keys.own) + '</div>';
  if (keys.extra.length) {
    out += '<div class="study-again">Also on this board \\u2014 met before, due for another look</div>' +
           '<div class="study-list">' + studyRowsHTML(p, lv, keys.extra) + '</div>';
  }
  return out;
}

/* Rebuild a board so relatives travel together.""", "levelPool")

    # ---- 3. the board draws from the remembered pool --------------------
    rep("""  const full = boardPool(p);""",
        """  const full = levelPool(p);""", "startSession pool")

    # ---- 4. the sheet can be handed an explicit list --------------------
    rep("""function studyRowsHTML(p, lvIn) {
  const lv = lvIn || levelInfo(p);""",
        """function studyRowsHTML(p, lvIn, keysIn) {
  const lv = lvIn || levelInfo(p);""", "studyRowsHTML signature")

    rep("""  return lv.kana.map(function (key) {
    const it = itemOf(p, key);""",
        """  return (keysIn || lv.kana).map(function (key) {
    const it = itemOf(p, key);""", "studyRowsHTML keys")

    # ---- 5. both sheets show the whole board ----------------------------
    rep("""      studyStageHTML() +
      '<div class="study-list">' + studyRowsHTML(p, lv) + '</div>' +
      '<p style="font-size:13px;text-align:center">Take your time — then the level starts over from the top.</p>' +""",
        """      studyStageHTML() +
      studySheetHTML(p, lv) +
      '<p style="font-size:13px;text-align:center">Take your time — then the level starts over from the top.</p>' +""",
        "overlay sheet")

    rep("""  const cfg = tierOf(p).power;
  const rows = studyRowsHTML(p);
  const gameIcon = game.icon || "🎮";""",
        """  const cfg = tierOf(p).power;
  const gameIcon = game.icon || "🎮";""", "renderStudy rows var")

    rep("""        studyStageHTML() +
        '<div class="study-list">' + rows + '</div>' +
      '</div>' +""",
        """        studyStageHTML() +
        studySheetHTML(p, lv) +
      '</div>' +""", "renderStudy sheet")

    # ---- 6. play-through walks the whole board --------------------------
    rep("""  const items = (lv.kana || []).slice();""",
        """  const items = studyKeys(p, lv).all;""", "play-through items")

    # ---- 7. the heading looks like a heading ----------------------------
    rep(""".purse.sound, .purse.vol { font-size: 15px; padding: 6px 10px; }""",
        """.purse.sound, .purse.vol { font-size: 15px; padding: 6px 10px; }
.study-again { margin: 14px 0 6px; font-size: 12px; letter-spacing: .04em;
               text-transform: uppercase; opacity: .65; text-align: center; }""", "study-again css")

    io.open(GAME, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    if r.returncode != 0:
        print("syntax:", r.stderr[:800])
        return
    print("syntax: OK")
    shutil.copyfile(GAME, INDEX)
    print("index.html updated")


if __name__ == "__main__":
    main()
