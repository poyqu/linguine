"""Re-score every existing build in builds.json with the CURRENT verifier (verify/sim.py + enemy_decks.json),
exactly as CI would: story/both builds get fresh `eff` (both seasons) + `eff_s1` / `eff_s2`.
PvP standings are only re-run with --pvp (the round-robin is slow and unaffected by story-only changes).
Usage: python rescore_builds.py [--pvp]"""
import json, os, sys
from multiprocessing import Pool
import verify   # verify imports sim + DECKS + BUILDS_PATH

def score(b):
    e, e1, e2 = verify.story_eff(b["leaders"], b.get("supp", []))
    return round(e, 3), round(e1, 3), round(e2, 3)

if __name__ == "__main__":
    if sys.platform == "win32":   # below-normal priority: don't steal CPU from anything interactive
        import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    BUILDS = json.load(open(verify.BUILDS_PATH))
    story = [b for b in BUILDS if b.get("for") in ("story", "both")]
    print(f"re-scoring {len(story)} story builds over {len(verify.DECKS)} chapters...", flush=True)
    with Pool(min(8, os.cpu_count() or 1)) as p:
        for b, (e, e1, e2) in zip(story, p.map(score, story)):
            b["eff"], b["eff_s1"], b["eff_s2"] = e, e1, e2
    if "--pvp" in sys.argv:
        pvp_builds = [b for b in BUILDS if b.get("for") in ("pvp", "both")]
        if pvp_builds: verify.pvp_league(pvp_builds)
    json.dump(BUILDS, open(verify.BUILDS_PATH, "w"), indent=1)
    print("builds.json re-scored ->", verify.BUILDS_PATH)
    for b in sorted(story, key=lambda b: -b["eff"])[:8]:
        print(f"  {b['eff']*100:5.1f}%  (S1 {b['eff_s1']*100:5.1f}%, S2 {b['eff_s2']*100:5.1f}%)  {'+'.join(map(str, b['leaders']))}  by {b.get('by', '?')}")
