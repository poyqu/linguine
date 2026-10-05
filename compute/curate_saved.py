"""Curate the broad-search output into 8 hand-picked CORES per chapter for the Sandbox's saved
'best team for this fixed chapter' panel.

Each core = a shared 2-card pair plus its ranked 3rd-card alternatives (e.g. Bricks + Bad Time
with third = Dramatic Outlaw / Steampunk / White Branded Visor / ...). This collapses near-
duplicate teams into one entry-with-alternatives instead of either spamming them or dropping
the good ones. At most PREM_CAP of the 8 cores lean on the single most-relied-on card (chad on
the hard chapters), so the rest are genuine chad-free options for players who don't own it.

Reads {CH}_teams.json (full ranked list from broad_search). Writes saved_teams.json =
{CH: [ {lead:[a,b], wr, nochad, alts:[{team,supp,wr}...]} ...up to 8 ]}. Re-runnable.
"""
import json, os, sys, glob
from collections import Counter
import sim

HERE=os.path.dirname(os.path.abspath(__file__))
CHAD=377
PREM_CAP=2        # at most this many of the 8 cores use the premium card (chad is daily-only, so keep alternatives dominant)
ALT_MAX=6         # 3rd-card alternatives listed per core
ALT_FLOOR=0.33    # hide alternatives weaker than this (unless it's the core's only option)
CORE_FLOOR=0.40   # a non-premium core needs at least this win rate to be shown...
MIN_FREE=3        # ...unless fewer than this many clear it, then show the best few anyway
nm=lambda i: sim.LEADERS[i]['name'].replace('Linguine','L.') if i in sim.LEADERS else f"#{i}"

def anchor_pair(team, ranked):
    """The team's pair shared by the most other teams - the natural 'core', with the 3rd slot
    as the flex position whose alternatives we list."""
    best=None
    for p in ((team[0],team[1]),(team[0],team[2]),(team[1],team[2])):
        mem=[r for r in ranked if p[0] in r['team'] and p[1] in r['team']]
        if best is None or len(mem)>len(best[1]): best=(p,mem)
    return best   # (pair, members win-rate-desc)

def curate(teams):
    ranked=sorted(teams,key=lambda r:-r['wr'])
    prem=Counter(c for r in ranked[:10] for c in r['team']).most_common(1)[0][0]
    # 1) pick 8 pairwise-distinct representatives (no two share 2 cards), premium-capped
    reps=[]; prem_used=0
    def distinct(t): return all(len(set(t)&set(r['team']))<=1 for r in reps)
    for r in ranked:
        if len(reps)>=8: break
        if not distinct(r['team']): continue
        if prem in r['team'] and prem_used>=PREM_CAP: continue
        reps.append(r); prem_used+= prem in r['team']
    if len(reps)<8:                               # cap starved us -> relax it, keep distinctness
        rid=set(id(r) for r in reps)
        for r in ranked:
            if len(reps)>=8: break
            if id(r) in rid or not distinct(r['team']): continue
            reps.append(r)
    # 2) headline = the rep itself (so headlines are pairwise distinct); alternatives = weaker
    #    3rd-card swaps on the rep's anchor pair, each team shown under only one core
    shown=set(); out=[]
    for r in reps:
        t=r['team']; p,mem=anchor_pair(t,ranked)
        alts=[]
        for m in mem:
            if m['wr']>r['wr']+1e-9: continue                       # never list a team stronger than the headline
            if prem not in t and prem in m['team']: continue        # keep chad-free cores chad-free
            k=tuple(sorted(m['team']))
            if k in shown: continue
            if m['wr']<min(ALT_FLOOR,r['wr']): continue
            alts.append(m); shown.add(k)
            if len(alts)>=ALT_MAX: break
        out.append({"lead":list(p),"wr":r['wr'],"nochad":CHAD not in t,"isprem":prem in t,
                    "alts":[{"team":m["team"],"supp":m["supp"],"wr":m["wr"]} for m in alts]})
    # keep the premium cores + the GOOD alternative cores; on brutal chapters show fewer rather
    # than pad with junk, but always surface at least MIN_FREE alternatives for chad-less players
    prem_cores=[c for c in out if c["isprem"]]
    free_cores=sorted((c for c in out if not c["isprem"]),key=lambda c:-c["wr"])
    good_free=[c for c in free_cores if c["wr"]>=CORE_FLOOR]
    if len(good_free)<MIN_FREE: good_free=free_cores[:MIN_FREE]
    out=sorted(prem_cores+good_free,key=lambda c:-c["wr"])[:8]
    for c in out: c.pop("isprem",None)
    return prem,out

if __name__=="__main__":
    chaps=sys.argv[1:] or sorted((os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(HERE,"F*_teams.json"))),
                                 key=lambda c:int(c[1:]))
    out={}
    for CH in chaps:
        p=os.path.join(HERE,f"{CH}_teams.json")
        if not os.path.exists(p): continue
        teams=json.load(open(p)); prem,cores=curate(teams); out[CH]=cores
        print(f"\n=== {CH}  (premium={nm(prem)}) ===")
        for c in cores:
            third=lambda t: [i for i in t if i not in c['lead']][0]
            tag=" [no chad]" if c["nochad"] else ""
            print(f"  {c['wr']*100:5.1f}%  {nm(c['lead'][0])} + {nm(c['lead'][1])}{tag}")
            for m in c["alts"]:
                print(f"          + {nm(third(m['team'])):30} {m['wr']*100:5.1f}%   supp={[nm(i) for i in m['supp']]}")
    json.dump(out,open(os.path.join(HERE,"saved_teams.json"),"w"),indent=1)
    print(f"\nwrote saved_teams.json ({len(out)} chapters)")
