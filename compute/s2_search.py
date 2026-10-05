"""PRIVATE (never published): best teams for the Season 2 EXTREME chapters.

Season 2 is far harder than Season 1 (enemy levels 9-25 on the S2 level curve) and most S1
champion teams score 0% from S2E12 on, so the pool can't be hand-picked. Pipeline per chapter:
  A) card screen: every obtainable card in random trios, scored by a smooth fitness
     (win = 1..1.3 by speed, loss = 0.8 * share of enemy HP removed) so hopeless chapters still give signal
  B) all trios over (top screened cards + known contenders + previous chapter winners)
  C) supporter screen on the best trios, then trio x supporter-config grid
  D) final validation (n=FN) at the search level, plus the finalists re-run at L10 and L15

Obtainable = crate/shop/fishing cards + all Season 1 story rewards (S2 opens after S1) + Season 2
story rewards from earlier episodes (+ this episode's NORMAL reward, which you get before EXTREME).

Usage: python s2_search.py [S2E1 S2E2 ...] [--level 20] [--smoke]
Writes s2_teams.json (merged, private).
"""
import sim, fastsim, re, os, json, itertools, time, sys, random
from collections import Counter
from multiprocessing import Pool
from story_search import CHAPTERS_S2, CHAPTERS, chapter_key, sd, split_args, find_call
# STORY_SEASON=1: run the same pipeline on Season 1 (crate cards only, no story rewards, files s1_*)
SEASON1 = os.environ.get("STORY_SEASON") == "1"
CHAPS = CHAPTERS if SEASON1 else CHAPTERS_S2
from godot_seed import cpu_supporters, cpu_supporter_cards

HERE = os.path.dirname(os.path.abspath(__file__))
t0 = time.time()
def log(m): print(f"[{time.time()-t0:7.1f}s] {m}", flush=True)

SMOKE = "--smoke" in sys.argv
LEVEL = int(sys.argv[sys.argv.index("--level")+1]) if "--level" in sys.argv else 20
ARGS = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]

# ---- availability ----
UNAVAIL = set(json.load(open(os.path.join(HERE, "unavailable.json"))))
import story_bundle as _SB
if _SB.ACTIVE:
    CRATE = set(_SB.B['crate'])
    byid = {int(k): v for k, v in _SB.B['byid'].items()}
else:
    _sm = open(os.path.join(HERE, "decompiled", "skin_manager.gd"), encoding="utf-8").read()
    _i = _sm.index("var skins =[")+len("var skins ="); _d = 0; _j = _i
    while _j < len(_sm):
        if _sm[_j] == "[": _d += 1
        elif _sm[_j] == "]":
            _d -= 1
            if _d == 0: break
        _j += 1
    byid = {}
    for s, cs in re.findall(r'"image":\s*"res://[Ss]ubject ?(\d+)\.png".*?"crate_sources":\s*(\[[^\]]*\])', _sm[_i:_j+1], re.S):
        byid.setdefault(int(s), []).extend(re.findall(r'"([^"]+)"', cs))
    def crate_ok(sid):
        lst = byid.get(sid)
        return bool(lst) and any(x not in ("money", "Story", "music") for x in lst) and sid in sim.LEADERS and sid != 150 and sid not in UNAVAIL
    CRATE = {s for s in byid if crate_ok(s)}

# story skin rewards per chapter: (normal, extreme)
if _SB.ACTIVE:
    REWARDS = {k: (v[0], v[1]) for k, v in _SB.B['rewards'].items()}
else:
    REWARDS = {}
    for m in re.finditer(r'_ch\("((?:F|S\d+E)\d+)"', sd):
        p = sd.find("(", m.start()); e = find_call(sd, p)
        a = split_args(sd[p+1:e])
        sk = lambda k: [int(x) for x in re.findall(r'_rew_skin\((\d+)\)', a[k])] if len(a) > k else []
        REWARDS[m.group(1)] = (sk(7), sk(9))
# S2_OWNED=1: a player who owns the Season 1 story rewards (Potato, Grunky, Muffin, Witch Hat, ...).
# These sit in unavailable.json for the PUBLIC recommendations, but a story player has them.
OWNED = os.environ.get("S2_OWNED") == "1"
TEAMS_FILE = ("s1_teams.json" if SEASON1 else "s2_teams_owned.json" if OWNED else "s2_teams.json")
# S2_MODE=normal: the NORMAL-difficulty fight (story_data _ch arg 6 = a single boss, other slots empty)
NORMAL_MODE = os.environ.get("S2_MODE") == "normal"
if NORMAL_MODE: TEAMS_FILE = TEAMS_FILE.replace(".json", "_normal.json")
if LEVEL != 20: TEAMS_FILE = TEAMS_FILE.replace(".json", f"_L{LEVEL}.json")   # don't overwrite the L20 run
if _SB.ACTIVE:
    NORMAL_OPP = {k: _SB.pairs(v['normal']) for k, v in _SB.B['chapters'].items() if v['normal']}
