/* Cloud save for Nihongo Adventure.
 *
 * One endpoint, three actions, one credential: a family code. The code is a
 * secret the way a share link is a secret - there are no accounts, no
 * passwords and no email addresses, because the people typing it are seven
 * years old. It is minted here rather than by the browser so it is always
 * drawn from a real random source and always spellable out loud.
 *
 * The hard part is not storing a save, it is merging two of them. A child
 * plays on the laptop on Saturday and the desktop on Sunday and neither
 * device may lose the other's afternoon. Every field of a profile is
 * therefore merged by a rule that cannot go backwards:
 *
 *   money, spent          two counters that only ever grow. Merged by delta
 *                         against the value at the client's last sync, so two
 *                         devices that each earned $2,000 arrive at +$4,000
 *                         rather than at whichever number happens to be bigger.
 *   cards                 per card, the larger count. Union of the keys, so
 *                         nothing collected is ever dropped.
 *   level, landmarks      the larger number.
 *   perfect, setsPaid     true wins - a green star, once earned, stays.
 *   boxes {b, t}          the record answered most recently, because that is
 *                         the truer picture of what the child knows now.
 *   name, face, course    from whichever side was touched last.
 *   opens                 the last ten, from either computer - it is what the
 *                         parents' page at /admin shows as "last played".
 *   wipe                  a deliberate reset. A newer wipe beats everything
 *                         older on the other side, or the merge would quietly
 *                         undo the thing the parent just asked for.
 *
 * Deletion is a tombstone, never a missing row: a profile deleted on one
 * computer has to stay deleted when the other one syncs, and an absent row
 * cannot say that.
 */

const ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"; // no I, L, O, U, 0 or 1
const CODE_LEN = 8;
const MAX_BODY = 1024 * 1024;
const MAX_PROFILES = 8;
const MAX_PROFILE_BYTES = 160 * 1024;
const RATE_PER_MIN = 90;
const NEW_PER_DAY = 20;

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

function bad(msg, status) {
  return json({ ok: false, error: msg }, status || 400);
}

function num(v) {
  return (typeof v === "number" && isFinite(v)) ? v : 0;
}

function obj(v) {
  return (v && typeof v === "object" && !Array.isArray(v)) ? v : {};
}

/* 256 does not divide by 30, so a plain modulo would make the first sixteen
   letters of the alphabet a shade likelier than the rest. Drawing again on the
   remainder costs nothing and keeps every code equally likely. */
function newCode(len) {
  const want = len || CODE_LEN;
  const ceiling = 256 - (256 % ALPHABET.length);
  let out = "";
  while (out.length < want) {
    const bytes = new Uint8Array(want * 2);
    crypto.getRandomValues(bytes);
    for (let i = 0; i < bytes.length && out.length < want; i++) {
      if (bytes[i] < ceiling) out += ALPHABET[bytes[i] % ALPHABET.length];
    }
  }
  return out;
}

// Typed by a child, so anything that is not a code character is simply not
// there: spaces, the hyphen we print for readability, lower case.
function cleanCode(raw) {
  const up = String(raw || "").toUpperCase();
  let out = "";
  for (let i = 0; i < up.length; i++) {
    if (ALPHABET.indexOf(up[i]) !== -1) out += up[i];
  }
  return out.length === CODE_LEN ? out : "";
}

/* The rate limit is keyed on a hash of the address, not the address: the only
   question being asked is "is this the same caller as a second ago", and that
   does not need to know who they are. */
async function ipKey(request) {
  const ip = request.headers.get("cf-connecting-ip") || "0";
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("nihongo:" + ip));
  const view = new Uint8Array(buf);
  let hex = "";
  for (let i = 0; i < 8; i++) hex += view[i].toString(16).padStart(2, "0");
  return hex;
}

async function tooMany(env, key, bucket, ceiling) {
  const row = await env.DB.prepare(
    "INSERT INTO hits (ip, minute, n) VALUES (?1, ?2, 1) " +
    "ON CONFLICT(ip, minute) DO UPDATE SET n = n + 1 RETURNING n"
  ).bind(key, bucket).first();
  // Yesterday's counters are litter; sweep a little, rarely, instead of
  // running a cron for three rows.
  if (row && row.n === 1 && (bucket % 37) === 0) {
    await env.DB.prepare("DELETE FROM hits WHERE minute < ?1").bind(bucket - 2880).run();
  }
  return !!row && row.n > ceiling;
}

/* ---------- the merge ---------- */

// Two counters that only grow. `base` is what this device had at its last
// sync, so (client - base) is what it earned since - which is what gets added
// to whatever the other device banked meanwhile.
function counter(serverVal, clientVal, baseVal) {
  const s = num(serverVal), c = num(clientVal);
  if (baseVal === undefined || baseVal === null) return Math.max(s, c);
  let b = num(baseVal);
  if (b > c) b = c;
  if (b > s) b = s;
  return s + (c - b);
}

