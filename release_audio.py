# -*- coding: utf-8 -*-
"""Generate the pronunciation clips and ship them.

One command, safe to re-run:

    python C:\\JapaneseLearning\\release_audio.py

Every step skips work already done, so if the daily Workers AI allowance runs
out part-way the script can simply be run again the next day and it picks up
where it stopped. Nothing is deployed unless at least one new clip exists.

Steps: generate -> embed -> copy to index.html -> deploy to Cloudflare -> push.
Republishing the Artifact is the one thing this cannot do; Claude does that.
"""
import io, os, json, base64, subprocess, sys, time

HERE     = r"C:\JapaneseLearning"
# Kept inside the project, not a session temp folder - a scheduled run hours
# later must not depend on scratch space that may have been cleaned up.
SCRATCH  = os.path.join(HERE, "audio-build")
WORDS    = os.path.join(SCRATCH, "tts_words.json")
AUDIO    = os.path.join(SCRATCH, "audio")
DIST     = os.path.join(SCRATCH, "dist")
SPEAK    = os.path.join(os.path.expanduser("~"), ".claude", "skills", "cf-image-gen", "scripts", "speak.py")
GAME     = os.path.join(HERE, "kana-quest.html")
INDEX    = os.path.join(HERE, "index.html")
PROJECT  = "nihongoadventure"


def run(cmd, **kw):
    print("\n$ " + (cmd if isinstance(cmd, str) else " ".join(cmd)))
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    if out:
        print("\n".join(out.splitlines()[-12:]))
    return r.returncode, out


def clips_present():
    if not os.path.isdir(AUDIO):
        return 0
    return len([n for n in os.listdir(AUDIO)
                if n.endswith(".mp3") and os.path.getsize(os.path.join(AUDIO, n)) > 512])


def model_alive():
    """One probe before committing to a half-hour run.

    Two ways this fails now. HTTP 429 code 4006 is the daily allowance, which
    does come back. HTTP 500 code 3043 is the model itself broken on
    Cloudflare's side - on 2026-08-23 every request failed that way, including
    plain English, while a deliberately malformed body still got a clean schema
    error, so the request shape was never the problem. Both are worth stopping
    for: speak.py retries each of the 1076 words three times with backoff, so a
    doomed run costs ~30 minutes and produces nothing.
    """
    import importlib.util, urllib.request, urllib.error
    spec = importlib.util.spec_from_file_location("speak", SPEAK)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    tok = m.find_token()
    acct = m.find_account(tok)
    body = json.dumps({"prompt": u"いぬ", "lang": "jp"}).encode("utf-8")
    req = urllib.request.Request(
        "%s/accounts/%s/ai/run/%s" % (m.API, acct, m.MODEL), data=body, method="POST",
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            r.read()
            return True, "answering (%s)" % r.headers.get("Content-Type", "?")
    except urllib.error.HTTPError as e:
        return False, "HTTP %s %s" % (e.code, e.read()[:160].decode("utf-8", "replace"))
    except Exception as e:
        return False, str(e)[:160]


def main():
    for path, what in ((WORDS, "word list"), (SPEAK, "speak.py"), (GAME, "the game")):
        if not os.path.exists(path):
            sys.exit("missing %s at %s" % (what, path))

    total = len(json.load(io.open(WORDS, encoding="utf-8")))
    before = clips_present()
    print("=" * 62)
    print("Nihongo Adventure - pronunciation release")
    print("%d clips wanted, %d already generated" % (total, before))
    print("=" * 62)

    ok, why = model_alive()
    print("model probe: %s" % why)
    if not ok:
        sys.exit("\nStopping: MeloTTS is not answering, so this run would only produce failures.\n"
                 "Nothing was changed and finished clips are kept - re-run another day.")

    # 1. generate whatever is still missing
    run([sys.executable, SPEAK, WORDS, "--out", AUDIO, "--lang", "jp", "--workers", "4"])
    after = clips_present()
    print("\nclips now: %d (+%d this run)" % (after, after - before))

    if after == 0:
        sys.exit("No clips were produced - the daily allowance is probably still spent. "
                 "Re-run after 00:00 UTC.")
    if after == before:
        print("Nothing new was generated; not redeploying.")
        return

    # 2. embed them into the single file
    code, _ = run([sys.executable, os.path.join(SCRATCH, "inject_audio.py")])
    if code != 0:
        sys.exit("embedding failed")

    # 3. the repo's canonical file, and the deploy folder
    io.open(INDEX, "w", encoding="utf-8").write(io.open(GAME, encoding="utf-8").read())
    os.makedirs(DIST, exist_ok=True)
    io.open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(
        io.open(INDEX, encoding="utf-8").read())
    print("\ngame is now %d KB" % (os.path.getsize(GAME) // 1024))

    # 4. ship it
    run(["npx", "-y", "wrangler@4", "pages", "deploy", DIST,
         "--project-name", PROJECT, "--branch", "main", "--commit-dirty=true"], cwd=HERE)

    msg = ("Add generated pronunciation for %d items\n\n"
           "Clips generated with MeloTTS on Workers AI and embedded as window.AUDIO,\n"
           "so every child hears the same correct Japanese rather than whatever voice\n"
           "the device happens to have - many have none.\n\n"
           "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>\n" % after)
    run(["git", "add", "-A"], cwd=HERE)
    run(["git", "-c", "core.safecrlf=false", "commit", "-q", "-m", msg], cwd=HERE)
    env = dict(os.environ, GCM_INTERACTIVE="never", GIT_TERMINAL_PROMPT="0")
    run(["git", "push"], cwd=HERE, env=env)

    # 5. confirm it is really live
    for _ in range(20):
        code, out = run('curl -s -o NUL -w "%%{http_code}" https://%s.pages.dev/' % PROJECT)
        if out.strip().endswith("200"):
            print("\nLIVE: https://%s.pages.dev/" % PROJECT)
            break
        time.sleep(5)

    print("\nDONE - %d/%d clips shipped." % (after, total))
    if after < total:
        print("%d still missing; re-run tomorrow to finish them." % (total - after))
    print("Remaining manual step: republish the Artifact from kana-quest.html.")


if __name__ == "__main__":
    main()
