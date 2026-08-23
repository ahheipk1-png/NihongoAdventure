# -*- coding: utf-8 -*-
"""Register the new vocabulary topics.

Reads audio-build/vocab_new.json (what the authoring workflow produced, after
its verifiers) and wires each topic into the five places a course has to be
registered, then queues every new word for a spoken clip.

Two rules that are not stylistic:
  - counters are APPENDED to the existing Numbers topic, never spliced in:
    p.setsPaid is keyed courseId:groupIndex and green stars by level index, so
    inserting a group in the middle re-attaches paid bonuses and earned stars
    to the wrong things.
  - COURSE_CARD_VALUE must gain an entry. Miss it and the topic's cards are
    silently worth 20 instead of ~130, every one renders "common", and its set
    bonuses pay less than half. Nothing errors; the numbers are just wrong.
"""
import io, os, re, json, hashlib, subprocess

SC = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\JapaneseLearning\kana-quest.html"

# Teaching order: kana, then the everyday world, then word classes, then the
# things they are here for, with N5 consolidating and grammar last.
ORDER = ["hiragana", "katakana", "kanamix",
         "numbers", "animals", "weekdays", "calendar", "time2",
         "food", "drink", "restaurant",
         "family", "body", "clothes", "home", "house2",
         "weather", "school", "travel", "town",
         "verbs", "verbs2", "verbs3", "nouns", "adjectives", "adj2",
         "greetings", "feel", "hobby",
         "anime", "culture",
         "n5", "grammar"]

NEW = {
    "calendar":   {"title": "Calendar",          "sub": "カレンダー",   "icon": "\U0001f4c6", "value": 110},
    "food":       {"title": "Food",              "sub": "たべもの",     "icon": "\U0001f35a", "value": 120},
    "drink":      {"title": "Drink & Sweets",    "sub": "のみもの",     "icon": "\U0001f375", "value": 120},
    "restaurant": {"title": "At the Restaurant", "sub": "レストラン",   "icon": "\U0001f371", "value": 140},
    "family":     {"title": "Family & People",   "sub": "かぞく",       "icon": "\U0001f46a", "value": 120},
    "body":       {"title": "The Body",          "sub": "からだ",       "icon": "\U0001f9d1", "value": 120},
    "clothes":    {"title": "Clothes & Colours", "sub": "ふくといろ",   "icon": "\U0001f455", "value": 120},
    "home":       {"title": "Home & Things",     "sub": "いえのもの",   "icon": "\U0001f3e0", "value": 130},
    "weather":    {"title": "Weather & Nature",  "sub": "てんき",       "icon": "\u26c5",     "value": 130},
    "school":     {"title": "School & Work",     "sub": "がっこう",     "icon": "\u270f\ufe0f", "value": 140},
    "travel":     {"title": "Getting Around",    "sub": "でかける",     "icon": "\U0001f686", "value": 140},
    "verbs2":     {"title": "More Verbs",        "sub": "どうし \u2461", "icon": "\U0001f3c3", "value": 150},
    "adj2":       {"title": "More Describing",   "sub": "けいようし \u2461", "icon": "\U0001f308", "value": 160},
    "anime":      {"title": "Anime & Manga",     "sub": "アニメ",       "icon": "\U0001f4fa", "value": 170},
    "culture":    {"title": "Japanese Culture",  "sub": "ぶんか",       "icon": "\u26e9\ufe0f", "value": 180},
    "time2":      {"title": "Telling the Time",   "sub": "じかん",       "icon": "⏰",         "value": 130},
    "town":       {"title": "Around Town",        "sub": "まちのなか",   "icon": "🏙️", "value": 140},
    "house2":     {"title": "More at Home",       "sub": "いえのなか",   "icon": "🧹",     "value": 140},
    "hobby":      {"title": "Hobbies & Sport",    "sub": "しゅみ",       "icon": "⚽",         "value": 150},
    "feel":       {"title": "Feelings & Manners", "sub": "きもち",       "icon": "🤝",     "value": 150},
    "verbs3":     {"title": "Everyday Verbs",     "sub": "どうし ③", "icon": "🤸",   "value": 160},
}


def esc(t):
    return t.replace('"', '\\"')


def group_js(g, indent="    "):
    lines = [indent + '{ label:"%s", items:[' % esc(g["label"])]
    for i in range(0, 5, 3):
        chunk = g["items"][i:i + 3]
        lines.append(indent + "  " + " ".join(
            'v("%s","%s","%s"),' % (it["jp"], esc(it["en"]), it["pic"]) for it in chunk))
    lines[-1] = lines[-1].rstrip(",") + " ]}"
    return "\n".join(lines)


