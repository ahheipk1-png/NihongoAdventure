/* The admin page itself, served at /admin.
 *
 * It is a Function rather than a file in the build output so that it lives in
 * the repository next to the endpoint it talks to, and so that the 5.8 MB game
 * is not the thing that has to grow every time this page changes. It holds no
 * game logic at all: every number it shows was written into the save by the
 * game, which is the only thing that knows what a level or a card is worth.
 */

const PAGE = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Nihongo Adventure - players</title>
<style nonce="__NONCE__">
  :root {
    --paper: #fbf7f0; --ink: #23201c; --faint: #7b7267; --line: #e6ded1;
    --ai: #b4462a; --wash: #f6e9e2; --good: #3f7d4e; --bad: #b03a2e;
    --card: #fffdf9;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper: #17151300; --ink: #f2ece2; --faint: #a79c8d; --line: #332e28;
      --ai: #e8825f; --wash: #2a211d; --card: #1e1b18;
    }
    body { background: #171513; }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px 16px 64px; background: var(--paper); color: var(--ink);
    font: 15px/1.55 ui-sans-serif, system-ui, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 1000px; margin: 0 auto; }
  h1 { font-size: 21px; margin: 0 0 2px; }
  .sub { color: var(--faint); font-size: 13px; margin: 0 0 22px; }
  .sheet {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 18px; margin-bottom: 16px;
  }
  label { display: block; font-size: 12px; color: var(--faint); margin: 0 0 4px; letter-spacing: .04em; text-transform: uppercase; }
  input, textarea, select {
    font: inherit; color: var(--ink); background: var(--paper);
    border: 2px solid var(--line); border-radius: 10px; padding: 8px 10px; width: 100%;
  }
  input:focus, textarea:focus { outline: none; border-color: var(--ai); }
  textarea { font-family: ui-monospace, Menlo, monospace; font-size: 12px; min-height: 220px; }
  button {
    font: inherit; font-weight: 600; cursor: pointer; border-radius: 10px;
    border: 2px solid var(--line); background: var(--paper); color: var(--ink); padding: 8px 14px;
  }
  button.primary { background: var(--ai); border-color: var(--ai); color: #fff; }
  button.danger { color: var(--bad); }
  button:disabled { opacity: .5; cursor: default; }
  .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
  .row > * { flex: 0 0 auto; }
  .grow { flex: 1 1 160px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { text-align: left; font-size: 11px; letter-spacing: .05em; text-transform: uppercase; color: var(--faint); padding: 6px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }
  td { padding: 9px 8px; border-bottom: 1px solid var(--line); vertical-align: middle; }
  tr:last-child td { border-bottom: 0; }
  tr.pick td { background: var(--wash); }
  .who { display: flex; align-items: center; gap: 8px; }
  .face { font-size: 20px; }
  .code {
    font-family: ui-monospace, Menlo, monospace; font-weight: 700; letter-spacing: 3px;
    font-size: 18px; background: var(--wash); color: var(--ai); padding: 4px 10px; border-radius: 8px;
  }
  .muted { color: var(--faint); }
  .warn { background: var(--wash); border-left: 4px solid var(--ai); padding: 10px 14px; border-radius: 0 10px 10px 0; font-size: 13px; }
  .opens { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; }
  .opens li { background: var(--wash); border-radius: 8px; padding: 3px 9px; font-size: 12px; }
  .bar { height: 7px; background: var(--line); border-radius: 99px; overflow: hidden; min-width: 70px; }
  .bar i { display: block; height: 100%; background: var(--ai); }
  .gone td { opacity: .5; }
  .pendtag { font-size: 11px; font-weight: 800; color: var(--ai); background: var(--wash); border-radius: 999px; padding: 2px 8px; }
  .btn.approve { padding: 3px 10px; font-size: 12px; background: var(--good); border-color: var(--good); color: #fff; }
  .msg { font-size: 13px; color: var(--faint); }
  .msg.bad { color: var(--bad); }
  .msg.good { color: var(--good); }
  .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
  .stat b { display: block; font-size: 19px; }
  .stat span { font-size: 12px; color: var(--faint); }
</style>
</head>
<body>
<div class="wrap">
  <h1>Nihongo Adventure</h1>
  <p class="sub">Every player in the cloud, what they have done, and when they last played.</p>

  <div class="sheet" id="gate">
    <div class="row">
      <div class="grow"><label for="pw">Password</label>
        <input id="pw" type="password" autocomplete="current-password" placeholder="password"></div>
      <button class="primary" id="in">Sign in</button>
    </div>
    <p class="msg" id="gateMsg"></p>
  </div>

  <div id="main" hidden>
    <div class="sheet" id="warnBox" hidden>
      <div class="warn"><b>This page is open to anyone who guesses the password.</b>
        Set a real one with<br>
        <code>npx -y wrangler@4 pages secret put ADMIN_PASSWORD --project-name nihongoadventure</code></div>
    </div>
    <div id="fams"></div>
    <div class="sheet" id="editor" hidden></div>
    <div class="row"><button id="out">Sign out</button>
      <button id="refresh">Refresh</button>
      <span class="msg" id="mainMsg"></span></div>
  </div>
</div>

<script nonce="__NONCE__">
var TOKEN = sessionStorage.getItem("nihongo-admin") || "";
var DATA = null, PICK = null;
// Redrawing the editor after a save would otherwise wipe the one line that
// tells the parent it worked, so it survives exactly one redraw.
var FLASH = null;

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function cash(n) { return "$" + String(Math.round(n || 0)).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ","); }
function when(t) {
  if (!t) return "never";
  var s = Math.round((Date.now() - t) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return Math.round(s / 60) + " min ago";
  if (s < 86400) return Math.round(s / 3600) + " h ago";
  if (s < 86400 * 7) return Math.round(s / 86400) + " days ago";
  return new Date(t).toLocaleDateString();
}
/* Everything the page shows came out of a save, and a save came from a request
   nobody had to authenticate. A field named "stars" is a number only because
   the game happened to write it; a stranger can write anything. */
function n(v, blank) {
  var x = Number(v);
  return (v == null || !isFinite(x)) ? (blank === undefined ? "-" : blank) : String(x);
}
function stamp(t) { return t ? new Date(t).toLocaleString() : ""; }

function api(payload) {
  payload.token = TOKEN;
  return fetch("/api/admin", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload)
  }).then(function (r) { return r.json().then(function (d) { d._status = r.status; return d; }); });
}

function say(id, text, kind) {
  var el = document.getElementById(id);
  el.textContent = text || "";
  el.className = "msg" + (kind ? " " + kind : "");
}

document.getElementById("in").onclick = function () {
  var pw = document.getElementById("pw").value;
  say("gateMsg", "checking…");
  fetch("/api/admin", { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ action: "login", password: pw }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (!d.ok) { say("gateMsg", d.error || "no", "bad"); return; }
      TOKEN = d.token;
      sessionStorage.setItem("nihongo-admin", TOKEN);
      document.getElementById("warnBox").hidden = !d.weak;
      say("gateMsg", "");
      load();
    })
    .catch(function () { say("gateMsg", "could not reach the server", "bad"); });
};
document.getElementById("pw").addEventListener("keydown", function (e) {
  if (e.key === "Enter") document.getElementById("in").click();
});
document.getElementById("out").onclick = function () {
  api({ action: "logout" });
  TOKEN = ""; sessionStorage.removeItem("nihongo-admin");
  document.getElementById("main").hidden = true;
  document.getElementById("gate").hidden = false;
};
document.getElementById("refresh").onclick = function () { load(); };

