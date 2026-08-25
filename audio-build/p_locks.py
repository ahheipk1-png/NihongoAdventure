# -*- coding: utf-8 -*-
u"""A password on each player, and a grown-up's approval before a new one plays.

Now that every device shares one set of players, two things were missing:

  * anyone could open any player. Each player can now carry a password; opening
    that player asks for it. It is stored as a SHA-256 hash, never in the clear,
    so a synced save and the /admin list never show the actual word.

  * anyone could make a new player and start straight away. A new player is now
    born "pending" and cannot be opened until a grown-up approves it on the
    /admin page. Approval travels through the same merge as everything else, so
    it reaches every device.

Existing players (made before this) have no password and are not pending, so
nothing they had is taken away; a password can be added to any of them from the
editor, and reset from /admin.
"""
import io, re, subprocess

GAME = r"C:\JapaneseLearning\kana-quest.html"
MIRROR = r"C:\JapaneseLearning\index.html"
SYNC = r"C:\JapaneseLearning\functions\api\sync.js"


def main():
    s = io.open(GAME, encoding="utf-8").read()

    def rep(old, new, note):
        nonlocal s
        assert s.count(old) == 1, "%s: found %d" % (note, s.count(old))
        s = s.replace(old, new, 1)

    # ---- a tiny password hasher, shared by the editor and the gate -----
    rep("""function esc(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c];
  });
}""",
        """function esc(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c];
  });
}

/* A player's password is kept only as a hash, so a synced save - and the
   parents' list at /admin - never carry the word itself. Async because
   crypto.subtle is; callers wait for it. */
function hashPw(word) {
  const w = String(word == null ? "" : word);
  if (!w) return Promise.resolve("");
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode("nihongo-pw:" + w))
    .then(function (buf) {
      const v = new Uint8Array(buf);
      let hex = "";
      for (let i = 0; i < v.length; i++) hex += v[i].toString(16).padStart(2, "0");
      return hex;
    });
}""", "hashPw")

    # ---- new profiles start pending -----------------------------------
    rep("""    cards: {}, money: 0, spent: 0, landmarks: {}, setsPaid: {}
  };
}""",
        """    cards: {}, money: 0, spent: 0, landmarks: {}, setsPaid: {},
    pw: "", pending: true       // a grown-up approves a new player before it plays
  };
}""", "newProfile pending")

    # ---- the editor: a password field ---------------------------------
    rep("""    draft = {
      name: p ? p.name : "", face: p ? p.face : pick(FACES),
      tier: ONE_TIER, unlockAll: p ? !!p.unlockAll : false
    };""",
        """    draft = {
      name: p ? p.name : "", face: p ? p.face : pick(FACES),
      tier: ONE_TIER, unlockAll: p ? !!p.unlockAll : false,
      pw: "", pwTouched: false     // typed only if the grown-up sets/changes it
    };""", "draft pw")

    rep("""        '<div class="faces">' + faces + '</div>' +
      '</div>' +""",
        """        '<div class="faces">' + faces + '</div>' +
      '</div>' +
      '<div class="sheet stack">' +
        '<label class="sr" for="pwIn">Player password</label>' +
        '<div class="row" style="gap:8px">' +
          '<span aria-hidden="true" style="font-size:18px">\U0001f512</span>' +
          '<input class="namefield" id="pwIn" type="text" maxlength="24" style="flex:1" ' +
            'placeholder="' + (isNew ? "A password for this player" :
              (p && p.pw ? "Type a new password to change it" : "Add a password")) + '" ' +
            'autocomplete="off" value="">' +
        '</div>' +
        '<p class="fineprint">' + (isNew
          ? "Pick something they can remember. They will type it to open this player."
          : (p && p.pw ? "This player has a password. Leave blank to keep it, or type a new one."
                       : "Add a password so only they can open this player. Leave blank for none.")) +
        '</p>' +
      '</div>' +""", "pw field")

    # wire the pw field
    rep("""  const nameIn = document.getElementById("nameIn");
  nameIn.oninput = function () { draft.name = nameIn.value; };""",
        """  const nameIn = document.getElementById("nameIn");
  nameIn.oninput = function () { draft.name = nameIn.value; };
  const pwIn = document.getElementById("pwIn");
  if (pwIn) pwIn.oninput = function () { draft.pw = pwIn.value; draft.pwTouched = true; };""", "wire pw")

    # ---- save: hash the password, keep pending state ------------------
    rep("""  document.getElementById("saveP").onclick = function () {
    const name = (draft.name || "").trim() || "Player " + (state.profiles.length + 1);
    if (isNew) {
      const np = newProfile(name, draft.face, draft.tier);
      np.unlockAll = draft.unlockAll;
      state.profiles.push(np);
      state.activeId = np.id;
    } else {
      p.name = name; p.face = draft.face; p.tier = draft.tier; p.unlockAll = draft.unlockAll;
      prog(p).level = Math.max(0, Math.min(prog(p).level || 0, ladderFor(p).length - 1));   // a ladder can only ever be as long as it is
    }
    draft = null;
    save();
    go("menu");
  };""",
        """  document.getElementById("saveP").onclick = function () {
    const name = (draft.name || "").trim() || "Player " + (state.profiles.length + 1);
    // The password is hashed before it touches the save; an untouched field on
    // an existing player leaves the old password alone.
    const setPw = draft.pwTouched
      ? hashPw((draft.pw || "").trim())
      : Promise.resolve(isNew ? "" : (p.pw || ""));
    setPw.then(function (pwHash) {
      if (isNew) {
        const np = newProfile(name, draft.face, draft.tier);
        np.unlockAll = draft.unlockAll;
        np.pw = pwHash;                       // pending stays true until approved
        state.profiles.push(np);
        // A pending player is not opened straight into a round; it waits.
        state.activeId = null;
        draft = null;
        save();
        go("home");
      } else {
        p.name = name; p.face = draft.face; p.tier = draft.tier; p.unlockAll = draft.unlockAll;
        p.pw = pwHash;
        prog(p).level = Math.max(0, Math.min(prog(p).level || 0, ladderFor(p).length - 1));
        draft = null;
        save();
        go("menu");
      }
    });
  };""", "save with pw")

    # ---- the picker: pending badge, and a password gate on open -------
    rep("""  screenEl.querySelectorAll("[data-open]").forEach(function (b) {
    b.onclick = function () {
      audio.prime();
      state.activeId = b.getAttribute("data-open");
      noteOpen(currentProfile());
      save();
      go("menu");
    };
  });""",
        """  screenEl.querySelectorAll("[data-open]").forEach(function (b) {
    b.onclick = function () {
      audio.prime();
      const who = state.profiles.find(function (x) { return x.id === b.getAttribute("data-open"); });
      if (!who) return;
      if (who.pending) {
        window.alert(who.name + " is waiting for a grown-up to approve them.\\n\\n" +
          "Open the game's admin page and approve this player.");
        return;
      }
      openPlayer(who);
    };
  });""", "picker gate")

    # openPlayer: ask for the password, then enter
    rep("""function renderHome() {
  const grid = state.profiles.map(function (p) {""",
        """/* Opening a player: if it has a password, it must be typed first. A parent can
   always get in from /admin, and can reset a forgotten password there. */
function openPlayer(who) {
  if (!who.pw) { enterPlayer(who); return; }
  const tries = 3;
  (function ask(left) {
    const word = window.prompt("Password for " + who.name + ":");
    if (word === null) return;                 // cancelled
    hashPw((word || "").trim()).then(function (h) {
      if (h === who.pw) { enterPlayer(who); return; }
      if (left > 1) { window.alert("That is not the password. " + (left - 1) + " more " +
        ((left - 1) === 1 ? "try" : "tries") + "."); ask(left - 1); }
      else window.alert("That is not the password. Ask a grown-up - they can reset it on the admin page.");
    });
  })(tries);
}

function enterPlayer(who) {
  state.activeId = who.id;
  noteOpen(currentProfile());
  save();
  go("menu");
}

function renderHome() {
  const grid = state.profiles.map(function (p) {""", "openPlayer")

    # a small badge on a pending / locked profile tile
    rep("""               '<span class="profile-meta">' + esc(courseOf(p).title) + '</span>' +
               '<span class="profile-meta">' + esc(lv.label + ' of ' + lv.total) + '</span>' +
               '<span class="profile-bar"><i style="width:' +
                 (lv.total ? Math.round((lv.number / lv.total) * 100) : 0) + '%"></i></span>' +
             '</button>' +""",
        """               '<span class="profile-meta">' + esc(courseOf(p).title) + '</span>' +
               '<span class="profile-meta">' +
                 (p.pending ? '\u23f3 waiting for approval'
                   : esc(lv.label + ' of ' + lv.total) + (p.pw ? ' \U0001f512' : '')) + '</span>' +
               '<span class="profile-bar"><i style="width:' +
                 (lv.total ? Math.round((lv.number / lv.total) * 100) : 0) + '%"></i></span>' +
             '</button>' +""", "pending badge")

    io.open(GAME, "w", encoding="utf-8").write(s)
    io.open(MIRROR, "w", encoding="utf-8").write(s)

    # ---- the merge carries pw and pending ----------------------------
    f = io.open(SYNC, encoding="utf-8").read()
    fold = """    unlockAll: !!(server.unlockAll || client.unlockAll),
    progress: mergeProgress(server.progress, client.progress),"""
    fnew = """    unlockAll: !!(server.unlockAll || client.unlockAll),
    // The password follows whichever side was touched last; an admin reset,
    // being wipe-stamped, has already won the whole record above.
    pw: (newer.pw !== undefined ? newer.pw : (server.pw !== undefined ? server.pw : client.pw)) || "",
    // Pending is a gate that only opens: once either side has approved
    // (pending false/absent) the player stays approved everywhere.
    pending: !!server.pending && !!client.pending,
    progress: mergeProgress(server.progress, client.progress),"""
    assert f.count(fold) == 1, "merge anchor: %d" % f.count(fold)
    f = f.replace(fold, fnew, 1)
    io.open(SYNC, "w", encoding="utf-8").write(f)

    js = max(re.findall(r"<script>(.*?)</script>", s, re.S), key=len)
    chk = r"C:\JapaneseLearning\audio-build\_check.js"
    io.open(chk, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", chk], capture_output=True, text=True)
    print("game syntax:", "OK" if r.returncode == 0 else r.stderr[:700])
    r2 = subprocess.run(["node", "--input-type=module", "--check"], input=f, capture_output=True, text=True)
    print("sync.js syntax:", "OK" if r2.returncode == 0 else r2.stderr[:400])


if __name__ == "__main__":
    main()
