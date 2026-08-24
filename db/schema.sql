-- One family = one code. The code is the only credential, like a secret link.
CREATE TABLE IF NOT EXISTS families (
  code    TEXT PRIMARY KEY,
  created INTEGER NOT NULL,
  seen    INTEGER NOT NULL
);

-- One row per child, so two children on two computers never contend.
-- `data` is the profile JSON exactly as the game holds it; `rev` counts merges.
CREATE TABLE IF NOT EXISTS saves (
  code    TEXT NOT NULL,
  pid     TEXT NOT NULL,
  data    TEXT NOT NULL,
  rev     INTEGER NOT NULL DEFAULT 1,
  updated INTEGER NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (code, pid)
);

-- A crude per-minute throttle. Rows are disposable; old minutes are swept.
CREATE TABLE IF NOT EXISTS hits (
  ip     TEXT NOT NULL,
  minute INTEGER NOT NULL,
  n      INTEGER NOT NULL,
  PRIMARY KEY (ip, minute)
);
