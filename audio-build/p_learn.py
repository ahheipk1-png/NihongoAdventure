# -*- coding: utf-8 -*-
"""The Learn session shows each item, says it, and moves on - once, on its
own, when it opens - then settles into the static list with a button to play
it through again."""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note, count=1):
    global s
    n = s.count(a)
    assert n == count, "expected %d of (%s), found %d" % (count, note, n)
    s = s.replace(a, b, count)


# ---------------------------------------------------------------- speech knows when it is done
rep("""    say: function (key) {
      const src = clip(key);
      if (src) {
        try {
          if (!el) { el = new Audio(); el.preload = "auto"; }
          el.pause(); el.src = src; el.currentTime = 0;
          const pr = el.play();
          if (pr && pr.catch) pr.catch(function () {});
          return;
        } catch (e) { /* fall through to the device voice */ }
      }
      if (!jaVoice) return;
      try {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(key);
        u.voice = jaVoice; u.lang = jaVoice.lang; u.rate = 0.85;
        window.speechSynthesis.speak(u);
      } catch (e) { /* no-op */ }
    }
  };
})();""",
"""    // `onEnd`, when given, fires once when the sound has finished - or at
    // once if nothing can play - so a sequence can wait for it.
    say: function (key, onEnd) {
      let fired = false;
      const done = function () { if (fired) return; fired = true; if (onEnd) onEnd(); };
      const src = clip(key);
      if (src) {
        try {
          if (!el) { el = new Audio(); el.preload = "auto"; }
          el.pause(); el.src = src; el.currentTime = 0;
          el.onended = done; el.onerror = done;
          const pr = el.play();
          if (pr && pr.catch) pr.catch(function () { done(); });
          return;
        } catch (e) { /* fall through to the device voice */ }
      }
      if (!jaVoice) { setTimeout(done, 0); return; }
      try {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(key);
        u.voice = jaVoice; u.lang = jaVoice.lang; u.rate = 0.85;
        u.onend = done; u.onerror = done;
        window.speechSynthesis.speak(u);
      } catch (e) { setTimeout(done, 0); }
    },
    stop: function () {
      try { if (el) { el.onended = null; el.pause(); } } catch (e) { /* no-op */ }
      try { if ("speechSynthesis" in window) window.speechSynthesis.cancel(); } catch (e) { /* no-op */ }
    }
  };
})();""", "speech onEnd + stop")

