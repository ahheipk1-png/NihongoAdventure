# -*- coding: utf-8 -*-
"""Embed the generated clips into the game as window.AUDIO.

    python inject_audio.py

Two sources, in order of preference per word:

  1. audio/<name>.mp3          - MeloTTS via Cloudflare Workers AI, the better
                                 voice, blocked on a quota bug as of 2026-08-22
  2. local_trimmed/<name>.wav  - Microsoft Haruka, synthesised offline on this
                                 machine and trimmed of SAPI's padding

Preferring mp3 per word rather than per run is what makes the upgrade path
free: when the Cloudflare allowance returns, generate the mp3s and re-run this,
and every word that now has a better clip takes it while the rest keep Haruka.
No rewrite, no flag to remember.

Safe to re-run: it replaces any existing AUDIO block. Words with no clip at all
are simply absent and the game falls back to a device voice for those.
"""
import io, os, re, json, base64, sys

SC = os.path.dirname(os.path.abspath(__file__))
MP3 = os.path.join(SC, "audio")
WAV = os.path.join(SC, "local_trimmed")
GAME = r"C:\JapaneseLearning\kana-quest.html"

jobs = json.load(io.open(os.path.join(SC, "tts_words.json"), encoding="utf-8"))
s = io.open(GAME, encoding="utf-8").read()

audio = {}
bytes_used = 0
from_mp3 = from_wav = missing = blank = 0

for j in jobs:
    text = (j.get("text") or "").strip()
    if not text:
        blank += 1
        continue
    mp3 = os.path.join(MP3, j["name"] + ".mp3")
    wav = os.path.join(WAV, j["name"] + ".wav")
    if os.path.exists(mp3) and os.path.getsize(mp3) > 512:
        src, mime = mp3, "audio/mpeg"
        from_mp3 += 1
    elif os.path.exists(wav) and os.path.getsize(wav) > 512:
        src, mime = wav, "audio/wav"
        from_wav += 1
    else:
        missing += 1
        continue
    b = open(src, "rb").read()
    audio[text] = "data:%s;base64,%s" % (mime, base64.b64encode(b).decode("ascii"))
    bytes_used += len(b)

if not audio:
    sys.exit("No clips found in %s or %s." % (MP3, WAV))

block = "<script>window.AUDIO=" + json.dumps(audio, ensure_ascii=False, separators=(",", ":")) + ";</script>\n"

old = re.search(r'<script>window\.AUDIO=.*?</script>\n', s, re.S)
if old:
    s = s[:old.start()] + block + s[old.end():]
else:
    anchor = '<script>window.PICS='
    i = s.index(anchor)
    s = s[:i] + block + s[i:]

io.open(GAME, "w", encoding="utf-8").write(s)
mb = 1048576.0
print("embedded %d clips: %d MeloTTS mp3, %d local wav" % (len(audio), from_mp3, from_wav))
print("  %d missing, %d blank entries skipped" % (missing, blank))
print("  %.1f MB of audio -> %.1f MB of page" % (bytes_used / mb, os.path.getsize(GAME) / mb))