function load() {
  say("mainMsg", "loading…");
  return api({ action: "list" }).then(function (d) {
    if (!d.ok) {
      // Only a refused session sends you back to the door. "Slow down" and a
      // dropped connection are not reasons to throw the parent out.
      if (d._status === 401) {
        TOKEN = ""; sessionStorage.removeItem("nihongo-admin");
        document.getElementById("main").hidden = true;
        document.getElementById("gate").hidden = false;
        say("gateMsg", d.error || "sign in again", "bad");
      } else {
        say("mainMsg", d.error || "could not load", "bad");
      }
      return;
    }
    DATA = d.families;
    document.getElementById("gate").hidden = true;
    document.getElementById("main").hidden = false;
    drawFamilies();
    say("mainMsg", "as of " + new Date().toLocaleTimeString());
  });
}

function drawFamilies() {
  if (!DATA.length) {
    document.getElementById("fams").innerHTML =
      '<div class="sheet"><p class="muted">No family has turned cloud save on yet. ' +
      'Open the game, press <b>Turn on cloud save</b>, and this fills in.</p></div>';
    return;
  }
  document.getElementById("fams").innerHTML = DATA.map(function (f) {
    var rows = f.players.map(function (p) {
      var st = p.stat || {};
      var pct = st.items ? Math.round((st.mastered / st.items) * 100) : 0;
      return '<tr class="' + (p.deleted ? "gone" : "") + '" data-code="' + esc(f.code) + '" data-pid="' + esc(p.pid) + '">' +
        '<td><div class="who"><span class="face">' + esc(p.face) + '</span><b>' + esc(p.name) + '</b>' +
          (p.hasPw ? ' 🔒' : '') +
          (p.deleted ? ' <span class="muted">(deleted)</span>' : '') +
          (p.pending ? ' <span class="pendtag">waiting</span> ' +
            '<button class="btn approve" data-approve="' + esc(p.pid) + '" data-code="' + esc(f.code) + '">Approve</button>' : '') +
          '</div></td>' +
        '<td>' + esc(st.topic || p.course || "-") +
          (st.levels ? ' <span class="muted">' + n(st.level) + " / " + n(st.levels) + '</span>' : '') + '</td>' +
        '<td>' + (st.stars == null ? "-" : "\\u2605 " + n(st.stars)) + '</td>' +
        '<td>' + (st.items ? '<div class="bar" title="' + n(st.mastered) + " of " + n(st.items) +
          ' mastered"><i style="width:' + pct + '%"></i></div>' : "-") + '</td>' +
        '<td>' + (st.balance == null ? "-" : cash(st.balance)) + '</td>' +
        '<td>' + n(st.cards) + '</td>' +
        '<td title="' + esc(stamp(p.opens[0])) + '">' + when(p.opens[0]) + '</td>' +
        '<td title="' + esc(stamp(p.synced)) + '">' + when(p.synced) + '</td>' +
        '</tr>';
    }).join("");
    return '<div class="sheet">' +
      '<div class="row" style="margin-bottom:12px">' +
        '<span class="code">' + esc(f.code.slice(0, 4)) + "-" + esc(f.code.slice(4)) + '</span>' +
        '<span class="muted">' + f.players.length + ' player' + (f.players.length === 1 ? "" : "s") +
          ' &middot; last sync ' + when(f.seen) + '</span>' +
        '<span class="grow"></span>' +
        '<button class="danger" data-drop="' + esc(f.code) + '">Delete this family</button>' +
      '</div>' +
      '<table><thead><tr><th>Player</th><th>Topic</th><th>Stars</th><th>Mastered</th>' +
      '<th>Money</th><th>Cards</th><th>Last opened</th><th>Last synced</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>';
  }).join("");

  Array.prototype.forEach.call(document.querySelectorAll("tr[data-pid]"), function (tr) {
    tr.onclick = function () { open(tr.getAttribute("data-code"), tr.getAttribute("data-pid")); };
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-approve]"), function (b) {
    b.onclick = function (e) {
      e.stopPropagation();
      api({ action: "approve", code: b.getAttribute("data-code"), pid: b.getAttribute("data-approve") }).then(load);
    };
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-drop]"), function (b) {
    b.onclick = function (e) {
      e.stopPropagation();
      var code = b.getAttribute("data-drop");
      if (!confirm("Delete family " + code + " and every player in it?\\n\\nThis cannot be undone.")) return;
      api({ action: "dropFamily", code: code }).then(load);
    };
  });
}

