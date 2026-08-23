# -*- coding: utf-8 -*-
"""The map: 47 prefectures as a cartoon tile map, ten famous places in each,
bought in order and raised through three stages, and a prefecture card for
every prefecture built in full. Reachable from anywhere via the top bar."""
import io, re, json, subprocess
f = r"C:\JapaneseLearning\kana-quest.html"
s = io.open(f, encoding="utf-8").read()
SC = r"C:\JapaneseLearning\audio-build"


def rep(a, b, note, count=1):
    global s
    n = s.count(a)
    assert n == count, "expected %d of (%s), found %d" % (count, note, n)
    s = s.replace(a, b, count)


# ---------------------------------------------------------------- the data
prefs = json.load(io.open(SC + r"\prefs.json", encoding="utf-8"))
sights = json.load(io.open(SC + r"\sights.json", encoding="utf-8"))
geo = "<script>window.GEO=" + json.dumps({"prefs": prefs, "sights": sights}, ensure_ascii=False, separators=(",", ":")) + ";</script>\n"
if "<script>window.GEO=" in s:
    s = re.sub(r"<script>window\.GEO=.*?</script>\n", lambda m: geo, s, count=1, flags=re.S)
else:
    i = s.index("<script>window.PICS=")
    s = s[:i] + geo + s[i:]

# ---------------------------------------------------------------- the model
rep("""function cardHome(key) { return CARD_HOME[key] || "hiragana"; }""",
"""/* The map's data: 47 prefectures and ten famous places in each, embedded as
   window.GEO so the artifact and the site carry the same list. */
const GEO = window.GEO || { prefs: [], sights: [] };
const PREFS = GEO.prefs;
const SIGHTS = GEO.sights;
const PREF_BY_ID = {}, PREF_BY_KANJI = {}, SIGHTS_BY_PREF = {}, SIGHT_BY_JP = {};
PREFS.forEach(function (r) { PREF_BY_ID[r.id] = r; PREF_BY_KANJI[r.kanji] = r; });
SIGHTS.forEach(function (sg) {
  (SIGHTS_BY_PREF[sg.pref] = SIGHTS_BY_PREF[sg.pref] || []).push(sg);
  SIGHT_BY_JP[sg.jp] = sg;
});
Object.keys(SIGHTS_BY_PREF).forEach(function (id) {
  SIGHTS_BY_PREF[id].sort(function (a, b) { return a.k - b.k; });
});

// A prefecture card lives in the collection under its kanji, so the card
// helpers need to know that key is a prefecture and not a word.
function cardHome(key) { return PREF_BY_KANJI[key] ? "pref" : (CARD_HOME[key] || "hiragana"); }

// The plain English name: the romaji without its suffix or its macrons.
function prefEnglish(r) {
  return r.romaji.replace(/-(ken|to|fu)$/, "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "");
}

const STAGES = ["Built", "Lit up", "Golden"];
const TYPE_EMOJI = { shrine: "\u26e9\ufe0f", temple: "\U0001f6d5", castle: "\U0001f3ef", tower: "\U0001f5fc",
                     bridge: "\U0001f309", modern: "\U0001f3e2", museum: "\U0001f3db\ufe0f", traditional: "\U0001f3d8\ufe0f",
                     garden: "\U0001f3de\ufe0f", station: "\U0001f689", stadium: "\U0001f3df\ufe0f", mountain: "\U0001f5fb" };

function sightsOf(pid) { return SIGHTS_BY_PREF[pid] || []; }
function sightStage(p, jp) { const v = (p.landmarks || {})[jp]; return typeof v === "number" ? v : 0; }
// Building costs $200 a step up the prefecture's list; each polish costs half.
function stagePrice(k, stage) { return (stage === 1 ? 200 : 100) * k; }
function prefBuilt(p, pid)  { return sightsOf(pid).filter(function (sg) { return sightStage(p, sg.jp) >= 1; }).length; }
function prefGolden(p, pid) { return sightsOf(pid).filter(function (sg) { return sightStage(p, sg.jp) >= 3; }).length; }
function nextSight(p, pid)  { return sightsOf(pid).filter(function (sg) { return sightStage(p, sg.jp) === 0; })[0] || null; }
function prefComplete(p, pid) { return sightsOf(pid).length > 0 && prefBuilt(p, pid) === sightsOf(pid).length; }
function totalBuilt(p)  { return SIGHTS.filter(function (sg) { return sightStage(p, sg.jp) >= 1; }).length; }
function totalGolden(p) { return SIGHTS.filter(function (sg) { return sightStage(p, sg.jp) >= 3; }).length; }
function prefCardsOwned(p) { return PREFS.filter(function (r) { return !!cards(p)[r.kanji]; }).length; }

/* The prefecture nearest its card: the most built among those not yet
   complete. A fresh player is pointed at the first tile so the map always
   has somewhere to go. */
function closestPref(p) {
  let best = null, bestN = -1;
  PREFS.forEach(function (r) {
    if (prefComplete(p, r.id)) return;
    const n = prefBuilt(p, r.id);
    if (n > bestN) { bestN = n; best = r; }
  });
  return best || PREFS[0] || null;
}

/* Build the next place in a prefecture, or raise one already built. Ordered
   building is what makes a prefecture a journey; upgrades are free choice.
   Returns what happened, or what was short. */
function advanceSight(p, jp) {
  const sg = SIGHT_BY_JP[jp];
  if (!sg) return null;
  const stage = sightStage(p, jp);
  if (stage >= 3) return null;
  if (stage === 0 && (nextSight(p, sg.pref) || {}).jp !== jp) return null;
  const price = stagePrice(sg.k, stage + 1);
  if (balance(p) < price) return { short: price - balance(p), price: price };
  pay(p, price);
  if (!p.landmarks) p.landmarks = {};
  p.landmarks[jp] = stage + 1;
  const out = { stage: stage + 1, price: price, card: null };
  const key = PREF_BY_ID[sg.pref].kanji;
  if (stage + 1 === 1 && prefComplete(p, sg.pref) && !cards(p)[key]) {
    cards(p)[key] = 1;                 // earned, never drawn
    out.card = key;
  }
  save();
  return out;
}""", "map model")

