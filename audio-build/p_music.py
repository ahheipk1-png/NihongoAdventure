# -*- coding: utf-8 -*-
"""Background music, composed rather than recorded.

Not a file. The page is already 5.8 MB and a loop worth listening to for twenty
minutes would add megabytes more, so the music is played by the browser from a
few hundred bytes of rules - and because it is generated it never repeats
exactly, which is the thing that makes a short loop unbearable by the third
time round.

WHAT IT PLAYS. D major pentatonic - D E F# A B - which is the yonanuki scale
most Japanese children's songs are built on: five notes with no semitone
between any adjacent pair, so nothing it picks can sound wrong. 66 beats a
minute, slower than a resting heartbeat.

Four voices, all quiet:
  bass    the root, every four beats, swelling in and out over three seconds
  pad     a held fifth underneath, barely there
  koto    the melody - a plucked triangle with a fast attack and a long decay,
          walking up and down the scale a step at a time with the odd leap
  bell    a high note at the end of a phrase, now and then

Every fourth phrase the melody drops out entirely and leaves the bass and pad
alone. That is the part that stops it wearing out: music that never rests is
what a child notices, and then cannot stop noticing.

WHAT IT DOES NOT DO. It never plays over a listening round - the whole exercise
there is telling one Japanese word from another, and a bed of fifths underneath
is exactly the wrong help. Everywhere else it ducks to a fifth of its volume
whenever a word is spoken, and comes back after. It also stops when the tab is
hidden, because music from a tab nobody is looking at is just noise in a room.

It obeys both pills: the volume pill scales it, and the sound pill - which the
user originally asked for as "a button to turn off background music", when
there was none to turn off - now silences it along with the effects.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
MIRROR = r"C:\JapaneseLearning\index.html"

MODULE = '''
/* ============================================================
   6b. MUSIC
   ============================================================ */

/* Composed at run time out of a scale and a few rules, so it costs the page
   nothing and never loops back on itself exactly. See audio-build/p_music.py
   for what it is playing and why. */
const music = (function () {
  const BEAT = 60 / 66;                 // slower than a resting heartbeat
  const PHRASE = 8;                     // beats
  const LOOKAHEAD = 0.7, TICK = 200;    // seconds of schedule, ms between ticks
  const BASE = 0.055;                   // very quiet: the cues must cut through

  // D major pentatonic - the yonanuki scale, no semitones, nothing can clash.
  const LOW  = [73.42, 110];                                   // D2, A2
  const PAD  = [146.83, 220];                                  // D3, A3
  const KOTO = [293.66, 329.63, 369.99, 440, 493.88,           // D4 E4 F#4 A4 B4
                587.33, 659.25, 739.99, 880, 987.77];          // D5 E5 F#5 A5 B5
  const BELL = [1174.66, 1318.51];                             // D6, E6

  let bus = null, lp = null, timer = null;
  let next = 0, beat = 0, phrase = 0, here = 4, ducked = 0;

  function ctx() { return audio.context(); }

  // Nothing over a listening round: telling one Japanese word from another is
  // the entire exercise, and a bed of fifths under it is the wrong help.
  function wanted() {
    if (quietMode()) return false;
    if (document.hidden) return false;
    if (session && !session.ended && session.mode === "listen") return false;
    return true;
  }

  function level() {
    const soft = ducked > (ctx() ? ctx().currentTime : 0) ? 0.2 : 1;
    return BASE * volLevel() * soft;
  }

  function bench() {
    const c = ctx();
    if (!c || bus) return !!bus;
    lp = c.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = 2600;          // takes the buzz off a raw triangle
    bus = c.createGain();
    bus.gain.value = 0;
    lp.connect(bus).connect(c.destination);
    return true;
  }

  // One plucked note: a triangle for the body, a quiet octave above for the
  // shimmer, a fast attack and a long exponential tail.
  function pluck(freq, at, dur, gain, type) {
    const c = ctx();
    const amp = c.createGain();
    amp.gain.setValueAtTime(0.0001, at);
    amp.gain.exponentialRampToValueAtTime(Math.max(0.0002, gain), at + 0.012);
    amp.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    amp.connect(lp);
    const o = c.createOscillator();
    o.type = type || "triangle";
    o.frequency.value = freq;
    o.connect(amp);
    o.start(at);
    o.stop(at + dur + 0.05);
    if (!type) {                        // the shimmer, only on the koto
      const o2 = c.createOscillator();
      o2.type = "sine";
      o2.frequency.value = freq * 2.004;
      const a2 = c.createGain();
      a2.gain.setValueAtTime(0.0001, at);
      a2.gain.exponentialRampToValueAtTime(Math.max(0.0002, gain * 0.25), at + 0.012);
      a2.gain.exponentialRampToValueAtTime(0.0001, at + dur * 0.6);
      o2.connect(a2).connect(lp);
      o2.start(at);
      o2.stop(at + dur * 0.6 + 0.05);
    }
  }

  // A slow swell rather than a pluck: the bass and the pad breathe.
  function swell(freq, at, dur, gain) {
    const c = ctx();
    const amp = c.createGain();
    amp.gain.setValueAtTime(0.0001, at);
    amp.gain.linearRampToValueAtTime(gain, at + dur * 0.35);
    amp.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    const o = c.createOscillator();
    o.type = "sine";
    o.frequency.value = freq;
    o.connect(amp).connect(lp);
    o.start(at);
    o.stop(at + dur + 0.05);
  }

  function step() {
    // A walk, not a jump: mostly one step up or down the scale, rarely more.
    const r = Math.random();
    const d = r < 0.34 ? -1 : r < 0.68 ? 1 : r < 0.8 ? -2 : r < 0.92 ? 2 : 0;
    here = Math.max(0, Math.min(KOTO.length - 1, here + d));
    return KOTO[here];
  }

  function schedule(at) {
    const inPhrase = beat % PHRASE;
    const resting = (phrase % 4) === 3;      // every fourth phrase, a breath

    if (inPhrase === 0) {
      const root = LOW[(phrase % 2)];
      swell(root, at, BEAT * 3.6, 0.09);
      swell(PAD[(phrase % 2)], at + 0.1, BEAT * 3.2, 0.045);
    }
    if (!resting) {
      // Beats that carry a note. The gaps matter as much as the notes.
      const strong = [0, 2, 3, 5, 7].indexOf(inPhrase) !== -1;
      if (strong ? Math.random() < 0.85 : Math.random() < 0.25) {
        pluck(step(), at, 1.5, 0.075);
      }
      if (inPhrase === PHRASE - 1 && Math.random() < 0.35) {
        pluck(BELL[Math.random() < 0.5 ? 0 : 1], at + BEAT * 0.5, 2.4, 0.03, "sine");
      }
    }

    beat += 1;
    if (beat % PHRASE === 0) phrase += 1;
  }

  function tick() {
    const c = ctx();
    if (!c || !bus) return;
    const want = wanted() ? level() : 0;
    // Always a ramp: a gain that jumps is a click.
    bus.gain.setTargetAtTime(want, c.currentTime, 0.25);
    if (!wanted()) { next = Math.max(next, c.currentTime + 0.05); return; }
    if (next < c.currentTime) next = c.currentTime + 0.05;
    while (next < c.currentTime + LOOKAHEAD) {
      schedule(next);
      next += BEAT;
    }
  }

  return {
    start: function () {
      if (!bench() || timer) return;
      next = 0;
      timer = window.setInterval(tick, TICK);
      tick();
    },
    stop: function () {
      if (timer) { window.clearInterval(timer); timer = null; }
      const c = ctx();
      if (bus && c) bus.gain.setTargetAtTime(0, c.currentTime, 0.2);
    },
    // Speech is the point of the game; the music gets out of its way.
    duck: function (seconds) {
      const c = ctx();
      if (!c) return;
      ducked = Math.max(ducked, c.currentTime + (seconds || 2));
      tick();
    },
    playing: function () { return !!timer; }
  };
})();
'''


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # the module sits after the audio module, which it borrows the context from
    rep("""/* ============================================================
   7. RENDER PLUMBING
   ============================================================ */""",
        MODULE.strip("\n") + """

