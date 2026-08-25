# -*- coding: utf-8 -*-
"""Cloud save on by default - no button to press.

The database was empty because saving to it was opt-in and nobody ever pressed
"Turn on cloud save". Now every player is saved automatically: the first time a
computer has a player and can reach the cloud, it mints a family code by itself
and syncs from then on. The code is shown on the home screen so it can be typed
on another computer, and typing an existing code still brings a family across.

The design review of this change flagged six ways an on-by-default default can
bite, and every one is guarded here:

  1. "off" is remembered. "Stop syncing here" sets it, so a parent who turns
     sync off is not overruled by the device re-minting on the next save.
  2. It never mints on an empty computer. Zero players and no code is exactly a
     fresh second computer - the one moment to type the family code instead of
     starting a rival family - so it waits for a player to exist.
  3. The mint is single-flight. save() can fire several times a second; a
     `minting` latch means that becomes one code, not five.
  4. The family code never rides the "Save a link" URL any more - a credential
     in a link ends up in history and bookmarks. encodeState drops it, and boot
     keeps the real code rather than letting a restored link wipe it.
  5. Joining a code clears the old baseline, so money does not merge against a
     different family's numbers.
  6. A finished level flushes at once, so the star and the money are in the
     database seconds after they are earned, not whenever four idle seconds
     happen to pass.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
MIRROR = r"C:\JapaneseLearning\index.html"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- 1. off flag + minting latch, in the cloud closure --------------
    rep("""  let timer = null, chain = Promise.resolve(false), applying = false;""",
        """  let timer = null, chain = Promise.resolve(false), applying = false;
  let minting = false;              // single-flight the auto-mint""", "latch")

    rep("""  function code() { return conf().code || ""; }
  function on() { return !!code(); }""",
        """  function code() { return conf().code || ""; }
  function on() { return !!code(); }
  // A deliberate "Stop syncing here" is remembered, so the device does not just
  // mint a new code on the next save and undo the choice.
  function off() { return !!conf().off; }""", "off getter")

    # ---- 2. the auto-mint, and touch() drives it -----------------------
    rep("""    // Called from save(). Cheap, debounced, and never on the critical path.
    touch: function () {
      if (!on() || reachable === false || applying) return;
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(function () { timer = null; queue(false); }, DEBOUNCE);
    },""",
        """    // Called from save(). Cheap, debounced, and never on the critical path.
    // With no code yet, this is also where saving turns itself on.
    touch: function () {
      if (applying) return;
      if (!on()) { this.auto(); return; }
      if (reachable === false) return;
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(function () { timer = null; queue(false); }, DEBOUNCE);
    },

    /* Turn saving on by itself, once, the first time there is something to
       save and a cloud to save it to. Not on an empty computer - that is a
       fresh second machine, and it should be offered the family code rather
       than start a second family - and not after a deliberate stop. */
    auto: function () {
      if (on() || off() || minting || reachable === false) return;
      if (!state.profiles.length) return;
      minting = true;
      this.begin().then(function () { minting = false; render(); },
                        function () { minting = false; });
    },""", "auto")

    # ---- 3. stop() remembers off; begin() clears it --------------------
    rep("""    stop: function () {
      conf().code = "";
      conf().at = 0;
      lastSent = {};
      note = "";
      save();
    },""",
        """    stop: function () {
      conf().code = "";
      conf().at = 0;
      conf().off = true;             // remembered, so auto() does not re-mint
      lastSent = {};
      note = "";
      save();
    },""", "stop off")

    rep("""    begin: function () {
      note = "";
      return post({ action: "new" }).then(function (res) {
        reachable = true;
        if (!res.data || !res.data.ok || !res.data.code) throw new Error("no code");
        conf().code = res.data.code;
        conf().at = 0;
        save();
        return queue(true);""",
        """    begin: function () {
      note = "";
      return post({ action: "new" }).then(function (res) {
        reachable = true;
        if (!res.data || !res.data.ok || !res.data.code) throw new Error("no code");
        conf().code = res.data.code;
        conf().at = 0;
        delete conf().off;           // starting on purpose clears a past stop
        save();
        return queue(true);""", "begin clears off")

    # ---- 4. join clears off and the stale baseline --------------------
    rep("""    join: function (raw) {
      const want = String(raw || "").toUpperCase().replace(/[^0-9A-Z]/g, "");
      if (want.length !== 8) { note = "a code is eight letters and numbers"; return Promise.resolve(false); }
      note = "";
      conf().code = want;
      conf().at = 0;
      lastSent = {};
      save();""",
        """    join: function (raw) {
      const want = String(raw || "").toUpperCase().replace(/[^0-9A-Z]/g, "");
      if (want.length !== 8) { note = "a code is eight letters and numbers"; return Promise.resolve(false); }
      note = "";
      conf().code = want;
      conf().at = 0;
      delete conf().off;
      lastSent = {};
      // The old baseline belonged to a different family; the money delta must
      // not be measured against it.
      state.profiles.forEach(function (pf) { delete pf.sync; });
      save();""", "join clears baseline")

    # ---- 5. finish() flushes so a cleared level lands at once ----------
    rep("""    session.levelUp = session.replay === undefined ? advanceLevel(p) : null;
  }
  save();
  go("result");
}""",
        """    session.levelUp = session.replay === undefined ? advanceLevel(p) : null;
  }
  save();
  // The star, the money and the advance are worth getting into the database now
  // rather than after four idle seconds - a child often taps straight on.
  if (typeof cloud !== "undefined") cloud.flush();
  go("result");
}""", "finish flush")

    # ---- 6. the share link stops carrying the credential --------------
    rep("""function encodeState(data) {
  const bytes = new TextEncoder().encode(JSON.stringify(data));""",
        """function encodeState(data) {
  // A "Save a link" URL is shared and bookmarked, so the family code and the
  // deletion tombstones are stripped out of it - a credential does not belong
  // in a link. The cloud is the durable copy anyway.
  const bare = {};
  Object.keys(data).forEach(function (k) { if (k !== "cloud" && k !== "gone") bare[k] = data[k]; });
  data = bare;
  const bytes = new TextEncoder().encode(JSON.stringify(data));""", "encodeState strip")

    # ---- 7. a restored link keeps the real code, not the link's blank --
    rep("""  if (hash.indexOf("s=") === 0) {
    const restored = decodeState(hash.slice(2));
    if (restored && Array.isArray(restored.profiles)) { state = restored; save(); }
  }""",
        """  if (hash.indexOf("s=") === 0) {
    const restored = decodeState(hash.slice(2));
    if (restored && Array.isArray(restored.profiles)) {
      // The link no longer carries the code or the tombstones; keep whatever
      // this device already had so restoring one does not silently mint a
      // second family or resurrect a deleted player.
      restored.cloud = state.cloud || restored.cloud;
      restored.gone = state.gone || restored.gone;
      state = restored;
      save();
    }
  }""", "boot restore merge")

    # ---- 8. the home-screen sheet, rewritten for on-by-default ---------
    rep("""function cloudSheet() {
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
}""",
        """function cloudSheet() {
  if (!cloud.ready()) return "";
  const c = cloud.code();

  // On by default: once there is a player and a cloud, a code exists and this
  // shows it. The join box stays reachable so a second computer - or this one,
  // if it made its own family by mistake - can still join an existing code.
  if (c) {
    return '<div class="sheet stack">' +
             '<span class="eyebrow">\\u2601 Saved to the cloud, automatically</span>' +
             '<div class="row">' +
               '<span class="code-box" title="Your family code. Type it on another computer to open these same players there.">' +
                 esc(c.slice(0, 4)) + '<i>-</i>' + esc(c.slice(4)) + '</span>' +
               '<button class="btn btn-sm" id="cloudCopy" title="Copy the family code">Copy</button>' +
               '<span class="grow-label" id="cloudMsg">' + esc(cloud.note()) + '</span>' +
             '</div>' +
             '<p class="fineprint">Type this code on another computer and the same players, levels, ' +
               'stars, cards and money open there. Keep it in the family. ' +
               '<button class="linkish" id="cloudJoinToggle" title="Open a box to type a different family code">Use a different code</button> ' +
               '\\u00b7 <button class="linkish" id="cloudOff" title="Stop saving to the cloud on this computer. Nothing already saved is deleted.">Stop</button></p>' +
             '<div class="row" id="cloudJoinRow" hidden>' +
               '<input class="code-in" id="cloudCode" maxlength="9" placeholder="CODE" aria-label="Family code" />' +
               '<button class="btn btn-sm" id="cloudJoin" title="Bring that family\\'s players onto this computer">Use this code</button>' +
             '</div>' +
           '</div>';
  }

  // No code yet - either a brand-new computer, or one where sync was stopped.
  // A fresh second computer belongs here: type the family code rather than
  // start a rival family.
  return '<div class="sheet stack">' +
           '<span class="eyebrow">Same progress on every computer</span>' +
           '<p class="fineprint">' +
             (state.profiles.length
               ? 'Saving to the cloud turns on by itself as soon as a player is here. '
               : 'Already set this up on another computer? Type the family code and the same ' +
                 'players open here. Or just start playing - a new family is saved for you.') +
             '</p>' +
           '<div class="row">' +
             '<input class="code-in" id="cloudCode" maxlength="9" placeholder="CODE" ' +
               'title="The eight-letter code from the computer you already set up" aria-label="Family code" />' +
             '<button class="btn btn-sm" id="cloudJoin" title="Bring this family\\'s players onto this computer">Use this code</button>' +
             (cloud.stopped() ? '<span class="grow-label">or</span>' +
               '<button class="btn btn-sm" id="cloudOn" title="Turn saving back on for this computer">Turn saving back on</button>' : '') +
           '</div>' +
           '<span class="grow-label" id="cloudMsg">' + esc(cloud.note()) + '</span>' +
         '</div>';
}""", "cloudSheet rewrite")

    # a `stopped` reporter for the sheet
    rep("""    ready: function () { return reachable !== false; },
    note: function () { return note || (on() ? stamp() : ""); },""",
        """    ready: function () { return reachable !== false; },
    stopped: function () { return off(); },
    note: function () { return note || (on() ? stamp() : ""); },""", "stopped reporter")

    # ---- 9. wire the new controls -------------------------------------
    rep("""  const onBtn = document.getElementById("cloudOn");
  if (onBtn) onBtn.onclick = function () {
    onBtn.disabled = true;
    say("making a code…");
    cloud.begin().then(function () { render(); });
  };""",
        """  const onBtn = document.getElementById("cloudOn");
  if (onBtn) onBtn.onclick = function () {
    onBtn.disabled = true;
    say("making a code…");
    delete (state.cloud || {}).off;
    cloud.begin().then(function () { render(); });
  };

  const toggle = document.getElementById("cloudJoinToggle");
  if (toggle) toggle.onclick = function () {
    const row = document.getElementById("cloudJoinRow");
    if (row) { row.hidden = !row.hidden; const i = document.getElementById("cloudCode"); if (i && !row.hidden) i.focus(); }
  };""", "wire toggle")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("syntax:", "OK" if r.returncode == 0 else r.stderr[:800])


if __name__ == "__main__":
    main()