rep("""function cardValue(key) {
  const home = cardHome(key);
  let v = COURSE_CARD_VALUE[home] || 20;""",
"""function cardValue(key) {
  const home = cardHome(key);
  if (home === "pref") return 100;               // legendary, and only ever earned
  let v = COURSE_CARD_VALUE[home] || 20;""", "cardValue pref")

rep("""function cardFace(p, key) {
  const home = cardHome(key);""",
"""function cardFace(p, key) {
  const home = cardHome(key);
  if (home === "pref") {
    const r = PREF_BY_KANJI[key];
    return { jp: r.kanji, en: prefEnglish(r), kana: r.kana, pic: null };
  }""", "cardFace pref")

# ---------------------------------------------------------------- the screen
rep("""function renderTopics(p) {""",
"""/* ============================================================
   THE MAP
   A cartoon tile map of the 47 prefectures. Each tile is a prefecture in
   its true place on the grid; tap one and its ten places open beneath.
   ============================================================ */

let mapSel = null;            // the prefecture whose panel is open
let mapToast = null;          // one-render celebration after a build

function tileName(r) { return r.kanji.replace(/[\u770c\u5e9c\u90fd]$/, ""); }
function regionClass(r) { return "r-" + r.region.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase(); }

function mapHTML(p) {
  if (!mapSel || !PREF_BY_ID[mapSel]) mapSel = (closestPref(p) || {}).id;
  const close = closestPref(p);
  const sel = PREF_BY_ID[mapSel];
  const tiles = PREFS.map(function (r) {
    const built = prefBuilt(p, r.id), all = sightsOf(r.id).length;
    const hasCard = !!cards(p)[r.kanji];
    const top = sightsOf(r.id)[all - 1];
    const tip = r.kanji + " \u00b7 " + r.kana + " \u00b7 " + r.romaji + " \u2014 " + built + " of " + all + " built" +
                (hasCard ? " \u00b7 prefecture card won" : "") + (close && close.id === r.id ? " \u00b7 closest to a card" : "");
    return '<button class="ptile ' + regionClass(r) + (r.id === mapSel ? " sel" : "") +
             (close && close.id === r.id ? " pulse" : "") + (hasCard ? " carded" : "") +
             '" style="grid-column:' + (r.col + 1) + ';grid-row:' + (r.row + 1) + '" data-pref="' + r.id +
             '" title="' + esc(tip) + '" aria-label="' + esc(r.romaji) + '">' +
             '<span class="ptile-k" lang="ja">' + esc(tileName(r)) + '</span>' +
             '<span class="ptile-e" aria-hidden="true">' + (top ? (TYPE_EMOJI[top.type] || "\U0001f38c") : "\U0001f38c") + '</span>' +
             '<span class="ptile-n">' + (hasCard ? "\U0001f3b4" : built + "/" + all) + '</span>' +
           '</button>';
  }).join("");
  const nx = close ? nextSight(p, close.id) : null;
  const closeLine = close
    ? '<button class="btn btn-sm" id="mapJump" title="Jump to the prefecture nearest its card">' +
        '\U0001f3af Closest to a card: ' + esc(close.kanji) + ' ' + prefBuilt(p, close.id) + ' / ' + sightsOf(close.id).length +
        (nx ? ' \u00b7 next ' + esc(nx.jp) + ' ' + cash(stagePrice(nx.k, 1)) : '') + '</button>'
    : '';
  const n = prefCardsOwned(p);
  return '<div class="sheet stack">' +
      '<span class="eyebrow">\U0001f5fe Japan \u00b7 ' + n + ' prefecture card' + (n === 1 ? '' : 's') + ' \u00b7 ' +
        totalBuilt(p) + ' of ' + SIGHTS.length + ' built \u00b7 ' + totalGolden(p) + ' golden</span>' +
      '<h2>' + cash(balance(p)) + ' to spend</h2>' +
      '<p style="margin:0;font-size:13px">Tap a prefecture. Build its ten famous places in order, then light ' +
        'them up and gild them. Build all ten and its card is yours.</p>' +
      closeLine +
    '</div>' +
    '<div class="mapwrap"><div class="japan" role="group" aria-label="Map of Japan">' + tiles +
      '<span class="sea-deco" style="grid-column:3;grid-row:3" aria-hidden="true">\u26f5</span>' +
      '<span class="sea-deco" style="grid-column:6;grid-row:12" aria-hidden="true">\U0001f41f</span>' +
      '<span class="sea-deco" style="grid-column:13;grid-row:9" aria-hidden="true">\u26f5</span>' +
      '<span class="sea-deco" style="grid-column:1;grid-row:6" aria-hidden="true">\U0001f41f</span>' +
    '</div></div>' +
    (sel ? prefPanelHTML(p, sel) : '');
}

function prefPanelHTML(p, r) {
  const list = sightsOf(r.id);
  const nxt = nextSight(p, r.id);
  const hasCard = !!cards(p)[r.kanji];
  const rows = list.map(function (sg) {
    const st = sightStage(p, sg.jp);
    const isNext = !!(nxt && nxt.jp === sg.jp);
    const price = st < 3 ? stagePrice(sg.k, st + 1) : 0;
    const can = st < 3 && (st > 0 || isNext);
    const afford = balance(p) >= price;
    const label = st === 0 ? 'Build ' + cash(price) : STAGES[st] + ' ' + cash(price);
    const action = st >= 3
      ? '<span class="stop-gold">\u2728 Golden</span>'
      : can
        ? '<button class="btn btn-sm' + (afford ? ' btn-primary' : '') + '" data-adv="' + esc(sg.jp) + '"' +
          (afford ? ' title="' + esc(label) + '"' : ' disabled title="' + cash(price) + ' \u2014 you have ' + cash(balance(p)) + '"') + '>' +
          label + '</button>'
        : '<span class="stop-price" title="Build the places before it first">' + cash(price) + '</span>';
    const pips = st ? '<span class="stop-pips" aria-label="stage ' + st + ' of 3">' +
                      new Array(st + 1).join("\u25c6") + new Array(4 - st).join("\u25c7") + '</span>' : '';
    const tip = sg.jp + " \u00b7 " + sg.kana + " \u00b7 " + sg.en + " \u2014 " +
                (st ? STAGES[st - 1] : (isNext ? "next to build" : "build the ones before it first"));
    return '<div class="stop s' + st + (isNext ? ' next' : '') + '" title="' + esc(tip) + '">' +
      '<span class="stop-k">' + sg.k + '</span>' +
      '<span class="stop-emoji" aria-hidden="true">' + (TYPE_EMOJI[sg.type] || "\U0001f38c") +
        (st >= 2 ? '<i class="stop-lantern">\U0001f3ee</i>' : '') + '</span>' +
      '<span class="stop-main">' +
        '<span class="stop-jp" lang="ja">' + esc(sg.jp) + speakerBtn(p, sg.jp, null) + '</span>' +
        '<span class="stop-sub">' + esc(sg.kana) + ' \u00b7 ' + esc(sg.en) + '</span>' + pips +
      '</span>' +
      '<span class="stop-act">' + action + '</span>' +
    '</div>';
  }).join("");
  const toast = mapToast && mapToast.pref === r.id
    ? '<div class="maptoast' + (mapToast.card ? ' card' : '') + '">' + mapToast.text + '</div>' : '';
  mapToast = null;
  return '<div class="sheet stack prefpanel" id="prefPanel">' +
    '<div class="pref-head">' +
      '<span class="pref-kanji" lang="ja">' + esc(r.kanji) + '</span>' +
      '<span class="pref-read"><span class="pref-kana" lang="ja">' + esc(r.kana) + '</span>' +
        '<span class="pref-romaji">' + esc(r.romaji) + '</span></span>' +
      speakerBtn(p, r.kana, null).replace('class="say"', 'class="say big"') +
    '</div>' +
    '<p class="pref-meta">' + esc(r.region) + ' \u00b7 ' + prefBuilt(p, r.id) + ' of ' + list.length + ' built \u00b7 ' +
      prefGolden(p, r.id) + ' golden</p>' +
    toast +
    (hasCard ? '<div class="prefcard-won">\U0001f3b4 <strong>Prefecture card won</strong> \u2014 ' + esc(r.kanji) +
               ' is in your collection.</div>' : '') +
    '<div class="stoplist">' + rows + '</div>' +
  '</div>';
}

// Wire a rendered map, wherever it was rendered. `again` redraws the host.
function wireMap(p, host, again) {
  Array.prototype.forEach.call(host.querySelectorAll("[data-pref]"), function (b) {
    b.onclick = function () { mapSel = b.getAttribute("data-pref"); again(); };
  });
  const jump = host.querySelector("#mapJump");
  if (jump) jump.onclick = function () { const c = closestPref(p); if (c) { mapSel = c.id; again(); } };
  Array.prototype.forEach.call(host.querySelectorAll("[data-adv]"), function (b) {
    b.onclick = function () {
      audio.prime();
      const jp = b.getAttribute("data-adv");
      const r = advanceSight(p, jp);
      if (!r || r.short) { audio.bad(); return; }
      const sg = SIGHT_BY_JP[jp];
      mapSel = sg.pref;
      if (r.card) {
        audio.star();
        mapToast = { pref: sg.pref, card: true,
                     text: '\U0001f3b4 <strong>Prefecture card!</strong> All ten built \u2014 ' + esc(r.card) + ' joins your collection.' };
      } else {
        audio.good();
        mapToast = { pref: sg.pref, card: false,
                     text: (r.stage === 1 ? '\U0001f3d7\ufe0f Built ' : r.stage === 2 ? '\U0001f3ee Lit up ' : '\u2728 Golden \u2014 ') +
                           esc(sg.jp) + ' for ' + cash(r.price) + '.' };
      }
      if (speech.can(jp)) speech.say(jp);
      renderTopbar();
      again();
    };
  });
  // keep the chosen tile in view inside the map's own scroll box
  const t = host.querySelector(".ptile.sel"), wrap = host.querySelector(".mapwrap");
  if (t && wrap) {
    wrap.scrollLeft = t.offsetLeft - wrap.clientWidth / 2 + t.offsetWidth / 2;
    wrap.scrollTop  = t.offsetTop  - wrap.clientHeight / 2 + t.offsetHeight / 2;
  }
}

function renderMap(p) {
  screenEl.innerHTML =
    '<div class="stack">' + mapHTML(p) +
      '<div class="row"><button class="btn btn-ghost" id="mapBack">Back</button></div>' +
    '</div>';
  wireMap(p, screenEl, function () { renderMap(p); });
  document.getElementById("mapBack").onclick = function () { go("menu"); };
}

/* From inside a game the map must not throw the round away, so it opens as
   a pausing overlay - the same idea as the Learn overlay - and "Back to the
   game" resumes exactly where they were. */
function openMapOverlay(p) {
  if (!session || document.getElementById("mapOverlay")) return;
  session.studyOpen = true;
  session.paused = true;
  const wrap = document.createElement("div");
  wrap.className = "study-overlay";
  wrap.id = "mapOverlay";
  const draw = function () {
    wrap.innerHTML =
      '<div class="study-panel map-panel">' + mapHTML(p) +
        '<div class="row"><button class="btn btn-primary" id="mapResume">Back to the game \u2192</button></div>' +
      '</div>';
    wireMap(p, wrap, draw);
    document.getElementById("mapResume").onclick = function () { closeMapOverlay(); renderTopbar(); };
  };
  document.body.appendChild(wrap);
  draw();
}

function closeMapOverlay() {
  const el = document.getElementById("mapOverlay");
  if (el && el.parentNode) el.parentNode.removeChild(el);
  if (session && !document.getElementById("studyOverlay")) {
    session.studyOpen = false;
    session.paused = false;
  }
}

function renderTopics(p) {""", "map screen")

