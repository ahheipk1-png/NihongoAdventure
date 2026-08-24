/* The parents' end of cloud save: look at every child, and change anything.
 *
 * One password, which is `ADMIN_PASSWORD` if that secret is set on the Pages
 * project and "admin" if it is not. Set it with:
 *
 *     npx -y wrangler@4 pages secret put ADMIN_PASSWORD --project-name nihongoadventure
 *
 * Worth doing, because this endpoint walks straight past the family code: the
 * code is 39 bits of secret and "admin" is five characters. What holds the
 * line meanwhile is that a wrong password is rate limited to twenty attempts a
 * minute per address, and that there is nothing here but a child's game.
 *
 * A login hands back an opaque token, stored in D1 with a twelve-hour expiry
 * rather than signed, because a row that can be deleted is a session that can
 * be revoked.
 *
 * Editing is deliberately blunt. A saved profile carries a fresh `wipe` stamp,
 * which is the merge's way of saying "this is now the truth" - so a change made
 * here beats whatever the children's computers are holding, instead of being
 * quietly undone by the next sync.
 */

const SESSION_MS = 12 * 3600 * 1000;
const TRY_PER_MIN = 20;
const MAX_BODY = 1024 * 1024;

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex, nofollow"
    }
  });
}

function bad(msg, status) {
  return json({ ok: false, error: msg }, status || 400);
}

function num(v) {
  return (typeof v === "number" && isFinite(v)) ? v : 0;
}

// Length is not a secret worth protecting here; the comparison itself is.
function sameSecret(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

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
  return !!row && row.n > ceiling;
}

function newToken() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  let hex = "";
  for (let i = 0; i < bytes.length; i++) hex += bytes[i].toString(16).padStart(2, "0");
  return hex;
}

/* A session remembers which password let it in, so changing the password ends
   every session that the old one opened. Without it, someone who got in while
   the password was still "admin" would keep their twelve hours after the owner
   had changed it - which is the one moment it matters. */
async function pwMark(env) {
  const want = env.ADMIN_PASSWORD || "admin";
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("nihongo-pw:" + want));
  const view = new Uint8Array(buf);
  let hex = "";
  for (let i = 0; i < 8; i++) hex += view[i].toString(16).padStart(2, "0");
  return hex;
}

async function whoIsThis(env, token) {
  if (typeof token !== "string" || token.length !== 48) return false;
  const row = await env.DB.prepare("SELECT exp, pw FROM sessions WHERE token = ?1").bind(token).first();
  if (!row || num(row.exp) < Date.now()) return false;
  return row.pw === (await pwMark(env));
}

function text(v, cap) {
  return String(v == null ? "" : v).slice(0, cap || 64);
}

/* The summary is rebuilt field by field rather than passed through.

   Everything in a save arrived over /api/sync, which by design has no
   credential beyond a family code anyone can mint - so a "number" in there is
   whatever a stranger felt like putting in it. Sending the object on as it
   came would make the parents' page render it, and a page that renders a
   stranger's markup is a page that hands over its own session. */
function safeStat(s) {
  if (!s || typeof s !== "object") return null;
  return {
    topic: text(s.topic, 40), level: num(s.level), levels: num(s.levels),
    stars: num(s.stars), mastered: num(s.mastered), items: num(s.items),
    balance: num(s.balance), cards: num(s.cards), sights: num(s.sights),
    at: num(s.at)
  };
}

/* One row per child is what the list is built from; the summary the game
   writes into each save is what makes it readable without this endpoint
   knowing a single thing about kana, cards or the map. */
function overview(row) {
  let p = null;
  try { p = JSON.parse(row.data || "null"); } catch (e) { p = null; }
  return {
    pid: text(row.pid, 64),
    deleted: !!row.deleted,
    rev: num(row.rev),
    synced: num(row.updated),
    // A child deleted from inside the game leaves a tombstone with no save at
    // all; say that, rather than implying the file is corrupt.
    name: (p && text(p.name, 40)) || (row.deleted ? "(deleted from the game)" : "(unreadable)"),
    face: (p && text(p.face, 8)) || "",
    course: (p && text(p.course, 32)) || "",
    stat: safeStat(p && p.stat),
    opens: (p && Array.isArray(p.opens)) ? p.opens.slice(0, 10).map(num) : [],
    bytes: (row.data || "").length
  };
}

/* `wrangler pages secret put` writes to production only, and a preview build
   binds the same database - so a project whose owner has done exactly what
   they were told still has every old *.pages.dev preview URL answering to the
   default password, over live data, for as long as the deployment exists.
   Unless a real password has been set, this endpoint therefore exists on one
   hostname and nowhere else. */
const HOME = "nihongoadventure.pages.dev";

function atHome(request) {
  const host = new URL(request.url).hostname;
  return host === HOME || host === "localhost" || host === "127.0.0.1";
}

