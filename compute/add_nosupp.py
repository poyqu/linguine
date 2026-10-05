"""Adds "wr_ns" (win rate with NO supporters, at the season's level cap) to every recommended team that uses
supporters, so the site can show what a team is worth when a player doesn't own them. Run after s2_public.py
(both seasons); rewrites s1_recommended.json / s2_recommended.json in place."""
import os, json
from multiprocessing import Pool
import fastsim, team_s2 as T
HERE = os.path.dirname(os.path.abspath(__file__))
N = 400

def job(a):
    key, ch, mode, trio, lv = a
    return key, fastsim.run(trio, [], lv, T.edeck(ch, mode), ch + ":" + mode, N, 7919, 31337)[0] / N

def rows_of(e):
    rs = [e, e.get("best"), e.get("lowest_level")] + [a for c in e.get("cores", []) for a in c.get("alts", [])]
    return [r for r in rs if r and r.get("team") and r.get("supp")]

if __name__ == "__main__":
    from lowprio import lowprio; lowprio()
    for season, cap in ((2, 20), (1, 15)):
        fn = os.path.join(HERE, f"s{season}_recommended.json")
        if not os.path.exists(fn): continue
        d = json.load(open(fn)); jobs = {}
        for ch, modes in d.items():
            for mode, e in modes.items():
                for r in rows_of(e):
                    k = (ch, mode, tuple(r["team"]))
                    jobs[k] = (k, ch, mode, list(r["team"]), cap)
        with Pool(fastsim.POOL) as p:
            R = dict(p.imap_unordered(job, jobs.values(), chunksize=4))
        for ch, modes in d.items():
            for mode, e in modes.items():
                for r in rows_of(e): r["wr_ns"] = round(R[(ch, mode, tuple(r["team"]))], 3)
        json.dump(d, open(fn, "w"), indent=1)
        print(f"season {season}: {len(jobs)} teams with supporters re-run without them", flush=True)
