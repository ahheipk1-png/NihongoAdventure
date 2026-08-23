# -*- coding: utf-8 -*-
"""Short real hiragana words, so the kana topics can host spelling.

Word Building only offers itself where every one of a level's kana appears in
some word it can build - otherwise the level is winnable but can never advance.
With 42 words no five-kana row was fully covered, so the hiragana and katakana
topics got no spelling at all. These are real, short, child-familiar words
chosen to close the gaps row by row; nothing is invented to fill a hole.
"""
import io, re, subprocess

f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()

# (word, English, emoji) - all real words, two or three kana
NEW = [
    (u"うえ", u"up, above", u"\u2b06\ufe0f"),
    (u"きく", u"to listen", u"\U0001f442"),
    (u"いけ", u"pond", u"\U0001f3de\ufe0f"),
    (u"せき", u"seat", u"\U0001f4ba"),
    (u"そら", u"sky", u"\u2601\ufe0f"),
    (u"つき", u"moon", u"\U0001f319"),
    (u"ちち", u"father", u"\U0001f468"),
    (u"てら", u"temple", u"\u26e9\ufe0f"),
    (u"とけい", u"clock", u"\U0001f552"),
    (u"ぬの", u"cloth", u"\U0001f9f5"),
    (u"にわ", u"garden", u"\U0001f333"),
    (u"ひも", u"string", u"\U0001f9f6"),
    (u"へや", u"room", u"\U0001f6cf\ufe0f"),
    (u"ほし", u"star", u"\u2b50"),
    (u"みみ", u"ear", u"\U0001f442"),
    (u"むし", u"insect", u"\U0001f41b"),
    (u"めも", u"memo", u"\U0001f4dd"),
    (u"ゆき", u"snow", u"\u2744\ufe0f"),
    (u"よる", u"night", u"\U0001f319"),
    (u"れい", u"zero", u"0\ufe0f\u20e3"),
    (u"ろく", u"six", u"6\ufe0f\u20e3"),
    (u"わたし", u"me", u"\U0001f9d2"),
    (u"のり", u"seaweed", u"\U0001f363"),
    (u"ふゆ", u"winter", u"\u26c4"),
    (u"はる", u"spring", u"\U0001f338"),
    (u"あめ", u"rain", u"\U0001f327\ufe0f"),
    (u"やま", u"mountain", u"\U0001f5fb"),
    (u"ゆめ", u"dream", u"\U0001f4ad"),
    (u"こえ", u"voice", u"\U0001f5e3\ufe0f"),
    (u"ぬま", u"marsh", u"\U0001f99f"),
]

# Which row each kana belongs to, read from the game's own ROWS table so the
# `row` field cannot drift from the ladder.
i = s.index("const ROWS = [")
j = s.index("\n];", i)
rows_src = s[i:j]
row_of = {}
for idx, line in enumerate(re.findall(r'kana:\s*\[([^\]]+)\]', rows_src)):
    for k in re.findall(r'"([^"]+)"', line):
        row_of[k] = idx

i2 = s.index("const WORDS = [")
j2 = s.index("\n];", i2)
block = s[i2:j2]
have = set(re.findall(r'w:"([^"]+)"', block))

added, skipped = [], []
lines = []
for w, en, pic in NEW:
    if w in have:
        skipped.append(w + " (already there)")
        continue
    if any(ch not in row_of for ch in w):
        skipped.append(w + " (uses a kana outside the base rows)")
        continue
    r = max(row_of[ch] for ch in w)
    lines.append(u'  { w:"%s", en:"%s", pic:"%s", row:%d }' % (w, en, pic, r))
    added.append(w)

if lines:
    s = s[:j2] + ",\n" + ",\n".join(lines) + s[j2:]
    io.open(f, "w", encoding="utf-8").write(s)

print("added %d words: %s" % (len(added), " ".join(added)))
if skipped:
    print("skipped: %s" % "; ".join(skipped))

js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:500])
