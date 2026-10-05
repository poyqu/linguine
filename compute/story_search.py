"""Best team per story chapter (EXTREME), multiprocess over 8 workers.
Writes recommended_story.json for the lab's Recommended Teams tab.
"""
import sim, itertools, json, os, re, time
from multiprocessing import Pool
from godot_seed import cpu_supporters, cpu_supporter_cards

HERE=os.path.dirname(os.path.abspath(__file__))
# all 21 chapters from story_data (id -> hard opponents)
import story_bundle as _SB
sd="" if _SB.ACTIVE else open(os.path.join(HERE,"decompiled","story_data.gd"),encoding="utf-8").read()
def split_args(s):
    args=[];depth=0;cur="";instr=False
    for ch in s:
        if ch=='"': instr=not instr; cur+=ch
        elif instr: cur+=ch
        elif ch in "([{": depth+=1;cur+=ch
        elif ch in ")]}": depth-=1;cur+=ch
        elif ch=="," and depth==0: args.append(cur.strip());cur=""
        else: cur+=ch
    if cur.strip(): args.append(cur.strip())
    return args
def find_call(s,start):
    depth=0;instr=False
    for i in range(start,len(s)):
        ch=s[i]
        if ch=='"': instr=not instr
        elif instr: continue
        elif ch=="(": depth+=1
        elif ch==")":
            depth-=1
            if depth==0: return i
    return -1
if _SB.ACTIVE:
    CHAPTERS_ALL={k:_SB.pairs(v['hard']) for k,v in _SB.B['chapters'].items() if v['hard']}
else:
    CHAPTERS_ALL={}
    for m in re.finditer(r'_ch\("((?:F|S\d+E)\d+)"',sd):     # Season 1 = F1..F21, Season 2 = S2E1.. (no S2E3)
        p=sd.find("(",m.start()); e=find_call(sd,p)
        args=split_args(sd[p+1:e])
        hard=[(int(a),int(b)) for a,b in re.findall(r'_opp\((\d+),\s*(\d+)\)',args[8])] if len(args)>8 else []
        if hard: CHAPTERS_ALL[m.group(1)]=hard
def season_of(cid):   # story_data.season_of
    return int(cid[1:cid.index("E")]) if cid.startswith("S") and "E" in cid else 1
def chapter_key(cid):   # sort key: (season, episode number)
    return (season_of(cid), int(cid[cid.index("E")+1:]) if cid.startswith("S") else int(cid[1:]))
# CHAPTERS stays Season 1 only: every existing pipeline (incl. the PUBLIC Builds-board verifier) keeps
# its old meaning. Season 2 tools opt in explicitly via CHAPTERS_S2 / CHAPTERS_ALL.
CHAPTERS={k:v for k,v in CHAPTERS_ALL.items() if season_of(k)==1}
CHAPTERS_S2={k:v for k,v in CHAPTERS_ALL.items() if season_of(k)==2}

# candidate pool: NO story-exclusive cards (a player clearing chapters in order cannot
# field later rewards; recommendations must be crate/shop-obtainable only)
STORY_EXCL={506,510,531,541,545,561,565,570,594,601,615,616,617,635,645,646,647}
import json as _json
_bp=os.path.join(HERE,"broad_pool.json")   # 111-card broad pool (chap_ga.POOL); replaces the old 35-card list
POOL=list(_json.load(open(_bp))) if os.path.exists(_bp) else [325,275,273,324,372,484,190,191,412,413,334,319,305,170,175,253,217,240,238,239,182,118,117,195,475,24,335,56,423,199,297,299,221,252,213]
POOL=[c for c in POOL if c not in STORY_EXCL]
SUPPS={"pumpHigh":[660,420,632,634],"pumpLow":[653,417,632,634],"heal":[633,644,628,637],
 "mix":[660,420,633,644],"one_tv":[660],"none":[]}

def edeck(ch):
    pairs=CHAPTERS[ch]
    d=[sim.enemy_card(c,l) for c,l in pairs]
    d+=cpu_supporter_cards(ch,[c for c,_ in pairs],"hard")
    return d

def eval_batch(job):
    ch,teams,n=job
    ed=edeck(ch)
    out=[]
    for team,sk in teams:
        supp=SUPPS[sk]
        w=sum(1 for s2 in range(n) if sim.Sim(s2*13+5).run(sim.player_deck(list(team),supp),ed)==0)
        out.append((w/n,team,sk))
    return ch,out

if __name__=="__main__":
    t0=time.time()
    combos=list(itertools.combinations(POOL,3))
    print(f"pool {len(POOL)} -> {len(combos)} teams x {len(SUPPS)} supporter sets, {len(CHAPTERS)} chapters")
    result={}
    with Pool(8) as pool:
        for ch in sorted(CHAPTERS, key=lambda c:int(c[1:])):
            # coarse: all teams x all supps at n=8, chunked across workers
            jobs=[]
            work=[(t,sk) for t in combos for sk in SUPPS]
            CH=2000
            jobs=[(ch,work[i:i+CH],8) for i in range(0,len(work),CH)]
            scored=[]
            for _,out in pool.imap_unordered(eval_batch,jobs):
                scored.extend(out)
            scored.sort(reverse=True)
            # validate top 12 distinct teams at n=300
            seen=set(); vjobs=[]
            for v,team,sk in scored:
                if team in seen: continue
                seen.add(team); vjobs.append((team,sk))
                if len(vjobs)>=12: break
            _,vout=eval_batch((ch,vjobs,300))
            vout.sort(reverse=True)
            v,team,sk=vout[0]
            result[ch]={"team":list(team),"supp":SUPPS[sk],"supp_key":sk,"winrate":round(v,3),
                        "names":[sim.LEADERS[c]["name"] for c in team]}
            print(f"{ch}: {v*100:5.1f}%  {[sim.LEADERS[c]['name'][:24] for c in team]} +{sk}  [{time.time()-t0:.0f}s]")
    json.dump(result,open(os.path.join(HERE,"recommended_story.json"),"w"),indent=1)
    print(f"done {time.time()-t0:.0f}s -> recommended_story.json")