# ---------------------------------------------------------------- the sequencer
rep("""function studyRowsHTML(p) {
  const lv = levelInfo(p);""",
"""/* ------------------------------------------------------------
   THE LEARN SEQUENCE
   One item at a time: shown large, said aloud, held a moment, then the
   next. It runs once when the study sheet opens and then hands over to
   the list. Every timer checks the run token so leaving mid-way, or
   opening it twice, can never leave two sequences racing.
   ------------------------------------------------------------ */
const studyPlayer = { seq: 0, timer: null, paused: false, idx: 0 };

function stopStudyPlay() {
  studyPlayer.seq += 1;
  if (studyPlayer.timer) { clearTimeout(studyPlayer.timer); studyPlayer.timer = null; }
  speech.stop();
}

// One slide. It shows what the level asks - the same forms the list shows.
function slideHTML(p, lv, key, i, n) {
  const c = courseOf(p);
  const forms = lv.forms || c.forms;
  const it = itemOf(p, key);
  const isGrammar = c.kind === "grammar" && lv.kind !== "kanji";
  let body;
  if (isGrammar) {
    body = '<div class="slide-jp sentence" lang="ja">' +
             esc(key).replace(/\\uff3f/g, '<span class="study-ans">' + esc(it.ans) + '</span>') + '</div>' +
           '<div class="slide-en">' + esc(it.en || "") + '</div>';
  } else if (lv.game === "word") {
    body = '<div class="slide-jp" lang="ja">' + esc(key) + '</div>' +
           '<div class="spell-row">' + key.split("").map(function (ch) {
             return '<span class="spell-tile">' + esc(ch) + '</span>';
           }).join('<span class="spell-plus" aria-hidden="true">+</span>') + '</div>' +
           '<div class="slide-en">' + esc(showForm(p, key, forms[forms.length - 1])) + '</div>';
  } else {
    body = '<div class="slide-jp ' + formClass(forms[0]) + '">' + esc(showForm(p, key, forms[0])) + '</div>' +
           forms.slice(1).map(function (fm) {
             return '<div class="slide-form ' + formClass(fm) + '">' + esc(showForm(p, key, fm)) + '</div>';
           }).join("");
  }
  const pic = picFor(key) ? picImg(key, "slide-img")
            : (it.pic && !isGrammar ? '<span class="slide-pic" aria-hidden="true">' + it.pic + '</span>' : '');
  return '<div class="slide">' +
           '<span class="slide-count">' + (i + 1) + ' / ' + n + '</span>' +
           pic + body +
           (speech.can(key)
             ? '<button class="say big slide-say stage-replay" title="Hear it again" aria-label="Hear it again">\\U0001f50a</button>'
             : '<span class="slide-say quiet" aria-hidden="true">\\U0001f4d6</span>') +
           '<div class="row slide-ctl">' +
             '<button class="btn btn-sm stage-pause" title="Pause the sequence">' +
               (studyPlayer.paused ? '\\u25b6 Resume' : '\\u23f8 Pause') + '</button>' +
             '<button class="btn btn-sm stage-skip" title="Go to the next one">\\u23ed Next</button>' +
             '<button class="btn btn-ghost btn-sm stage-list" title="Stop and show the whole list">Skip to the list</button>' +
           '</div>' +
         '</div>';
}

/* Run the sequence inside `host`, which holds a .study-stage, a .study-list
   and a .study-play button. The stage shows while it runs; the list and the
   button take over when it ends. */
function startStudyPlay(p, host, lv) {
  stopStudyPlay();
  const mySeq = studyPlayer.seq;
  const stage = host.querySelector(".study-stage");
  const list = host.querySelector(".study-list");
  const playBtn = host.querySelector(".study-play");
  if (!stage) return;
  const items = (lv.kana || []).slice();
  studyPlayer.paused = false;
  studyPlayer.idx = 0;
  const alive = function () { return mySeq === studyPlayer.seq && document.body.contains(host); };

  const finish = function () {
    if (!alive()) return;
    stage.style.display = "none";
    stage.innerHTML = "";
    if (list) list.style.display = "";
    if (playBtn) playBtn.style.display = "";
  };

  const step = function () {
    if (!alive()) return;
    if (studyPlayer.idx >= items.length) { finish(); return; }
    const key = items[studyPlayer.idx];
    stage.innerHTML = slideHTML(p, lv, key, studyPlayer.idx, items.length);
    wireStage();
    // Hold after the sound: long enough to look, longer for a gentle pace.
    const hold = p.pace === "gentle" ? 1000 : 500;
    let advanced = false;
    const next = function () {
      if (advanced || !alive()) return;
      advanced = true;
      if (studyPlayer.timer) clearTimeout(studyPlayer.timer);
      studyPlayer.timer = setTimeout(function () {
        if (!alive() || studyPlayer.paused) return;
        studyPlayer.idx += 1;
        step();
      }, hold);
    };
    if (speech.can(key)) {
      speech.say(key, next);
      studyPlayer.timer = setTimeout(next, 2500);      // a clip that never ends must not stall the run
    } else {
      studyPlayer.timer = setTimeout(next, 1100);      // nothing to hear: time to read it
    }
  };

  function wireStage() {
    const pz = stage.querySelector(".stage-pause");
    if (pz) pz.onclick = function () {
      studyPlayer.paused = !studyPlayer.paused;
      if (studyPlayer.paused) {
        speech.stop();
        if (studyPlayer.timer) { clearTimeout(studyPlayer.timer); studyPlayer.timer = null; }
        pz.textContent = "\\u25b6 Resume";
      } else {
        step();                                        // the same item again, from the top
      }
    };
    const sk = stage.querySelector(".stage-skip");
    if (sk) sk.onclick = function () {
      speech.stop();
      if (studyPlayer.timer) { clearTimeout(studyPlayer.timer); studyPlayer.timer = null; }
      studyPlayer.paused = false;
      studyPlayer.idx += 1;
      step();
    };
    const ls = stage.querySelector(".stage-list");
    if (ls) ls.onclick = function () {
      speech.stop();
      if (studyPlayer.timer) { clearTimeout(studyPlayer.timer); studyPlayer.timer = null; }
      studyPlayer.idx = items.length;
      finish();
    };
    const rp = stage.querySelector(".stage-replay");
    if (rp) rp.onclick = function () { audio.prime(); speech.say(items[studyPlayer.idx]); };
  }

  stage.style.display = "";
  if (list) list.style.display = "none";
  if (playBtn) playBtn.style.display = "none";
  step();
}

// Both study hosts - the screen and the overlay - get the same wiring.
function wireStudyHost(p, host, lv) {
  const playBtn = host.querySelector(".study-play");
  if (playBtn) playBtn.onclick = function () { audio.prime(); startStudyPlay(p, host, lv); };
  startStudyPlay(p, host, lv);
}

function studyStageHTML() {
  return '<div class="study-stage" aria-live="polite"></div>' +
         '<button class="btn btn-sm study-play" style="display:none" title="Show and say every item again, one by one">\\u25b6 Play through</button>';
}

function studyRowsHTML(p, lvIn) {
  const lv = lvIn || levelInfo(p);""", "sequencer")

