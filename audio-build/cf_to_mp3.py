# -*- coding: utf-8 -*-
"""Vet the Cloudflare clips and re-encode the good ones small enough to embed.

    python cf_to_mp3.py

Two things are wrong with what Workers AI hands back, and both are silent
failures in the literal sense - the files look fine on disk.

**They are not mp3s.** MeloTTS returns uncompressed 44.1 kHz PCM WAV and
speak.py stores it under an .mp3 name, so audio/*.mp3 are 705 kb/s WAV
averaging 36 KB for a third of a second of speech. Left alone they take the
page from 5.6 MB to 30.3 MB, past the 25 MiB ceiling Cloudflare Pages puts on a
single file, so the deploy is refused and nothing ships. Re-encoded the way the
Haruka clips already are - 32 kbps mono 16 kHz, via the static ffmpeg that
ships with imageio_ffmpeg, no install and nothing on PATH - the same clip is
about 2 KB. 16 kHz is deliberate and matches to_mp3.py: 8 kHz telephone quality
blurs し against ち and swallows つ, which is the whole point of the clips.

**Most of them are silent.** On the 2026-08-25 run 472 of 556 clips came back
as a correctly formed WAV of plausible length carrying nothing but dither -
peak around -74 dBFS, i.e. inaudible - while 84 held real speech at a normal
-4 dBFS. There is no middle: the two groups sit 40 dB apart, so PEAK_FLOOR
separates them cleanly. This matters more than the size bug, because a silent
clip is *preferred over a working Haruka one* by inject_audio.py and would
replace 472 spoken words with nothing. The game would look fine and say
nothing.

Rejected clips are moved to audio_rejected/ rather than deleted: it keeps the
evidence, and it gets them out of audio/ so release_audio.py stops counting
them as finished and generates them again on a later run. Originals that pass
are left untouched in audio/ - they cost real neurons and re-encoding is lossy
- so this writes to audio_small/, which is the only Cloudflare folder
inject_audio.py will read.

Safe to re-run: a clip already encoded is skipped.
"""
import math, os, shutil, subprocess, sys, wave

import imageio_ffmpeg

SC = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(SC, "audio")
DST = os.path.join(SC, "audio_small")
BAD = os.path.join(SC, "audio_rejected")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Anything peaking below this is not speech. Observed: the dead clips top out
# at -76..-72 dBFS and the good ones at -30..-3, so the line can sit anywhere
# in between; -45 leaves room for a genuinely quiet word without letting
# dither through.
PEAK_FLOOR_DB = -45.0
# Below this a file is a bare RIFF header with no samples at all - Workers AI
# returns one of those occasionally too.
FLOOR = 512


def peak_db(path):
    """Loudest sample as dBFS, or None if this is not readable PCM."""
    try:
        w = wave.open(path, "rb")
        try:
            width = w.getsampwidth()
            raw = w.readframes(w.getnframes())
        finally:
            w.close()
    except Exception:
        return None
    if not raw:
        return -99.0
    full = float(1 << (8 * width - 1))
    peak = max(abs(int.from_bytes(raw[i:i + width], "little", signed=True))
               for i in range(0, len(raw) - width + 1, width))
    return -99.0 if peak == 0 else 20.0 * math.log10(peak / full)


def encode(src, dst):
    r = subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", src,
         "-codec:a", "libmp3lame", "-b:a", "32k", "-ac", "1", "-ar", "16000", dst],
        capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) <= 256:
        if os.path.exists(dst):
            os.remove(dst)
        return False, (r.stderr or "").strip()[:120]
    return True, ""


def reject(name, why):
    """Move a dud out of audio/ so a later run regenerates it."""
    if not os.path.isdir(BAD):
        os.makedirs(BAD)
    shutil.move(os.path.join(SRC, name), os.path.join(BAD, name))
    # An earlier run may already have encoded it before this check existed.
    stale = os.path.join(DST, name)
    if os.path.exists(stale):
        os.remove(stale)
    return why


def main():
    if not os.path.isdir(SRC):
        print("nothing to encode: %s does not exist" % SRC)
        return
    if not os.path.isdir(DST):
        os.makedirs(DST)

    made = skipped = failed = 0
    silent = empty = unreadable = 0
    before = after = 0
    for name in sorted(os.listdir(SRC)):
        if not name.endswith(".mp3"):
            continue
        src = os.path.join(SRC, name)

        if os.path.getsize(src) <= FLOOR:
            reject(name, "empty")
            empty += 1
            continue
        db = peak_db(src)
        if db is None:
            reject(name, "unreadable")
            unreadable += 1
            continue
        if db < PEAK_FLOOR_DB:
            reject(name, "silent")
            silent += 1
            continue

        dst = os.path.join(DST, name)
        before += os.path.getsize(src)
        if os.path.exists(dst) and os.path.getsize(dst) > 256:
            after += os.path.getsize(dst)
            skipped += 1
            continue
        ok, why = encode(src, dst)
        if ok:
            after += os.path.getsize(dst)
            made += 1
        else:
            failed += 1
            print("FAILED %s %s" % (name, why))

    mb = 1048576.0
    print("encoded %d, already there %d, failed %d" % (made, skipped, failed))
    print("rejected %d silent, %d empty, %d unreadable -> %s"
          % (silent, empty, unreadable, os.path.basename(BAD)))
    if before:
        print("%.1f MB of wav -> %.1f MB of mp3 (%.0f%% smaller)"
              % (before / mb, after / mb, 100 * (1 - after / float(before))))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