function maxMap(a, b) {
  const out = {}, src = [obj(a), obj(b)];
  src.forEach(function (m) {
    Object.keys(m).forEach(function (k) {
      const v = num(m[k]);
      if (!(k in out) || v > out[k]) out[k] = v;
    });
  });
  return out;
}

function orMap(a, b) {
  const out = {}, src = [obj(a), obj(b)];
  src.forEach(function (m) {
    Object.keys(m).forEach(function (k) { if (m[k]) out[k] = true; });
  });
  return out;
}

// A box is {b: how well it is known, t: when it was last answered}. The later
// answer is the true one; an older device must not restore a stale box.
function mergeBoxes(a, b) {
  const out = {}, A = obj(a), B = obj(b);
  Object.keys(A).forEach(function (k) { out[k] = A[k]; });
  Object.keys(B).forEach(function (k) {
    const mine = out[k];
    if (!mine) { out[k] = B[k]; return; }
    const ta = (mine && typeof mine === "object") ? num(mine.t) : 0;
    const tb = (B[k] && typeof B[k] === "object") ? num(B[k].t) : 0;
    if (tb > ta) out[k] = B[k];
  });
  return out;
}

function mergeProgress(a, b) {
  const out = {}, A = obj(a), B = obj(b);
  const ids = {};
  Object.keys(A).forEach(function (k) { ids[k] = true; });
  Object.keys(B).forEach(function (k) { ids[k] = true; });
  Object.keys(ids).forEach(function (cid) {
    const x = obj(A[cid]), y = obj(B[cid]);
    out[cid] = {
      level: Math.max(num(x.level), num(y.level)),
      boxes: mergeBoxes(x.boxes, y.boxes),
      perfect: orMap(x.perfect, y.perfect)
    };
  });
  return out;
}

/* The last ten opens, from either computer, newest first. Two devices see
   different halves of the same week and both halves are worth keeping. */
function mergeOpens(a, b) {
  const all = (Array.isArray(a) ? a : []).concat(Array.isArray(b) ? b : []);
  const seen = {}, out = [];
  all.map(num).filter(function (t) { return t > 0; })
     .sort(function (x, y) { return y - x; })
     .forEach(function (t) { if (!seen[t]) { seen[t] = 1; out.push(t); } });
  return out.slice(0, 10);
}

function mergeProfile(server, client, base) {
  if (!server) return client;
  if (!client) return server;

  // A wipe is a decision, not an accident. Whichever side made it last is the
  // one the family meant to keep.
  const sw = num(server.wipe), cw = num(client.wipe);
  if (cw > sw) return client;
  if (sw > cw) return server;

  const st = num(server.touched), ct = num(client.touched);
  const newer = ct >= st ? client : server;
  const b = obj(base);

  return {
    id: client.id,
    name: newer.name || server.name || client.name,
    face: newer.face || server.face || client.face,
    tier: newer.tier || server.tier || client.tier,
    course: newer.course || server.course || client.course,
    unlockAll: !!(server.unlockAll || client.unlockAll),
    progress: mergeProgress(server.progress, client.progress),
    cards: maxMap(server.cards, client.cards),
    money: counter(server.money, client.money, b.money),
    spent: counter(server.spent, client.spent, b.spent),
    landmarks: maxMap(server.landmarks, client.landmarks),
    setsPaid: orMap(server.setsPaid, client.setsPaid),
    opens: mergeOpens(server.opens, client.opens),
    // Derived, not authoritative: whichever side is fresher describes itself.
    stat: newer.stat || server.stat || client.stat || null,
    wipe: Math.max(sw, cw),
    touched: Math.max(st, ct)
  };
}

/* Read, merge, write - with the write conditional on the row not having moved
   in between. Two computers syncing the same child in the same second would
   otherwise each merge against the same old row and the second would erase the
   first. On a clash it simply reads what landed and merges on top of that. */
async function store(env, code, p, base, now) {
  for (let attempt = 0; attempt < 8; attempt++) {
    // Back off a little between clashes, and by a different amount than
    // whoever we are clashing with, or two writers keep colliding in step.
    if (attempt) await new Promise(function (go) { setTimeout(go, 8 * attempt + Math.floor(Math.random() * 12)); });
    const row = await env.DB.prepare(
      "SELECT data, rev, deleted FROM saves WHERE code = ?1 AND pid = ?2"
    ).bind(code, p.id).first();
    if (row && row.deleted) return true;         // deleted on purpose, elsewhere
    if (!row) {
      const ins = await env.DB.prepare(
        "INSERT INTO saves (code, pid, data, rev, updated, deleted) VALUES (?1, ?2, ?3, 1, ?4, 0) " +
        "ON CONFLICT(code, pid) DO NOTHING"
      ).bind(code, p.id, JSON.stringify(p), now).run();
      if (ins && ins.meta && ins.meta.changes === 1) return true;
      continue;                                  // someone got there first
    }
    let server = null;
    if (row.data) {
      try { server = JSON.parse(row.data); } catch (e) { server = null; }
    }
    const merged = mergeProfile(server, p, base);
    const upd = await env.DB.prepare(
      "UPDATE saves SET data = ?1, rev = rev + 1, updated = ?2 WHERE code = ?3 AND pid = ?4 AND rev = ?5"
    ).bind(JSON.stringify(merged), now, code, p.id, row.rev).run();
    if (upd && upd.meta && upd.meta.changes === 1) return true;
  }
  /* Eight clashes in a row means something is hammering this one child. Say so
     rather than answering 200 with the push silently dropped: the client keeps
     its own copy, does not adopt ours, and tries again. */
  return false;
}

