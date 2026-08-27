# -*- coding: utf-8 -*-
u"""Choose how a single kana is spoken, without regenerating anything.

    python use_kana_style.py plain    # あ, spoken slowly       (default)
    python use_kana_style.py held     # あー, the vowel drawn out

Both sets were made by edge_tts_build.py and sit side by side; this only copies
the chosen one into edge_mp3/, where inject_audio.py reads. Run inject_audio.py
afterwards to put it in the game.

Why plain is the default: at -30% a lone kana already runs about twice as long
as the old voice managed - ん went from 0.07s to 0.26s, which was the worst of
the "too short" - and it stays the sound it claims to be. あー is a long vowel,
a different thing in Japanese from あ, and a game teaching kana should not
blur that unless a person decides it sounds better.
"""
import os, shutil, sys

SC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SC, "edge_mp3")
SETS = {"plain": os.path.join(SC, "edge_kana_plain"),
        "held": os.path.join(SC, "edge_kana_held")}


def main():
    style = (sys.argv[1] if len(sys.argv) > 1 else "plain").lower()
    if style not in SETS:
        sys.exit("style must be 'plain' or 'held'")
    src = SETS[style]
    if not os.path.isdir(src):
        sys.exit("no clips in %s - run edge_tts_build.py first" % src)
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for f in os.listdir(src):
        if f.endswith(".mp3"):
            shutil.copyfile(os.path.join(src, f), os.path.join(OUT, f))
            n += 1
    print("kana style '%s': %d clips copied into edge_mp3/" % (style, n))
    print("now run:  python inject_audio.py")


if __name__ == "__main__":
    main()