function open(code, pid) {
  Array.prototype.forEach.call(document.querySelectorAll("tr[data-pid]"), function (tr) {
    tr.className = (tr.getAttribute("data-pid") === pid && tr.getAttribute("data-code") === code)
      ? "pick" : (tr.className.indexOf("gone") !== -1 ? "gone" : "");
  });
  api({ action: "get", code: code, pid: pid }).then(function (d) {
    if (!d.ok) { say("mainMsg", d.error || "could not open that player", "bad"); return; }
    PICK = { code: code, pid: pid, data: d.data, rev: d.rev, deleted: d.deleted };
    drawEditor();
    document.getElementById("editor").scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
}

function drawEditor() {
  var p = PICK.data || {}, st = p.stat || {};
  var flash = FLASH;
  FLASH = null;
  var courses = Object.keys(p.progress || {});
  var opens = (p.opens || []).map(function (t) {
    return "<li title=" + JSON.stringify(stamp(t)) + ">" + esc(when(t)) + "</li>";
  }).join("") || '<li class="muted">never opened on a computer with cloud save on</li>';

  var levels = courses.map(function (cid) {
    var g = p.progress[cid] || {};
    var stars = Object.keys(g.perfect || {}).filter(function (k) { return g.perfect[k]; }).length;
    return '<tr><td>' + esc(cid) + '</td>' +
      '<td style="width:120px"><input type="number" min="1" data-level="' + esc(cid) + '" value="' +
        (n(g.level, 0) + 1) + '" data-was="' + (n(g.level, 0) + 1) + '"></td>' +
      '<td>\\u2605 ' + stars + '</td>' +
      '<td><button data-clear="' + esc(cid) + '">Clear stars</button></td></tr>';
  }).join("");

  document.getElementById("editor").hidden = false;
  document.getElementById("editor").innerHTML =
    '<div class="row" style="margin-bottom:14px">' +
      '<span class="face" style="font-size:28px">' + esc(p.face) + '</span>' +
      '<h1 style="margin:0">' + esc(p.name) + '</h1>' +
      '<span class="grow muted">' + esc(PICK.code) + ' &middot; ' + esc(PICK.pid) +
        ' &middot; revision ' + PICK.rev + (PICK.deleted ? ' &middot; deleted' : '') + '</span>' +
    '</div>' +

    '<div class="cols" style="margin-bottom:16px">' +
      '<div class="stat"><b>' + esc(st.topic || "-") + '</b><span>level ' + n(st.level, "?") +
        ' of ' + n(st.levels, "?") + '</span></div>' +
      '<div class="stat"><b>\\u2605 ' + n(st.stars) + '</b><span>green stars</span></div>' +
      '<div class="stat"><b>' + n(st.mastered) + '</b><span>of ' +
        n(st.items, "?") + ' mastered</span></div>' +
      '<div class="stat"><b>' + (st.balance == null ? "-" : cash(st.balance)) + '</b><span>to spend</span></div>' +
      '<div class="stat"><b>' + n(st.cards) + '</b><span>cards</span></div>' +
      '<div class="stat"><b>' + n(st.sights) + '</b><span>places built</span></div>' +
    '</div>' +

    '<p class="muted" style="font-size:12px;margin:0 0 14px">The six numbers above are what ' +
      'the game itself last reported. They catch up the next time this player is opened on a ' +
      'computer, not the moment you save here.</p>' +
    '<label>Last few times this player was opened</label>' +
    '<ul class="opens" style="margin-bottom:16px">' + opens + '</ul>' +

    '<div class="row" style="margin-bottom:14px">' +
      '<div style="width:170px"><label for="eName">Name</label>' +
        '<input id="eName" value="' + esc(p.name) + '"></div>' +
      '<div style="width:110px"><label for="eFace">Face</label>' +
        '<input id="eFace" value="' + esc(p.face) + '"></div>' +
      '<div style="width:150px"><label for="eMoney">Earned, total</label>' +
        '<input id="eMoney" type="number" value="' + n(p.money, "0") + '"></div>' +
      '<div style="width:150px"><label for="eSpent">Spent, total</label>' +
        '<input id="eSpent" type="number" value="' + n(p.spent, "0") + '"></div>' +
    '</div>' +

    (courses.length ? '<label>Level in each topic</label><table style="margin-bottom:14px"><tbody>' +
      levels + '</tbody></table>' : '') +

    '<details style="margin-bottom:14px"><summary class="muted">The whole save, as it is stored</summary>' +
      '<textarea id="eRaw" spellcheck="false">' + esc(JSON.stringify(p, null, 1)) + '</textarea></details>' +

    '<div class="row">' +
      '<button class="primary" id="eSave">Save</button>' +
      (PICK.data && PICK.data.pending ? '<button class="approve" id="eApprove">Approve player</button>' : '') +
      (PICK.data && PICK.data.pw ? '<button id="eClearPw">Reset password</button>' : '') +
      (PICK.deleted ? '<button id="eRestore">Restore</button>'
                    : '<button class="danger" id="eDrop">Delete this player</button>') +
      '<button id="eClose">Close</button>' +
      '<span class="msg' + (flash ? " " + flash.kind : "") + '" id="eMsg">' +
        esc(flash ? flash.text : "Saving here overrules the children\\u2019s computers " +
            "the next time they sync.") + '</span>' +
    '</div>';

  Array.prototype.forEach.call(document.querySelectorAll("[data-clear]"), function (b) {
    b.onclick = function () {
      var cid = b.getAttribute("data-clear");
      if (!confirm("Clear every green star in " + cid + "?")) return;
      PICK.data.progress[cid].perfect = {};
      drawEditor();
      say("eMsg", "stars cleared - press Save to keep it", "good");
    };
  });

  document.getElementById("eClose").onclick = function () {
    document.getElementById("editor").hidden = true; PICK = null;
  };
  var appr = document.getElementById("eApprove");
  if (appr) appr.onclick = function () {
    api({ action: "approve", code: PICK.code, pid: PICK.pid }).then(function () {
      load().then(function () { open(PICK.code, PICK.pid); });
    });
  };
  var clr = document.getElementById("eClearPw");
  if (clr) clr.onclick = function () {
    if (!confirm("Reset this player's password? They will be able to open with no password until a new one is set.")) return;
    api({ action: "clearpw", code: PICK.code, pid: PICK.pid }).then(function () {
      load().then(function () { open(PICK.code, PICK.pid); });
    });
  };
  var drop = document.getElementById("eDrop");
  if (drop) drop.onclick = function () {
    if (!confirm("Delete " + PICK.data.name + "?\\n\\nThey disappear from every computer at the next sync.")) return;
    api({ action: "drop", code: PICK.code, pid: PICK.pid }).then(function () {
      document.getElementById("editor").hidden = true; PICK = null; load();
    });
  };
  var back = document.getElementById("eRestore");
  if (back) back.onclick = function () {
    api({ action: "restore", code: PICK.code, pid: PICK.pid }).then(function () { load(); });
  };

  document.getElementById("eSave").onclick = function () {
    var raw = document.getElementById("eRaw").value, next;
    try { next = JSON.parse(raw); } catch (e) { say("eMsg", "that JSON will not parse: " + e.message, "bad"); return; }
    /* The boxes above and the JSON below are two views of one save, and a
       parent who edited the JSON meant it. So a box only overrules the text if
       the box itself was changed. */
    function typed(id, was) {
      var el = document.getElementById(id);
      return el && el.value !== String(was) ? el.value : null;
    }
    var nm = typed("eName", p.name); if (nm !== null && nm.trim()) next.name = nm.trim();
    var fc = typed("eFace", p.face); if (fc !== null && fc.trim()) next.face = fc.trim();
    var mn = typed("eMoney", n(p.money)); if (mn !== null) next.money = Number(mn) || 0;
    var sp = typed("eSpent", n(p.spent)); if (sp !== null) next.spent = Number(sp) || 0;
    Array.prototype.forEach.call(document.querySelectorAll("[data-level]"), function (i) {
      var cid = i.getAttribute("data-level");
      if (i.value === i.getAttribute("data-was")) return;
      if (next.progress && next.progress[cid]) {
        next.progress[cid].level = Math.max(0, (Number(i.value) || 1) - 1);
      }
    });
    say("eMsg", "saving…");
    api({ action: "put", code: PICK.code, pid: PICK.pid, data: next, rev: PICK.rev }).then(function (d) {
      if (!d.ok) { say("eMsg", d.error || "could not save", "bad"); return; }
      FLASH = { text: "Saved. The children's computers take this at their next sync.", kind: "good" };
      load().then(function () { open(PICK.code, PICK.pid); });
    });
  };
}

if (TOKEN) load();
</script>
</body>
</html>
`;

/* A nonce, and a policy that allows nothing else.

   Escaping is the fix for injected markup and this is the belt to its braces:
   under a script-src nonce, an onerror= that slipped through would sit
   in the page inert, because an inline event handler is not a nonced script. */
export async function onRequestGet() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let nonce = "";
  for (let i = 0; i < bytes.length; i++) nonce += bytes[i].toString(16).padStart(2, "0");
  return new Response(PAGE.split("__NONCE__").join(nonce), {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex, nofollow",
      "referrer-policy": "no-referrer",
      "content-security-policy":
        "default-src 'none'; script-src 'nonce-" + nonce + "'; style-src 'nonce-" + nonce + "'; " +
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    }
  });
}
