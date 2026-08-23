# -*- coding: utf-8 -*-
"""The card is won on a wheel the player stops. The tap decides it - read from
the wheel's rendered angle, the thing the child is actually looking at - and
the settle only turns the wheel to face what was decided."""
import io, re, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()


def rep(a, b, note):
    global s
    n = s.count(a)
    assert n == 1, "expected 1 of (%s), found %d" % (note, n)
    s = s.replace(a, b, 1)


rep("""function awardCard(p) {
  const paid = room.kind === "room";
  const perfect = room.missed === 0 && !room.restarts && room.need > 0;
  const tries = [drawCard(p, { preferNew: paid }), drawCard(p, { preferNew: paid })];
  if (paid && perfect) tries.push(drawCard(p, { preferNew: true }));
  const key = tries.filter(Boolean).sort(function (x, y) {
    return cardValue(y) - cardValue(x);
  })[0];
  if (!key) { go("menu"); return; }
  const already = !!cards(p)[key];
  cards(p)[key] = (cards(p)[key] || 0) + 1;
  // A second copy is not a dead end: the wallet counts every copy, so a
  // duplicate still makes the collection worth more.
  room.prize = { key: key, already: already, perfect: paid && perfect,
                 gain: cardValue(key) };
  save();
  renderTopbar();          // the badges are about to be read against the prize
  audio.star();
}""",
"""const WHEEL_SLICES = 6;      // six is readable on a phone; eight is a blur

/* The cards that go on the wheel. Drawing several and showing them all is what
   turns a hidden roll into something a child can see the shape of: they can
   read the prices before they stop it. A clean run draws extra candidates and
   keeps the dearest, so playing well visibly improves the wheel rather than
   silently improving a number. */
function wheelKeys(p) {
  const paid = room.kind === "room";
  const perfect = room.missed === 0 && !room.restarts && room.need > 0;
  const seen = {}, keys = [];
  const add = function (k) { if (k && !seen[k]) { seen[k] = 1; keys.push(k); } };
  for (let i = 0; i < 60 && keys.length < WHEEL_SLICES; i++) add(drawCard(p, { preferNew: paid }));
  if (perfect) {
    for (let i = 0; i < 30 && keys.length < WHEEL_SLICES + 3; i++) add(drawCard(p, { preferNew: true }));
    keys.sort(function (x, y) { return cardValue(y) - cardValue(x); });
    keys.length = Math.min(keys.length, WHEEL_SLICES);
  }
  // A small pool repeats what it has rather than showing a gap.
  const n0 = keys.length;
  while (n0 && keys.length < WHEEL_SLICES) keys.push(keys[keys.length % n0]);
  return shuffle(keys);
}

// Questions are over: bring out the wheel. Nothing is granted until it stops.
function awardCard(p) {
  const keys = wheelKeys(p);
  if (!keys.length) { go("menu"); return; }
  room.wheel = {
    keys: keys,
    perfect: room.kind === "room" && room.missed === 0 && !room.restarts && room.need > 0,
    stopping: false, landed: null,
    step: 0, ticker: null          // the reduced-motion wheel steps instead of spinning
  };
}

/* The angle the wheel is actually drawn at. Reading the rendered transform,
   rather than a clock, means the outcome is the picture the child stopped -
   a re-render restarts the CSS animation but not any clock, so the two drift. */
function wheelAngle(el) {
  const m = el ? getComputedStyle(el).transform : "";
  const v = m && m.match(/matrix\\(([^)]+)\\)/);
  if (!v) return 0;
  const a = v[1].split(",").map(parseFloat);
  let deg = Math.atan2(a[1], a[0]) * 180 / Math.PI;
  if (deg < 0) deg += 360;
  return deg;
}

// Which slice sits under a pin fixed at the top when the wheel has turned `deg`
// clockwise: the slice whose own angle is 360 - deg.
function wheelIndexAt(deg) {
  const slice = 360 / WHEEL_SLICES;
  return Math.floor(((360 - (deg % 360)) % 360) / slice) % WHEEL_SLICES;
}

// The card actually joins the collection here, once the wheel has stopped.
function landCard(p, key) {
  const already = !!cards(p)[key];
  cards(p)[key] = (cards(p)[key] || 0) + 1;
  // A second copy is not a dead end: the wallet counts every copy, so a
  // duplicate still makes the collection worth more.
  room.prize = { key: key, already: already,
                 perfect: !!(room.wheel && room.wheel.perfect),
                 gain: cardValue(key) };
  room.wheel = null;
  save();
  renderTopbar();          // the badges are about to be read against the prize
  audio.star();
}""", "wheel model")