export async function onRequestPost(context) {
  const env = context.env, request = context.request;
  if (!env.DB) return bad("no database bound", 500);
  if (!env.ADMIN_PASSWORD && !atHome(request)) {
    return bad("the admin page is only open on the live site", 404);
  }
  if (Number(request.headers.get("content-length") || 0) > MAX_BODY) return bad("too much", 413);

  let body;
  try { body = await request.json(); } catch (e) { return bad("not json"); }
  if (!body || typeof body !== "object") return bad("not json");

  const action = String(body.action || "");
  const key = await ipKey(request);
  const minute = Math.floor(Date.now() / 60000);

  if (action === "login") {
    if (await tooMany(env, key + ":a", minute, TRY_PER_MIN)) return bad("too many tries", 429);
    const want = env.ADMIN_PASSWORD || "admin";
    if (!sameSecret(String(body.password || ""), want)) return bad("wrong password", 401);
    const token = newToken(), exp = Date.now() + SESSION_MS;
    await env.DB.prepare("DELETE FROM sessions WHERE exp < ?1").bind(Date.now()).run();
    await env.DB.prepare("INSERT INTO sessions (token, exp, pw) VALUES (?1, ?2, ?3)")
      .bind(token, exp, await pwMark(env)).run();
    return json({ ok: true, token: token, exp: exp, weak: !env.ADMIN_PASSWORD });
  }

  if (!(await whoIsThis(env, body.token))) return bad("sign in first", 401);
  if (await tooMany(env, key + ":A", minute, 240)) return bad("slow down", 429);

  if (action === "logout") {
    await env.DB.prepare("DELETE FROM sessions WHERE token = ?1").bind(body.token).run();
    return json({ ok: true });
  }

  if (action === "list") {
    const fams = await env.DB.prepare("SELECT code, created, seen FROM families ORDER BY created").all();
    const rows = await env.DB.prepare(
      "SELECT code, pid, data, rev, updated, deleted FROM saves"
    ).all();
    const byCode = {};
    ((rows && rows.results) || []).forEach(function (r) {
      (byCode[r.code] = byCode[r.code] || []).push(overview(r));
    });
    const out = ((fams && fams.results) || []).map(function (f) {
      const kids = (byCode[f.code] || []).sort(function (a, b) { return (b.synced || 0) - (a.synced || 0); });
      return { code: f.code, created: num(f.created), seen: num(f.seen), players: kids };
    });
    return json({ ok: true, families: out, now: Date.now() });
  }

  if (action === "get") {
    const row = await env.DB.prepare(
      "SELECT data, rev, updated, deleted FROM saves WHERE code = ?1 AND pid = ?2"
    ).bind(String(body.code || ""), String(body.pid || "")).first();
    if (!row) return bad("no such player", 404);
    let data = null;
    try { data = JSON.parse(row.data || "null"); } catch (e) { data = null; }
    return json({ ok: true, data: data, rev: num(row.rev), synced: num(row.updated), deleted: !!row.deleted });
  }

  if (action === "put") {
    const code = String(body.code || ""), pid = String(body.pid || "");
    const data = body.data;
    if (!code || !pid || !data || typeof data !== "object") return bad("nothing to save");
    if (data.id !== pid) return bad("that save belongs to a different player");
    const blob = JSON.stringify(data);
    if (blob.length > 160 * 1024) return bad("that save is too big", 413);
    // Two tabs open on the same child should not silently overwrite each
    // other; the second one is told to re-read rather than guess.
    if (body.rev !== undefined) {
      const at = await env.DB.prepare(
        "SELECT rev FROM saves WHERE code = ?1 AND pid = ?2"
      ).bind(code, pid).first();
      if (at && num(at.rev) !== num(body.rev)) {
        return json({ ok: false, error: "this player changed somewhere else - reopen them", stale: true }, 409);
      }
    }
    // The stamp is what makes an edit stick: the merge lets the newer wipe win,
    // so the children's computers take this rather than argue with it.
    data.wipe = Date.now();
    data.touched = Date.now();
    const now = Date.now();
    await env.DB.prepare(
      "INSERT INTO saves (code, pid, data, rev, updated, deleted) VALUES (?1, ?2, ?3, 1, ?4, 0) " +
      "ON CONFLICT(code, pid) DO UPDATE SET data = ?3, updated = ?4, rev = saves.rev + 1, deleted = 0"
    ).bind(code, pid, JSON.stringify(data), now).run();
    return json({ ok: true, saved: now });
  }

  if (action === "drop") {
    /* The save itself is kept, unlike a deletion made from the game: a parent
       who deletes the wrong child here should be one button away from having
       them back, and the tombstone alone is what stops the computers pushing
       them back in. */
    const now = Date.now();
    await env.DB.prepare(
      "INSERT INTO saves (code, pid, data, rev, updated, deleted) VALUES (?1, ?2, '', 1, ?3, 1) " +
      "ON CONFLICT(code, pid) DO UPDATE SET deleted = 1, updated = ?3, rev = saves.rev + 1"
    ).bind(String(body.code || ""), String(body.pid || ""), now).run();
    return json({ ok: true });
  }

  if (action === "restore") {
    // Undo a deletion, if the row still carries a save worth bringing back.
    const row = await env.DB.prepare(
      "SELECT data FROM saves WHERE code = ?1 AND pid = ?2"
    ).bind(String(body.code || ""), String(body.pid || "")).first();
    if (!row || !row.data) return bad("nothing left to restore", 404);
    await env.DB.prepare(
      "UPDATE saves SET deleted = 0, rev = rev + 1, updated = ?1 WHERE code = ?2 AND pid = ?3"
    ).bind(Date.now(), String(body.code || ""), String(body.pid || "")).run();
    return json({ ok: true });
  }

  if (action === "dropFamily") {
    const code = String(body.code || "");
    if (!code) return bad("which family?");
    await env.DB.prepare("DELETE FROM saves WHERE code = ?1").bind(code).run();
    await env.DB.prepare("DELETE FROM families WHERE code = ?1").bind(code).run();
    return json({ ok: true });
  }

  return bad("unknown action");
}

export async function onRequestGet() {
  return json({ ok: true, service: "nihongo admin", post: true });
}
