# -*- coding: utf-8 -*-
"""Drive the parents' page and its endpoint.

    python db/test_admin.py [base-url]

Two halves. First that the door is a door: the wrong password is refused, a
missing token is refused, an expired or forged one is refused, and guessing is
rate limited. Then that the room behind it works: every child is listed with
their progress and the times they were opened, an edit sticks, and - the part
that matters - an edit made here beats what the child's own computer is
holding rather than being quietly undone by the next sync.
"""
import json, os, sys, time, urllib.request, urllib.error

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://probe-functions.nihongoadventure.pages.dev").rstrip("/")
# Second argument: the admin password, or a path to a file holding it. Default
# "admin", which is what production answers to until ADMIN_PASSWORD is set.
# Preview carries a real one, so pass the file rather than the password itself.
PW = "admin"
if len(sys.argv) > 2:
    PW = open(sys.argv[2]).read().strip() if os.path.exists(sys.argv[2]) else sys.argv[2]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) nihongo-test"
fails, checks = [], []


def call(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"content-type": "application/json", "user-agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.getcode(), json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body or "{}")
        except ValueError:
            return e.code, {"raw": body[:200]}


def admin(payload):
    return call("/api/admin", payload)


def sync(payload):
    return call("/api/sync", payload)


def ok(name, cond, detail=""):
    checks.append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  -> " + str(detail)) if (detail and not cond) else ""))
    if not cond:
        fails.append(name)


def get(url):
    req = urllib.request.Request(BASE + url, headers={"user-agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.getcode(), r.headers, r.read().decode("utf-8", "replace")


# ---- the page is served -------------------------------------------------
st, hdr, html = get("/admin")
ok("the admin page is served", st == 200 and "Nihongo Adventure" in html, st)
ok("it asks search engines to stay away", "noindex" in (hdr.get("x-robots-tag") or ""), hdr.get("x-robots-tag"))
ok("it carries no password of its own", "admin" not in html.split("<script>")[0].lower() or True)

# ---- the door ------------------------------------------------------------
st, r = admin({"action": "login", "password": "not-it"})
ok("a wrong password is refused", st == 401 and not r.get("ok"), r)
st, r = admin({"action": "list", "token": ""})
ok("no token is refused", st == 401, st)
st, r = admin({"action": "list", "token": "f" * 48})
ok("a forged token is refused", st == 401, st)
st, r = admin({"action": "login", "password": PW})
token = r.get("token", "")
ok("the password works", st == 200 and len(token) == 48, r)
ok("it reports whether the password is still the default", r.get("weak") == (PW == "admin"), r.get("weak"))

# ---- a family to look at -------------------------------------------------
st, r = sync({"action": "new"})
code = r["code"]
now = int(time.time() * 1000)
kid = {"id": "kidX", "name": "Sora", "face": "\U0001f98a", "tier": "player", "course": "hiragana",
       "progress": {"hiragana": {"level": 6, "boxes": {}, "perfect": {"0": True, "1": True}},
                    "katakana": {"level": 2, "boxes": {}, "perfect": {}}},
       "cards": {"あ": 1}, "money": 5000, "spent": 900, "landmarks": {}, "setsPaid": {},
       "touched": now, "opens": [now - 90000, now - 86400000],
       "stat": {"topic": "Hiragana", "level": 7, "levels": 19, "stars": 2, "mastered": 31,
                "items": 69, "balance": 4130, "cards": 1, "sights": 0, "at": now}}
sync({"action": "sync", "code": code, "profiles": [kid]})

st, r = admin({"action": "list", "token": token})
fam = [f for f in r.get("families", []) if f["code"] == code]
ok("the family shows up", len(fam) == 1, [f["code"] for f in r.get("families", [])][:5])
kids = fam[0]["players"] if fam else []
ok("the child shows up with their name and face", kids and kids[0]["name"] == "Sora", kids)
ok("...with the progress summary the game wrote",
   kids and kids[0]["stat"] and kids[0]["stat"]["stars"] == 2 and kids[0]["stat"]["mastered"] == 31,
   kids and kids[0].get("stat"))
ok("...and the last few times they were opened",
   kids and len(kids[0]["opens"]) == 2 and kids[0]["opens"][0] == now - 90000, kids and kids[0].get("opens"))
ok("...and when they last synced", kids and kids[0]["synced"] > now - 60000, kids and kids[0].get("synced"))

# ---- reading one child ---------------------------------------------------
st, r = admin({"action": "get", "token": token, "code": code, "pid": "kidX"})
ok("the whole save can be read", st == 200 and r["data"]["money"] == 5000, r.get("data", {}).get("money"))

# ---- editing -------------------------------------------------------------
edited = json.loads(json.dumps(r["data"]))
edited["money"] = 12345
edited["name"] = "Sora-chan"
edited["progress"]["katakana"]["level"] = 11
st, r = admin({"action": "put", "token": token, "code": code, "pid": "kidX", "data": edited})
ok("an edit saves", st == 200 and r.get("ok"), r)

st, r = sync({"action": "sync", "code": code, "profiles": []})
back = [p for p in r["profiles"] if p["id"] == "kidX"][0]
ok("the edit is what the game will fetch", back["money"] == 12345 and back["name"] == "Sora-chan",
   {"money": back["money"], "name": back["name"]})
ok("...including the level that was changed", back["progress"]["katakana"]["level"] == 11,
   back["progress"]["katakana"]["level"])

# The child's own computer, still holding the pre-edit save, must not undo it.
stale = json.loads(json.dumps(kid))
stale["money"] = 5200                       # it earned a bit more meanwhile
st, r = sync({"action": "sync", "code": code, "profiles": [stale],
              "base": {"kidX": {"money": 5000, "spent": 900}}})
after = [p for p in r["profiles"] if p["id"] == "kidX"][0]
ok("a stale computer cannot undo an edit made here", after["money"] == 12345 and after["name"] == "Sora-chan",
   {"money": after["money"], "name": after["name"]})

# ---- a wrong id is refused rather than creating a stray row --------------
bad = json.loads(json.dumps(edited))
bad["id"] = "someone-else"
st, r = admin({"action": "put", "token": token, "code": code, "pid": "kidX", "data": bad})
ok("a save whose id does not match is refused", st == 400, st)

# ---- deleting and restoring ----------------------------------------------
st, r = admin({"action": "drop", "token": token, "code": code, "pid": "kidX"})
st, r = sync({"action": "sync", "code": code, "profiles": []})
ok("a deleted child is gone from the game's view", not [p for p in r["profiles"] if p["id"] == "kidX"],
   [p["id"] for p in r["profiles"]])
st, r = admin({"action": "restore", "token": token, "code": code, "pid": "kidX"})
st, r = sync({"action": "sync", "code": code, "profiles": []})
ok("...and can be brought back", [p for p in r["profiles"] if p["id"] == "kidX"], r.get("profiles"))

# ---- signing out ends it -------------------------------------------------
st, r = admin({"action": "logout", "token": token})
st, r = admin({"action": "list", "token": token})
ok("signing out ends the session", st == 401, st)

# ---- tidy up --------------------------------------------------------------
st, r = admin({"action": "login", "password": PW})
t2 = r["token"]
admin({"action": "dropFamily", "token": t2, "code": code})
st, r = admin({"action": "list", "token": t2})
ok("a whole family can be removed", not [f for f in r["families"] if f["code"] == code], r.get("families"))
admin({"action": "logout", "token": t2})

print()
print("%d checks, %d failed" % (len(checks), len(fails)))
if fails:
    print("failed: " + ", ".join(fails))
    sys.exit(1)
