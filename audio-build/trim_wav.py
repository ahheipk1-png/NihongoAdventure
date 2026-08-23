# -*- coding: utf-8 -*-
"""Trim the silence SAPI pads onto every clip, and report what the set would
weigh embedded.

The synthesiser hands back about a second of room tone around each word - あ
arrives as 1.11s of which 0.24s is speech - so trimming is the difference
between a page nobody can load and one that is merely large.
"""
import wave, audioop, glob, os, sys, json, io

SRC  = r"C:\JapaneseLearning\audio-build\local_wav"
DST  = r"C:\JapaneseLearning\audio-build\local_trimmed"
RATE_OUT = int(sys.argv[1]) if len(sys.argv) > 1 else 16000


def trim(raw, width, rate, thresh=600, pad_ms=60):
    """Cut to the speech, leaving a short pad so nothing sounds clipped."""
    n = len(raw) // width
    step = max(1, rate // 1000)
    lo, hi = 0, n
    for i in range(0, n, step):
        c = raw[i * width:(i + step) * width]
        if c and audioop.max(c, width) > thresh:
            lo = i
            break
    for i in range(n - step, 0, -step):
        c = raw[i * width:(i + step) * width]
        if c and audioop.max(c, width) > thresh:
            hi = i + step
            break
    pad = int(rate * pad_ms / 1000.0)
    return raw[max(0, lo - pad) * width:min(n, hi + pad) * width]


def main():
    if not os.path.isdir(DST):
        os.makedirs(DST)
    before = after = 0
    dur = 0.0
    longest = []
    files = sorted(glob.glob(os.path.join(SRC, "*.wav")))
    for p in files:
        f = wave.open(p, "rb")
        width, rate, n = f.getsampwidth(), f.getframerate(), f.getnframes()
        raw = f.readframes(n)
        f.close()
        before += os.path.getsize(p)
        t = trim(raw, width, rate)
        if RATE_OUT != rate:
            t, _ = audioop.ratecv(t, width, 1, rate, RATE_OUT, None)
        secs = len(t) / float(width * RATE_OUT)
        dur += secs
        longest.append((secs, os.path.basename(p)))
        o = os.path.join(DST, os.path.basename(p))
        g = wave.open(o, "wb")
        g.setnchannels(1)
        g.setsampwidth(width)
        g.setframerate(RATE_OUT)
        g.writeframes(t)
        g.close()
        after += os.path.getsize(o)

    longest.sort(reverse=True)
    mb = 1048576.0
    print("clips           : %d" % len(files))
    print("sample rate     : %d Hz" % RATE_OUT)
    print("before trimming : %6.1f MB" % (before / mb))
    print("after trimming  : %6.1f MB   (%.0f%% saved)" % (after / mb, 100.0 * (1 - after / float(before))))
    print("embedded base64 : %6.1f MB" % (after * 1.34 / mb))
    print("total speech    : %6.1f s   (mean %.2fs)" % (dur, dur / max(1, len(files))))
    print("longest clips   : %s" % ", ".join("%.1fs" % s for s, _ in longest[:5]))


if __name__ == "__main__":
    main()