# ---------------------------------------------------------------- the screen
rep("""        '<h2>What this level asks</h2>' +
        '<div class="study-list">' + rows + '</div>' +""",
"""        '<h2>What this level asks</h2>' +
        studyStageHTML() +
        '<div class="study-list">' + rows + '</div>' +""", "study screen stage")

rep("""  document.getElementById("studyPlay").onclick = function () { startLevel(p); };
  document.getElementById("studyBack").onclick = function () { go("menu"); };
}""",
"""  document.getElementById("studyPlay").onclick = function () { startLevel(p); };
  document.getElementById("studyBack").onclick = function () { go("menu"); };
  wireStudyHost(p, screenEl, lv);
}""", "study screen wiring")

# ---------------------------------------------------------------- the overlay
rep("""      '<div class="study-list">' + studyRowsHTML(p) + '</div>' +
      '<p style="font-size:13px;text-align:center">Take your time — then the level starts over from the top.</p>' +""",
"""      studyStageHTML() +
      '<div class="study-list">' + studyRowsHTML(p, lv) + '</div>' +
      '<p style="font-size:13px;text-align:center">Take your time — then the level starts over from the top.</p>' +""",
    "overlay stage")

rep("""  document.body.appendChild(wrap);
  wrap.addEventListener("click", function (e) {
    if (e.target.id === "studyResume") { closeStudyOverlay(); startLevel(p); }
  });
}""",
"""  document.body.appendChild(wrap);
  wrap.addEventListener("click", function (e) {
    if (e.target.id === "studyResume") { closeStudyOverlay(); startLevel(p); }
  });
  wireStudyHost(p, wrap, lv);
}""", "overlay wiring")

rep("""function closeStudyOverlay() {
  const el = document.getElementById("studyOverlay");""",
"""function closeStudyOverlay() {
  stopStudyPlay();
  const el = document.getElementById("studyOverlay");""", "overlay close stops the run")

rep("""function go(name) {
  closeStudyOverlay();
  closeMapOverlay();""",
"""function go(name) {
  stopStudyPlay();
  closeStudyOverlay();
  closeMapOverlay();""", "go stops the run")

# ---------------------------------------------------------------- the look
rep(""".tipbtn { border-color: var(--yamabuki); color: var(--yamabuki); }""",
""".study-stage { display: flex; justify-content: center; }
.slide {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 10px;
  width: 100%; max-width: 420px; padding: 26px 20px 16px;
  border: 2px solid var(--ai); border-radius: var(--r-lg); background: var(--ai-wash);
  animation: settle .45s cubic-bezier(.2,1.3,.4,1) both;
}
.slide-count { position: absolute; top: 10px; left: 14px; font-size: 12px; font-weight: 800; color: var(--ink-faint); }
.slide-jp { font-family: var(--font-kana); font-weight: 900; font-size: clamp(44px, 12vw, 64px); line-height: 1.1; color: var(--ai); text-align: center; }
.slide-jp.sentence { font-size: clamp(22px, 6vw, 30px); line-height: 1.4; }
.slide-jp.romaji, .slide-form.romaji, .slide-form.en { font-family: var(--font-ui); }
.slide-form { font-size: 22px; font-weight: 800; color: var(--ink); }
.slide-en { font-size: 17px; font-weight: 700; color: var(--ink-soft); text-align: center; }
.slide-img { width: 150px; height: 150px; object-fit: cover; border-radius: 14px; border: 2px solid var(--paper); box-shadow: var(--shadow); }
.slide-pic { font-size: 64px; line-height: 1; }
.slide-say { margin-top: 2px; animation: lowpulse 1.1s ease-in-out infinite; }
.slide-say.quiet { font-size: 22px; opacity: .5; animation: none; }
.slide-ctl { margin-top: 6px; justify-content: center; }
.study-play { align-self: flex-start; }
.tipbtn { border-color: var(--yamabuki); color: var(--yamabuki); }""", "learn css")

io.open(f, "w", encoding="utf-8").write(s)
print("learn sequence applied")
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
