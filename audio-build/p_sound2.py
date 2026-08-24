# -*- coding: utf-8 -*-
"""Two separate controls: one for the game's noises, one for how loud it is.

The single pill did too much and the wrong thing. This splits it:

  * a music pill turns the game's own noises off - the ding, the buzz, the
    fanfare and the closing chord - and never touches the Japanese;
  * a volume pill cycles loud / medium / quiet, and moves BOTH the voice and
    the noises together, because "how loud is this game" is one question.

It also takes the voice back out of the Web Audio graph. Routing an <audio>
element through createMediaElementSource is a one-way door: from that moment
the element no longer reaches the speakers on its own, and if the context is
ever not running - suspended tab, a device that never granted the gesture, an
iPad on silent - the pronunciation goes silent with it, which is exactly the
symptom that was reported. Volume now rides on el.volume, which has no such
failure mode. The cost is the fifth of extra loudness that gain node bought,
since el.volume cannot go past 1.0; that boost existed to make quiet clips
carry, and the request now is a way to make them quieter, so the ceiling is
where the loud setting sits.
"""
import io, re, shutil, subprocess

GAME  = r"C:\JapaneseLearning\kana-quest.html"
INDEX = r"C:\JapaneseLearning\index.html"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- 1. the two settings, side by side ------------------------------
    rep("""function quietMode() { return !!(state && state.quiet); }""",
        """function quietMode() { return !!(state && state.quiet); }

/* Loud, medium, quiet. Three steps and no slider: a slider in a top bar is a
   thing a six-year-old drags by accident, and there is no volume worth having
   between these. Nothing here is zero - silence is the other button's job, and
   a zero would also break the exponential ramps the tones are drawn with. */
const VOL_STEPS = [1, 0.6, 0.3];
const VOL_ICON  = ["\\ud83d\\udd0a", "\\ud83d\\udd09", "\\ud83d\\udd08"];

function volLevel() {
  const v = state && state.vol;
  return typeof v === "number" && v > 0 && v <= 1 ? v : VOL_STEPS[0];
}

function volStep() {
  let best = 0;
  for (let i = 1; i < VOL_STEPS.length; i++) {
    if (Math.abs(VOL_STEPS[i] - volLevel()) < Math.abs(VOL_STEPS[best] - volLevel())) best = i;
  }
  return best;
}""", "volLevel")

    # ---- 2. the voice leaves the audio graph ----------------------------
    rep("""  let el = null, jaVoice = null, wired = false;

  // Exactly a fifth louder than the clip was recorded.
  const SAY_GAIN = 1.2;
""",
        """  let el = null, jaVoice = null;
""", "speech header")

    rep("""  /* Routed once, the first time there is a running audio context to route it
     into. Before that the element plays on its own at its own level, which is
     the old behaviour and is better than silence: an element connected to a
     context that never resumes makes no sound at all. */
  function louder() {
    const ctx = audio.context();
    if (!ctx) return;
    if (ctx.state === "suspended") { try { ctx.resume(); } catch (e) { /* no-op */ } }
    if (wired || ctx.state !== "running") return;
    wired = true;
    try {
      const node = ctx.createMediaElementSource(el);
      const amp = ctx.createGain();
      amp.gain.value = SAY_GAIN;
      node.connect(amp).connect(ctx.destination);
    } catch (e) { /* one attempt only - a second would throw for good */ }
  }
""", "", "drop louder")

    rep("""          if (!el) { el = new Audio(); el.preload = "auto"; }
          louder();
          el.pause(); el.src = src; el.currentTime = 0;""",
        """          if (!el) { el = new Audio(); el.preload = "auto"; }
          // Set every time: the pill can move between one word and the next.
          el.volume = volLevel();
          el.pause(); el.src = src; el.currentTime = 0;""", "el.volume")

    # The device voice is a fallback on machines with no clips aboard, and it
    # has its own volume that has to be told the same thing.
    rep("""        u.voice = jaVoice; u.lang = jaVoice.lang; u.rate = 0.85;""",
        """        u.voice = jaVoice; u.lang = jaVoice.lang; u.rate = 0.85;
        u.volume = volLevel();""", "utterance volume")

    # ---- 3. the noises follow the same dial -----------------------------
    rep("""    amp.gain.exponentialRampToValueAtTime(gain || 0.16, ctx.currentTime + when + 0.015);""",
        """    amp.gain.exponentialRampToValueAtTime(Math.max(0.0001, (gain || 0.16) * volLevel()),
                                          ctx.currentTime + when + 0.015);""", "tone gain")

    # ---- 4. two pills, each saying only what it does --------------------
    rep("""  html += '<button class="purse sound" id="toSound" title="' +
          (quietMode()
            ? 'Game sounds are off. The ding, the buzz and the little fanfare are silent; ' +
              'the Japanese still plays.'
            : 'Turn off the game sounds - the ding, the buzz and the little fanfare. ' +
              'The Japanese keeps playing.') +
          '" aria-pressed="' + (quietMode() ? "true" : "false") +
          '" aria-label="Game sounds">' + (quietMode() ? "\\ud83d\\udd07" : "\\ud83c\\udfb5") + '</button>';""",
        """  html += '<button class="purse sound" id="toSound" title="' +
          (quietMode()
            ? 'Game sounds are off. The ding, the buzz and the little fanfare are silent; ' +
              'the Japanese still plays.'
            : 'Turn off the game sounds - the ding, the buzz and the little fanfare. ' +
              'The Japanese keeps playing.') +
          '" aria-pressed="' + (quietMode() ? "true" : "false") +
          '" aria-label="Game sounds">' + (quietMode() ? "\\ud83d\\udd07" : "\\ud83c\\udfb5") + '</button>' +
          '<button class="purse vol" id="toVol" title="How loud everything is - ' +
          'the Japanese and the game sounds together. Tap to go ' +
          ['quieter', 'quieter', 'back to loud'][volStep()] + '." aria-label="Volume">' +
          VOL_ICON[volStep()] + '</button>';""", "two pills")

    rep("""  const snd = document.getElementById("toSound");
  if (snd) snd.onclick = function () {
    state.quiet = !quietMode();
    save();
    // Turning them back on should make a sound; turning them off should not.
    if (!quietMode()) { audio.prime(); audio.good(); }
    renderTopbar();
  };""",
        """  const snd = document.getElementById("toSound");
  if (snd) snd.onclick = function () {
    state.quiet = !quietMode();
    save();
    // Turning them back on should make a sound; turning them off should not.
    if (!quietMode()) { audio.prime(); audio.good(); }
    renderTopbar();
  };
  const vol = document.getElementById("toVol");
  if (vol) vol.onclick = function () {
    state.vol = VOL_STEPS[(volStep() + 1) % VOL_STEPS.length];
    save();
    /* Hear the level you just chose, on whichever channel is still on - a
       volume control you cannot hear the effect of is a guess. */
    audio.prime();
    if (!quietMode()) audio.good();
    else speech.say(SAMPLE_WORD);
    renderTopbar();
  };""", "vol handler")

    # A word every course has a clip for, used only to demonstrate volume.
    rep("""function quietMode() { return !!(state && state.quiet); }""",
        """const SAMPLE_WORD = "\\u3042";   // just an /a/ - the shortest thing with a clip
function quietMode() { return !!(state && state.quiet); }""", "sample word")

    # ---- 5. it looks like its neighbour ---------------------------------
    rep(""".purse.sound { font-size: 15px; padding: 6px 10px; }""",
        """.purse.sound, .purse.vol { font-size: 15px; padding: 6px 10px; }""", "pill css")

    io.open(GAME, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    if r.returncode != 0:
        print("syntax:", r.stderr[:800])
        return
    print("syntax: OK")
    shutil.copyfile(GAME, INDEX)
    print("index.html updated")


if __name__ == "__main__":
    main()