rep("""  if (room.prize) {
    const key = room.prize.key, face = cardFace(p, key);""",
"""  /* The wheel. It spins under its own CSS animation until the child stops it;
     the tap picks the slice, and the settle only turns the wheel to face what
     was already decided. */
  if (room.wheel) {
    const w = room.wheel;
    const runId = room.id;
    const slice = 360 / WHEEL_SLICES;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const stops = [], labels = [];
    w.keys.forEach(function (k, i) {
      const v = cardValue(k), rar = cardRarity(v), jp = cardFace(p, k).jp;
      stops.push('var(--wheel-' + rar + ') ' + (i * slice) + 'deg ' + ((i + 1) * slice) + 'deg');
      labels.push('<span class="wheel-slot" style="transform:rotate(' + (i * slice + slice / 2) + 'deg)">' +
                    '<span class="wheel-slot-in">' +
                      '<span class="wheel-jp' + (jp.length > 3 ? ' long' : '') + '">' + esc(jp) + '</span>' +
                      '<span class="wheel-val">' + cash(v) + '</span>' +
                    '</span></span>');
    });

    screenEl.innerHTML =
      '<div class="stack">' +
        '<div class="sheet stack" style="align-items:center;gap:14px">' +
          '<span class="eyebrow">' +
            (room.need
              ? (room.done >= room.need ? room.need + ' questions answered'
                                        : room.done + ' of ' + room.need + ' answered')
              : 'Level passed') +
            (w.perfect ? ' \u00b7 not one missed' : '') + '</span>' +
          '<h2 style="text-align:center">\U0001f3a1 Stop the wheel</h2>' +
          '<p style="text-align:center;font-size:13px;margin:0">' +
            'Six cards, six prices. Tap <b>STOP</b> and you keep whatever the pin lands on.' +
            (w.perfect ? ' A clean run put dearer cards on it.' : '') + '</p>' +
          '<div class="wheel-wrap">' +
            '<span class="wheel-pin" aria-hidden="true"></span>' +
            '<div class="wheel' + (w.stopping ? ' settling' : (reduce ? '' : ' spinning')) + '" id="wheel" ' +
              'style="background:conic-gradient(' + stops.join(",") + ')">' +
              labels.join("") +
            '</div>' +
            '<span class="wheel-hub" aria-hidden="true">\U0001f0cf</span>' +
          '</div>' +
          '<button class="btn btn-primary wheel-stop" id="wheelStop"' +
            (w.stopping ? ' disabled' : '') + '>' +
            (w.stopping ? 'Slowing\u2026' : 'STOP') + '</button>' +
        '</div>' +
      '</div>';

    const el = document.getElementById("wheel");

    // Reduced motion: the CSS animation is clamped to nothing, so step the
    // wheel by hand - one slice at a time - and take the index from the step.
    if (reduce && !w.stopping && el) {
      if (w.ticker) clearInterval(w.ticker);
      w.ticker = setInterval(function () {
        if (!(screen === "room" && room && room.wheel === w)) { clearInterval(w.ticker); w.ticker = null; return; }
        w.step = (w.step + 1) % WHEEL_SLICES;
        const node = document.getElementById("wheel");
        if (node) node.style.transform = "rotate(" + (w.step * slice) + "deg)";
      }, 450);
    }

    if (!w.stopping) {
      document.getElementById("wheelStop").onclick = function () {
        audio.prime();
        let cur;
        if (w.ticker) { clearInterval(w.ticker); w.ticker = null; cur = (w.step * slice) % 360; }
        else cur = wheelAngle(el);
        const idx = wheelIndexAt(cur);
        const key = w.keys[idx];
        w.stopping = true;
        w.landed = key;
        const btn = document.getElementById("wheelStop");
        if (btn) { btn.disabled = true; btn.textContent = "Slowing\u2026"; }
        if (el) {
          // Freeze at the angle it is really at, then ease two more turns
          // round to the won slice - no snap back to zero on the way.
          el.style.transform = "rotate(" + cur + "deg)";
          el.classList.remove("spinning");
          void el.offsetWidth;
          el.classList.add("settling");
          const target = cur + ((360 - ((cur + idx * slice + slice / 2) % 360)) % 360) + 720;
          el.style.transform = "rotate(" + target + "deg)";
        }
        setTimeout(function () {
          if (!(screen === "room" && room && room.id === runId && room.wheel === w)) return;
          landCard(p, key);
          renderRoom(p);
        }, 1500);
      };
    }
    return;
  }

  if (room.prize) {
    const key = room.prize.key, face = cardFace(p, key);""", "wheel screen")

