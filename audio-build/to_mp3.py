# -*- coding: utf-8 -*-
"""Re-encode the trimmed clips as small mp3s.

A 16 kHz WAV runs about 15 KB a clip, which was fine for 552 of them and is not
fine for 1,150: the page would pass 20 MB and stop being loadable on a phone.
The same clip as 32 kbps mono mp3 is about 84% smaller, and at that size the
whole spoken vocabulary costs a couple of megabytes.

No install needed - imageio_ffmpeg ships a static ffmpeg and is already here.
Safe to re-run: a clip already converted is skipped.
"""
import io, os, subprocess, sys

import imageio_ffmpeg

SC = os.path.dirname(os.path.abspath(__file__))
PAIRS = [
    (os.path.join(SC, "local_trimmed"), os.path.join(SC, "local_mp3")),
    (os.path.join(SC, "local_trimmed_prefs"), os.path.join(SC, "local_mp3")),
]
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def encode(src, dst):
    r = subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", src,
         "-codec:a", "libmp3lame", "-b:a", "32k", "-ac", "1", "-ar", "16000", dst],
        capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 256


def main():
    made = skipped = failed = 0
    before = after = 0
    for srcdir, dstdir in PAIRS:
        if not os.path.isdir(srcdir):
            continue
        if not os.path.isdir(dstdir):
            os.makedirs(dstdir)
        for name in sorted(os.listdir(srcdir)):
            if not name.endswith(".wav"):
                continue
            src = os.path.join(srcdir, name)
            dst = os.path.join(dstdir, name[:-4] + ".mp3")
            before += os.path.getsize(src)
            if os.path.exists(dst) and os.path.getsize(dst) > 256:
                after += os.path.getsize(dst)
                skipped += 1
                continue
            if encode(src, dst):
                after += os.path.getsize(dst)
                made += 1
            else:
                failed += 1
                print("FAILED", name)

    mb = 1048576.0
    print("encoded %d, already there %d, failed %d" % (made, skipped, failed))
    print("%.1f MB of wav -> %.1f MB of mp3 (%.0f%% smaller)"
          % (before / mb, after / mb, 100 * (1 - after / max(1.0, before))))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