def main():
    data = json.load(io.open(os.path.join(SC, "vocab_new.json"), encoding="utf-8"))
    s = io.open(GAME, encoding="utf-8").read()
    words = []

    # ---- counters: APPENDED to Numbers ----------------------------------
    if "counters" in data:
        i = s.index("  numbers: [")
        j = s.index("\n  ],", i)
        add = ",\n" + ",\n".join(group_js(g) for g in data["counters"]["groups"])
        s = s[:j] + add + s[j:]
        for g in data["counters"]["groups"]:
            for it in g["items"]:
                words.append(it["jp"])
        print("numbers: appended %d counter groups" % len(data["counters"]["groups"]))

    # ---- the new topics -------------------------------------------------
    blocks = []
    already_reg = set(re.findall(r"\n  (\w+):\s*buildVocabCourse", s))
    for cid in ORDER:
        if cid not in NEW or cid not in data or cid in already_reg:
            continue
        gs = data[cid]["groups"]
        blocks.append("  %s: [\n%s\n  ]" % (cid, ",\n".join(group_js(g) for g in gs)))
        for g in gs:
            for it in g["items"]:
                words.append(it["jp"])
    end = s.index("\n};", s.index("const VOCAB = {"))
    s = s[:end] + ",\n" + ",\n".join(blocks) + s[end:]

    # ---- COURSES --------------------------------------------------------
    lines = []
    for cid in ORDER:
        if cid not in NEW or cid not in data or cid in already_reg:
            continue
        m = NEW[cid]
        lines.append('  %s: buildVocabCourse("%s", "%s", VOCAB.%s)' % (cid, m["title"], m["sub"], cid))
    anchor = '  grammar:    buildGrammarCourse("Grammar", "ぶんぽう", GRAMMAR)\n};'
    assert s.count(anchor) == 1
    s = s.replace(anchor, ",\n".join(lines) + ",\n" + anchor, 1)

    # ---- COURSE_ORDER ---------------------------------------------------
    old_order = re.search(r'const COURSE_ORDER = \[.*?\];', s, re.S)
    # Keep whatever is already registered in COURSES, plus whatever this run
    # is adding. A wave must never drop the wave before it.
    already = set(re.findall(r"\n  (\w+):\s*build(?:Vocab|Kana|Mix|Grammar)", s))
    live = [c for c in ORDER if c in already or c in data]
    wrapped, line = [], "const COURSE_ORDER = ["
    for c in live:
        piece = '"%s", ' % c
        if len(line) + len(piece) > 96:
            wrapped.append(line.rstrip())
            line = "                      "
        line += piece
    wrapped.append(line.rstrip().rstrip(",") + "];")
    s = s[:old_order.start()] + "\n".join(wrapped) + s[old_order.end():]

    # ---- icons and card values -----------------------------------------
    # Insert before each table's closing brace rather than matching its last
    # line. Matching the last line worked on the first wave and then silently
    # did nothing on the second, because the first wave had changed that line -
    # str.replace reports nothing when it matches nothing, so seven topics went
    # in with no card value. That does not crash; it just quietly prices their
    # cards at the fallback 20 instead of 130, renders them all "common", and
    # halves their set bonuses. Hence the assertions at the end.
    fresh = [c for c in ORDER if c in NEW and c in data and c not in already_reg]

    def add_before_close(src, decl, additions):
        if not additions:
            return src
        i = src.index(decl)
        j = src.index("\n};", i)
        return src[:j] + ",\n  " + additions + src[j:]

    s = add_before_close(s, "const COURSE_ICONS = {",
                         ", ".join('%s:"%s"' % (c, NEW[c]["icon"]) for c in fresh))
    s = add_before_close(s, "const COURSE_CARD_VALUE = {",
                         ", ".join("%s: %d" % (c, NEW[c]["value"]) for c in fresh))
    for c in fresh:
        assert ('%s:"' % c) in s, "icon for %s did not land" % c
        assert re.search(r"\b%s: \d+" % c, s), "card value for %s did not land" % c

    io.open(GAME, "w", encoding="utf-8").write(s)

    # ---- queue the clips ------------------------------------------------
    jobs = json.load(io.open(os.path.join(SC, "tts_words.json"), encoding="utf-8"))
    have = set(j.get("text") for j in jobs)
    added = 0
    for w in words:
        if w in have:
            continue
        have.add(w)
        jobs.append({"name": hashlib.sha1(w.encode("utf-8")).hexdigest()[:12], "text": w})
        added += 1
    io.open(os.path.join(SC, "tts_words.json"), "w", encoding="utf-8").write(
        json.dumps(jobs, ensure_ascii=False, indent=1))

    print("registered %d topics, %d new words, %d clips queued (%d total)"
          % (len([c for c in ORDER if c in NEW and c in data]), len(words), added, len(jobs)))

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    io.open(os.path.join(SC, "_check.js"), "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", os.path.join(SC, "_check.js")], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])


if __name__ == "__main__":
    main()
