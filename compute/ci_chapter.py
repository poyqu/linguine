"""One chapter's full search, for one GitHub Actions machine (or locally): the same steps as
run_recompute_*.sh, limited to this chapter, then its level checks (s2_public.py levels).
Usage: python ci_chapter.py S2E20   -> out/S2E20/ holds this chapter's team + levels files"""
import os, sys, subprocess, shutil, glob, json
HERE = os.path.dirname(os.path.abspath(__file__))
CH = sys.argv[1]
S1 = CH.startswith("F")
DEEP = {"S2E20", "S2E21", "S2E22", "F17", "F20", "F21"}   # the hardest fights get the wider search too

def run(args, **env):
    e = dict(os.environ, **{k: str(v) for k, v in env.items()})
    if S1: e["STORY_SEASON"] = "1"
    print("::group::" + " ".join(args) + " " + " ".join(f"{k}={v}" for k, v in env.items()), flush=True)
    if os.environ.get("CI_SMOKE") == "1" and args[0] == "s2_search.py": args = args + ["--smoke"]   # dry run
    r = subprocess.run([sys.executable, "-X", "utf8"] + args, cwd=HERE, env=e)
    print("::endgroup::", flush=True)
    if r.returncode: sys.exit(f"step failed: {args}")

cap, low_hard, low_norm = (15, 10, 5) if S1 else (20, 12, 10)
run(["s2_search.py", CH, "--thorough", "--level", str(cap)])
run(["s2_search.py", CH, "--thorough", "--level", str(low_hard)])
if CH in DEEP: run(["s2_search.py", CH, "--deep", "--level", str(cap)])
run(["s2_search.py", CH, "--level", str(cap)], S2_MODE="normal")
run(["s2_search.py", CH, "--level", str(low_norm)], S2_MODE="normal")
run(["s2_public.py", "levels"])
out = os.path.join(HERE, "out", CH); os.makedirs(out, exist_ok=True)
pre = "s1" if S1 else "s2"
for f in glob.glob(os.path.join(HERE, f"{pre}_teams*.json")) + [os.path.join(HERE, f"{pre}_levels.json")]:
    if os.path.exists(f): shutil.copy(f, out)
print("saved:", sorted(os.listdir(out)))
