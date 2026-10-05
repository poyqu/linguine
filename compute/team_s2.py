"""PRIVATE: one leader trio (L20) vs every Season 2 chapter under a few supporter decks.
Usage: python team_s2.py 411,323,630 [n]"""
import sim, sys, json, os, fastsim
from multiprocessing import Pool
import s2_search as S
from story_search import chapter_key, sd, split_args, find_call, CHAPTERS_ALL
from godot_seed import cpu_supporters, cpu_supporter_cards
import re
import story_bundle as _SB
if _SB.ACTIVE:
    NORMAL = {k: _SB.pairs(v['normal']) for k, v in _SB.B['chapters'].items() if v['normal']}
else:
    NORMAL = {}                                   # story_data _ch arg 6 = normal opponents (arg 8 = hard)
    for m in re.finditer(r'_ch\("(S2E\d+|F\d+)"', sd):
        p = sd.find("(", m.start()); a = split_args(sd[p + 1:find_call(sd, p)])
        o = [(int(x), int(y)) for x, y in re.findall(r'_opp\((\d+),\s*(\d+)\)', a[6])]
        if o: NORMAL[m.group(1)] = o
def edeck(ch, mode):
    p = NORMAL[ch] if mode == "normal" else CHAPTERS_ALL[ch]
    lead = [sim.enemy_card(c, l, 2) for c, l in p]
    return lead + [None] * (3 - len(lead)) + cpu_supporter_cards(ch, [c for c, _ in p], "normal" if mode == "normal" else "hard")

SUPPS = {"none": [], "TV+Flame Crown": [660, 420]}

def job(a):
    trio, ch, n, mode = a
    ed = edeck(ch, mode); out = {}
    for name, supp in SUPPS.items():
        if fastsim.ENABLED: out[name] = fastsim.run(trio, supp, 20, ed, ch + ":" + mode, n, 13, 5)[0] / n; continue
        w = 0
        for k in range(n):
            pd = [sim.apply_player_level(sim.LEADERS[i], 20) for i in trio] + [dict(sim.LEADERS[i]) for i in supp]
            if sim.Sim(k * 13 + 5).run(pd, [dict(c) if c else None for c in ed]) == 0: w += 1
        out[name] = w / n
    return ch, out

if __name__ == "__main__":
    trio = [int(x) for x in sys.argv[1].split(",")]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    chs = sorted(S.CHAPTERS_S2, key=chapter_key)
    mode = "normal" if "--normal" in sys.argv else "hard"
    with Pool(fastsim.POOL) as p:
        res = dict(p.map(job, [(trio, ch, n, mode) for ch in chs]))
    print("mode", mode, {ch: NORMAL.get(ch) for ch in chs[:3]})
    json.dump(res, open(os.path.join(S.HERE, f"team_s2_{mode}.json"), "w"), indent=1)
    print("chapter  " + "  ".join(f"{k:>20}" for k in SUPPS))
    for ch in chs: print(f"{ch:8} " + "  ".join(f"{res[ch][k]*100:19.1f}%" for k in SUPPS))
