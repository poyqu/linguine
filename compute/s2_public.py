"""Season 2 PUBLIC recommendations: minimum levels + curated alternatives for every S2 chapter.

Inputs (from s2_search.py, public availability = crate + earlier story rewards, no owned-only bosses):
  hard:   s2_teams.json (searched at L20, --thorough)  +  s2_teams_L12.json (searched at L12)
  normal: s2_teams_normal.json (L20)                    +  s2_teams_normal_L10.json (L10)
Phases (python s2_public.py levels|curate|validate|all):
  levels   every finalist team: win rate at L20/L15/L10 + LOWEST level (all 3 leaders equal) that
           still wins >=95% (teams that can't reach 95%: within 5 points of their own L20 rate).
           Fresh seeds, independent of the search seeds. Checkpointed -> s2_levels.json
  curate   per chapter+mode: best team, accessible-first headline, lowest-level pick, and up to 8
           pairwise-distinct cores with 3rd-card alternatives (curate_saved.curate) -> s2_recommended.json
  validate headline + lowest-level picks re-measured at n=1000 (L20 and at their min level)
"""
import os, sys, json
import sim, fastsim
from multiprocessing import Pool
import team_s2 as T
import s2_search as S
from story_search import chapter_key
from curate_saved import curate
from lowprio import lowprio

HERE = os.path.dirname(os.path.abspath(__file__))
SURE = 0.95
SEASON1 = os.environ.get("STORY_SEASON") == "1"     # same pipeline for Season 1 (crate cards only, level cap 15)
CAP = 15 if SEASON1 else 20                            # story level cap of the season = the rated level
P_ = "s1" if SEASON1 else "s2"
LV_FILE = os.path.join(HERE, f"{P_}_levels.json")
OUT = os.path.join(HERE, f"{P_}_recommended.json")
SRC = ({"hard": ["s1_teams_L15.json", "s1_teams_L10.json"], "normal": ["s1_teams_normal_L15.json", "s1_teams_normal_L5.json"]} if SEASON1 else
       {"hard": ["s2_teams.json", "s2_teams_L12.json"], "normal": ["s2_teams_normal.json", "s2_teams_normal_L10.json"]})
TOP_PER_FILE = 40

def wr(trio, supp, ch, mode, lv, n, base=101):
    ed = T.edeck(ch, mode); w = 0
    if fastsim.ENABLED: return fastsim.run(trio, supp, lv, ed, ch + ":" + mode, n, 7919, base)[0] / n
    for k in range(n):
        pd = [sim.apply_player_level(sim.LEADERS[i], lv) for i in trio] + [dict(sim.LEADERS[i]) for i in supp]
        if sim.Sim(k * 7919 + base).run(pd, [dict(c) if c else None for c in ed]) == 0: w += 1
    return w / n

def measure(a):
    mode, ch, trio, supp = a
    w20 = wr(trio, supp, ch, mode, CAP, 300)
    target = SURE if w20 >= SURE else w20 - 0.05
    cache = {}
    def ok(lv):
        if lv not in cache: cache[lv] = wr(trio, supp, ch, mode, lv, 200)
        return cache[lv] >= target
    lo, hi = 1, CAP
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid): hi = mid
        else: lo = mid + 1
    w10 = cache[10] if 10 in cache else wr(trio, supp, ch, mode, 10, 200)
    w15 = cache[15] if 15 in cache else wr(trio, supp, ch, mode, 15, 200)
    return {"mode": mode, "ch": ch, "team": list(trio), "supp": list(supp), "wr": round(w20, 3),
            "wr15": round(w15, 3), "wr10": round(w10, 3), "min_level": lo}

def candidates():
    out = {}
    for mode, files in SRC.items():
        for fn in files:
            p = os.path.join(HERE, fn)
            if not os.path.exists(p): print("missing", fn, flush=True); continue
            for ch, d in json.load(open(p)).items():
                for t in (d.get("teams") or [])[:TOP_PER_FILE]:
                    supp = tuple(x for x in t["supp"] if x not in t["team"])   # the game allows one copy per card
                    out.setdefault((mode, ch), {})[(tuple(t["team"]), supp)] = 1
    if os.environ.get("S2_EXTRA") == "1":   # also re-test every team any earlier search found (same chapter), if obtainable by then
        import glob
        for fn in glob.glob(os.path.join(HERE, "stale_presupp", "s2_teams*.json")):
            if SEASON1: break
            mode = "normal" if "_normal" in fn else "hard"
            for ch, d in json.load(open(fn)).items():
                av = S.available_for(ch)
                for t in (d.get("teams") or [])[:TOP_PER_FILE]:
                    supp = tuple(x for x in t["supp"] if x not in t["team"])
                    if set(t["team"]) | set(supp) <= av:
                        out.setdefault((mode, ch), {})[(tuple(t["team"]), supp)] = 1
    return out