# ---------------------------------------------------------------- the ways in
rep("""function go(name) {
  closeStudyOverlay();""",
"""function go(name) {
  closeStudyOverlay();
  closeMapOverlay();""", "go tears down the overlay")

rep("""  else if (screen === "levels")  renderLevels(p);""",
"""  else if (screen === "levels")  renderLevels(p);
  else if (screen === "map")     renderMap(p);""", "route")

rep("""            '<button class="purse" id="toWallet" title="Cards collected \u2014 tap to open your wallet">' +
              '\U0001f0cf <span>' + cardCount(p) + '</span></button>';""",
"""            '<button class="purse" id="toWallet" title="Cards collected \u2014 tap to open your wallet">' +
              '\U0001f0cf <span>' + cardCount(p) + '</span></button>' +
            '<button class="purse map" id="toMap" title="The map \u2014 build famous places with your money">\U0001f5fe</button>';""",
    "top bar pill")

rep("""  const w = document.getElementById("toWallet");
  if (w) w.onclick = function () { stopLoops(); go("wallet"); };""",
"""  const w = document.getElementById("toWallet");
  if (w) w.onclick = function () { stopLoops(); go("wallet"); };
  const mp = document.getElementById("toMap");
  if (mp) mp.onclick = function () {
    audio.prime();
    const inGame = !!session && !session.ended &&
      ["match", "listen", "pairs", "fruit", "word", "fish"].indexOf(screen) !== -1;
    if (inGame) openMapOverlay(p); else { stopLoops(); go("map"); }
  };""", "top bar handler")

