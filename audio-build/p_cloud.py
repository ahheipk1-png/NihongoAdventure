# -*- coding: utf-8 -*-
"""Cloud save in the game: the client half of functions/api/sync.js.

The rule the whole design follows: the game never waits for the network. Play
writes to localStorage exactly as it always did, and the cloud is a second,
slower copy that catches up a few seconds later. A computer with no internet
plays the same game; the Artifact build, whose CSP forbids every outside
request, simply hides the feature instead of erroring.
"""
import io, os, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"


def main():
    s = io.open(GAME, encoding="utf-8").read()
    assert "const cloud = (function" not in s, "already applied"

    def rep(old, new, note, count=1):
        nonlocal s
        assert s.count(old) == count, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- 1. the module -------------------------------------------------
    module = '''
/* ============================================================
   2b. CLOUD SAVE
   ============================================================ */

/* The same progress on the laptop and on the desktop, without an account.

   A family code minted by the server is the entire credential - a secret the
   way a share link is a secret - because the people typing it are seven. It is
   entered once on the second computer and never again.

   Nothing here is allowed to make the game wait. Every change is saved locally
   first, exactly as before; a few seconds later the same change is pushed, and
   what comes back is merged in. Two computers that both played offline both
   keep their afternoon: the server adds each one's earnings rather than
   picking a winner (see functions/api/sync.js for the rules).

   The Artifact build cannot reach the endpoint at all - its CSP blocks every
   outside request - so the first call fails and the feature hides itself. */

const cloud = (function () {
  const ENDPOINT = "/api/sync";
  const DEBOUNCE = 4000;
  let timer = null, busy = false, again = false;
  let reachable = null;            // null until the first call answers
  let note = "";                   // what the pill and the sheet say
  let lastSent = {};               // pid -> fingerprint of what was pushed
  let held = null;                 // a merged answer waiting for a safe moment

  function conf() {
    if (!state.cloud || typeof state.cloud !== "object") state.cloud = {};
    return state.cloud;
  }
  function code() { return conf().code || ""; }
  function on() { return !!code(); }
  function gone() {
    if (!state.gone || typeof state.gone !== "object") state.gone = {};
    return state.gone;
  }

  // Cheap enough to run on every save, exact enough that an unchanged profile
  // is never pushed twice.
  function mark(text) {
    let h = 5381;
    for (let i = 0; i < text.length; i++) h = ((h * 33) ^ text.charCodeAt(i)) >>> 0;
    return h + ":" + text.length;
  }

  // What the device is not entitled to send: its own sync bookkeeping.
  function outgoing(p) {
    const copy = {};
    Object.keys(p).forEach(function (k) { if (k !== "sync") copy[k] = p[k]; });
    return copy;
  }

  function post(body) {
    return fetch(ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (res) {
      const kind = res.headers.get("content-type") || "";
      // A deployment without the Function answers this path with the page
      // itself, or with a 405. Neither is the endpoint.
      if (kind.indexOf("json") === -1) throw new Error("not the sync endpoint");
      return res.json().then(function (data) { return { status: res.status, data: data }; });
    });
  }

  /* Merged profiles are copied INTO the objects the game already holds. A
     round in progress has a reference to its player, and swapping the object
     underneath it would send the rest of the round into a copy nobody saves. */
  function adopt(local, remote) {
    Object.keys(local).forEach(function (k) {
      if (k !== "sync" && !(k in remote)) delete local[k];
    });
    Object.keys(remote).forEach(function (k) { local[k] = remote[k]; });
    local.sync = { money: money(local), spent: spent(local) };
  }

  function playing() {
    return !!session && !session.ended &&
      ["match", "listen", "pairs", "fruit", "word", "fish"].indexOf(screen) !== -1;
  }

  function apply(data) {
    const seen = {};
    (data.profiles || []).forEach(function (rp) {
      if (!rp || !rp.id) return;
      seen[rp.id] = true;
      const mine = state.profiles.find(function (x) { return x.id === rp.id; });
      if (mine) adopt(mine, rp);
      else {
        rp.sync = { money: money(rp), spent: spent(rp) };
        state.profiles.push(rp);
      }
    });
    (data.gone || []).forEach(function (id) {
      state.profiles = state.profiles.filter(function (x) { return x.id !== id; });
      delete gone()[id];
    });
    // A profile that came from another computer may have completed a card set
    // this device has never paid for.
    state.profiles.forEach(function (p) {
      lastSent[p.id] = mark(JSON.stringify(outgoing(p)));
      if (typeof checkSets === "function") checkSets(p);
    });
    if (state.activeId && !state.profiles.some(function (x) { return x.id === state.activeId; })) {
      state.activeId = null;
    }
    conf().at = Date.now();
    save();
  }

  function stamp() {
    const at = conf().at;
    if (!at) return "";
    const mins = Math.round((Date.now() - at) / 60000);
    if (mins < 1) return "saved just now";
    if (mins === 1) return "saved a minute ago";
    if (mins < 60) return "saved " + mins + " minutes ago";
    const hrs = Math.round(mins / 60);
    return "saved " + hrs + (hrs === 1 ? " hour ago" : " hours ago");
  }

  function run(full) {
    if (!on() || busy || reachable === false) return Promise.resolve(false);
    busy = true;
    const body = { action: "sync", code: code(), profiles: [], base: {}, gone: [] };
    state.profiles.forEach(function (p) {
      const text = JSON.stringify(outgoing(p));
      if (full || lastSent[p.id] !== mark(text)) body.profiles.push(JSON.parse(text));
      const base = p.sync;
      if (base) body.base[p.id] = { money: money(base), spent: spent(base) };
    });
    Object.keys(gone()).forEach(function (id) { body.gone.push(id); });

    return post(body).then(function (res) {
      reachable = true;
      if (res.status === 404 && res.data && res.data.unknownCode) {
        // The family was deleted, or the code was mistyped into the save.
        note = "that code is not known any more";
        conf().code = "";
        save();
        return false;
      }
      if (!res.data || !res.data.ok) {
        note = (res.data && res.data.error) || "could not save to the cloud";
        return false;
      }
      // Never rearrange a player's world mid-round; hold it for the next
      // moment they are back on a menu.
      if (playing()) held = res.data; else apply(res.data);
      note = stamp();
      return true;
    }).catch(function () {
      if (reachable === null) reachable = false;   // no endpoint here at all
      note = navigator.onLine === false ? "offline - saved on this computer" : "will try again";
      return false;
    }).then(function (okFlag) {
      busy = false;
      if (again) { again = false; setTimeout(function () { run(false); }, 50); }
      return okFlag;
    });
  }

  return {
    on: on,
    code: code,
    ready: function () { return reachable !== false; },
    note: function () { return note || (on() ? stamp() : ""); },

    // Called from save(). Cheap, debounced, and never on the critical path.
    touch: function () {
      if (!on() || reachable === false) return;
      if (busy) { again = true; return; }
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(function () { timer = null; run(false); }, DEBOUNCE);
    },

    // Called when a round ends and it is safe to change what is on screen.
    settle: function () {
      if (!held) return false;
      const data = held;
      held = null;
      apply(data);
      return true;
    },

    forget: function (id) {
      gone()[id] = Date.now();
      save();
      this.flush();
    },

    flush: function () {
      if (timer) { window.clearTimeout(timer); timer = null; }
      return run(false);
    },

    start: function () {
      if (!on()) return Promise.resolve(false);
      return run(true).then(function (okFlag) { render(); return okFlag; });
    },

    // Mint a family for this computer and push everything it already has.
    begin: function () {
      return post({ action: "new" }).then(function (res) {
        reachable = true;
        if (!res.data || !res.data.ok || !res.data.code) throw new Error("no code");
        conf().code = res.data.code;
        conf().at = 0;
        save();
        return run(true);
      }).catch(function () {
        if (reachable === null) reachable = false;
        note = "could not reach the cloud";
        return false;
      });
    },

    // Join an existing family. Whatever is on this computer joins it too.
    join: function (raw) {
      const want = String(raw || "").toUpperCase().replace(/[^0-9A-Z]/g, "");
      if (want.length !== 8) { note = "a code is eight letters and numbers"; return Promise.resolve(false); }
      conf().code = want;
      conf().at = 0;
      lastSent = {};
      save();
      return run(true).then(function (okFlag) {
        if (!okFlag && !conf().code) note = "no family has that code";
        return okFlag;
      });
    },

    stop: function () {
      conf().code = "";
      conf().at = 0;
      lastSent = {};
      note = "";
      save();
    },

    // The top bar tells the truth in one glyph, and the tooltip in a sentence.
    pill: function () {
      if (!on() || reachable === false) return "";
      return '<span class="cloud-pill" title="Cloud save is on - ' + esc(stamp() || "saving") +
             '. This player opens with the same levels, stars and money on any computer.">' +
             '\\u2601</span>';
    }
  };
})();
'''
    rep("""function encodeState(data) {""", module.lstrip("\n") + "\nfunction encodeState(data) {", "cloud module")

    # ---- 2. save() also nudges the cloud --------------------------------
    rep("""function save() { store.write(state); }""",
        """function save() {
  // `touched` breaks ties on the name and the face when two computers both
  // edited a player; the cloud push itself is debounced and never blocks.
  const who = currentProfile();
  if (who) who.touched = Date.now();
  store.write(state);
  if (typeof cloud !== "undefined") cloud.touch();
}""", "save hook")

    # ---- 3. a wipe has to beat an older copy of the same player ---------
    rep("""function wipeRecord(p) {
  p.progress = { hiragana: { level: 0, boxes: {}, perfect: {} } };""",
        """function wipeRecord(p) {
  /* A cleared record is a decision, and the merge has to be able to tell it
     from a stale save - otherwise the other computer would hand every level
     and every dollar straight back. The stamp is what says "this is newer than
     anything you have". */
  p.wipe = Date.now();
  p.sync = { money: 0, spent: 0 };
  p.progress = { hiragana: { level: 0, boxes: {}, perfect: {} } };""", "wipe stamp")

    # ---- 4. deleting a player has to travel ------------------------------
    rep("""    if (!window.confirm("Delete " + p.name + " and all their progress?")) return;
    state.profiles = state.profiles.filter(function (x) { return x.id !== p.id; });
    state.activeId = null; draft = null; save(); go("home");""",
        """    if (!window.confirm("Delete " + p.name + " and all their progress?")) return;
    state.profiles = state.profiles.filter(function (x) { return x.id !== p.id; });
    // A missing row cannot say "deleted"; the other computer would just push
    // its copy back. The tombstone travels instead.
    cloud.forget(p.id);
    state.activeId = null; draft = null; save(); go("home");""", "delete tombstone")

    # ---- 5. a merged answer lands between rounds, never during one -------
    rep("""function go(name) {
  stopStudyPlay();""",
        """function go(name) {
  // Anything the cloud sent while a round was running is applied now, on the
  // way out of it, so nothing changes under a child mid-question.
  if (["match", "listen", "pairs", "fruit", "word", "fish"].indexOf(name) === -1) cloud.settle();
  stopStudyPlay();""", "settle on leaving a game")

    # ---- 6. the top bar pill ---------------------------------------------
    rep("""            '<button class="purse map" id="toMap" title="The map — build famous places with your money">🗾</button>';""",
        """            '<button class="purse map" id="toMap" title="The map — build famous places with your money">🗾</button>' +
            cloud.pill();""", "top bar pill")

    # ---- 7. the home screen sheet ----------------------------------------
    old_home = """      (state.profiles.length
        ? '<div class="row"><button class="btn btn-sm" id="saveLink">Save a link</button><span class="grow-label" id="saveMsg"></span></div>'
        : '') +"""
    new_home = """      cloudSheet() +
      (state.profiles.length
        ? '<div class="row"><button class="btn btn-sm" id="saveLink">Save a link</button><span class="grow-label" id="saveMsg"></span></div>'
        : '') +"""
    rep(old_home, new_home, "home sheet slot")

    sheet = '''
/* The only part of cloud save a family ever sees: one code, one button to
   copy it, one box to type it into on the other computer. Deliberately on the
   player-picking screen and nowhere else, so a child cannot wander into it. */
function cloudSheet() {
  if (!cloud.ready()) return "";
  if (!cloud.on()) {
    return '<div class="sheet stack">' +
             '<span class="eyebrow">Same progress on every computer</span>' +
             '<p class="fineprint">Turn this on and every player here is saved to the cloud. ' +
             'Type the code it gives you on another computer and the same levels, green stars, ' +
             'cards and money are waiting there.</p>' +
             '<div class="row">' +
               '<button class="btn btn-sm" id="cloudOn" title="Save every player here to the cloud and show the family code">Turn on cloud save</button>' +
               '<span class="grow-label">or</span>' +
               '<input class="code-in" id="cloudCode" maxlength="9" placeholder="CODE" ' +
                 'title="The eight-letter code from the computer you already set up" ' +
                 'aria-label="Family code" />' +
               '<button class="btn btn-sm" id="cloudJoin" title="Bring this family\\'s players onto this computer">Use this code</button>' +
             '</div>' +
             '<span class="grow-label" id="cloudMsg">' + esc(cloud.note()) + '</span>' +
           '</div>';
  }
  const c = cloud.code();
  return '<div class="sheet stack">' +
           '<span class="eyebrow">Cloud save is on</span>' +
           '<div class="row">' +
             '<span class="code-box" title="Your family code. Type it on another computer to bring these players across.">' +
               esc(c.slice(0, 4)) + '<i>-</i>' + esc(c.slice(4)) + '</span>' +
             '<button class="btn btn-sm" id="cloudCopy" title="Copy the family code">Copy</button>' +
             '<span class="grow-label" id="cloudMsg">' + esc(cloud.note()) + '</span>' +
           '</div>' +
           '<p class="fineprint">Anyone with this code can open these players, so keep it in the family. ' +
             '<button class="linkish" id="cloudOff" title="Stop saving to the cloud on this computer. Nothing already saved is deleted.">Stop syncing here</button></p>' +
         '</div>';
}

function wireCloud() {
  const msg = document.getElementById("cloudMsg");
  function say(t) { if (msg) msg.textContent = t; }

  const onBtn = document.getElementById("cloudOn");
  if (onBtn) onBtn.onclick = function () {
    onBtn.disabled = true;
    say("making a code…");
    cloud.begin().then(function () { render(); });
  };

  const joinBtn = document.getElementById("cloudJoin");
  if (joinBtn) joinBtn.onclick = function () {
    const input = document.getElementById("cloudCode");
    say("looking for that family…");
    cloud.join(input ? input.value : "").then(function (okFlag) {
      if (!okFlag) say(cloud.note() || "no family has that code");
      render();
    });
  };

  const copy = document.getElementById("cloudCopy");
  if (copy) copy.onclick = function () {
    const c = cloud.code();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(c).then(function () { say("code copied"); }, function () { say(c); });
    } else { say(c); }
  };

  const off = document.getElementById("cloudOff");
  if (off) off.onclick = function () {
    if (!window.confirm("Stop cloud save on this computer?\\n\\nThe players stay here and stay in the cloud. " +
        "You can turn it back on with the same code.")) return;
    cloud.stop();
    render();
  };
}
'''
    rep("""function renderHome() {""", sheet.lstrip("\n") + "\nfunction renderHome() {", "cloudSheet")

    rep("""  const link = document.getElementById("saveLink");
  if (link) link.onclick = function () {""",
        """  wireCloud();

  const link = document.getElementById("saveLink");
  if (link) link.onclick = function () {""", "wireCloud call")

    # ---- 8. styling -------------------------------------------------------
    css = """.cloud-pill {
  font-size: 14px; line-height: 1; padding: 6px 9px; border-radius: 999px;
  background: var(--ai-wash); color: var(--ai); border: 1px solid transparent;
}
.code-box {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 700;
  font-size: 20px; letter-spacing: 3px; padding: 8px 14px; border-radius: 12px;
  background: var(--ai-wash); color: var(--ai);
}
.code-box i { opacity: .45; font-style: normal; }
.code-in {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 700;
  font-size: 15px; letter-spacing: 2px; text-transform: uppercase; width: 8.5em;
  padding: 8px 10px; border-radius: 10px; border: 2px solid var(--line);
  background: var(--paper); color: var(--ink);
}
.code-in:focus { outline: none; border-color: var(--ai); }
.linkish {
  background: none; border: 0; padding: 0; font: inherit; color: var(--ai);
  text-decoration: underline; cursor: pointer;
}
"""
    rep(".study-arrow {", css + ".study-arrow {", "css")

    # ---- 9. boot: pull, and keep pushing at the right moments -------------
    rep("""  state.activeId = null;
  render();
  photos.start();""",
        """  state.activeId = null;
  /* The pull happens after the migration pass above, so anything that arrives
     from another computer is already in the shape this build expects. */
  cloud.start();
  window.addEventListener("online", function () { cloud.flush(); });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") cloud.flush();
  });
  render();
  photos.start();""", "boot start")

    io.open(GAME, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    io.open(os.path.join(os.path.dirname(GAME), "audio-build", "_check.js"), "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", os.path.join(os.path.dirname(GAME), "audio-build", "_check.js")],
                       capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:800])
    print("size: %.1f MB" % (os.path.getsize(GAME) / 1048576.0))


if __name__ == "__main__":
    main()