def phase_levels():
    done = json.load(open(LV_FILE)) if os.path.exists(LV_FILE) else {}
    C = candidates()
    keys = sorted(C, key=lambda k: (k[0] != "hard", chapter_key(k[1])))
    with Pool(fastsim.POOL) as pool:
        for mode, ch in keys:
            key = f"{mode}:{ch}"
            have = {(tuple(r["team"]), tuple(r["supp"])) for r in done.get(key, [])}
            jobs = [(mode, ch, list(t), list(s)) for (t, s) in C[(mode, ch)] if (t, s) not in have]
            if not jobs: continue
            res = list(pool.imap_unordered(measure, jobs, chunksize=1))
            done[key] = done.get(key, []) + res
            json.dump(done, open(LV_FILE, "w"))
            best = max(done[key], key=lambda r: (r["wr"], -r["min_level"]))
            print(f"[levels] {key}: {len(done[key])} teams, best {best['wr']*100:.1f}% min L{best['min_level']}", flush=True)

# ---- obtainability tiers (same idea as the lab's srcEase): 0 crate/seasonal/default, 1 story, 2 daily, 3 limited/shop/music
_SEAS = {"Spring", "Summer", "Fall", "Winter", "Sring"}
def ease(sid):
    srcs = set(S.byid.get(sid, []))
    if sid == 4 or "Normal" in srcs or srcs & _SEAS or "Ocean" in srcs: return 0
    if "Story" in srcs: return 1
    if "Daily" in srcs or "Gold" in srcs: return 2
    return 3
def team_ease(r): return max(ease(i) for i in r["team"] + r["supp"])

def pick(rows):
    best = max(rows, key=lambda r: (r["wr"], -r["min_level"], -team_ease(r)))
    near = [r for r in rows if r["wr"] >= best["wr"] - 0.02]
    head = min(near, key=lambda r: (team_ease(r), -r["wr"], r["min_level"]))          # accessible-first
    pool_ok = [r for r in rows if r["wr"] >= (SURE if best["wr"] >= SURE else best["wr"] - 0.03)]
    low = min(pool_ok, key=lambda r: (r["min_level"], -r["wr"], team_ease(r)))       # needs the fewest levels
    return best, head, low

def slim(r): return {k: r[k] for k in ("team", "supp", "wr", "wr15", "wr10", "min_level")}

def phase_curate():
    L = json.load(open(LV_FILE)); out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for key, rows in sorted(L.items(), key=lambda kv: (kv[0].split(":")[0], chapter_key(kv[0].split(":")[1]))):
        mode, ch = key.split(":")
        best, head, low = pick(rows)
        _, cores = curate([dict(r) for r in rows])
        idx = {(tuple(r["team"]), tuple(r["supp"])): r for r in rows}
        for c in cores:
            c["alts"] = [slim(idx[(tuple(a["team"]), tuple(a["supp"]))]) for a in c["alts"]]
            c.pop("nochad", None)
        e = {"team": head["team"], "supp": head["supp"], "winrate": head["wr"], "level": CAP,
             "min_level": head["min_level"], "wr15": head["wr15"], "wr10": head["wr10"],
             "names": [sim.LEADERS[c]["name"] for c in head["team"]],
             "best": slim(best), "lowest_level": slim(low), "cores": cores,
             "enemy": T.NORMAL[ch] if mode == "normal" else T.CHAPTERS_ALL[ch]}
        out.setdefault(ch, {})[mode] = e
        print(f"[curate] {key}: head {head['wr']*100:.0f}% L{head['min_level']} | best {best['wr']*100:.0f}% | "
              f"lowest L{low['min_level']} ({low['wr']*100:.0f}%) | {len(cores)} cores", flush=True)
    json.dump(out, open(OUT, "w"), indent=1)

def vjob(a):
    mode, ch, trio, supp, lv = a
    return (mode, ch, tuple(trio), tuple(supp), lv, wr(trio, supp, ch, mode, lv, 1000, base=900001))

def phase_validate():
    out = json.load(open(OUT)); jobs = []
    for ch, modes in out.items():
        for mode, e in modes.items():
            for r in (e, e["lowest_level"]):
                jobs += [(mode, ch, r["team"], r["supp"], CAP), (mode, ch, r["team"], r["supp"], r["min_level"])]
    with Pool(fastsim.POOL) as pool:
        V = {(m, c, t, s, lv): v for m, c, t, s, lv, v in pool.imap_unordered(vjob, jobs, chunksize=1)}
    for ch, modes in out.items():
        for mode, e in modes.items():
            for r in (e, e["lowest_level"]):
                k = (mode, ch, tuple(r["team"]), tuple(r["supp"]))
                r["val20"] = round(V[k + (CAP,)], 3); r["val_min"] = round(V[k + (r["min_level"],)], 3)
            e["winrate"] = e["val20"]
            print(f"[validate] {mode}:{ch} head L20 {e['val20']*100:.1f}% / L{e['min_level']} {e['val_min']*100:.1f}%  "
                  f"lowest L{e['lowest_level']['min_level']} {e['lowest_level']['val_min']*100:.1f}%", flush=True)
    json.dump(out, open(OUT, "w"), indent=1)

if __name__ == "__main__":
    lowprio()
    ph = sys.argv[1] if len(sys.argv) > 1 else "all"
    if ph in ("levels", "all"): phase_levels()
    if ph in ("curate", "all"): phase_curate()
    if ph in ("validate", "all"): phase_validate()