rep(""".drawcard.common    { border-color: var(--rule-strong); }""",
""".wheel-wrap { position: relative; width: min(300px, 80vw); aspect-ratio: 1; margin-top: 8px; }
.wheel {
  position: absolute; inset: 0; border-radius: 50%;
  border: 5px solid var(--paper);
  box-shadow: 0 0 0 3px var(--rule-strong), var(--shadow);
  will-change: transform;
}
.wheel.spinning { animation: wheelspin 1300ms linear infinite; }
.wheel.settling { transition: transform 1.4s cubic-bezier(.15,.85,.2,1); }
@keyframes wheelspin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.wheel-slot { position: absolute; inset: 0; display: flex; justify-content: center; pointer-events: none; }
.wheel-slot-in {
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  margin-top: 11%; color: var(--ink); text-shadow: 0 1px 0 rgba(255,255,255,.5);
}
.wheel-jp  { font-family: var(--font-kana); font-weight: 800; font-size: 17px; line-height: 1; }
.wheel-jp.long { font-size: 12px; }
.wheel-val { font-size: 11px; font-weight: 800; opacity: .8; }
.wheel-pin {
  position: absolute; top: -13px; left: 50%; transform: translateX(-50%);
  border-left: 11px solid transparent; border-right: 11px solid transparent;
  border-top: 20px solid var(--shu); z-index: 3;
  filter: drop-shadow(0 1px 1px rgba(0,0,0,.25));
}
.wheel-hub {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  width: 54px; height: 54px; border-radius: 50%; background: var(--paper);
  border: 3px solid var(--rule-strong); display: grid; place-items: center;
  font-size: 22px; z-index: 2;
}
.wheel-stop { min-width: 148px; font-size: 17px; letter-spacing: .06em; }
:root { --wheel-common: #e8e2d4; --wheel-rare: #cfe0f2; --wheel-epic: #f7e3ae; --wheel-legendary: #f6c9bf; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --wheel-common: #3a3a44; --wheel-rare: #22364f; --wheel-epic: #4a3d16; --wheel-legendary: #4a2420; }
}
:root[data-theme="dark"] { --wheel-common: #3a3a44; --wheel-rare: #22364f; --wheel-epic: #4a3d16; --wheel-legendary: #4a2420; }
.drawcard.common    { border-color: var(--rule-strong); }""", "wheel css")

io.open(f, "w", encoding="utf-8").write(s)
print("wheel applied")

js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(r"C:\JapaneseLearning\audio-build\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", r"C:\JapaneseLearning\audio-build\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
