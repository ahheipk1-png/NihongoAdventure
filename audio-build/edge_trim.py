# -*- coding: utf-8 -*-
u"""Trim the silence edge-tts wraps around every clip.

The neural voice returns about 1.8 seconds for a third of a second of speech -
the rest is padding - and at 32 kbps that is 7.9 KB a clip instead of 2 KB.
Across 1,196 clips it is the difference between a page a phone loads and one it
does not.

So each clip is cut to its audible part plus a little air: 60 ms before, so the
first consonant is never clipped, and 140 ms after, because a sound that stops
the instant the voice does is what "too fast" feels like. Idempotent - a clip
already tight is left alone.
"""
import os, struct, subprocess, sys, wave
import imageio_ffmpeg

SC = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
DIRS = ["edge_mp3", "edge_kana_plain", "edge_kana_held"]

LEAD = 0.06        # air before the first sound
TAIL = 0.14        # and after the last, so nothing feels cut off
FLOOR = 655        # 2% of full scale counts as sound


def bounds(path):
    """Where the audible part starts and ends, in seconds."""
    wav = path + ".t.wav"
    r = subprocess.run([FF, "-y", "-i", path, "-ac", "1", "-ar", "16000", wav],
                       capture_output=True)
    if r.returncode != 0 or not os.path.exists(wav):
        return None
    try:
        with wave.open(wav) as w:
            n = w.getnframes()
            if not n:
                return None
            vals = struct.unpack("<%dh" % n, w.readframes(n))
        loud = [i for i, v in enumerate(vals) if abs(v) > FLOOR]
        if not loud:
            return None
        return loud[0] / 16000.0, loud[-1] / 16000.0, n / 16000.0
    finally:
        if os.path.exists(wav):
            os.remove(wav)


def trim(path):
    b = bounds(path)
    if not b:
        return "silent"
    start, end, total = b
    a = max(0.0, start - LEAD)
    length = min(total, end + TAIL) - a
    if total - length < 0.25:          # already tight enough to leave alone
        return "kept"
    tmp = path + ".cut.mp3"
    subprocess.run([FF, "-y", "-ss", "%.3f" % a, "-t", "%.3f" % length, "-i", path,
                    "-codec:a", "libmp3lame", "-b:a", "32k", "-ac", "1", "-ar", "16000", tmp],
                   capture_output=True)
    if os.path.exists(tmp) and os.path.getsize(tmp) > 256:
        os.replace(tmp, path)
        return "cut"
    if os.path.exists(tmp):
        os.remove(tmp)
    return "failed"


def main():
    for d in DIRS:
        p = os.path.join(SC, d)
        if not os.path.isdir(p):
            continue
        files = sorted(f for f in os.listdir(p) if f.endswith(".mp3"))
        before = sum(os.path.getsize(os.path.join(p, f)) for f in files)
        tally = {}
        for i, f in enumerate(files):
            r = trim(os.path.join(p, f))
            tally[r] = tally.get(r, 0) + 1
            if (i + 1) % 200 == 0:
                print("  %s %d/%d" % (d, i + 1, len(files)))
        after = sum(os.path.getsize(os.path.join(p, f)) for f in files)
        print("%-18s %4d clips  %5d KB -> %4d KB  (avg %d B)  %s"
              % (d, len(files), before // 1024, after // 1024,
                 after // max(1, len(files)), tally))


if __name__ == "__main__":
    main()
