# -*- coding: utf-8 -*-
"""同音異義語 - words that sound the same and mean different things.

The point of the topic is discrimination, so the wrong answers are not random:
they are the other members of the family. Asked what 橋 means, the child is
offered bridge, chopsticks and edge - all はし - and the only thing that tells
them apart is the character. The game already has a mechanism for exactly this
(`courseOf(p).confuse`, "the pairs learners actually mix up"), so the topic
needs no new game: Match, Listening, Pair Up and Fishing all become
discrimination drills the moment the confuse map is populated.

Two things are deliberately not done:
  - the new kanji (飴, 鼻, 蛙) are shown but never added to the kanji levels,
    so the 105-character N5 target stays clean
  - the reading is not a question form. はし -> 橋 is unanswerable when 箸 and
    端 are equally はし, so questions run kanji <-> meaning only, and the
    reading is shown on the study sheet and the card instead.
"""
import io, os, re, json, hashlib, subprocess

SC = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\JapaneseLearning\kana-quest.html"
ID, TITLE, SUB, ICON, VALUE = "homophones", "Same Sound", "どうおん", "\U0001f3ad", 190


def esc(t):
    return t.replace('"', '\\"')


def main():
    fams = json.load(io.open(os.path.join(SC, "homophones.json"), encoding="utf-8"))
    s = io.open(GAME, encoding="utf-8").read()
    assert "const HOMOPHONES" not in s, "already applied"

    # Pack families into groups of five or six, never splitting one: a group is
    # a set, so a completed set is a completed family.
    groups, cur, cur_reads = [], [], []
    for f in fams:
        if len(cur) >= 5:
            groups.append((cur_reads, cur))
            cur, cur_reads = [], []
        cur += [[f["read"]] + it for it in f["items"]]
        cur_reads.append(f["read"])
    if cur:
        groups.append((cur_reads, cur))

    # ---- the data ------------------------------------------------------
    lines = []
    for reads, items in groups:
        lines.append('  { label:"%s", items:[' % " \u30fb ".join(reads))
        for i in range(0, len(items), 2):
            chunk = items[i:i + 2]
            lines.append("    " + " ".join(
                'h("%s","%s","%s","%s"),' % (it[1], it[0], esc(it[2]), it[3]) for it in chunk))
        lines[-1] = lines[-1].rstrip(",") + " ]},"
    lines[-1] = lines[-1].rstrip(",")
    block = (
        "\n/* \u540c\u97f3\u7570\u7fa9\u8a9e. h(jp, kana, en, pic): the reading is carried on the item but\n"
        "   is never a question form - \u306f\u3057 cannot ask for \u6a4b when \u7bb8 is equally \u306f\u3057 - so it\n"
        "   shows on the study sheet and the card, and the questions run kanji against\n"
        "   meaning with the family itself supplying the wrong answers. */\n"
        "function h(jp, kana, en, pic) { return { jp: jp, kana: kana, en: en, pic: pic }; }\n\n"
        "const HOMOPHONES = [\n" + "\n".join(lines) + "\n];\n\n"
        "function buildHomophoneCourse(title, sub, groups) {\n"
        "  const items = {}, words = [], confuse = {};\n"
        "  const units = groups.map(function (g, gi) {\n"
        "    const byRead = {};\n"
        "    g.items.forEach(function (it) {\n"
        "      items[it.jp] = { jp: it.jp, en: it.en, pic: it.pic, kana: it.kana };\n"
        "      words.push({ w: it.jp, en: it.en, pic: it.pic, row: gi });\n"
        "      (byRead[it.kana] = byRead[it.kana] || []).push(it.jp);\n"
        "    });\n"
        "    // The family is the distractor pool: nothing else is as confusable.\n"
        "    Object.keys(byRead).forEach(function (r) {\n"
        "      byRead[r].forEach(function (k) {\n"
        "        confuse[k] = byRead[r].filter(function (o) { return o !== k; });\n"
        "      });\n"
        "    });\n"
        "    return { label: g.label, keys: g.items.map(function (it) { return it.jp; }) };\n"
        "  });\n"
        "  return {\n"
        "    title: title, sub: sub, kind: \"vocab\", homophone: true, forms: [\"jp\", \"en\"],\n"
        "    units: units, extraUnits: [], items: withKanji(items, confuse),\n"
        "    confuse: confuse, words: words,\n"
        "    games: [\"match\", \"listen\", \"pairs\", \"fruit\", \"word\", \"fish\"]\n"
        "  };\n"
        "}\n")
    anchor = "\nconst COURSES = {"
    s = s.replace(anchor, block + anchor, 1)

    # ---- registration ---------------------------------------------------
    s = s.replace('  grammar:    buildGrammarCourse("Grammar", "ぶんぽう", GRAMMAR)\n};',
                  '  %s: buildHomophoneCourse("%s", "%s", HOMOPHONES),\n'
                  '  grammar:    buildGrammarCourse("Grammar", "ぶんぽう", GRAMMAR)\n};' % (ID, TITLE, SUB), 1)

    m = re.search(r'const COURSE_ORDER = \[(.*?)\];', s, re.S)
    order = re.findall(r'"(\w+)"', m.group(1))
    order.insert(order.index("n5"), ID)          # after the fun topics, before N5
    wrapped, line = [], "const COURSE_ORDER = ["
    for c in order:
        piece = '"%s", ' % c
        if len(line) + len(piece) > 96:
            wrapped.append(line.rstrip()); line = "                      "
        line += piece
    wrapped.append(line.rstrip().rstrip(",") + "];")
    s = s[:m.start()] + "\n".join(wrapped) + s[m.end():]

    def add_before_close(src, decl, addition):
        i = src.index(decl); j = src.index("\n};", i)
        return src[:j] + ",\n  " + addition + src[j:]

    s = add_before_close(s, "const COURSE_ICONS = {", '%s:"%s"' % (ID, ICON))
    s = add_before_close(s, "const COURSE_CARD_VALUE = {", "%s: %d" % (ID, VALUE))
    assert ('%s:"' % ID) in s and re.search(r"\b%s: \d+" % ID, s), "registration did not land"

    # ---- the study sheet shows the reading -------------------------------
    old = """  return lv.kana.map(function (key) {
    const it = itemOf(p, key);
"""
    new = """  return lv.kana.map(function (key) {
    const it = itemOf(p, key);

    // A homophone is only interesting next to what it sounds like, so the
    // reading sits between the character and the meaning even though it is
    // never asked as a question.
    if (c.homophone && it.kana) {
      return '<div class="study-row">' +
               (it.pic ? '<span class="study-pic" aria-hidden="true">' + it.pic + '</span>' : '') +
               '<span class="study-part kana">' + esc(it.jp) + '</span>' +
               '<span class="homo-read">' + esc(it.kana) + '</span>' +
               '<span class="study-arrow" aria-hidden="true">\\u2192</span>' +
               '<span class="study-part en">' + esc(it.en) + '</span>' +
               say(key) +
             '</div>';
    }
"""
    assert s.count(old) == 1
    s = s.replace(old, new, 1)

    # the reading also belongs on the collectible card
    oldc = """             '<span class="wcard-jp">' + esc(face.jp) + '</span>' +"""
    newc = """             '<span class="wcard-jp">' + esc(face.jp) + '</span>' +
             (face.kana && face.kana !== face.jp
               ? '<span class="wcard-read">' + esc(face.kana) + '</span>' : '') +"""
    assert s.count(oldc) == 1
    s = s.replace(oldc, newc, 1)

    oldf = """    const it = (c.items && c.items[key]) || KANJI_ITEMS[key] || {};
  return { jp: it.jp || key, en: it.en || it.romaji || it.kana || "", pic: picFor(key) };"""
    if oldf not in s:
        oldf = """  const it = (c.items && c.items[key]) || KANJI_ITEMS[key] || {};
  return { jp: it.jp || key, en: it.en || it.romaji || it.kana || "", pic: picFor(key) };"""
    assert s.count(oldf) == 1, "cardFace shape changed"
    s = s.replace(oldf, oldf.replace(
        'pic: picFor(key) };', 'pic: picFor(key), kana: it.kana || "" };'), 1)

    s = s.replace(""".study-arrow""", """.homo-read {
  font-family: var(--font-kana); font-weight: 700; font-size: 15px;
  color: var(--ai); background: var(--ai-wash);
  border-radius: 8px; padding: 2px 8px;
}
.wcard-read { font-family: var(--font-kana); font-size: 11px; color: var(--ink-faint); }
.study-arrow""", 1)

    io.open(GAME, "w", encoding="utf-8").write(s)

    # ---- clips say the READING, stored under the kanji -------------------
    jobs = json.load(io.open(os.path.join(SC, "tts_words.json"), encoding="utf-8"))
    have = set(j.get("key") or j.get("text") for j in jobs)
    added = 0
    for f in fams:
        for jp, en, pic in f["items"]:
            if jp in have:
                continue
            have.add(jp)
            jobs.append({"name": hashlib.sha1(f["read"].encode("utf-8")).hexdigest()[:12],
                         "text": f["read"], "key": jp})
            added += 1
    io.open(os.path.join(SC, "tts_words.json"), "w", encoding="utf-8").write(
        json.dumps(jobs, ensure_ascii=False, indent=1))

    print("%d families, %d words, %d groups; %d clips queued" %
          (len(fams), sum(len(f["items"]) for f in fams), len(groups), added))
    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    io.open(os.path.join(SC, "_check.js"), "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", os.path.join(SC, "_check.js")], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])


if __name__ == "__main__":
    main()
