# -*- coding: utf-8 -*-
u"""Generate every clip with Microsoft's neural Japanese voice (Nanami).

    python edge_tts_build.py            # generate whatever is missing
    python edge_tts_build.py --report   # just say what is on disk

Why: the game speaks in Microsoft Haruka, an old robotic SAPI voice, and the
one attempt to replace it (MeloTTS through Workers AI) returned 472 silent
files out of 556. Nanami is the neural voice Edge itself uses - free, far more
natural, and it re-encodes to the same 2 KB the game already carries.

THE LESSON FROM THAT FAILURE IS BUILT IN. Every clip is decoded and measured
before it is accepted: a file of plausible size carrying only dither is exactly
what shipped last time, and it looked perfectly healthy in every count. A clip
that is too quiet or too short is written to edge_rejected/ instead, so a later
run tries it again rather than silently leaving a hole.

SINGLE KANA GET BOTH TREATMENTS. A lone kana is about 0.13s of speech - the
"too short, too fast" the game sounds like now - and there is no honest way to
stretch that far. So two versions are made and kept side by side:

  plain  the kana alone, spoken slowly (-30%)          ~0.17s
  held   the kana with a long-vowel mark, あ -> あー    ~0.37s

`use_kana_style.py` swaps between them without regenerating anything. Words
and kanji are unaffected - they are already several mora long.
"""
import asyncio, base64, io, json, os, struct, subprocess, sys, wave

import edge_tts
import imageio_ffmpeg

SC = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "ja-JP-NanamiNeural"

OUT = os.path.join(SC, "edge_mp3")              # what inject_audio reads
KANA_PLAIN = os.path.join(SC, "edge_kana_plain")
KANA_HELD = os.path.join(SC, "edge_kana_held")
REJECT = os.path.join(SC, "edge_rejected")

WORD_RATE = "-10%"
KANA_PLAIN_RATE = "-30%"
KANA_HELD_RATE = "-10%"

CONCURRENCY = 6
TRIES = 3

# A clip must be at least this loud and this long, or it is dither.
MIN_PEAK = 0.05          # the silent MeloTTS files sat near -74 dBFS
MIN_SPEECH = 0.04        # seconds of audible signal


def is_kana(text):
    t = text.strip()
    return len(t) == 1 and "぀" <= t <= "ヿ"


def jobs():
    """Every clip the game wants: words, kanji and the 47 prefecture names."""
    out = []
    for fn in ("tts_words.json", "tts_prefs.json"):
        path = os.path.join(SC, fn)
        if not os.path.exists(path):
            continue
        for j in json.load(io.open(path, encoding="utf-8")):
            text = (j.get("text") or "").strip()
            if text:
                out.append({"name": j["name"], "text": text})
    seen, uniq = set(), []
    for j in out:
        if j["name"] not in seen:
            seen.add(j["name"])
            uniq.append(j)
    return uniq


def measure(path):
    """Peak level and the length of the audible part, via a temp wav."""
    wav = path + ".probe.wav"
    r = subprocess.run([FF, "-y", "-i", path, "-ac", "1", "-ar", "16000", wav],
                       capture_output=True)
    if r.returncode != 0 or not os.path.exists(wav):
        return 0.0, 0.0
    try:
        with wave.open(wav) as w:
            n = w.getnframes()
            if not n:
                return 0.0, 0.0
            vals = struct.unpack("<%dh" % n, w.readframes(n))
        peak = max(abs(v) for v in vals) / 32768.0
        loud = [i for i, v in enumerate(vals) if abs(v) > 655]
        speech = (loud[-1] - loud[0]) / 16000.0 if loud else 0.0
        return peak, speech
    finally:
        if os.path.exists(wav):
            os.remove(wav)


def shrink(src, dst):
    """The game's format: 32 kbps mono 16 kHz, about 2 KB a clip."""
    subprocess.run([FF, "-y", "-i", src, "-codec:a", "libmp3lame",
                    "-b:a", "32k", "-ac", "1", "-ar", "16000", dst],
                   capture_output=True)
    return os.path.exists(dst) and os.path.getsize(dst) > 256


async def make(text, rate, dst, sem, stats):
    """One clip: synthesise, vet, shrink. Rejects go where a rerun finds them."""
    if os.path.exists(dst) and os.path.getsize(dst) > 256:
        stats["kept"] += 1
        return True
    raw = dst + ".raw.mp3"
    async with sem:
        for attempt in range(TRIES):
            try:
                await edge_tts.Communicate(text, VOICE, rate=rate).save(raw)
                if os.path.getsize(raw) > 512:
                    break
            except Exception:
                await asyncio.sleep(1.5 * (attempt + 1))
        else:
            stats["failed"] += 1
            return False
    if not os.path.exists(raw):
        stats["failed"] += 1
        return False
    peak, speech = measure(raw)
    if peak < MIN_PEAK or speech < MIN_SPEECH:
        os.makedirs(REJECT, exist_ok=True)
        os.replace(raw, os.path.join(REJECT, os.path.basename(dst)))
        stats["silent"] += 1
        return False
    ok = shrink(raw, dst)
    os.remove(raw)
    stats["made" if ok else "failed"] += 1
    return ok


async def main():
    for d in (OUT, KANA_PLAIN, KANA_HELD):
        os.makedirs(d, exist_ok=True)
    js = jobs()
    kana = [j for j in js if is_kana(j["text"])]
    words = [j for j in js if not is_kana(j["text"])]
    print("%d clips wanted: %d words/kanji, %d single kana (x2 styles)"
          % (len(js), len(words), len(kana)))

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"made": 0, "kept": 0, "silent": 0, "failed": 0}
    tasks = []
    for j in words:
        tasks.append(make(j["text"], WORD_RATE, os.path.join(OUT, j["name"] + ".mp3"), sem, stats))
    for j in kana:
        tasks.append(make(j["text"], KANA_PLAIN_RATE,
                          os.path.join(KANA_PLAIN, j["name"] + ".mp3"), sem, stats))
        tasks.append(make(j["text"] + "ー", KANA_HELD_RATE,
                          os.path.join(KANA_HELD, j["name"] + ".mp3"), sem, stats))

    done = 0
    for chunk in [tasks[i:i + 60] for i in range(0, len(tasks), 60)]:
        await asyncio.gather(*chunk)
        done += len(chunk)
        print("  %d/%d  made %d, kept %d, silent %d, failed %d"
              % (done, len(tasks), stats["made"], stats["kept"], stats["silent"], stats["failed"]))

    print("\nwords/kanji in %s: %d" % (os.path.basename(OUT), len(os.listdir(OUT))))
    print("kana plain: %d   kana held: %d" % (len(os.listdir(KANA_PLAIN)), len(os.listdir(KANA_HELD))))
    if stats["silent"] or stats["failed"]:
        print("rejected/failed: %d silent, %d failed - rerun to retry them"
              % (stats["silent"], stats["failed"]))


if __name__ == "__main__":
    if "--report" in sys.argv:
        for d in (OUT, KANA_PLAIN, KANA_HELD, REJECT):
            print("%-20s %d" % (os.path.basename(d),
                                len(os.listdir(d)) if os.path.exists(d) else 0))
    else:
        asyncio.run(main())
