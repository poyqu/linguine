"""Best teams OVERALL: rank teams by how much of the story they clear on their own, per season and for both
seasons together, every EXTREME fight at the season's story level cap (Season 1: 15, Season 2: 20).

Candidates = every finalist the per-chapter pipelines measured (s1_levels.json, s2_levels.json, EXTREME only),
plus the community story builds and the old whole-story list. Stages:
  1  screen every candidate on every EXTREME chapter of both seasons (n=SN, fixed seeds)
  2  the best ~N per view are re-measured at n=FN on fresh seeds
  3  diversity pick per view (no two teams share 2 leaders) -> top K
Writes overall_teams.json = {"s1": [...], "s2": [...], "both": [...]}, each row
{team, supp, s1:{mean, clears, n}, s2:{mean, clears, n}, per:{chapter: wr}}.
Usage: python overall_teams.py [--smoke]"""
import os, sys, json, time
import sim, fastsim
from multiprocessing import Pool
import team_s2 as T
from story_search import chapter_key, CHAPTERS_ALL
from lowprio import lowprio

HERE = os.path.dirname(os.path.abspath(__file__))
SMOKE = "--smoke" in sys.argv
QUICK = os.environ.get("OV_QUICK") == "1"   # fast preview while the full Season 1 data is still being computed
SN, KEEP, FN, K = (8, 6, 30, 4) if SMOKE else (16, 25, 150, 10) if QUICK else (40, 60, 300, 15)
CAP = {1: 15, 2: 20}
CHS = sorted(CHAPTERS_ALL, key=chapter_key)
season = lambda ch: 2 if ch.startswith("S2") else 1
t0 = time.time()
def log(m): print(f"[{time.time()-t0:7.1f}s] {m}", flush=True)

def wr(team, supp, ch, n, base):
    ed = T.edeck(ch, "hard"); lv = CAP[season(ch)]; w = 0
    if fastsim.ENABLED: return fastsim.run(team, supp, lv, ed, ch + ":hard", n, 7919, base)[0] / n
    for k in range(n):
        pd = [sim.apply_player_level(sim.LEADERS[i], lv) for i in team] + [dict(sim.LEADERS[i]) for i in supp]
        if sim.Sim(base + k * 7919).run(pd, [dict(c) if c else None for c in ed]) == 0: w += 1
    return w / n

def job(a):
    team, supp, n, base = a
    return tuple(team), tuple(supp), {ch: wr(team, supp, ch, n, base) for ch in CHS}

def summarize(per):
    out = {}
    for s in (1, 2):
        v = [per[c] for c in CHS if season(c) == s]
        out[f"s{s}"] = {"mean": round(sum(v) / len(v), 4), "clears": sum(1 for x in v if x >= .95), "n": len(v)}
    return out

def candidates():
    C = {}
    for fn in ("s1_levels.json", "s2_levels.json"):
        p = os.path.join(HERE, fn)
        if not os.path.exists(p): log(f"missing {fn}"); continue
        for key, rows in json.load(open(p)).items():
            if not key.startswith("hard:"): continue
            for r in rows:
                if r.get("wr", 0) < .5: continue
                sp = tuple(x for x in r["supp"] if x not in r["team"])
                C[(tuple(sorted(r["team"])), sp)] = 1
    for fn in ("recommended_story.json", "saved_teams.json"):   # Season 1 picks + their alternatives
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            for ch, v in json.load(open(p)).items():
                rows = [v] if isinstance(v, dict) and "team" in v else []
                for c in (v if isinstance(v, list) else v.get("cores", []) if isinstance(v, dict) else []):
                    rows += c.get("alts", [])
                for r in rows:
                    if "team" in r: C[(tuple(sorted(r["team"])), tuple(x for x in r.get("supp", []) if x not in r["team"]))] = 1
    for fn, get in (("../linguine-repo/builds.json" if os.path.exists(os.path.join(HERE, "../linguine-repo/builds.json")) else "../builds.json", lambda d: [(b["leaders"], b.get("supp", [])) for b in d if b.get("for") in ("story", "both")]),
                    ("story_wide.json", lambda d: [(t["team"], t.get("supp", [])) for t in d.get("teams", [])])):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            for t, sp in get(json.load(open(p))):
                C[(tuple(sorted(t)), tuple(x for x in sp if x not in t))] = 1
    return [(list(t), list(s)) for t, s in C]

def diverse(rows, k):
    out = []
    for r in rows:
        if all(len(set(r["team"]) & set(o["team"])) <= 1 for o in out): out.append(r)
        if len(out) >= k: break
    return out

if __name__ == "__main__":
    lowprio()
    cand = candidates()
    if SMOKE: cand = cand[:24]
    log(f"{len(cand)} candidate teams x {len(CHS)} chapters (screen n={SN})")
    with Pool(fastsim.POOL) as pool:
        S1 = list(pool.imap_unordered(job, [(t, s, SN, 101) for t, s in cand], chunksize=2))
        scored = [{"team": list(t), "supp": list(s), **summarize(p)} for t, s, p in S1]
        views = {"s1": lambda r: (r["s1"]["clears"], r["s1"]["mean"]), "s2": lambda r: (r["s2"]["clears"], r["s2"]["mean"]),
                 "both": lambda r: (r["s1"]["clears"] + r["s2"]["clears"], r["s1"]["mean"] + r["s2"]["mean"])}
        pick = {}
        for v, key in views.items():
            for r in sorted(scored, key=key, reverse=True)[:KEEP]: pick[(tuple(r["team"]), tuple(r["supp"]))] = 1
        log(f"stage 2: {len(pick)} teams at n={FN}")
        S2 = list(pool.imap_unordered(job, [(list(t), list(s), FN, 900001) for t, s in pick], chunksize=1))
    final = [{"team": list(t), "supp": list(s), **summarize(p), "per": {c: round(x, 3) for c, x in p.items()}} for t, s, p in S2]
    out = {v: diverse(sorted(final, key=key, reverse=True), K) for v, key in views.items()}
    json.dump(out, open(os.path.join(HERE, "overall_quick.json" if QUICK else "overall_teams.json"), "w"), indent=1)
    for v, rows in out.items():
        log(f"=== {v} ===")
        for r in rows[:6]:
            log(f"  S1 {r['s1']['clears']:2}/21 {r['s1']['mean']*100:5.1f}%  S2 {r['s2']['clears']:2}/21 {r['s2']['mean']*100:5.1f}%  "
                f"{' + '.join(sim.LEADERS[i]['name'].replace('Linguine', 'L.') for i in r['team'])}")
    log("ALL DONE -> overall_teams.json")
