# -*- coding: utf-8 -*-
"""Embed the generated clips into the game as window.AUDIO.

Run after speak.py has filled the audio folder:

    python inject_audio.py

Safe to re-run: it replaces any existing AUDIO block. Clips that were not
generated are simply absent, and the game falls back to a device voice for
those, so a partial set is fine.
"""
import io, os, re, json, base64, hashlib, sys

SC = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(SC, "audio")
GAME = r"C:\JapaneseLearning\kana-quest.html"

jobs = json.load(io.open(os.path.join(SC, "tts_words.json"), encoding="utf-8"))
s = io.open(GAME, encoding="utf-8").read()

audio, total, missing = {}, 0, 0
for j in jobs:
    p = os.path.join(AUD, j["name"] + ".mp3")
    if not os.path.exists(p) or os.path.getsize(p) < 512:
        missing += 1
        continue
    b = open(p, "rb").read()
    audio[j["text"]] = "data:audio/mpeg;base64," + base64.b64encode(b).decode("ascii")
    total += len(b)

if not audio:
    sys.exit("No clips found in %s - run speak.py first." % AUD)

block = "<script>window.AUDIO=" + json.dumps(audio, ensure_ascii=False, separators=(",", ":")) + ";</script>\n"

old = re.search(r'<script>window\.AUDIO=.*?</script>\n', s, re.S)
if old:
    s = s[:old.start()] + block + s[old.end():]
else:
    anchor = '<script>window.PICS='
    i = s.index(anchor)
    s = s[:i] + block + s[i:]

io.open(GAME, "w", encoding="utf-8").write(s)
print("embedded %d clips (%d KB of audio, %d still missing)" % (len(audio), total // 1024, missing))
print("file now %d KB" % (os.path.getsize(GAME) // 1024))