/* ============================================================
   7. RENDER PLUMBING
   ============================================================ */""", "music module")

    # ---- it starts on the first gesture that unlocks audio at all --------
    rep("""    prime: function () {
      if (primed) return;
      primed = true;
      try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (AC) ctx = new AC();
        if (ctx && ctx.state === "suspended") ctx.resume();
      } catch (e) { ctx = null; }
    },""",
        """    prime: function () {
      if (primed) return;
      primed = true;
      try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (AC) ctx = new AC();
        if (ctx && ctx.state === "suspended") ctx.resume();
      } catch (e) { ctx = null; }
      // A browser will not make a sound until it has been touched, so this is
      // the earliest honest moment the music can begin.
      if (ctx && typeof music !== "undefined") music.start();
    },""", "start on prime")

    # ---- and gets out of the way whenever a word is spoken ---------------
    rep("""      const src = clip(key);
      if (src) {
        try {
          if (!el) { el = new Audio(); el.preload = "auto"; }
          louder();""",
        """      const src = clip(key);
      if (typeof music !== "undefined") music.duck(2.2);
      if (src) {
        try {
          if (!el) { el = new Audio(); el.preload = "auto"; }
          louder();""", "duck on speech")

    # ---- the sound pill now means the music too --------------------------
    rep("""          (quietMode()
            ? 'Game sounds are off. The ding, the buzz and the little fanfare are silent; ' +
              'the Japanese still plays.'
            : 'Turn off the game sounds - the ding, the buzz and the little fanfare. ' +
              'The Japanese keeps playing.') +""",
        """          (quietMode()
            ? 'Music and game sounds are off. The Japanese still plays.'
            : 'Turn off the music and the game sounds - the ding, the buzz and the ' +
              'little fanfare. The Japanese keeps playing.') +""", "pill tooltip")

    rep("""          '" aria-label="Game sounds">' + (quietMode() ? "\\ud83d\\udd07" : "\\ud83c\\udfb5") + '</button>' +""",
        """          '" aria-label="Music and game sounds">' +
          (quietMode() ? "\\ud83d\\udd07" : "\\ud83c\\udfb5") + '</button>' +""", "pill label")

    rep("""    state.quiet = !quietMode();
    save();
    // Turning them back on should make a sound; turning them off should not.
    if (!quietMode()) { audio.prime(); audio.good(); }
    renderTopbar();""",
        """    state.quiet = !quietMode();
    save();
    // Turning them back on should make a sound; turning them off should not.
    if (!quietMode()) { audio.prime(); audio.good(); music.start(); }
    renderTopbar();""", "pill starts music")

    # ---- a hidden tab is silent -----------------------------------------
    rep("""  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") cloud.flush(true);
  });""",
        """  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") cloud.flush(true);
    // The music checks document.hidden itself on the next tick; this only
    // wakes the context back up when the tab returns.
    if (document.visibilityState === "visible") audio.prime();
  });""", "hidden tab")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
    import os
    print("page: %.1f MB" % (os.path.getsize(GAME) / 1048576.0))


if __name__ == "__main__":
    main()
