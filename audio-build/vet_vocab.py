# -*- coding: utf-8 -*-
"""Vet the authored vocabulary before any of it reaches the game.

The authors were told not to repeat words and mostly obeyed, but not entirely -
チョコレート turns up in both Food and Drink, and a few words the game already
teaches came back. A repeat is not cosmetic here: CARD_HOME gives a card to the
first topic that claims it, and CARD_SETS silently drops a group whose five keys
match an existing group, so a duplicate quietly costs a whole set bonus.

Rules enforced:
  - kana only (a kanji in the jp field means the author ignored the brief)
  - no word the game already teaches
  - no word repeated between or within the new topics
  - groups of exactly five, so survivors are re-packed and short tails dropped
"""
import io, os, re, json

SC = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\JapaneseLearning\kana-quest.html"
RESULT = (r"C:\Users\MICHAE~1\AppData\Local\Temp\claude\C--JapaneseLearning"
          r"\92eda8c4-e589-4414-8677-ad9f2474d45b\tasks\wvii6zvpi.output")

KANJI = re.compile(u"[\u4e00-\u9fff]")
KANA = re.compile(u"^[\u3041-\u309f\u30a0-\u30ff\u30fc\u30fb]+$")


def existing_keys():
    """Everything the game already teaches, read out of the source."""
    s = io.open(GAME, encoding="utf-8").read()
    keys = set()
    for m in re.finditer(r'\bv\("([^"]+)"', s):
        keys.add(m.group(1))
    for m in re.finditer(r'\bn\("([^"]+)"', s):
        keys.add(m.group(1))
    for m in re.finditer(r'\bkj\("([^"]+)"', s):
        keys.add(m.group(1))
    for m in re.finditer(r'kana:\s*\[([^\]]+)\]', s):
        for k in re.findall(r'"([^"]+)"', m.group(1)):
            keys.add(k)
    for m in re.finditer(r'\bw:"([^"]+)"', s):
        keys.add(m.group(1))
    return keys


def load_topics():
    """The workflow's aggregated output, already keyed by topic id."""
    d = json.load(io.open(RESULT, encoding="utf-8"))
    r = d.get("result", d)
    if isinstance(r, str):
        r = json.loads(r)
    return r["topics"]


def main():
    topics = load_topics()
    have = existing_keys()
    print("topics returned:", len(topics))
    print("words the game already teaches:", len(have))

    seen = set()
    clean, report = {}, []
    total_in = total_out = 0

    for cid, t in topics.items():
        labels = [g["label"] for g in t["groups"]]
        keep = []
        for g in t["groups"]:
            for it in g["items"]:
                total_in += 1
                jp, en, pic = it["jp"].strip(), it["en"].strip(), (it.get("pic") or "").strip()
                if KANJI.search(jp):
                    report.append("%s: %s has kanji" % (cid, jp)); continue
                if not KANA.match(jp):
                    report.append("%s: %s is not kana" % (cid, jp)); continue
                if not en or not pic:
                    report.append("%s: %s missing en/pic" % (cid, jp)); continue
                if jp in have:
                    report.append("%s: %s already in the game" % (cid, jp)); continue
                if jp in seen:
                    report.append("%s: %s repeated across topics" % (cid, jp)); continue
                seen.add(jp)
                keep.append({"jp": jp, "en": en, "pic": pic})
        groups = []
        for i in range(0, len(keep) - len(keep) % 5, 5):
            groups.append({"label": labels[len(groups)] if len(groups) < len(labels)
                           else "More " + cid, "items": keep[i:i + 5]})
        dropped_tail = len(keep) % 5
        if dropped_tail:
            report.append("%s: %d left over, not a full group" % (cid, dropped_tail))
        # Two groups is the floor: Word Building needs more than one row
        # (MODE_META.word has minRows 2), and a one-group topic is a two-level
        # course, which is not a topic.
        if len(groups) >= 2:
            clean[cid] = {"title": t.get("title", cid), "groups": groups}
            total_out += len(groups) * 5
        elif groups:
            report.append("%s: only %d group, held back for the next wave"
                          % (cid, len(groups)))
            for g in groups:
                for it in g["items"]:
                    seen.discard(it["jp"])

    io.open(os.path.join(SC, "vocab_new.json"), "w", encoding="utf-8").write(
        json.dumps(clean, ensure_ascii=False, indent=1))

    # Everything now spoken for, so a second wave can be told what not to say.
    # Kana and single kanji are left out: nobody is going to propose あ as a
    # vocabulary word, and the list is long enough already.
    words = sorted(w for w in (have | seen) if len(w) > 1 and not KANJI.search(w))
    io.open(os.path.join(SC, "vocab_taken.txt"), "w", encoding="utf-8").write(
        " ".join(words))
    print("exclusion list for the next wave: %d words" % len(words))

    print("\n%d words authored -> %d kept (%d groups)" %
          (total_in, total_out, sum(len(t["groups"]) for t in clean.values())))
    print("per topic:", ", ".join("%s %d" % (c, len(t["groups"]) * 5) for c, t in sorted(clean.items())))
    print("\nrejected %d:" % len(report))
    for r in report[:40]:
        print("  -", r)
    if len(report) > 40:
        print("  ... and %d more" % (len(report) - 40))


if __name__ == "__main__":
    main()
