# -*- coding: utf-8 -*-
"""Drive the cloud-save endpoint the way two computers would.

    python db/test_sync.py [base-url]

Every case is a thing that actually happens to a child: two machines earning
money on the same Saturday, a card collected on one and a level passed on the
other, a record cleared on purpose, a player deleted. The point is that nothing
a child did may vanish, and that no amount of syncing may invent money.
"""
import json, sys, time, urllib.request, urllib.error

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://probe-functions.nihongoadventure.pages.dev").rstrip("/")
URL = BASE + "/api/sync"
fails = []


def post(payload, expect=200):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"content-type": "application/json",
                                          # Cloudflare turns away urllib's own
                                          # user agent with a 1010 before the
                                          # Function ever runs.
                                          "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) nihongo-test"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.getcode(), json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


checks = []


def ok(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (("  -> " + str(detail)) if (detail and not cond) else ""))
    checks.append(name)
    if not cond:
        fails.append(name)


def prof(pid, **kw):
    p = {"id": pid, "name": "Sora", "face": "\U0001f98a", "tier": "player", "course": "hiragana",
         "progress": {"hiragana": {"level": 0, "boxes": {}, "perfect": {}}},
         "cards": {}, "money": 0, "spent": 0, "landmarks": {}, "setsPaid": {},
         "touched": int(time.time() * 1000)}
    p.update(kw)
    return p


def by_id(res, pid):
    for p in res.get("profiles", []):
        if p["id"] == pid:
            return p
    return None


# ---- a code is minted -------------------------------------------------
st, r = post({"action": "ping"})
ok("the endpoint answers", st == 200 and r.get("ok"), r)
st, r = post({"action": "new"})
code = r.get("code", "")
ok("a family code is minted", st == 200 and len(code) == 8, r)
ok("the code has no letters a child could misread",
   not any(c in code for c in "IL0O1U"), code)
st, r = post({"action": "sync", "code": "ZZZZZZZZ", "profiles": []})
ok("an unknown code is refused", st == 404 and r.get("unknownCode"), r)
st, r = post({"action": "sync", "code": "nope", "profiles": []})
ok("a malformed code is refused", st == 400, r)

# ---- one computer pushes ---------------------------------------------
A = prof("kidA", money=1000, spent=200)
A["progress"]["hiragana"]["level"] = 3
A["progress"]["hiragana"]["perfect"]["0"] = True
A["cards"]["あ"] = 1
st, r = post({"action": "sync", "code": code, "profiles": [A], "base": {}})
ok("the first push is stored", st == 200 and by_id(r, "kidA")["money"] == 1000, r)

# ---- the other computer arrives empty and receives it -----------------
st, r = post({"action": "sync", "code": code, "profiles": [], "base": {}})
got = by_id(r, "kidA")
ok("a second computer pulls the whole player", got and got["money"] == 1000 and
   got["progress"]["hiragana"]["level"] == 3, r)

# ---- both play offline, then both sync --------------------------------
# A earned 2000 more and passed level 5; B earned 500 and collected a card.
base = {"kidA": {"money": 1000, "spent": 200}}
A2 = json.loads(json.dumps(A)); A2["money"] = 3000; A2["progress"]["hiragana"]["level"] = 5
A2["progress"]["hiragana"]["boxes"]["あ"] = {"b": 3, "t": 2000}
B2 = json.loads(json.dumps(A)); B2["money"] = 1500; B2["cards"]["い"] = 2
B2["progress"]["hiragana"]["perfect"]["1"] = True
B2["progress"]["hiragana"]["boxes"]["あ"] = {"b": 1, "t": 9000}

st, r = post({"action": "sync", "code": code, "profiles": [A2], "base": base})
st, r = post({"action": "sync", "code": code, "profiles": [B2], "base": base})
m = by_id(r, "kidA")
ok("both afternoons of money are kept (1000 + 2000 + 500)", m["money"] == 3500, m["money"])
ok("the higher level wins", m["progress"]["hiragana"]["level"] == 5, m["progress"]["hiragana"]["level"])
ok("both green stars are kept", m["progress"]["hiragana"]["perfect"] == {"0": True, "1": True},
   m["progress"]["hiragana"]["perfect"])
ok("the card collected on the other machine is kept", m["cards"].get("い") == 2, m["cards"])
ok("the box answered most recently wins", m["progress"]["hiragana"]["boxes"]["あ"]["t"] == 9000,
   m["progress"]["hiragana"]["boxes"]["あ"])

# ---- syncing twice with nothing new must not invent money -------------
base2 = {"kidA": {"money": m["money"], "spent": m["spent"]}}
st, r = post({"action": "sync", "code": code, "profiles": [m], "base": base2})
st, r = post({"action": "sync", "code": code, "profiles": [m], "base": base2})
ok("re-syncing the same save does not multiply money", by_id(r, "kidA")["money"] == 3500,
   by_id(r, "kidA")["money"])

# ---- spending on one machine ------------------------------------------
spend = json.loads(json.dumps(m)); spend["spent"] = m["spent"] + 900
st, r = post({"action": "sync", "code": code, "profiles": [spend], "base": base2})
ok("what was spent stays spent", by_id(r, "kidA")["spent"] == m["spent"] + 900, by_id(r, "kidA")["spent"])

# ---- a deliberate wipe beats an older save ----------------------------
wiped = json.loads(json.dumps(by_id(r, "kidA")))
wiped["money"] = 0; wiped["spent"] = 0; wiped["progress"] = {"hiragana": {"level": 0, "boxes": {}, "perfect": {}}}
wiped["wipe"] = int(time.time() * 1000)
st, r = post({"action": "sync", "code": code, "profiles": [wiped], "base": base2})
w = by_id(r, "kidA")
ok("clearing a record is not undone by the merge",
   w["money"] == 0 and w["progress"]["hiragana"]["level"] == 0, w["money"])
stale = json.loads(json.dumps(m))            # the other machine, still pre-wipe
st, r = post({"action": "sync", "code": code, "profiles": [stale], "base": base2})
w = by_id(r, "kidA")
ok("a stale machine cannot resurrect the cleared record", w["money"] == 0, w["money"])

# ---- deleting a player -------------------------------------------------
st, r = post({"action": "sync", "code": code, "profiles": [], "gone": ["kidA"]})
ok("a deleted player is reported gone", "kidA" in r.get("gone", []), r.get("gone"))
ok("a deleted player is no longer served", by_id(r, "kidA") is None, r.get("profiles"))
st, r = post({"action": "sync", "code": code, "profiles": [stale], "base": {}})
ok("a stale machine cannot resurrect a deleted player", by_id(r, "kidA") is None, r.get("profiles"))

# ---- caps ---------------------------------------------------------------
big = prof("fat", money=1)
big["cards"] = dict(("k%05d" % i, 3) for i in range(30000))
st, r = post({"action": "sync", "code": code, "profiles": [big]})
ok("an absurd save is refused", st == 413, st)
st, r = post({"action": "sync", "code": code, "profiles": [{"nope": 1}]})
ok("a profile with no id is refused", st == 400, st)

print()
print("%d checks, %d failed" % (len(checks), len(fails)))
if fails:
    print("failed: " + ", ".join(fails))
    sys.exit(1)
