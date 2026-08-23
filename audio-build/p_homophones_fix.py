# -*- coding: utf-8 -*-
"""Re-lay the homophone families after review.

A Japanese teacher went through all 26 and found one outright error and a
handful of judgement calls:

  - 先 is NOT read せん on its own. せん is its compound reading (先生, 先週);
    alone it is さき, and a child shown 先 would read it correctly and be
    marked wrong. The family is 千 / 線 now.
  - 揚がる, "to finish deep-frying", is a cook's word no child will ever
    produce. Cut.
  - five obvious families were missing: ひ (火/日) above all, then なおす,
    ひく, かぜ, きく. かえる gained 変える, あける swapped 明ける - abstract and
    unusable - for 空ける.
  - glosses and emoji: 気 "spirit" to "feeling", 芽 "bud" to "sprout" to match
    the seedling, 鳴く "to chirp" to "to cry (animal)" since it covers every
    animal, and 取る off the pinching hand.

The three 同訓異字 families - まち, あたたかい, のぼる - are one word written two
ways rather than two words, so they now sit at the end, after the true
homophones.
"""
import io, os, re, json, hashlib, subprocess

SC = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\JapaneseLearning\kana-quest.html"


def esc(t):
    return t.replace('"', '\\"')


def main():
    fams = json.load(io.open(os.path.join(SC, "homophones.json"), encoding="utf-8"))
    s = io.open(GAME, encoding="utf-8").read()

    groups, cur, cur_reads = [], [], []
    for f in fams:
        if len(cur) >= 5:
            groups.append((cur_reads, cur))
            cur, cur_reads = [], []
        cur += [[f["read"]] + it for it in f["items"]]
        cur_reads.append(f["read"])
    if cur:
        groups.append((cur_reads, cur))

    lines = []
    for reads, items in groups:
        lines.append('  { label:"%s", items:[' % " \u30fb ".join(reads))
        for i in range(0, len(items), 2):
            chunk = items[i:i + 2]
            lines.append("    " + " ".join(
                'h("%s","%s","%s","%s"),' % (it[1], it[0], esc(it[2]), it[3]) for it in chunk))
        lines[-1] = lines[-1].rstrip(",") + " ]},"
    lines[-1] = lines[-1].rstrip(",")

    i = s.index("const HOMOPHONES = [")
    j = s.index("\n];", i) + 3
    s = s[:i] + "const HOMOPHONES = [\n" + "\n".join(lines) + "\n];" + s[j:]
    io.open(GAME, "w", encoding="utf-8").write(s)

    jobs = json.load(io.open(os.path.join(SC, "tts_words.json"), encoding="utf-8"))
    keys = set(j2.get("key") or j2.get("text") for j2 in jobs)
    wanted = set()
    added = 0
    for f in fams:
        for jp, en, pic in f["items"]:
            wanted.add(jp)
            if jp in keys:
                continue
            jobs.append({"name": hashlib.sha1(f["read"].encode("utf-8")).hexdigest()[:12],
                         "text": f["read"], "key": jp})
            added += 1
    # a family that was cut should not keep queueing a clip
    before = len(jobs)
    jobs = [j2 for j2 in jobs if not (j2.get("key") and j2["key"] not in wanted)]
    io.open(os.path.join(SC, "tts_words.json"), "w", encoding="utf-8").write(
        json.dumps(jobs, ensure_ascii=False, indent=1))

    print("%d families, %d words, %d groups" %
          (len(fams), sum(len(f["items"]) for f in fams), len(groups)))
    print("clips: %d queued, %d dropped" % (added, before - len(jobs)))
    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    io.open(os.path.join(SC, "_check.js"), "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", os.path.join(SC, "_check.js")], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])


if __name__ == "__main__":
    main()