rep("""        (lv.index > 0 ? '<button class="btn" id="toLevels">\U0001f4dc Earlier levels</button>' : '') +""",
"""        (lv.index > 0 ? '<button class="btn" id="toLevels">\U0001f4dc Earlier levels</button>' : '') +
        '<button class="btn" id="toMapBtn">\U0001f5fe Map</button>' +""", "menu button")

rep("""  const tl = document.getElementById("toLevels");
  if (tl) tl.onclick = function () { go("levels"); };""",
"""  const tl = document.getElementById("toLevels");
  if (tl) tl.onclick = function () { go("levels"); };
  document.getElementById("toMapBtn").onclick = function () { go("map"); };""", "menu handler")

rep("""          ' different. Cards are worth more when the word is harder. Tap one to hear it.</p>' +""",
"""          ' different. Cards are worth more when the word is harder. Tap one to hear it.</p>' +
        '<p>\U0001f5fe <strong>' + prefCardsOwned(p) + '</strong> prefecture card' + (prefCardsOwned(p) === 1 ? '' : 's') +
          ' \u00b7 ' + totalBuilt(p) + ' of ' + SIGHTS.length + ' famous places built. ' +
          '<button class="btn btn-sm" id="wMap">Open the map</button></p>' +""", "wallet line")

rep("""  const wr = document.getElementById("wRoom");""",
"""  const wm = document.getElementById("wMap");
  if (wm) wm.onclick = function () { go("map"); };
  const wr = document.getElementById("wRoom");""", "wallet handler")