else:
    NORMAL_OPP = {}
    for m in re.finditer(r'_ch\("(S2E\d+|F\d+)"', sd):
        p = sd.find("(", m.start()); a = split_args(sd[p+1:find_call(sd, p)])
        o = [(int(x), int(y)) for x, y in re.findall(r'_opp\((\d+),\s*(\d+)\)', a[6])]
        if o: NORMAL_OPP[m.group(1)] = o
def available_for(CH):
    if CH.startswith("F"):   # Season 1 recs: crate cards only (story rewards would be circular)
        return {c for c in CRATE if c in sim.LEADERS and c not in UNAVAIL and c != 150}
    have = set(CRATE)
    for cid, (norm, hard) in REWARDS.items():
        if cid.startswith("F") or chapter_key(cid) < chapter_key(CH): have |= set(norm) | set(hard)
        elif cid == CH: have |= set(norm)
    ok = {c for c in have if c in sim.LEADERS and c not in UNAVAIL and c != 150}
    if OWNED:
        ok |= {c for cid, (n, h) in REWARDS.items() if cid.startswith("F") for c in n + h if c in sim.LEADERS and c != 635}
    return ok

OLD = [325,275,273,324,372,190,191,412,413,334,285,319,305,170,175,217,240,238,239,182,118,117,
       195,475,24,335,56,423,199,297,299,221,252,213,377,653,619,263,390,94,321,467,630,632,634,631,643,
       633,644,660,420,637,628,484,483,477,459,458,457,40,39,241,546,529,540,553,575,379,443,601,645,646,647]
BASE_SUPP = [660,420,633,644,637,628,632,634,631,643,653,265,190,645,646,647]

# knobs: screen trios/card, screen n, pool top-K, stage-B n, stage-B keep, supp-screen trios, grid n, grid keep, final n
K = (dict(SC=4, SN=2, TOP=14, BN=2, BK=30, SS=6, GN=6, GK=8, FN=30) if SMOKE else
     dict(SC=32, SN=3, TOP=110, BN=4, BK=400, SS=24, GN=40, GK=40, FN=400) if "--deep" in sys.argv else
     dict(SC=16, SN=3, TOP=64, BN=4, BK=400, SS=24, GN=40, GK=60, FN=400) if "--thorough" in sys.argv else
     dict(SC=16, SN=3, TOP=46, BN=6, BK=260, SS=24, GN=40, GK=40, FN=400))

def edeck(CH):
    p = NORMAL_OPP[CH] if NORMAL_MODE else CHAPS[CH]
    lead = [sim.enemy_card(c, l, 2) for c, l in p]
    return lead + [None]*(3-len(lead)) + cpu_supporter_cards(CH, [c for c, _ in p], "normal" if NORMAL_MODE else "hard")
_ED = {}
def get_ed(CH):
    ed = _ED.get(CH)
    if ed is None: ed = edeck(CH); _ED[CH] = ed
    return ed
def fit(trio, supp, CH, n, lv=None, wins_only=False):
    ed = get_ed(CH)
    if fastsim.ENABLED:   # the site's JS engine under Node (same rules, ~3x faster per core)
        w, f = fastsim.run(trio, supp, lv or LEVEL, ed, CH + (":normal" if NORMAL_MODE else ":hard"), n, 13, 5)
        return (w if wins_only else f) / n
    tot = 0.0; ehp = sum(c["hp"] for c in ed[:3] if c)
    for s in range(n):
        pd = [sim.apply_player_level(sim.LEADERS[i], lv or LEVEL) for i in trio]+[dict(sim.LEADERS[i]) for i in supp]
        S = sim.Sim(s*13+5)
        if S.run(pd, [dict(c) if c else None for c in ed]) == 0: tot += 1 if wins_only else 1+0.3*max(0, 1-S.turn/30)   # faster wins rank higher
        elif not wins_only:
            left = sum(max(0, l.hp) for l in S.teams[1]); tot += 0.8*max(0.0, 1-left/ehp)
    return tot/n
def job(a):
    trio, supp, CH, n, lv, wo = a
    return (fit(trio, supp, CH, n, lv, wo), tuple(trio), tuple(supp))

