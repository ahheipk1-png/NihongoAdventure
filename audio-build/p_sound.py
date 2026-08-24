# -*- coding: utf-8 -*-
"""A switch for the game's own sounds, and a louder voice.

There is no music track in this game - what a room hears as background noise is
the ding, the buzz, the little fanfare on a green star and the chord at the end
of a board. Those are what the switch turns off, and it deliberately leaves the
Japanese alone: the pronunciation is the lesson, not the soundtrack.

The voice goes up by a fifth. An <audio> element cannot be turned past 1.0, and
these clips are quiet - 32 kbps mono out of a system voice, recorded well below
full scale - so the only way past the ceiling is a gain node in front of it.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- 1. the switch itself -------------------------------------------
    rep("""const speech = (function () {
  let el = null, jaVoice = null;""",
        """/* The game's own noises, on or off. It lives on the device rather than on a
   player, because it is a fact about the room the computer is in - one child
   playing next to a sleeping brother wants it off whoever is holding the
   mouse, and it should not follow them to school on the next sync. */
function quietMode() { return !!(state && state.quiet); }

const speech = (function () {
  let el = null, jaVoice = null, wired = false;

  // Exactly a fifth louder than the clip was recorded.
  const SAY_GAIN = 1.2;""", "quietMode")

    # ---- 2. the voice goes through a gain node ---------------------------
    rep("""      if (src) {
        try {
          if (!el) { el = new Audio(); el.preload = "auto"; }
          el.pause(); el.src = src; el.currentTime = 0;""",
        """      if (src) {
        try {
          if (!el) { el = new Audio(); el.preload = "auto"; }
          louder();
          el.pause(); el.src = src; el.currentTime = 0;""", "louder call")

    rep("""  function clip(key) { return (window.AUDIO && window.AUDIO[key]) || null; }""",
        """  function clip(key) { return (window.AUDIO && window.AUDIO[key]) || null; }

  /* Routed once, the first time there is a running audio context to route it
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
  }""", "louder")

    # ---- 3. the tones obey the switch, and lend out their context --------
    rep("""  function tone(freq, when, dur, type, gain) {
    if (!ctx) return;""",
        """  function tone(freq, when, dur, type, gain) {
    if (!ctx || quietMode()) return;""", "tone gate")

    rep("""    prime: function () {
      if (primed) return;""",
        """    // The voice borrows this context to play louder than an element can.
    context: function () { return ctx; },
    prime: function () {
      if (primed) return;""", "context getter")

    # ---- 4. a pill, on every screen, with a tooltip that says what it does
    rep("""  topbarEl.innerHTML = html;""",
        """  /* Always present, including on the player-picking screen: whoever wants
     the noise to stop is usually not the one holding the mouse. */
  html += '<button class="purse sound" id="toSound" title="' +
          (quietMode()
            ? 'Game sounds are off. The ding, the buzz and the little fanfare are silent; ' +
              'the Japanese still plays.'
            : 'Turn off the game sounds - the ding, the buzz and the little fanfare. ' +
              'The Japanese keeps playing.') +
          '" aria-pressed="' + (quietMode() ? "true" : "false") +
          '" aria-label="Game sounds">' + (quietMode() ? "\\ud83d\\udd07" : "\\ud83c\\udfb5") + '</button>';

  topbarEl.innerHTML = html;
  const snd = document.getElementById("toSound");
  if (snd) snd.onclick = function () {
    state.quiet = !quietMode();
    save();
    // Turning them back on should make a sound; turning them off should not.
    if (!quietMode()) { audio.prime(); audio.good(); }
    renderTopbar();
  };""", "sound pill")

    # ---- 5. it looks like the other pills --------------------------------
    rep(""".cloud-pill {""",
        """.purse.sound { font-size: 15px; padding: 6px 10px; }
.cloud-pill {""", "pill css")

    io.open(GAME, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:600])


if __name__ == "__main__":
    main()
