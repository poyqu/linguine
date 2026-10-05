"""Run battle batches on the site's JS engine (fastsim_worker.js under Node) instead of sim.py: ~2-3x faster per core,
same rules (lab_engine.js is cross-validated against sim.py). Each process gets its own Node child, so the
existing multiprocessing Pools keep working: every pool worker just becomes a thin messenger.
Seeds differ from sim.py's (mulberry32 vs Python's random), so results match statistically, not battle by battle.
FASTSIM=0 in the environment falls back to sim.py everywhere."""
import os, json, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ENABLED = os.environ.get("FASTSIM", "1") != "0" and shutil.which("node") is not None
POOL = int(os.environ.get("POOL", "12" if ENABLED else "8"))   # worker processes (16 threads: leave a few free)
_P = None; _SENT = set(); _PID = None

def _proc():
    global _P, _PID
    if _P is None or _P.poll() is not None or _PID != os.getpid():   # new process after fork (Linux): own Node child
        _PID = os.getpid()
        _P = subprocess.Popen(["node", os.path.join(HERE, "fastsim_worker.js")], cwd=HERE, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, text=True, bufsize=1, encoding="utf-8")
        _SENT.clear()
    return _P

def run(trio, supp, lv, ed, ek, n, sa, sb, story=True):
    """n battles of player trio (at level lv) + supporters vs enemy deck ed (cached under key ek),
    battle k seeded sa*k+sb. -> (wins, fit_sum) with s2_search.fit's per-battle score."""
    p = _proc()
    job = {"ek": ek, "trio": list(trio), "lv": int(lv), "supp": list(supp), "n": int(n), "sa": sa, "sb": sb, "story": story}
    if ek not in _SENT:
        job["ed"] = ed; _SENT.add(ek)
    p.stdin.write(json.dumps(job) + "\n"); p.stdin.flush()
    r = json.loads(p.stdout.readline())
    return r["w"], r["f"]

def run_full(ek, ed, n, sa, sb, story=True, pd=None, trio=None, lv=20, supp=()):
    """like run() but takes a ready player deck (pd) if given; -> dict w/l/d/f (l = team wiped, d = timeout/both)"""
    p = _proc()
    job = {"ek": ek, "n": int(n), "sa": sa, "sb": sb, "story": story}
    if pd is not None: job["pd"] = pd
    else: job.update(trio=list(trio), lv=int(lv), supp=list(supp))
    if ek not in _SENT:
        job["ed"] = ed; _SENT.add(ek)
    p.stdin.write(json.dumps(job) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())