def main():
    from lowprio import lowprio; lowprio()
    chaps = ARGS or sorted(CHAPS, key=chapter_key)
    nm = lambda i: sim.LEADERS[i]['name'].replace('Linguine', 'L.')
    outp = os.path.join(HERE, TEAMS_FILE)
    merged = json.load(open(outp)) if os.path.exists(outp) and not SMOKE else {}
    prev_win = []
    log(f"chapters={chaps} level={LEVEL} smoke={SMOKE} knobs={K}")
    with Pool(fastsim.POOL) as pool:
        for CH in chaps:
            av = sorted(available_for(CH)); avs = set(av)
            rng = random.Random(sum(map(ord, CH)))
            # A) card screen with a generic pump supporter
            jobs = []
            for c in av:
                for _ in range(K["SC"]):
                    mates = rng.sample([x for x in av if x != c], 2)
                    jobs.append(((c, *mates), [660], CH, K["SN"], None, False))
            sc = {}
            for v, t, _ in pool.imap_unordered(job, jobs, chunksize=64):
                sc.setdefault(t[0], []).append(v)
            rank = sorted(av, key=lambda c: -sum(sc[c])/len(sc[c]))
            top = rank[:K["TOP"]]
            wide = set(rank[:150])   # known S1 contenders only if they also screen decently here
            P = sorted(set(top) | {c for c in OLD if c in avs and c in wide} | {c for c in prev_win if c in avs})
            if SMOKE: P = sorted(set(top) | {c for c in OLD[:6] if c in avs})
            log(f"[{CH}] avail {len(av)}; screen top: {', '.join(nm(c)[:22] for c in top[:10])}; pool {len(P)}")
            # B) all trios over the pool
            trios = list(itertools.combinations(P, 3))
            B = list(pool.imap_unordered(job, [(t, [660], CH, K["BN"], None, False) for t in trios], chunksize=64))
            B.sort(reverse=True)
            best = [t for _, t, _ in B[:K["BK"]]]
            log(f"[{CH}] stage B {len(trios)} trios; best fit {B[0][0]:.2f} ({' + '.join(nm(i) for i in B[0][1])})")
            # C) supporter screen: every available supporter alone, on the top trios
            spool = [c for c in av if sim.LEADERS[c].get("supporter")]
            sj = [(t, [s], CH, 8, None, False) for t in best[:K["SS"]] for s in spool if s not in t]   # one copy per card
            ss = Counter(); sn = Counter()
            for v, t, s in pool.imap_unordered(job, sj, chunksize=32):
                ss[s[0]] += v; sn[s[0]] += 1
            srank = sorted(spool, key=lambda s: -ss[s]/sn[s] if sn[s] else 0)
            ts = srank[:10]
            cfgs = [[]]+[[s] for s in ts]+[list(p) for p in itertools.combinations(ts[:6], 2)]+[ts[:3], ts[:4]]
            cfgs += [c for c in ([633,644], [660,420], [633,644,660,420], [645,646,647,660], [645,646,647], [645,646,647,420]) if set(c) <= avs]
            log(f"[{CH}] supporters: " + ", ".join("%s %.2f" % (nm(s)[:20], ss[s]/max(1, sn[s])) for s in ts[:6]) + f"; {len(cfgs)} configs")
            G = list(pool.imap_unordered(job, [(t, c, CH, K["GN"], None, False) for t in best for c in cfgs if not set(c) & set(t)], chunksize=16))
            G.sort(reverse=True)
            seen = set(); cand = []
            for v, t, c in G:
                if t in seen: continue
                seen.add(t); cand.append((t, c))
                if len(cand) >= K["GK"]: break
            # D) final win rates at LEVEL, then the same finalists at L15 / L10
            F = list(pool.imap_unordered(job, [(t, c, CH, K["FN"], None, True) for t, c in cand], chunksize=1))
            F.sort(reverse=True)
            low = {}
            for lv in (15, 10):
                for v, t, c in pool.imap_unordered(job, [(t, c, CH, K["FN"]//2, lv, True) for _, t, c in F[:20]], chunksize=1):
                    low[(lv, t, c)] = v
            teams = [{"team": list(t), "supp": list(c), "wr": round(v, 3),
                      "wr15": round(low[(15, t, c)], 3) if (15, t, c) in low else None,
                      "wr10": round(low[(10, t, c)], 3) if (10, t, c) in low else None} for v, t, c in F]
            merged[CH] = {"level": LEVEL, "enemy": (NORMAL_OPP if NORMAL_MODE else CHAPS)[CH], "teams": teams,
                          "screen_top": top[:20], "supp_top": ts}
            if not SMOKE or os.environ.get("SMOKE_WRITE") == "1": json.dump(merged, open(outp, "w"), indent=1)
            prev_win = sorted({c for x in teams[:5] for c in x["team"]})
            log(f"=== {CH} top (L{LEVEL} n={K['FN']}; L15/L10 n={K['FN']//2}) ===")
            for x in teams[:8]:
                print(f"   {x['wr']*100:5.1f}%  L15 {('%.0f' % (x['wr15']*100)) if x['wr15'] is not None else '-':>3}%  "
                      f"L10 {('%.0f' % (x['wr10']*100)) if x['wr10'] is not None else '-':>3}%  "
                      f"{' + '.join(nm(i) for i in x['team'])} | {[nm(i) for i in x['supp']]}", flush=True)
    log(f"ALL DONE -> {TEAMS_FILE}")

if __name__ == "__main__":
    main()
