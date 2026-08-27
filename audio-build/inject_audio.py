# -*- coding: utf-8 -*-
"""Embed the generated clips into the game as window.AUDIO.

    python inject_audio.py

Three sources, in order of preference per word:

  1. audio_small/<name>.mp3    - MeloTTS via Cloudflare Workers AI, the better
                                 voice, vetted and encoded by cf_to_mp3.py
  2. local_mp3/<name>.mp3      - Microsoft Haruka, synthesised offline and
                                 encoded small by to_mp3.py
  3. local_trimmed/<name>.wav  - the same clip before encoding, kept as a
                                 fallback for anything to_mp3.py has not reached

Preferring mp3 per word rather than per run is what makes the upgrade path
free: when the Cloudflare allowance returns, generate the mp3s and re-run this,
and every word that now has a better clip takes it while the rest keep Haruka.
No rewrite, no flag to remember.

Read audio_small/ and never the raw audio/ next to it. What Workers AI writes
there is neither vetted nor mp3: on 2026-08-25, 472 of 556 clips were a
well-formed WAV carrying only dither, and because a Cloudflare clip *outranks*
a working Haruka one they would have silenced 472 spoken words while the page
looked perfectly healthy. cf_to_mp3.py is what tells the two apart.

The WAVs are what makes the page enormous - 15 KB a clip against 2.5 KB for the
same thing at 32 kbps - so local_mp3 sitting above them is the difference
between a page a phone loads and one it does not.

Safe to re-run: it replaces any existing AUDIO block. Words with no clip at all
are simply absent and the game falls back to a device voice for those.
"""
import io, os, re, json, base64, sys

SC = os.path.dirname(os.path.abspath(__file__))
EDGE = os.path.join(SC, "edge_mp3")          # Nanami neural voice - preferred
MP3 = os.path.join(SC, "audio_small")
LOCAL_MP3 = os.path.join(SC, "local_mp3")
WAV = os.path.join(SC, "local_trimmed")
GAME = r"C:\JapaneseLearning\kana-quest.html"

jobs = json.load(io.open(os.path.join(SC, "tts_words.json"), encoding="utf-8"))
# The 47 prefecture names for the map. Local voice only - there is no
# Cloudflare list for these - trimmed into their own folder.
PREF_WAV = os.path.join(SC, "local_trimmed_prefs")
pref_jobs = json.load(io.open(os.path.join(SC, "tts_prefs.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(SC, "tts_prefs.json")) else []
for j in pref_jobs:
    j["_wavdir"] = PREF_WAV
jobs = jobs + pref_jobs
s = io.open(GAME, encoding="utf-8").read()

audio = {}
bytes_used = 0
from_edge = from_mp3 = from_local = from_wav = missing = blank = 0


def usable(path, floor=256):
    return os.path.exists(path) and os.path.getsize(path) > floor


def sniff(path, assumed):
    """Label a clip by its bytes rather than its file name.

    The Cloudflare clips are WAV stored under an .mp3 name and were being
    embedded as audio/mpeg. Browsers sniff data: URIs so they played regardless,
    but nothing guarantees that, and the mislabelling is what hid the fact that
    they had never been through an encoder at all.
    """
    with open(path, "rb") as f:
        head = f.read(4)
    if head[:4] == b"RIFF":
        return "audio/wav"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa"):
        return "audio/mpeg"
    return assumed


for j in jobs:
    text = (j.get("text") or "").strip()
    if not text:
        blank += 1
        continue
    edge = os.path.join(EDGE, j["name"] + ".mp3")
    mp3 = os.path.join(MP3, j["name"] + ".mp3")
    local = os.path.join(LOCAL_MP3, j["name"] + ".mp3")
    wav = os.path.join(j.get("_wavdir") or WAV, j["name"] + ".wav")
    if usable(edge, 512):
        src, mime = edge, "audio/mpeg"
        from_edge += 1
    elif usable(mp3, 512):
        src, mime = mp3, "audio/mpeg"
        from_mp3 += 1
    elif usable(local):
        src, mime = local, "audio/mpeg"
        from_local += 1
    elif usable(wav, 512):
        src, mime = wav, "audio/wav"
        from_wav += 1
    else:
        missing += 1
        continue
    mime = sniff(src, mime)
    b = open(src, "rb").read()
    # A job may name the key it is stored under. The homophones need this: the
    # clip says はし but has to be findable as 橋, 箸 and 端, because those are
    # the item keys and speech.can() looks a clip up by item.
    audio[j.get("key") or text] = "data:%s;base64,%s" % (mime, base64.b64encode(b).decode("ascii"))
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
print("embedded %d clips: %d Nanami, %d MeloTTS, %d Haruka, %d raw wav"
      % (len(audio), from_edge, from_mp3, from_local, from_wav))
print("  %d missing, %d blank entries skipped" % (missing, blank))
print("  %.1f MB of audio -> %.1f MB of page" % (bytes_used / mb, os.path.getsize(GAME) / mb))
