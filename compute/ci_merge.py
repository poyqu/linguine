"""Combine the per-chapter results (parts/<CH>/*.json from ci_chapter.py) and finish the recompute:
curate + validate per season (s2_public.py), no-supporter win rates (add_nosupp.py), best overall teams
(overall_teams.py). Writes results/ with s1/s2_recommended.json, s1/s2_levels.json, overall_teams.json."""
import os, sys, json, glob, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
parts = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "parts")

merged = {}
for f in glob.glob(os.path.join(parts, "*", "*.json")):
    name = os.path.basename(f)
    for k, v in json.load(open(f, encoding="utf-8")).items():
        merged.setdefault(name, {})[k] = v          # each part only holds its own chapter's keys
for name, d in merged.items():
    json.dump(d, open(os.path.join(HERE, name), "w", encoding="utf-8"), indent=1)
    print(f"{name}: {len(d)} entries", flush=True)

def run(args, **env):
    r = subprocess.run([sys.executable, "-X", "utf8"] + args, cwd=HERE, env=dict(os.environ, **env))
    if r.returncode: sys.exit(f"step failed: {args} {env}")

for season, env in ((2, {}), (1, {"STORY_SEASON": "1"})):
    if os.path.exists(os.path.join(HERE, f"s{season}_levels.json")):
        for f in (f"s{season}_recommended.json",):
            if os.path.exists(os.path.join(HERE, f)): os.remove(os.path.join(HERE, f))   # s2_public merges an existing file
        run(["s2_public.py", "curate"], **env)
        run(["s2_public.py", "validate"], **env)
run(["add_nosupp.py"])
run(["overall_teams.py"])
out = os.path.join(HERE, "results"); os.makedirs(out, exist_ok=True)
for f in ("s1_recommended.json", "s2_recommended.json", "s1_levels.json", "s2_levels.json", "overall_teams.json"):
    if os.path.exists(os.path.join(HERE, f)): shutil.copy(os.path.join(HERE, f), out)
print("results:", sorted(os.listdir(out)))