/* ---------- the endpoint ---------- */

export async function onRequestPost(context) {
  const env = context.env, request = context.request;
  if (!env.DB) return bad("no database bound", 500);

  const len = Number(request.headers.get("content-length") || 0);
  if (len > MAX_BODY) return bad("too much", 413);

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return bad("not json");
  }
  if (!body || typeof body !== "object") return bad("not json");

  const action = String(body.action || "sync");
  if (action === "ping") return json({ ok: true, now: Date.now() });

  const key = await ipKey(request);
  const minute = Math.floor(Date.now() / 60000);
  if (await tooMany(env, key, minute, RATE_PER_MIN)) return bad("slow down", 429);

  if (action === "new") {
    // A day bucket for code minting, so one address cannot fill the table.
    /* The same column as the per-minute counter, so it has to be on the same
       scale: a day bucket numbered in the twenty-thousands looked ancient to a
       sweep measuring in minutes and was deleted on sight, which quietly reset
       the daily limit every time it ran. */
    if (await tooMany(env, key + ":n", minute - (minute % 1440), NEW_PER_DAY)) {
      return bad("too many new codes today", 429);
    }
    for (let attempt = 0; attempt < 5; attempt++) {
      const code = newCode();
      const clash = await env.DB.prepare("SELECT code FROM families WHERE code = ?1").bind(code).first();
      if (clash) continue;
      await env.DB.prepare("INSERT INTO families (code, created, seen) VALUES (?1, ?2, ?2)")
        .bind(code, Date.now()).run();
      return json({ ok: true, code: code });
    }
    return bad("could not make a code", 500);
  }

  if (action !== "sync") return bad("unknown action");

  const code = cleanCode(body.code);
  if (!code) return bad("that code does not look right", 400);
  const fam = await env.DB.prepare("SELECT code FROM families WHERE code = ?1").bind(code).first();
  if (!fam) return json({ ok: false, error: "no such code", unknownCode: true }, 404);

  const profiles = Array.isArray(body.profiles) ? body.profiles.slice(0, MAX_PROFILES) : [];
  const bases = obj(body.base);
  const gone = Array.isArray(body.gone) ? body.gone.slice(0, MAX_PROFILES * 4) : [];
  const now = Date.now();

  for (let i = 0; i < profiles.length; i++) {
    const p = profiles[i];
    if (!p || typeof p !== "object" || typeof p.id !== "string" || !p.id) return bad("bad profile");
    if (JSON.stringify(p).length > MAX_PROFILE_BYTES) return bad("that save is too big", 413);
  }

  // Tombstones first, so a profile deleted on this device is not resurrected
  // by the copy this same request is about to push.
  for (let i = 0; i < gone.length; i++) {
    const id = String(gone[i] || "");
    if (!id) continue;
    await env.DB.prepare(
      "INSERT INTO saves (code, pid, data, rev, updated, deleted) VALUES (?1, ?2, '', 1, ?3, 1) " +
      "ON CONFLICT(code, pid) DO UPDATE SET deleted = 1, data = '', updated = ?3, rev = saves.rev + 1"
    ).bind(code, id, now).run();
  }

  const stale = [];
  for (let i = 0; i < profiles.length; i++) {
    const done = await store(env, code, profiles[i], bases[profiles[i].id], now);
    if (done === false) stale.push(profiles[i].id);
  }

  const all = await env.DB.prepare(
    "SELECT pid, data, rev, deleted FROM saves WHERE code = ?1"
  ).bind(code).all();

  const out = [], tombs = [];
  const rows = (all && all.results) || [];
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    if (r.deleted) { tombs.push(r.pid); continue; }
    try { out.push(JSON.parse(r.data)); } catch (e) { /* a corrupt row is not worth a failed sync */ }
  }

  await env.DB.prepare("UPDATE families SET seen = ?1 WHERE code = ?2").bind(now, code).run();
  return json({ ok: true, code: code, profiles: out, gone: tombs, stale: stale, now: now });
}

// A GET is not part of the protocol, but answering it plainly makes the
// endpoint easy to check from a terminal.
export async function onRequestGet() {
  return json({ ok: true, service: "nihongo cloud save", post: true });
}