rep("""        '<button class="btn" id="toGarden">\U0001f331 Kana Garden</button>' +""",
"""        (s.starPay ? '<button class="btn" id="toMapR">\U0001f5fe Spend it on the map</button>' : '') +
        '<button class="btn" id="toGarden">\U0001f331 Kana Garden</button>' +""", "result button")

rep("""  document.getElementById("toGarden").onclick = function () { go("garden"); };
  document.getElementById("toMenu2").onclick = function () { go("menu"); };""",
"""  document.getElementById("toGarden").onclick = function () { go("garden"); };
  const tm = document.getElementById("toMapR");
  if (tm) tm.onclick = function () { go("map"); };
  document.getElementById("toMenu2").onclick = function () { go("menu"); };""", "result handler")

# ---------------------------------------------------------------- the look
rep(""".setlist { display: flex; flex-direction: column; gap: 8px; }""",
""".purse.map { padding: 6px 10px; font-size: 17px; }
.mapwrap {
  position: relative; overflow: auto; max-height: min(70vh, 720px);
  border: 1.5px solid var(--rule); border-radius: var(--r-lg); box-shadow: var(--shadow);
  background: var(--sea);
  background-image: repeating-radial-gradient(circle at 30% 40%, transparent 0 22px, var(--sea-wave) 22px 24px, transparent 24px 60px);
}
.japan {
  display: grid; grid-template-columns: repeat(13, 66px); grid-auto-rows: 66px; gap: 7px;
  padding: 22px; width: max-content;
}
.ptile {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
  border: 2.5px solid rgba(0,0,0,.12); border-radius: 14px; cursor: pointer; padding: 2px;
  font: inherit; color: var(--ink); box-shadow: 0 2px 0 rgba(0,0,0,.12);
  transition: transform .12s ease, box-shadow .12s ease;
}
.ptile:hover { transform: translateY(-2px); box-shadow: 0 4px 0 rgba(0,0,0,.14); }
.ptile:focus-visible { outline: 3px solid var(--ai); outline-offset: 2px; }
.ptile.sel { border-color: var(--ai); box-shadow: 0 0 0 3px var(--ai-wash), 0 2px 0 rgba(0,0,0,.12); }
.ptile.pulse { animation: ptpulse 1.6s ease-in-out infinite; }
.ptile.carded { border-color: var(--yamabuki); }
@keyframes ptpulse { 0%,100% { box-shadow: 0 0 0 0 var(--ai-wash), 0 2px 0 rgba(0,0,0,.12); } 50% { box-shadow: 0 0 0 7px var(--ai-wash), 0 2px 0 rgba(0,0,0,.12); } }
.ptile-k { font-family: var(--font-kana); font-weight: 800; font-size: 15px; line-height: 1; }
.ptile-e { font-size: 17px; line-height: 1; }
.ptile-n { font-size: 10px; font-weight: 800; color: var(--ink-soft); line-height: 1; }
.sea-deco { display: grid; place-items: center; font-size: 20px; opacity: .7; pointer-events: none; }
.r-hokkaido { background: var(--rg-hokkaido); } .r-tohoku { background: var(--rg-tohoku); }
.r-kanto { background: var(--rg-kanto); }       .r-chubu { background: var(--rg-chubu); }
.r-kansai { background: var(--rg-kansai); }     .r-chugoku { background: var(--rg-chugoku); }
.r-shikoku { background: var(--rg-shikoku); }   .r-kyushu { background: var(--rg-kyushu); }
.r-okinawa { background: var(--rg-okinawa); }
:root {
  --sea: #dcf0f7; --sea-wave: rgba(255,255,255,.55);
  --rg-hokkaido: #cfe6f5; --rg-tohoku: #d5efd5; --rg-kanto: #fde0c4; --rg-chubu: #efe4bf;
  --rg-kansai: #f7d3d3; --rg-chugoku: #e4d9f1; --rg-shikoku: #d6efe5; --rg-kyushu: #fbe7cb; --rg-okinawa: #cdeff0;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --sea: #0f2230; --sea-wave: rgba(255,255,255,.06);
    --rg-hokkaido: #24405a; --rg-tohoku: #24452c; --rg-kanto: #5a3a22; --rg-chubu: #4a4226;
    --rg-kansai: #552c2c; --rg-chugoku: #3d3256; --rg-shikoku: #234a3c; --rg-kyushu: #55402a; --rg-okinawa: #1f4a4c;
  }
}
:root[data-theme="dark"] {
  --sea: #0f2230; --sea-wave: rgba(255,255,255,.06);
  --rg-hokkaido: #24405a; --rg-tohoku: #24452c; --rg-kanto: #5a3a22; --rg-chubu: #4a4226;
  --rg-kansai: #552c2c; --rg-chugoku: #3d3256; --rg-shikoku: #234a3c; --rg-kyushu: #55402a; --rg-okinawa: #1f4a4c;
}
.pref-head { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.pref-kanji { font-family: var(--font-kana); font-weight: 900; font-size: clamp(34px, 9vw, 46px); line-height: 1; color: var(--ai); }
.pref-read { display: flex; flex-direction: column; gap: 2px; }
.pref-kana { font-family: var(--font-kana); font-weight: 700; font-size: 17px; }
.pref-romaji { font-size: 13px; color: var(--ink-soft); font-weight: 700; }
.pref-meta { margin: 0; font-size: 13px; color: var(--ink-faint); }
.prefcard-won { border: 1.5px solid var(--yamabuki); background: var(--yamabuki-wash); border-radius: var(--r-md); padding: 10px 14px; font-size: 14px; }
.maptoast { border: 1.5px solid var(--wakakusa); background: var(--wakakusa-wash); border-radius: var(--r-md); padding: 10px 14px; font-size: 14px; animation: pop .3s ease; }
.maptoast.card { border-color: var(--yamabuki); background: var(--yamabuki-wash); }
.stoplist { display: flex; flex-direction: column; gap: 8px; }
.stop {
  display: flex; align-items: center; gap: 10px;
  border: 1.5px solid var(--rule); border-radius: var(--r-md); padding: 9px 12px; background: var(--paper);
}
.stop.s0 { opacity: .62; }
.stop.s0.next { opacity: 1; border-color: var(--ai); background: var(--ai-wash); }
.stop.s2 { background: var(--yamabuki-wash); }
.stop.s3 { border-color: var(--yamabuki); box-shadow: 0 0 0 3px var(--yamabuki-wash); }
.stop.s3 .stop-jp { color: var(--yamabuki); }
.stop-k { flex: 0 0 auto; min-width: 22px; font-family: var(--font-kana); font-weight: 800; color: var(--ink-soft); text-align: center; }
.stop-emoji { flex: 0 0 auto; position: relative; font-size: 26px; line-height: 1; }
.stop.s0 .stop-emoji { filter: grayscale(1); }
.stop-lantern { position: absolute; right: -8px; top: -8px; font-size: 13px; font-style: normal; }
.stop-main { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.stop-jp { font-family: var(--font-kana); font-weight: 800; font-size: 16px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.stop-sub { font-size: 12px; color: var(--ink-faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stop-pips { font-size: 11px; letter-spacing: 2px; color: var(--yamabuki); }
.stop-act { flex: 0 0 auto; }
.stop-price { font-size: 12.5px; font-weight: 800; color: var(--ink-faint); }
.stop-gold { font-size: 12.5px; font-weight: 800; color: var(--yamabuki); }
.map-panel { max-width: 720px; }
.setlist { display: flex; flex-direction: column; gap: 8px; }""", "map css")

io.open(f, "w", encoding="utf-8").write(s)
print("map applied: %d prefectures, %d sights embedded" % (len(prefs), len(sights)))
js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
io.open(SC + r"\_check.js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", SC + r"\_check.js"], capture_output=True, text=True)
print("syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
