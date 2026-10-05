"""Card data + level formulas + deck building, shared by the pipeline and the builds verifier.
The battle ENGINE lives only in lab_engine.js (run through fastsim.py / Node); the old Python engine is
archived in sim_engine_legacy.py and must not be used (it is no longer kept in sync with game patches)."""
import json, random, os, math
D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"cards.json")))
LEADERS = {int(k):v for k,v in D["leaders"].items()}
BOSSES  = {int(k):v for k,v in D["bosses"].items()}
MAXHP=999; MAXATK=199; MINATK=1; DEFCAP=50; OVERHEAL=1.2
def _rnd(x):   # GDScript round(): half away from zero
    return int(math.floor(x+0.5)) if x>=0 else -int(math.floor(-x+0.5))

_LEVEL_GAINS={3:("spd",10),4:("def",5),5:("hp",10),6:("atk",3),7:("spd",15),8:("def",6),9:("hp",15),10:("atk",5),
    11:("spd",20),12:("def",7),13:("hp",20),14:("atk",7),15:("spd",25),16:("def",8),17:("hp",25),18:("atk",8),19:("spd",30),20:("hp",27)}
SEASON_LEVEL_CAP={1:15,2:20}   # story_hub.SEASON_LEVEL_CAPS (player side)
def apply_player_level(card, lvl=10):
    """skin_manager.stats_at_level. Season 2 raised MAX_SKIN_LEVEL to 20; story caps the level per
    season (S1=15, S2=20) via get_cumulative_stats_capped. ability2 unlocks at level 2."""
    lvl=max(1,min(20,int(lvl)))
    c=dict(card); bonus={"hp":0,"atk":0,"spd":0,"def":0}
    for lv in range(2,lvl+1):
        g=_LEVEL_GAINS.get(lv)
        if g: bonus[g[0]]+=g[1]
    c["hp"]=min(MAXHP,card["hp"]+bonus["hp"]); c["atk"]=min(MAXATK,card["atk"]+bonus["atk"])
    c["spd"]=card["spd"]+bonus["spd"]; c["def"]=min(50,card["def"]+bonus["def"])
    c["level"]=lvl
    if lvl < 2: c["abilities"]=list(card.get("abilities",[]))[:1]
    return c

def _enemy_level_bonus(lvl, season=1):   # story_hub._enemy_level_bonus
    if season>=2 and lvl>=8:   # S2_BASE_LEVEL=8, S2_BASE {50,70,10,15} + n*S2_STEP {17,15,1,4}
        n=lvl-8; return 50+17*n, 70+15*n, 10+n, 15+4*n
    k=lvl-1; return 18*k, 8*k, 2*k, 4*k

def apply_enemy_level(card, lvl, season=1):
    # The REAL battle deck (story_hub._build_cpu_deck) always scales +18hp/+8spd/+2def/+4atk per level, in every
    # season. The S2 curve in _enemy_level_bonus only feeds the opponent PREVIEW panel (_get_opp_def_at_level),
    # so the preview and the fight disagree in Season 2. Verified vs an in-battle screenshot (S2E6 Jacks 410/429/487 hp).
    c=dict(card)
    if lvl>1:
        h,sp,d,a=_enemy_level_bonus(lvl,1)
        c["hp"]=min(MAXHP,card["hp"]+h); c["spd"]=card["spd"]+sp
        c["def"]=min(50,card["def"]+d); c["atk"]=min(MAXATK,card["atk"]+a)
    c["level"]=lvl
    return c

def enemy_card(cid, lvl, season=1):
    base = BOSSES[cid] if cid in BOSSES else LEADERS[cid]
    c = apply_enemy_level(base, lvl, season)
    if "element" not in c: c["element"]=LEADERS.get(cid,{}).get("element",-1)
    return c

def name_words(nm):
    o=[];c=""
    for ch in nm.lower():
        if ch.isalnum(): c+=ch
        else:
            if c: o.append(c); c=""
    if c: o.append(c)
    return o
def name_has_tag(nm,tag):
    if not tag: return False
    nw=name_words(nm); kw=tag.lower().split()
    k=len(kw)
    for i in range(len(nw)-k+1):
        if all(nw[i+j]==kw[j] or (j==k-1 and nw[i+j]==kw[j]+"s") for j in range(k)): return True
    return False

def def_has_tag(d,tag):   # LeaderDef.has_tag: name keyword OR an ability's extra_tags (case-insensitive)
    if name_has_tag(d.get("name",""),tag): return True
    low=(tag or "").lower()
    if not low: return False
    for a in d.get("abilities") or []:
        for t in (a.get("params") or {}).get("extra_tags") or []:
            if str(t).lower()==low: return True
    return False

def player_deck(ids, supporters=()):
    d=[apply_player_level(LEADERS[i]) for i in ids]
    for i in supporters: d.append(dict(LEADERS[i]))  # supporters: only .supporter ability matters
    return d
# story-exclusive/spoiler subjects excluded from the CPU supporter pool (skin_manager)
def _story_exclusive():
    """story-exclusive skins = '"Story" in crate_sources' (skin_manager.is_story_exclusive). Derived
    from the decompiled skin list so a patch that adds story rewards updates the CPU-supporter pool
    automatically (Season 2 grew it 17 -> 82; a stale hardcoded set shifts every seeded supporter)."""
    import re as _re
    p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"decompiled","skin_manager.gd")
    if not os.path.exists(p): return {506,510,531,541,545,561,565,570,594,601,615,616,617,635,645,646,647}
    sm=open(p,encoding="utf-8").read()
    i=sm.index("var skins =[")+len("var skins ="); d=0; j=i
    while j<len(sm):
        if sm[j]=="[": d+=1
        elif sm[j]=="]":
            d-=1
            if d==0: break
        j+=1
    out=set()
    for s,cs in _re.findall(r'"image":\s*"res://[Ss]ubject ?(\d+)\.png".*?"crate_sources":\s*(\[[^\]]*\])',sm[i:j+1],_re.S):
        if "Story" in _re.findall(r'"([^"]+)"',cs): out.add(int(s))
    return out
STORY_EXCL=_story_exclusive()
ENEMY_SUPP_POOL=[i for i in LEADERS if i not in STORY_EXCL]
def enemy_deck(pairs): return [enemy_card(cid,lv) for cid,lv in pairs]
