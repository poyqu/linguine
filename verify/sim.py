import json, random, os, math
D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"cards.json")))
LEADERS = {int(k):v for k,v in D["leaders"].items()}
BOSSES  = {int(k):v for k,v in D["bosses"].items()}

# ---------- element chart ----------
RULES=[
 {"eff":[[1,1.4]],"neff":[[3,0.4]],"res":[[4,0.9]],"weak":[[2,1.1]]},
 {"eff":[[2,1.4]],"neff":[[4,0.6]],"res":[[3,0.95]],"weak":[[5,1.05]]},
 {"eff":[[3,1.8]],"neff":[[5,0.1]],"res":[[0,0.75]],"weak":[[4,1.25]]},
 {"eff":[[4,1.8]],"neff":[[0,0.2]],"res":[[1,0.85]],"weak":[[5,1.15]]},
 {"eff":[[5,1.2],[1,1.4]],"neff":[],"res":[[0,0.95]],"weak":[[2,1.05]]},
 {"eff":[[0,1.2]],"neff":[[2,0.8]],"res":[[3,0.8]],"weak":[[1,1.2]]},
]
CHART=[[1.0]*6 for _ in range(6)]
for e in range(6):
    for t,m in RULES[e]["eff"]: CHART[e][t]=m
    for t,m in RULES[e]["neff"]: CHART[e][t]=m
    for t,m in RULES[e]["res"]: CHART[t][e]=m
    for t,m in RULES[e]["weak"]: CHART[t][e]=m
def cat_weakness(atk,dfn):  # is defender weak to attacker?
    for t,m in RULES[dfn]["weak"]:
        if t==atk: return True
    return False
def elem_mult(atk,dfn,dfn_apex):
    if atk<0 or dfn<0: return 1.0
    if dfn_apex and cat_weakness(atk,dfn): return 1.0
    return CHART[atk][dfn]

# ---------- statuses ----------
# Built from the game's own StatusDef table (extract_cards.py -> cards.json["statuses"]):
# id -> (duration, [per-turn deltas], flags). Game flag names are aliased to the engine's names.
_FLAG_ALIAS={"blocks_other_statuses":"blocks_other","damage_self_fraction_of_dealt":"recoil","targets_all_leaders":"targets_all"}
def _build_sta(src):
    out={}
    for sid,v in src.items():
        fl={_FLAG_ALIAS.get(k,k):val for k,val in (v.get("flags") or {}).items()}
        if sid=="dizzy": fl["dizzy"]=True
        out[sid]=(int(v["duration"]),list(v.get("deltas") or []),fl)
    return out
_STA_FALLBACK={
 "on_fire":(5,[{"health":-10}]*5,{}),
 "poisoned":(5,[{"health":-5},{"health":-15},{"health":-25},{"health":-15},{"health":-5}],{}),
 "bleeding":(7,[{"health":-5,"defense":-2}]*7,{}),
 "doomed":(5,[{},{},{},{},{"health":-200}],{}),
 "blessed":(3,[{"health":5},{"health":15},{"health":20}],{}),
 "ice_burn":(3,[{"health":-10,"speed":-30},{"health":-10,"speed":-45},{"health":-5,"speed":-100}],{}),
 "stunned":(1,[{}],{"blocks_attack":True}),
 "paralyzed":(1,[{"health":-7}],{"blocks_attack":True}),
 "weak":(1,[{}],{"blocks_block":True}),
 "slow":(1,[{}],{"override_speed":1}),
 "frozen":(2,[{},{}],{"override_speed":50}),
 "strengthened":(1,[{}],{"force_defense":50}),
 "lucky":(1,[{}],{"doubles_crit":True}),
 "purified":(2,[{},{}],{"blocks_other":True}),
 "dizzy":(1,[{}],{"dizzy":True}),
 "tired":(1,[{}],{"blocks_attack":True}),
 "cursed":(2,[{},{}],{"recoil":1.0/3.0}),
 "stinky":(2,[{"defense":-5,"speed":-20},{"defense":-5,"speed":-20,"attack":5}],{}),
 "burnout":(3,[{"speed":-50},{"speed":-100},{"speed":-300}],{}),
 "chaos":(4,[],{"targets_all":True}),
}
STA=_build_sta(D["statuses"]) if D.get("statuses") else _STA_FALLBACK
TURN_ONLY=("tired","stunned","paralyzed")      # RuntimeLeader.TURN_ONLY_STATUSES: cleared at every turn end
BUFF_STATUSES=("blessed","lucky","strengthened","purified","soul_protected","tired")   # battle_sim._BUFF_STATUSES
STYLE_FLIP={2:3,3:2,4:5,5:4,6:7,7:6,8:9,9:8}
STYLE_ALL=10                                    # BattleEnums.AttackStyle.ALL: hits every leader in the target pool
MAXHP=999; MAXATK=199; MINATK=1; DEFCAP=50; OVERHEAL=1.2
def _rnd(x):   # GDScript round(): half away from zero
    return int(math.floor(x+0.5)) if x>=0 else -int(math.floor(-x+0.5))

class L:
    __slots__=("d","side","slot","hp","mhp","atk","dfn","spd","elem","apex","abil","name","st","og","ot_turn","dmg_turn","alive","lvl","announced","eot",
               "wa_this","wa_last","turn_now","style_override","hits_turn","echo_guard")
    def __init__(s,d,side,slot):
        s.d=d; s.side=side; s.slot=slot
        s.hp=d["hp"]; s.mhp=d["hp"]; s.atk=d["atk"]; s.dfn=d["def"]; s.spd=d["spd"]
        s.elem=d.get("element",-1); s.apex=d.get("apex",False)
        s.abil=d.get("abilities",[]); s.name=d["name"]; s.lvl=d.get("level",1)
        s.st={}   # status_id -> [remaining, tick_index]; insertion order == the game's statuses list order
        s.og=set(); s.ot_turn=set(); s.dmg_turn=0; s.alive=True; s.announced=False; s.eot=[]
        s.wa_this=False; s.wa_last=False; s.turn_now=0; s.style_override=0; s.hits_turn=0; s.echo_guard=False
    def eff_def(s):   # RuntimeLeader.effective_defense: the FIRST status with force_defense wins; capped at 50
        for sid in s.st:
            f=STA.get(sid,(0,[],{}))[2]
            if f.get("force_defense",-1)>=0: return min(f["force_defense"],DEFCAP)
        return min(s.dfn,DEFCAP)
    def eff_spd(s):   # effective_speed: the FIRST status with override_speed wins
        for sid in s.st:
            f=STA.get(sid,(0,[],{}))[2]
            if f.get("override_speed",-1)>=0: return f["override_speed"]
        return s.spd
    def flag(s,name):
        for sid in s.st:
            if STA.get(sid,(0,[],{}))[2].get(name): return True
        return False
    def immune(s,sid):   # RuntimeLeader.is_immune_to (also_immune on any ability; passive_immunity may be turn-gated)
        for a in s.abil:
            p=a.get("params") or {}
            for x in p.get("also_immune") or []:
                if x=="all" or x==sid: return True
            if a.get("trigger")=="passive_immunity":
                turns=p.get("turns") or []
                if turns and s.turn_now not in turns: continue
                x=p.get("status_id","")
                if x=="all" or x==sid: return True
                for y in p.get("status_ids") or []:
                    if y=="all" or y==sid: return True
        return False
    def has_passive(s,trig):
        return any(a.get("trigger")==trig for a in s.abil)
    def has_tag(s,tag): return def_has_tag(s.d,tag)
    def has_hp_floor(s):
        return any(STA.get(sid,(0,[],{}))[2].get("hp_floor_1") for sid in s.st)
    def take_damage(s,amount):   # RuntimeLeader.take_damage: hp floor (soul_bound), marks dead immediately
        if amount<=0: return 0
        taken=min(s.hp,amount)
        if s.has_hp_floor() and taken>=s.hp: taken=max(0,s.hp-1)
        s.hp-=taken; s.dmg_turn+=taken
        if s.hp<=0: s.hp=0; s.alive=False
        return taken

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

UNIMPL=set()
class Sim:
    def __init__(s, seed):
        s.rng=random.Random(seed); s.shuf=[random.Random(seed^0x9E3779B9),random.Random(seed^0x85EBCA6B)]; s.turn=0; s.teams=[[],[]]; s.depth=0; s.pending=[]
        s.chain=0                      # _chain_depth (max 5) for nested trigger fires
        s.drawn=[0,0]; s.drawn_last=[0,0]   # supporters drawn this/last turn per side
        s._stat_gain_by_supporter=False     # true only while a supporter card's own ability runs
    def enemy_side(s,side): return 1-side
    def alive(s,side): return [l for l in s.teams[side] if l.alive]
    def all_leaders(s): return [l for l in s.teams[0]+s.teams[1] if l.alive]
    # ---- status ----
    def _dur_mult(s,tgt,sid):   # RuntimeLeader._status_duration_mult
        for a in tgt.abil:
            if a.get("trigger")=="passive_status_duration":
                if sid in ((a.get("params") or {}).get("status_ids") or []): return int(a["params"].get("mult",2))
        return 1
    def apply_status(s, tgt, sid):   # RuntimeLeader.apply_status (raw: no blocks/unique/replacement/triggers)
        if tgt is None or sid not in STA: return False
        if sid!="purified" and tgt.immune(sid): return False
        for x in tgt.st:
            if STA[x][2].get("blocks_other") and sid!=x: return False
        if sid in tgt.st:            # re-application (even of an expired-but-not-yet-swept status): refresh, NO trigger
            tgt.st[sid]=[STA[sid][0]*s._dur_mult(tgt,sid),0]; return False
        tgt.st[sid]=[STA[sid][0]*s._dur_mult(tgt,sid),0]
        return True
    def _replace(s, tgt, sid):   # _enforce_replacements: drop statuses this one overrides
        reps=STA[sid][2].get("replaces_status_ids") or []
        for x in [k for k in tgt.st if k!=sid and k in reps]: del tgt.st[x]
    def inflict(s, tgt, sid, src=None, notify=True):   # battle_sim._apply_status_notify
        if tgt is None or sid not in STA: return False
        if not notify: return s.apply_status(tgt,sid)   # game paths that call RuntimeLeader.apply_status directly
        for x in tgt.st:                                 # _status_blocked (blocks_status_ids, e.g. soul_protected)
            if sid in (STA[x][2].get("blocks_status_ids") or []): return False
        if STA[sid][2].get("unique_per_team"):           # _enforce_unique_per_team runs BEFORE apply, even if it fails
            for o in s.alive(tgt.side):
                if o is not tgt and sid in o.st: del o.st[sid]
        if not s.apply_status(tgt,sid):
            if sid in tgt.st: s._replace(tgt,sid)
            return False
        s._replace(tgt,sid)
        if sid in TURN_ONLY:                             # turn-only statuses tick once immediately on inflict
            rem,idx=tgt.st[sid]; dl=STA[sid][1]
            dd=dl[idx] if idx<len(dl) else {}
            tgt.st[sid][1]+=1; tgt.st[sid][0]-=1
            if dd: s.apply_stat_deltas(tgt,dd)            # no death check here (game: silent death possible)
        if s.depth<24:
            s.depth+=1; s.fire(tgt,"on_status_applied",{"affected":tgt,"status_id":sid}); s.depth-=1
        s.broadcast("on_any_status_applied",{"affected":tgt,"status_id":sid})
        return True
    def cleanse(s, tgt, sid):
        if tgt and sid in tgt.st: del tgt.st[sid]
    # ---- death ----
    def die(s, victim, killer=None, is_attack=False):   # battle_sim._kill + _handle_death_ripple
        victim.alive=False; victim.hp=0
        if victim.announced: return
        victim.announced=True
        s.fire(victim,"on_death",{"killer":killer},force=True)
        if is_attack and killer is not None:
            s.fire(killer,"on_kill",{"victim":victim})
            s.broadcast("on_any_kill",{"killer":killer,"victim":victim})
        s.broadcast("on_any_death",{"fallen":victim})
        living=s.alive(victim.side)
        for al in living: s.fire(al,"on_ally_killed",{"fallen":victim})
        if len(living)==1: s.fire(living[0],"on_last_standing",{"fallen":victim})
    def check_death(s, l, killer=None, is_attack=False):   # battle_sim._check_death
        if l is not None and (not l.alive or l.hp<=0) and not l.announced: s.die(l,killer,is_attack)
    def checkdeath(s, killer=None, is_attack=False):       # sweep, for effects that can kill several leaders
        for l in s.teams[0]+s.teams[1]:
            if (not l.alive or l.hp<=0) and not l.announced: s.die(l,killer,is_attack)
    # ---- ticks / stat changes ----
    def apply_stat_deltas(s, l, d):   # battle_sim._apply_stat_deltas (heal caps at max_hp; attack floor 0; no death check)
        if not d: return
        if "health" in d:
            a=int(d["health"])
            if a<0: l.take_damage(-a)
            else: l.hp=min(l.hp+a,l.mhp)
        if "attack" in d: l.atk=max(0,min(MAXATK,l.atk+int(d["attack"])))
        if "defense" in d: l.dfn=max(0,min(DEFCAP,l.dfn+int(d["defense"])))
        if "speed" in d: l.spd=max(0,l.spd+int(d["speed"]))
    def tick_statuses(s, l):   # RuntimeLeader.tick_statuses: sum this tick's deltas and advance. NO removal.
        tot={}
        for sid in list(l.st.keys()):
            rem,idx=l.st[sid]; dl=STA[sid][1]
            for k,v in (dl[idx] if idx<len(dl) else {}).items(): tot[k]=tot.get(k,0)+int(v)
            l.st[sid][1]+=1; l.st[sid][0]-=1
        return tot
    def sweep_expired(s, l):   # end of turn: clear_turn_markers + sweep_expired_statuses
        for sid in [k for k,v in l.st.items() if k in TURN_ONLY or v[0]<=0]: del l.st[sid]
    def mod(s,l,stat,amt):   # battle_sim._modify_stat
        if stat=="health":
            if amt<0: l.take_damage(-amt)
            else: l.hp=min(l.hp+amt,int(math.floor(l.mhp*OVERHEAL)))   # overheal up to 120% max hp
        elif stat=="attack":
            l.atk=max(MINATK,min(MAXATK,l.atk+amt))
            if amt>0 and s.depth<24:
                s.depth+=1; s.fire(l,"on_boost",{}); s.depth-=1
        elif stat=="defense": l.dfn=max(0,min(DEFCAP,l.dfn+amt))
        elif stat=="speed": l.spd=max(0,l.spd+amt)
        if amt>0:
            if s.depth<24:
                s.depth+=1; s.fire(l,"on_stat_gain",{"stat":stat,"amount":amt}); s.depth-=1
            s.broadcast("on_any_stat_gain",{"gainer":l,"stat":stat,"amount":amt,"by_supporter":s._stat_gain_by_supporter})
        s.check_death(l)
    # ---- targeting for effects ----
    def sel(s, self_l, key, ctx):
        if key in ctx and hasattr(ctx[key],"alive"): return ctx[key]
        if key=="self": return self_l
        allies=s.alive(self_l.side); enemies=s.alive(s.enemy_side(self_l.side))
        d={"random_ally":allies,"random_enemy":enemies,"random_any":allies+enemies,"random_leader":allies+enemies}
        if key in d:
            pool=d[key]; return s.rng.choice(pool) if pool else None
        SUP={"fastest":("spd",True),"slowest":("spd",False),"highest_hp":("hp",True),"lowest_hp":("hp",False),
             "highest_def":("dfn",True),"lowest_def":("dfn",False),"highest_atk":("atk",True),"lowest_atk":("atk",False)}
        for stem,(attr,hi) in SUP.items():
            for suf,pool in (("_ally",allies),("_enemy",enemies),("_overall",allies+enemies)):
                if key==stem+suf:
                    keyf=lambda l:(l.eff_spd() if attr=="spd" else l.eff_def() if attr=="dfn" else getattr(l,attr))
                    return s._ext(pool,keyf,hi)
        return None
    # ---- conditions ----
    def cond(s, self_l, cname, cp, ctx):
        if not cname: return True
        if cname=="self_hp_at_or_below": return self_l.hp<=cp.get("value",0)
        if cname=="self_hp_above": return self_l.hp>cp.get("value",0)
        if cname=="self_stat_at_least":   # game reads RAW defense/speed here, NOT effective (battle_sim.gd:994-996)
            v={"health":self_l.hp,"attack":self_l.atk,"defense":self_l.dfn,"speed":self_l.spd}[cp["stat"]]; return v>=int(cp.get("value",0))
        if cname=="self_stat_at_most":
            v={"health":self_l.hp,"attack":self_l.atk,"defense":self_l.dfn,"speed":self_l.spd}[cp["stat"]]; return v<=int(cp.get("value",0))
        if cname=="turn_equals": return s.turn==int(cp.get("value",1))
        if cname=="turn_in_set": return s.turn in cp.get("values",[])
        if cname=="self_has_status": return cp.get("status_id") in self_l.st
        if cname=="self_no_statuses": return len(self_l.st)==0
        if cname=="target_has_status":   # game default target "victim" via _select_target (battle_sim.gd:982-986)
            t=s.sel(self_l,cp.get("target","victim"),ctx); return t is not None and cp.get("status_id") in t.st
        if cname in("ally_has_tag","any_leader_has_tag"):
            tag=cp.get("tag","")
            # ally_has_tag EXCLUDES self (game: `if ally != self_l`); any_leader_has_tag includes all
            pool=[l for l in s.alive(self_l.side) if l is not self_l] if cname=="ally_has_tag" else s.all_leaders()
            return any(l.has_tag(tag) for l in pool)
        if cname=="ally_has_any_tag":   # also excludes self (game: `if a != self_l`)
            return any(any(l.has_tag(t) for t in cp.get("tags",[])) for l in s.alive(self_l.side) if l is not self_l)
        if cname=="enemies_count_at_least": return len(s.alive(s.enemy_side(self_l.side)))>=int(cp.get("value",1))
        if cname=="allies_count_at_least": return len(s.alive(self_l.side))>=int(cp.get("value",1))
        if cname=="self_is_fastest":
            return self_l.eff_spd()>=max(l.eff_spd() for l in s.all_leaders())
        if cname=="self_is_slowest":
            return self_l.eff_spd()<=min(l.eff_spd() for l in s.all_leaders())
        if cname=="target_hp_above_self":
            t=ctx.get("target"); return t is not None and t.hp>self_l.hp
        if cname=="allies_with_hp_above_at_least":
            n=sum(1 for l in s.alive(self_l.side) if l.hp>cp.get("value",0)); return n>=int(cp.get("count",1))
        if cname=="self_damage_this_turn_above": return self_l.dmg_turn>cp.get("value",0)
        if cname=="ctx_status_equals": return ctx.get("status_id")==cp.get("status_id")
        if cname=="ctx_status_in": return ctx.get("status_id") in cp.get("status_ids",[])
        if cname=="ctx_is_enemy":   # game default key "attacker" (battle_sim.gd:1311)
            t=ctx.get(cp.get("key","attacker")); return t is not None and hasattr(t,"alive") and t.side!=self_l.side
        if cname=="ctx_flag": return bool(ctx.get(cp.get("key","")))
        if cname in("drawn_card_has_tag","ctx_card_has_any_tag"):
            card=ctx.get("card");
            if card is None: return False
            tags=cp.get("tags",[]) or [cp.get("tag","")]
            return any(def_has_tag(card,t) for t in tags)
        if cname=="all_of": return all(s.cond(self_l,c["condition"],c.get("params",{}),ctx) for c in cp.get("conds",[]))
        if cname=="any_of": return any(s.cond(self_l,c["condition"],c.get("params",{}),ctx) for c in cp.get("conds",[]))
        if cname=="not_cond": return not s.cond(self_l,cp.get("condition",""),cp.get("params",{}),ctx)
        if cname=="target_hp_above":
            t=ctx.get("target"); return t is not None and t.hp>cp.get("value",0)
        if cname=="target_level_at_least":
            t=ctx.get("target"); return t is not None and t.lvl>=cp.get("value",0)
        if cname=="target_level_at_most":
            t=ctx.get("target"); return t is not None and t.lvl<=cp.get("value",999)
        if cname=="target_has_any_tag":
            t=ctx.get("target"); return t is not None and any(t.has_tag(tg) for tg in cp.get("tags",[]))
        if cname=="allies_count_at_most": return len(s.alive(self_l.side))<=cp.get("value",1)
        if cname=="enemy_has_status":
            return any(cp.get("status_id") in f.st for f in s.alive(s.enemy_side(self_l.side)))
        if cname=="leaders_with_tag_at_least":
            return sum(1 for l in s.all_leaders() if l.has_tag(cp.get("tag","")))>=cp.get("value",1)
        if cname=="fallen_has_tag":
            f=ctx.get("fallen"); return f is not None and f.has_tag(cp.get("tag",""))
        if cname=="fallen_has_any_tag":
            f=ctx.get("fallen"); return f is not None and any(f.has_tag(tg) for tg in cp.get("tags",[]))
        if cname=="damage_at_least": return ctx.get("damage",0)>=cp.get("value",0)
        if cname=="random_chance": return s.rng.random()<cp.get("chance",0.5)
        if cname=="target_no_statuses":
            t=ctx.get("target"); return t is not None and len(t.st)==0
        if cname=="target_has_any_status":
            t=ctx.get("target"); return t is not None and len(t.st)>0
        if cname=="target_status_count_at_least":
            t=ctx.get("target"); return t is not None and len(t.st)>=cp.get("value",1)
        if cname=="self_status_count_at_least": return len(self_l.st)>=cp.get("value",1)
        if cname=="incoming_damage_at_least": return ctx.get("damage",0)>=cp.get("value",0)
        if cname=="enemies_count_at_most": return len(s.alive(s.enemy_side(self_l.side)))<=cp.get("value",0)
        # ---- full registry parity (audited vs battle_sim.gd) ----
        def _stat_of(l,st_):
            return {"attack":l.atk,"defense":l.eff_def(),"speed":l.eff_spd(),"health":l.hp}.get(st_,0)
        def _ctxl(key):
            v=ctx.get(key); return v if hasattr(v,"alive") else None
        if cname=="self_hp_below": return self_l.hp<cp.get("value",0)
        if cname=="self_hp_fraction_below": return self_l.hp/max(self_l.mhp,1)<cp.get("value",0.5)
        if cname=="self_stat_above": return _stat_of(self_l,cp.get("stat",""))>cp.get("value",0)
        if cname=="self_stat_below": return _stat_of(self_l,cp.get("stat",""))<cp.get("value",0)
        if cname=="self_defense_at_least": return self_l.eff_def()>=cp.get("value",0)
        if cname=="self_has_any_status": return len(self_l.st)>0
        if cname=="self_has_all_statuses": return all(sd in self_l.st for sd in cp.get("statuses",[]))
        if cname=="self_is_fastest_ally":
            return all(a is self_l or a.eff_spd()<=self_l.eff_spd() for a in s.alive(self_l.side))
        if cname=="self_is_slowest_ally":
            return all(a is self_l or a.eff_spd()>=self_l.eff_spd() for a in s.alive(self_l.side))
        if cname=="self_not_fastest":
            return any(l is not self_l and l.eff_spd()>self_l.eff_spd() for l in s.all_leaders())
        if cname=="self_is_least_attack_alive":
            return all(a is self_l or a.atk>=self_l.atk for a in s.alive(self_l.side))
        if cname=="self_is_most_attack_alive":
            return all(a is self_l or a.atk<=self_l.atk for a in s.alive(self_l.side))
        if cname=="ally_has_status":
            return any(a is not self_l and cp.get("status_id") in a.st for a in s.alive(self_l.side))
        if cname=="ally_hp_above":
            return any(a is not self_l and a.hp>cp.get("value",0) for a in s.alive(self_l.side))
        if cname=="ally_attack_at_least":
            return any(a is not self_l and a.atk>=cp.get("value",0) for a in s.alive(self_l.side))
        if cname=="ally_defense_at_least":
            return any(a is not self_l and a.eff_def()>=cp.get("value",0) for a in s.alive(self_l.side))
        if cname=="ally_status_count_above":
            return any(a is not self_l and len(a.st)>cp.get("value",0) for a in s.alive(self_l.side))
        if cname=="allies_all_have_status":
            allies=s.alive(self_l.side)
            if len(allies)<cp.get("min_count",1): return False
            return all(cp.get("status_id") in a.st for a in allies)
        if cname=="any_leader_has_status":
            side=cp.get("side","all")
            pool=s.alive(self_l.side) if side=="ally" else s.alive(s.enemy_side(self_l.side)) if side=="enemy" else s.all_leaders()
            return any(cp.get("status_id") in l.st for l in pool)
        if cname=="enemy_has_any_status":
            return any(len(f.st)>0 for f in s.alive(s.enemy_side(self_l.side)))
        if cname=="enemy_has_all_statuses":
            sids=cp.get("statuses",[])
            return any(all(sd in f.st for sd in sids) for f in s.alive(s.enemy_side(self_l.side)))
        if cname=="enemies_with_status_count_at_least":
            n=sum(1 for f in s.alive(s.enemy_side(self_l.side)) if cp.get("status_id") in f.st)
            return n>=cp.get("value",1)
        if cname=="enemy_min_def_above_ally_max_def":
            allies=s.alive(self_l.side); enemies=s.alive(s.enemy_side(self_l.side))
            if not allies or not enemies: return False
            return min(e.eff_def() for e in enemies)>max(a.eff_def() for a in allies)
        if cname=="leader_with_tag_and_status":
            side=cp.get("side","all")
            pool=s.alive(self_l.side) if side=="ally" else s.alive(s.enemy_side(self_l.side)) if side=="enemy" else s.all_leaders()
            return any(l.has_tag(cp.get("tag","")) and cp.get("status_id") in l.st for l in pool)
        if cname=="side_has_any_tag":
            return any(any(a.has_tag(t) for t in cp.get("tags",[])) for a in s.alive(self_l.side))
        if cname=="total_leaders_equals": return len(s.all_leaders())==cp.get("value",0)
        if cname=="turn_at_or_after": return s.turn>=cp.get("value",1)
        if cname=="turn_in_range": return cp.get("min",1)<=s.turn<=cp.get("max",99)
        if cname=="turn_every":
            frm=cp.get("from",1); n=max(1,cp.get("n",1))
            return s.turn>=frm and (s.turn-frm)%n==0
        if cname=="target_hp_below":
            t=ctx.get("target"); return t is not None and t.hp<cp.get("value",0)
        if cname=="target_hp_fraction_below":
            t=ctx.get("target"); return t is not None and t.hp/max(t.mhp,1)<cp.get("value",0.5)
        if cname=="target_defense_below_self":
            t=ctx.get("target"); return t is not None and t.eff_def()<self_l.eff_def()
        if cname=="target_attack_below_self":
            t=ctx.get("target"); return t is not None and t.atk<self_l.atk
        if cname=="target_slower_than_self":
            t=ctx.get("target"); return t is not None and t.eff_spd()<self_l.eff_spd()
        if cname=="target_has_tag":
            t=ctx.get("target"); return t is not None and t.has_tag(cp.get("tag",""))
        if cname=="target_has_status_any":
            t=ctx.get("target"); return t is not None and any(sd in t.st for sd in cp.get("status_ids",[]))
        if cname=="attacker_has_tag":
            a=ctx.get("attacker"); return a is not None and a.has_tag(cp.get("tag",""))
        if cname=="attacker_hp_at_least":
            a=ctx.get("attacker"); return a is not None and a.hp>=cp.get("value",0)
        if cname=="attacker_hp_at_most":
            a=ctx.get("attacker"); return a is not None and a.hp<=cp.get("value",0)
        if cname=="attacker_speed_at_least":
            a=ctx.get("attacker"); return a is not None and a.eff_spd()>=cp.get("value",0)
        if cname=="attacker_speed_at_most":
            a=ctx.get("attacker"); return a is not None and a.eff_spd()<=cp.get("value",0)
        if cname=="fallen_has_status":
            f=ctx.get("fallen"); return f is not None and cp.get("status_id") in f.st
        if cname=="ctx_is_self": return _ctxl(cp.get("key","affected")) is self_l
        if cname=="ctx_not_self":
            l=_ctxl(cp.get("key","affected")); return l is not None and l is not self_l
        if cname=="ctx_is_ally":
            l=_ctxl(cp.get("key","attacker")); return l is not None and l.side==self_l.side
        if cname=="ctx_has_status":
            l=_ctxl(cp.get("key","affected")); return l is not None and cp.get("status_id") in l.st
        if cname=="ctx_has_tag":
            l=_ctxl(cp.get("key","attacker")); return l is not None and l.has_tag(cp.get("tag",""))
        if cname=="ctx_has_any_tag":
            l=_ctxl(cp.get("key","attacker")); return l is not None and any(l.has_tag(t) for t in cp.get("tags",[]))
        if cname=="ctx_stat_equals": return str(ctx.get("stat",""))==str(cp.get("stat",""))
        if cname=="ctx_amount_at_least": return ctx.get("amount",0)>=cp.get("value",0)
        if cname=="ctx_amount_equals": return ctx.get("amount",0)==cp.get("value",0)
        if cname=="ctx_card_has_tag":
            card=ctx.get("card"); return card is not None and def_has_tag(card,cp.get("tag",""))
        if cname=="no_supporters_drawn": return s.drawn[self_l.side]==0
        if cname=="opp_no_supporters_drawn": return s.drawn[s.enemy_side(self_l.side)]==0
        if cname=="this_turn_self_drew_at_least": return s.drawn[self_l.side]>=cp.get("value",1)
        if cname=="this_turn_opp_drew_at_least": return s.drawn[s.enemy_side(self_l.side)]>=cp.get("value",1)
        if cname=="last_turn_self_drew_at_least": return s.drawn_last[self_l.side]>=cp.get("value",1)
        if cname=="last_turn_self_drew_none": return s.drawn_last[self_l.side]==0
        if cname=="last_turn_opp_drew_at_least": return s.drawn_last[s.enemy_side(self_l.side)]>=cp.get("value",1)
        if cname=="last_turn_opp_drew_none": return s.drawn_last[s.enemy_side(self_l.side)]==0
        # ---- Season 2 conditions ----
        if cname=="ally_element_is":
            return any(a is not self_l and int(a.elem)==int(cp.get("element",-1)) for a in s.alive(self_l.side))
        if cname=="attacker_attack_above_self":
            a=ctx.get("attacker"); return a is not None and a.atk>self_l.atk
        if cname=="target_attack_above_self":
            t=ctx.get("target"); return t is not None and t.atk>self_l.atk
        if cname=="target_faster_than_self":
            t=ctx.get("target"); return t is not None and t.eff_spd()>self_l.eff_spd()
        if cname=="target_element_is":
            t=ctx.get("target"); return t is not None and int(t.elem)==int(cp.get("element",-1))
        if cname=="ctx_hp_below":
            l=ctx.get(str(cp.get("key","damaged"))); return hasattr(l,"alive") and l.hp<int(cp.get("value",0))
        if cname=="ctx_status_harmful":
            sid=str(ctx.get("status_id","") or ""); return sid!="" and sid not in BUFF_STATUSES
        if cname=="self_def_above_all_enemies":
            foes=s.alive(s.enemy_side(self_l.side))
            return bool(foes) and all(f.eff_def()<self_l.eff_def() for f in foes)
        if cname=="self_not_attacked_last_turn": return not self_l.wa_last
        if cname=="target_had_status":
            return str(cp.get("status_id","")) in (ctx.get("pre_statuses") or [])
        if cname=="target_had_any_status":
            pre=ctx.get("pre_statuses") or []; return any(str(x) in pre for x in (cp.get("status_ids") or []))
        if cname=="target_is_extreme":
            t=ctx.get("target")
            if t is None: return False
            stat=str(cp.get("stat","speed")); wmax=str(cp.get("want","max"))=="max"
            val=lambda l: l.eff_spd() if stat=="speed" else l.eff_def() if stat=="defense" else l.atk if stat=="attack" else l.hp
            tv=val(t)
            return not any((wmax and val(o)>tv) or ((not wmax) and val(o)<tv) for o in s.alive(t.side))
        UNIMPL.add("cond:"+cname); return False
    # ---- effects ----
    def run_effect(s, self_l, eff, p, ctx):
        if not eff: return
        # ---- Season 2 effects (battle_sim._register_extended3) ----
        if eff=="bonus_hit":
            if str(p.get("target","target"))=="random_other_enemy":
                main=ctx.get("target")
                pool=[f for f in s.alive(s.enemy_side(self_l.side)) if f is not main]
                if not pool: return
                tgt=s.rng.choice(pool)
            else: tgt=ctx.get("target")
            if tgt is None or not tgt.alive or not self_l.alive: return
            tgt.take_damage(_rnd(self_l.atk*float(p.get("mult",0.5)))); s.check_death(tgt,self_l); return
        if eff=="chance_branch":
            s.run_sub(self_l,p.get("then",{}) if s.rng.random()<float(p.get("chance",0.5)) else p.get("else",{}),ctx); return
        if eff=="random_choice":
            ch=p.get("choices") or []
            if ch: s.run_sub(self_l,s.rng.choice(ch),ctx)
            return
        if eff=="on_pick":
            pool=s._filtered(self_l,str(p.get("side","ally")),p.get("filter") or {})
            if p.get("exclude_self"): pool=[x for x in pool if x is not self_l]
            if not pool: return
            pick=s._ext(pool,lambda l:l.hp,False) if str(p.get("mode","random"))=="min_hp" else s.rng.choice(pool)
            c2=dict(ctx); c2["picked"]=pick
            for sub in p.get("effects") or []: s.run_sub(self_l,sub,c2)
            return
        if eff=="set_style":
            cur=self_l.style_override if self_l.style_override>0 else self_l.d.get("style",1)
            mode=str(p.get("mode",""))
            if mode=="random": self_l.style_override=s.rng.randint(1,9)
            elif mode=="copy_random_enemy":
                foes=s.alive(s.enemy_side(self_l.side))
                if foes:
                    f=s.rng.choice(foes); fs=f.style_override if f.style_override>0 else f.d.get("style",1)
                    if fs!=STYLE_ALL: self_l.style_override=fs
            elif mode=="flip": self_l.style_override=int(STYLE_FLIP.get(cur,cur))
            return
        if eff=="random_element":
            self_l.elem=s.rng.randint(0,5); return
        if eff=="swap_stats":
            if str(p.get("a",""))=="attack" and str(p.get("b",""))=="defense":
                a_,d_=self_l.atk,self_l.dfn
                self_l.atk=max(MINATK,min(MAXATK,d_)); self_l.dfn=max(0,min(DEFCAP,a_))
            return
        if eff=="steal_ctx_stat":
            g=ctx.get(str(p.get("key","gainer"))); stt=str(ctx.get("stat","") or "")
            if not hasattr(g,"alive") or not stt: return
            amt=min(int(p.get("amount",0)),int(ctx.get("amount",0) or 0))
            if amt>0: s.mod(g,stt,-amt); s.mod(self_l,stt,amt)
            return
        if eff=="gain_stat_scaled_from":
            src_=ctx.get(str(p.get("key","victim")))
            if not hasattr(src_,"alive"): return
            stt=str(p.get("stat","attack"))
            base={"attack":src_.atk,"defense":src_.dfn,"speed":src_.spd,"health":src_.mhp}.get(stt,0)
            amt=_rnd(base*float(p.get("frac",0.25)))
            if amt>0: s.mod(self_l,stt,amt)
            return
        if eff=="echo_stat_gain":
            if self_l.echo_guard: return
            stt=str(ctx.get("stat","") or "")
            if not stt: return
            self_l.echo_guard=True
            try: s.mod(self_l,stt,int(p.get("amount",1)))
            finally: self_l.echo_guard=False
            return
        if eff=="survive_at_hp":
            who=s.sel(self_l,str(p.get("key","self")),ctx)
            if who is None: return
            inc=int(ctx.get("incoming",0) or 0)
            who.hp=min(inc+int(p.get("hp",1)),MAXHP); who.mhp=min(max(who.mhp,who.hp),MAXHP); return
        if eff=="heal_to_fraction":
            want=int(math.floor(self_l.mhp*float(p.get("frac",0.75))))
            if want>self_l.hp: s.mod(self_l,"health",want-self_l.hp)
            return
        if eff=="cleanse_ctx_status":
            who=s.sel(self_l,str(p.get("target","self")),ctx); sid=str(ctx.get("status_id","") or "")
            if who is not None and sid and sid in who.st: del who.st[sid]
            return
        if eff=="cleanse_status_all":
            sid=str(p.get("status_id",""))
            for w in s.teams[0]+s.teams[1]:
                if w.alive and sid in w.st: del w.st[sid]
            return
        if eff=="schedule_status_next_turn":
            who=s.sel(self_l,str(p.get("target","target")),ctx)
            if who is None: return
            pre=ctx.get("pre_statuses") or []
            for sid in p.get("status_ids") or []:
                if str(sid) in who.st or str(sid) in pre:
                    s.pending.append({"leader":self_l,"effect":"inflict_status_alive",
                        "params":{"status_id":str(sid),"target":"sched_target"},"ctx":{"sched_target":who}})
            return
        if eff=="inflict_status_alive":
            who=s.sel(self_l,str(p.get("target","target")),ctx); sid=str(p.get("status_id",""))
            if who is not None and who.alive and sid in STA: s.inflict(who,sid,self_l)
            return
        if eff=="gain_stat_per_enemy_alive":
            tot=int(p.get("amount",0))*len(s.alive(s.enemy_side(self_l.side)))
            if tot>0: s.mod(self_l,str(p.get("stat","")),tot)
            return
        if eff=="multi_effect":
            for e in p.get("effects",[]): s.run_effect(self_l,e.get("effect",""),e.get("params",{}),ctx)
            return
        if eff=="gain_stat": s.mod(self_l,p["stat"],p.get("amount",0)); return
        if eff=="lose_stat": s.mod(self_l,p["stat"],-p.get("amount",0)); return
        if eff in("gain_stat_target","lose_stat_target"):
            t=s.sel(self_l,p.get("target","self"),ctx);   # game default target "self" (battle_sim.gd:642)
            if t: s.mod(t,p["stat"],p.get("amount",0)*(1 if eff.startswith("gain") else -1))
            return
        if eff=="conditional":            # faithful to game: multi_effect passes only params, so
            c=p.get("condition","")       # a conditional nested in multi_effect no-ops (game dev bug, matched)
            if c and not s.cond(self_l,c,p.get("condition_params",{}),ctx): return
            ie=p.get("effect","")
            if ie: s.run_effect(self_l,ie,p.get("params",{}),ctx)
            return
        if eff=="inflict_random_status_each":
            pool=p.get("pool") or ["poisoned","bleeding","cursed","slow","dizzy","weak","stunned","on_fire","stinky","paralyzed"]
            if not pool: return
            sc=p.get("scope","ally")
            pl=s.alive(s.enemy_side(self_l.side)) if sc=="enemy" else (s.all_leaders() if sc=="all" else s.alive(self_l.side))
            for l in pl: s.inflict(l,s.rng.choice(pool),self_l)
            return
        if eff=="gain_stat_all_allies":
            for l in s._ally_pool(self_l,p): s.mod(l,p["stat"],p.get("amount",0))
            return
        if eff=="gain_stat_all_enemies":
            for l in s.alive(s.enemy_side(self_l.side)): s.mod(l,p["stat"],p.get("amount",0))
            return
        if eff in("gain_stat_allies_with_tag","gain_stat_all_allies_with_tag"):
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            for l in s.alive(self_l.side):
                if p.get("exclude_self") and l is self_l: continue
                if (not tags) or any(l.has_tag(t) for t in tags): s.mod(l,p["stat"],p.get("amount",0))
            return
        if eff=="lose_stat_all_allies":
            for l in s._ally_pool(self_l,p): s.mod(l,p["stat"],-p.get("amount",0))
            return
        if eff=="gain_stat_allies_with_status":
            sid=p.get("status_id") or p.get("has_status","")
            for l in s.alive(self_l.side):
                if sid in l.st: s.mod(l,p["stat"],p.get("amount",0))   # game has_status(sid): empty matches NONE
            return
        if eff=="damage_target":
            t=s.sel(self_l,p.get("target","self"),ctx)
            if t is not None:
                t.take_damage(int(p.get("amount",0))); s.check_death(t,self_l)
            return
        if eff=="damage_all_enemies":
            amt=int(p.get("amount",0))
            if amt>0:
                for l in s.alive(s.enemy_side(self_l.side)):
                    l.take_damage(amt); s.check_death(l,self_l)
            return
        if eff=="extra_attack":
            xt=ctx.get("target")
            if xt is not None and self_l.alive and xt.alive: s.resolve(self_l,xt)
            return
        if eff=="lose_stat_all_enemies_eot":
            stt=p.get("stat",""); amt=p.get("amount",0)
            for l in s.alive(s.enemy_side(self_l.side)):
                s.mod(l,stt,-amt); l.eot.append({"stat":stt,"amount":amt})
            return
        if eff=="kill_self":
            if self_l.hp>0: self_l.take_damage(self_l.hp)
            s.check_death(self_l); return
        if eff=="set_stat":
            v=p.get("value",0); stt=p.get("stat","")
            if stt=="health":
                self_l.hp=max(0,min(self_l.mhp,v))          # game: max(0,min(value,max_hp)) then _check_death
                if self_l.hp<=0: s.check_death(self_l)
            elif stt=="attack": self_l.atk=max(0,min(MAXATK,v))
            elif stt=="defense": self_l.dfn=max(0,min(DEFCAP,v))
            elif stt=="speed": self_l.spd=max(0,v)
            return
        if eff=="inflict_random_status":
            pool=p.get("pool") or ["poisoned","bleeding","cursed","slow","dizzy","weak","stunned","on_fire","stinky","paralyzed"]
            t=s.sel(self_l,p.get("target","random_enemy"),ctx)
            if t is not None: s.inflict(t,pool[s.rng.randrange(len(pool))],self_l)
            return
        if eff=="refresh_target_random_status":
            t=s.sel(self_l,p.get("target","target"),ctx)
            if t is not None and t.st:
                ks=list(t.st.keys()); sid=ks[s.rng.randrange(len(ks))]
                mult=1
                for a in t.abil:
                    if a.get("trigger")=="passive_status_duration" and sid in (a.get("params",{}).get("status_ids") or []): mult=int(a.get("params",{}).get("mult",2))
                t.st[sid]=[STA[sid][0]*mult,0]
            return
        if eff=="cleanse_status_allies_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            sids=p.get("status_ids") or ([p["status_id"]] if p.get("status_id") else [])
            for l in s.alive(self_l.side):
                if (not tags) or any(l.has_tag(t) for t in tags):
                    for sd in sids: s.cleanse(l,sd)
            return
        if eff=="inflict_status_enemies_with_status":
            need=p.get("has_status","")
            for l in s.alive(s.enemy_side(self_l.side)):
                if (not need) or need in l.st: s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_allies_with_any_status":
            for l in s.alive(self_l.side):
                if l.st: s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_enemies_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            for l in s.alive(s.enemy_side(self_l.side)):
                if (not tags) or any(l.has_tag(t) for t in tags): s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_all_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            for l in s.teams[0]+s.teams[1]:   # game iterates all_leaders() and checks .dead lazily
                if l.alive and ((not tags) or any(l.has_tag(t) for t in tags)): s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status":
            t=s.sel(self_l,p.get("target","self"),ctx); s.inflict(t,p.get("status_id"),self_l); return
        if eff=="inflict_status_all_enemies":
            for l in s.alive(s.enemy_side(self_l.side)): s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_all_allies":
            for l in s._ally_pool(self_l,p): s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_all":
            for l in s.teams[0]+s.teams[1]:   # lazy dead check (a reaction can kill a later leader)
                if l.alive: s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_allies_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            for l in s.alive(self_l.side):
                if (not tags) or any(l.has_tag(t) for t in tags):
                    s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_filtered":
            for l in s._filtered(self_l,p.get("side","enemy"),p.get("filter",{})):
                s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="cleanse_status":
            t=s.sel(self_l,p.get("target","self"),ctx); s.cleanse(t,p.get("status_id")); return
        if eff=="survive_at_1":   # fired from on_miracle; the pending take_damage(incoming) then leaves 1 hp
            inc=int(ctx.get("incoming",0) or 0)
            self_l.hp=min(inc+1,MAXHP); self_l.mhp=min(max(self_l.mhp,self_l.hp),MAXHP); return
        if eff=="schedule_next_turn":
            s.pending.append({"leader":self_l,"effect":p.get("effect"),"params":p.get("params",{})}); return
        if eff=="lose_stat_all_enemies":
            for l in s.alive(s.enemy_side(self_l.side)): s.mod(l,p["stat"],-p.get("amount",0))
            return
        if eff=="gain_stat_per_leader_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            scope=p.get("scope","all")
            pool=s.alive(self_l.side) if scope=="ally" else s.alive(s.enemy_side(self_l.side)) if scope=="enemy" else s.all_leaders()
            amt=p.get("amount",0); tot=sum(amt for l in pool if not (p.get("exclude_self") and l is self_l) and any(l.has_tag(str(t)) for t in tags))
            if tot>0: s.mod(self_l,p["stat"],tot)
            return
        if eff=="gain_stat_per_ally_alive":
            tot=p.get("amount",0)*len(s.alive(self_l.side))
            if tot>0: s.mod(self_l,p["stat"],tot)
            return
        if eff in("gain_stat_filtered","lose_stat_filtered"):
            sign=1 if eff.startswith("gain") else -1
            side=p.get("side","ally" if sign>0 else "enemy")   # game: gain default "ally", lose default "enemy"
            for l in s._filtered(self_l,side,p.get("filter",{})):
                s.mod(l,p["stat"],sign*p.get("amount",0))
            return
        if eff=="damage_filtered":
            amt=int(p.get("amount",0))
            if amt>0:
                for l in s._filtered(self_l,p.get("side","enemy"),p.get("filter",{})):
                    l.take_damage(amt); s.check_death(l,self_l)
            return
        if eff=="gain_stat_per_leader_with_status":
            sid=p.get("status_id","")
            side=p.get("side","all")
            pool=s.alive(self_l.side) if side=="ally" else s.alive(s.enemy_side(self_l.side)) if side=="enemy" else s.all_leaders()
            n=sum(1 for l in pool if sid in l.st)   # game has_status(sid): empty matches NONE
            if n>0: s.mod(self_l,p["stat"],p.get("amount",0)*n)
            return
        if eff=="draw2_hat_chain":
            cards2=[]
            for _ in range(2):
                c2=s._draw_single(self_l)
                if c2 is not None: cards2.append(c2)
            if not any(def_has_tag(c2,"hat") for c2 in cards2): return
            enemies=s.alive(s.enemy_side(self_l.side))
            if not enemies: return
            slow=s._ext(enemies,lambda l:l.eff_spd(),False)
            slow.take_damage(22)
            if not slow.alive: s.check_death(slow,self_l); return
            if slow.hp<150:
                s.apply_status(slow,"poisoned"); s.apply_status(slow,"paralyzed")
                if slow.eff_def()<20:
                    s.apply_status(slow,"weak")
                    s.mod(slow,"attack",-10)
            return
        if eff=="draw_supporter":
            for _ in range(p.get("count",1)):
                if s._draw_single(self_l) is None: break
            return
        if eff=="draw_supporter_per_ally_with_tag":
            tag=p.get("tag",""); cnt=p.get("count",1)
            n=sum(1 for a in s.alive(self_l.side) if tag=="" or a.has_tag(tag))
            for _ in range(n*cnt):
                if s._draw_single(self_l) is None: break
            return
        if eff=="draw_supporter_per_enemy_with_tag":
            tag=p.get("tag",""); cnt=p.get("count",1)
            n=sum(1 for a in s.alive(s.enemy_side(self_l.side)) if a.has_tag(tag))
            for _ in range(n*cnt):
                if s._draw_single(self_l) is None: break
            return
        if eff=="draw_supporter_per_leader_with_status":
            sid=p.get("status_id",""); cnt=p.get("count",1); side=p.get("side","all")
            pool=s.alive(self_l.side) if side=="ally" else s.alive(s.enemy_side(self_l.side)) if side=="enemy" else s.all_leaders()
            n=sum(1 for l in pool if (l.st if sid=="" else sid in l.st))
            for _ in range(n*cnt):
                if s._draw_single(self_l) is None: break
            return
        if eff=="draw_supporter_per_doomed":
            n=sum(1 for l in s.all_leaders() if "doomed" in l.st)
            for _ in range(n):
                if s._draw_single(self_l) is None: break
            return
        if eff=="draw_supporter_tag_chain":
            card=s._draw_single(self_l)
            if card is not None:
                tags=p.get("tags",[]) or ([p["tag"]] if p.get("tag") else [])
                if (not tags) or any(def_has_tag(card,t) for t in tags):
                    th=p.get("then",{})
                    if th: s.run_effect(self_l,th.get("effect",""),th.get("params",{}),ctx)
            return
        if eff=="draw_supporter_with_tag_status":
            card=s._draw_single(self_l)
            tags=p.get("tags",[]) or ([p["tag"]] if p.get("tag") else [])
            sid=p.get("status_id","")
            if card is not None and sid and ((not tags) or any(def_has_tag(card,t) for t in tags)):
                for al in s.alive(self_l.side): s.inflict(al,sid,self_l,notify=False)  # game applies via apply_status (no triggers)
            return
        if eff=="draw_supporter_or_penalty":
            cnt=p.get("count",1); tags=p.get("tags",[]); pen=p.get("penalty",{}); had=(not tags)
            for _ in range(cnt):
                card=s._draw_single(self_l)
                if card is None: break
                if tags and any(def_has_tag(card,t) for t in tags): had=True
            if not had and pen: s.run_effect(self_l,pen.get("effect",""),pen.get("params",{}),ctx)
            return
        if eff.startswith("draw_supporter"):
            s._draw_single(self_l); return
        UNIMPL.add("eff:"+eff)
    def _filtered(s,self_l,side,filt):
        if side=="enemy": pool=s.alive(s.enemy_side(self_l.side))
        elif side=="all": pool=s.all_leaders()
        else: pool=s.alive(self_l.side)
        out=[]
        for l in pool:
            if filt.get("faster_than_self") and l.eff_spd()<=self_l.eff_spd(): continue
            if "tag" in filt and not l.has_tag(filt["tag"]): continue
            if "tags" in filt and not any(l.has_tag(t) for t in filt["tags"]): continue
            if "has_status" in filt and filt["has_status"] not in l.st: continue
            if "hp_min" in filt and l.hp<filt["hp_min"]: continue
            if "hp_max" in filt and l.hp>filt["hp_max"]: continue
            if "speed_eq" in filt and l.eff_spd()!=int(filt["speed_eq"]): continue   # game _filter_match uses effective_speed
            if "speed_min" in filt and l.eff_spd()<int(filt["speed_min"]): continue
            if "speed_max" in filt and l.eff_spd()>int(filt["speed_max"]): continue
            if "def_min" in filt and l.eff_def()<int(filt["def_min"]): continue       # effective_defense
            if "def_max" in filt and l.eff_def()>int(filt["def_max"]): continue
            if "atk_min" in filt and l.atk<int(filt["atk_min"]): continue             # raw attack
            if "atk_max" in filt and l.atk>int(filt["atk_max"]): continue
            out.append(l)
        return out
    def _draw_single(s, owner):
        deck=s.decks[owner.side]; disc=s.disc[owner.side]
        if not deck:
            if not disc: return None
            s.shuf[owner.side].shuffle(disc); deck.extend(disc); disc.clear()
        if not deck: return None
        card=deck.pop(0)
        s.drawn[owner.side]+=1
        sab=card.get("supporter")
        if sab:
            _prev_bs=s._stat_gain_by_supporter
            s._stat_gain_by_supporter=True   # stat gains inside a supporter's ability are "by supporter"
            s.run_effect(owner,sab.get("effect",""),sab.get("params",{}),{"card":card})
            s._stat_gain_by_supporter=_prev_bs
        disc.append(card)
        if s.depth<24:
            s.depth+=1
            for al in s.alive(owner.side): s.fire(al,"on_supporter_drawn",{"card":card})
            for foe in s.alive(s.enemy_side(owner.side)): s.fire(foe,"on_opp_supporter_drawn",{"card":card})
            for l in s.all_leaders(): s.fire(l,"on_any_supporter_drawn",{"card":card,"drawer_side":owner.side})
            s.depth-=1
        return card
    # ---- triggers ----
    def fire(s, l, trig, ctx, force=False):
        if s.chain>=5: return          # game _MAX_CHAIN_DEPTH
        if not l.alive and not (force or trig=="on_death"): return
        s.chain+=1
        try: s._fire_inner(l,trig,ctx)
        finally: s.chain-=1
    def _fire_inner(s, l, trig, ctx):
        for a in l.abil:
            if a.get("trigger")!=trig: continue
            key=(id(a),)
            if a.get("once_game") and key in l.og: continue
            if a.get("once_turn") and key in l.ot_turn: continue
            if not s.cond(l,a.get("condition",""),a.get("cond_params",{}),ctx): continue
            if a.get("once_game"): l.og.add(key)
            if a.get("once_turn"): l.ot_turn.add(key)
            s.run_effect(l,a.get("effect",""),a.get("params",{}),ctx)
    def broadcast(s, trig, ctx):
        if s.depth>=24: return
        s.depth+=1
        for l in s.all_leaders(): s.fire(l,trig,ctx)
        s.depth-=1
    def run_sub(s, self_l, sub, ctx):   # battle_sim._run_sub
        if isinstance(sub,dict): s.run_effect(self_l,str(sub.get("effect","")),sub.get("params") or {},ctx)
    # ---- attack ----
    def dmg_bonus(s, atk, tgt):   # _compute_attack_damage_bonus (+ every alive teammate's passive_team_damage_bonus)
        tot=0; ctx={"target":tgt,"attacker":atk}
        for a in atk.abil:
            if a.get("trigger")!="passive_damage_bonus": continue
            if not s.cond(atk,a.get("condition",""),a.get("cond_params",{}),ctx): continue
            p=a.get("params") or {}
            tot+=int(p.get("amount",0))
            ps=int(p.get("per_self_status",0))
            if ps: tot+=ps*len(atk.st)
            pt=int(p.get("per_target_status",0))
            if pt and tgt is not None: tot+=pt*len(tgt.st)
        for mate in s.alive(atk.side):
            for a in mate.abil:
                if a.get("trigger")=="passive_team_damage_bonus" and s.cond(mate,a.get("condition",""),a.get("cond_params",{}),ctx):
                    tot+=int((a.get("params") or {}).get("amount",0))
        return tot
    def status_ids(s,l): return list(l.st.keys()) if l is not None else []
    def crit_mult(s, atk, tgt):
        m=1.0; ctx={"target":tgt,"attacker":atk}
        for a in atk.abil:
            if a.get("trigger")=="passive_crit_mult" and s.cond(atk,a.get("condition",""),a.get("cond_params",{}),ctx):
                m*=float((a.get("params") or {}).get("mult",1.0))
        return m
    def crit_bonus(s, atk):
        return sum(int((a.get("params") or {}).get("amount",0)) for a in atk.abil if a.get("trigger")=="passive_crit_bonus")
    def attack_mults(s, atk, tgt, dmg):   # _apply_attack_mults (chance is ALWAYS rolled, even at 1.0)
        ctx={"target":tgt,"attacker":atk}
        for a in atk.abil:
            if a.get("trigger")!="passive_attack_mult": continue
            key=(id(a),)
            if a.get("once_game") and key in atk.og: continue
            if not s.cond(atk,a.get("condition",""),a.get("cond_params",{}),ctx): continue
            p=a.get("params") or {}
            if s.rng.random()>=float(p.get("chance",1.0)): continue
            mult=float(p.get("mult",1.0))
            if "min" in p and "max" in p: mult=s.rng.uniform(float(p["min"]),float(p["max"]))
            dmg=max(0,_rnd(dmg*mult))
            if a.get("once_game"): atk.og.add(key)
            ss=p.get("self_status","")
            if ss: s.inflict(atk,ss,atk)
        return dmg
    def mod_incoming(s, atk, tgt, dmg):   # _mod_incoming (target's passive_damage_taken)
        if tgt is None: return dmg
        ctx={"attacker":atk,"target":tgt}
        for a in tgt.abil:
            if a.get("trigger")!="passive_damage_taken": continue
            if not s.cond(tgt,a.get("condition",""),a.get("cond_params",{}),ctx): continue
            p=a.get("params") or {}
            if p.get("first_hit_only") and tgt.hits_turn>0: continue
            flat=int(p.get("flat",0))
            at=p.get("ally_tags") or []
            if at:
                for al in s.alive(tgt.side):
                    if al is tgt: continue
                    if any(al.has_tag(str(t)) for t in at):
                        flat+=int(p.get("ally_tag_flat",0)); break
            if flat: dmg=max(0,dmg+flat)
            if "mult" in p: dmg=max(0,_rnd(dmg*float(p["mult"])))
            if "cap" in p: dmg=min(dmg,int(p["cap"]))
            if "round_down" in p:
                r=int(p["round_down"])
                if r>0: dmg=(dmg//r)*r
        return dmg
    def share_damage(s, tgt, dmg):   # _share_damage (an ally with passive_share_damage soaks part of the hit)
        if dmg<=0: return dmg
        for g in s.alive(tgt.side):
            if g is tgt: continue
            for a in g.abil:
                if a.get("trigger")!="passive_share_damage": continue
                p=a.get("params") or {}
                if s.sel(g,str(p.get("protect","lowest_hp_ally")),{}) is not tgt: continue
                part=int(math.floor(dmg*float(p.get("frac",0.5))))
                if part<=0: continue
                g.take_damage(part); s.check_death(g)
                return dmg-part
        return dmg
    def resolve(s, atk, tgt):   # battle_sim._resolve_attack
        pre=s.status_ids(tgt)
        tgt.wa_this=True
        s.broadcast("on_any_attack",{"attacker":atk,"target":tgt})
        s.broadcast("on_any_attacked",{"attacked":tgt,"attacker":atk,"target":tgt})
        if not atk.alive or not tgt.alive: return
        if atk.flag("dizzy") and s.rng.random()<0.5:
            s.fire(atk,"on_attack",{"target":tgt,"damage":0,"missed":True,"pre_statuses":pre})
            s.fire(atk,"on_blocked_or_dodged",{"target":tgt})
            return
        fz=sum(float(STA[x][2].get("fizzle_chance",0.0)) for x in atk.st if float(STA[x][2].get("fizzle_chance",0.0))>0)
        if fz>0 and s.rng.random()<fz:                    # confused / very_confused: the attack fizzles
            pick=s.rng.random()*fz; frac=0.0; acc=0.0
            for x in atk.st:
                fc=float(STA[x][2].get("fizzle_chance",0.0))
                if fc<=0: continue
                acc+=fc
                if pick<acc: frac=float(STA[x][2].get("fizzle_self_frac",0.0)); break
            rc=int(math.floor(atk.atk*frac))
            if rc>0: s.mod(atk,"health",-rc)
            s.broadcast("on_any_fizzle",{"attacker":atk,"target":tgt})
            s.fire(atk,"on_attack",{"target":tgt,"damage":0,"missed":True,"pre_statuses":pre})
            s.fire(atk,"on_blocked_or_dodged",{"target":tgt})
            return
        elem_base=atk.atk; dmg=atk.atk
        em=elem_mult(atk.elem,tgt.elem,tgt.apex)
        if abs(em-1.0)>1e-9: dmg=max(0,_rnd(dmg*em))
        crit=0.1*(2 if atk.flag("doubles_crit") else 1)*s.crit_mult(atk,tgt)
        is_crit=False
        if s.rng.random()<crit:
            dmg+=5+s.crit_bonus(atk); is_crit=True
            s.fire(atk,"on_crit",{"target":tgt})
            for al in s.alive(atk.side): s.fire(al,"on_ally_crit",{"crit_leader":atk,"target":tgt})
        b=s.dmg_bonus(atk,tgt)
        if b: dmg=max(0,dmg+b)
        dmg=s.attack_mults(atk,tgt,dmg)
        for x in list(atk.st):                            # horrified: weak hit vs a stronger target
            f=STA[x][2]; wc=float(f.get("weak_hit_chance",0.0))
            if wc<=0: continue
            if f.get("weak_needs_stronger_target") and tgt.atk<=atk.atk: continue
            if s.rng.random()<wc:
                dmg=max(0,_rnd(dmg*float(f.get("weak_hit_mult",1.0)))); break
        dfv=tgt.eff_def()
        dodge=(dfv/4.0)/100.0; block=(dfv/2.0)/100.0
        pd=sum(float((a.get("params") or {}).get("amount",0))/100.0 for a in tgt.abil if a.get("trigger")=="passive_dodge")
        dodge=min(0.95,dodge+pd)
        nob=tgt.flag("blocks_block")
        if atk.has_passive("passive_unblockable"): dodge=block=0.0
        roll=s.rng.random()
        dodged=(not nob) and roll<dodge
        blocked=(not dodged) and (not nob) and roll<(dodge+block)
        if not dodged:                                    # passive_force_dodge (optional stat gain / inflict on attacker)
            for a in tgt.abil:
                if a.get("trigger")!="passive_force_dodge": continue
                key=(id(a),)
                if a.get("once_game") and key in tgt.og: continue
                dodged=True; blocked=False
                if a.get("once_game"): tgt.og.add(key)
                p=a.get("params") or {}
                if "stat" in p: s.mod(tgt,p["stat"],int(p.get("amount",0)))
                ia=p.get("inflict_attacker","")
                if ia: s.inflict(atk,ia,tgt)
                break
        if blocked: dmg//=2
        s.fire(atk,"on_attack",{"target":tgt,"damage":0 if dodged else dmg,"pre_statuses":pre})
        if dodged:
            s.fire(atk,"on_blocked_or_dodged",{"target":tgt})
            s.fire(tgt,"on_attacked",{"attacker":atk,"dodged":True,"blocked":False,"damage":0})
            return
        if blocked: s.fire(atk,"on_blocked_or_dodged",{"target":tgt})
        dmg=s.mod_incoming(atk,tgt,dmg)
        dmg=s.share_damage(tgt,dmg)
        if dmg>=tgt.hp: s.fire(tgt,"on_miracle",{"attacker":atk,"incoming":dmg})
        if dmg>=tgt.hp:
            for al in s.alive(tgt.side):
                if al is tgt: continue
                s.fire(al,"on_ally_miracle",{"ally":tgt,"attacker":atk,"incoming":dmg})
                if dmg<tgt.hp: break
        if not atk.alive or not tgt.alive: return
        actual=tgt.take_damage(dmg)
        if actual>0: tgt.hits_turn+=1
        if atk.elem==2 and tgt.elem==5:                   # Element.recoil_fraction: Blobgob -> Monblonkin 0.3
            rc=_rnd(elem_base*0.3)
            if rc>0: s.mod(atk,"health",-rc)
        if tgt.alive:
            s.fire(tgt,"on_attacked",{"attacker":atk,"dodged":False,"blocked":blocked,"damage":actual,"crit":is_crit})
            s.fire(tgt,"on_damaged",{"attacker":atk,"damage":actual})
            s.fire(tgt,"on_survive",{"attacker":atk,"damage":actual})
            if actual>0 and tgt.alive:
                s.broadcast("on_any_damaged",{"damaged":tgt,"attacker":atk,"damage":actual})
        else:
            s.die(tgt,atk,True)
        for x in list(atk.st):                            # cursed: self-damage from damage dealt (AFTER target triggers)
            fr=STA[x][2].get("recoil",0.0)
            if fr and fr>0:
                sd=int(actual*fr)
                if sd>0:
                    atk.take_damage(sd)
                    if not atk.alive:
                        s.check_death(atk); return
    def resolve_multi(s, atk, pool):   # battle_sim._resolve_multi_attack (AttackStyle.ALL)
        tg=[t for t in pool if t is not None and t.alive]
        if not tg: return
        for t in tg: t.wa_this=True
        s.broadcast("on_any_attack",{"attacker":atk,"target":tg[0]})
        for t in tg: s.broadcast("on_any_attacked",{"attacked":t,"attacker":atk,"target":t})
        if not atk.alive: return
        if atk.flag("dizzy") and s.rng.random()<0.5:
            s.fire(atk,"on_attack",{"target":tg[0],"damage":0,"missed":True})
            s.fire(atk,"on_blocked_or_dodged",{"target":tg[0]})
            return
        fz=sum(float(STA[x][2].get("fizzle_chance",0.0)) for x in atk.st if float(STA[x][2].get("fizzle_chance",0.0))>0)
        if fz>0 and s.rng.random()<fz:                    # a multi-attack fizzle costs no HP
            s.broadcast("on_any_fizzle",{"attacker":atk,"target":tg[0]})
            s.fire(atk,"on_attack",{"target":tg[0],"damage":0,"missed":True})
            s.fire(atk,"on_blocked_or_dodged",{"target":tg[0]})
            return
        hits=[]
        for t in tg:                                      # no crit / dodge / block / weak-hit / share / miracle on multi-hits
            eb=atk.atk; d=atk.atk
            em=elem_mult(atk.elem,t.elem,t.apex)
            if abs(em-1.0)>1e-9: d=max(0,_rnd(d*em))
            b=s.dmg_bonus(atk,t)
            if b: d=max(0,d+b)
            d=s.attack_mults(atk,t,d)
            d=s.mod_incoming(atk,t,d)
            hits.append([t,d,eb,s.status_ids(t),0])
        for h in hits:
            h[4]=h[0].take_damage(h[1])
            if h[4]>0: h[0].hits_turn+=1
        for h in hits:
            if not atk.alive: break
            if h[0].alive: s.fire(atk,"on_attack",{"target":h[0],"damage":h[4],"missed":False,"pre_statuses":h[3]})
        for h in hits:
            t=h[0]
            if atk.elem==2 and t.elem==5:
                rc=_rnd(h[2]*0.3)
                if rc>0: s.mod(atk,"health",-rc)
            if t.alive:
                s.fire(t,"on_attacked",{"attacker":atk,"dodged":False,"blocked":False,"damage":h[4],"crit":False})
                s.fire(t,"on_damaged",{"attacker":atk,"damage":h[4]})
                s.fire(t,"on_survive",{"attacker":atk,"damage":h[4]})
                if h[4]>0: s.broadcast("on_any_damaged",{"damaged":t,"attacker":atk,"damage":h[4]})
            s.check_death(t,atk,True)
        s.check_death(atk)
    def _ally_pool(s, self_l, p):     # allies, optionally excluding the caster (exclude_self param)
        pool=s.alive(self_l.side)
        return [a for a in pool if a is not self_l] if p.get("exclude_self") else pool
    def _ext(s, pool, keyf, hi):   # game _extremum: random pick among all leaders tied at the best value
        if not pool: return None
        best=(max if hi else min)(keyf(l) for l in pool)
        ties=[l for l in pool if keyf(l)==best]
        return ties[0] if len(ties)==1 else s.rng.choice(ties)
    # ---- targeting ----
    def untargetable_by(s, cand, atk):   # passive_untargetable_by: healthy enough + attacker carries a listed tag
        for a in cand.abil:
            if a.get("trigger")!="passive_untargetable_by": continue
            p=a.get("params") or {}
            if cand.hp<=cand.mhp*float(p.get("hp_frac_above",0.0)): continue
            if any(atk.has_tag(str(t)) for t in (p.get("tags") or [])): return True
        return False
    def target_pool(s, atk):   # battle_sim._target_pool
        enemies=s.alive(s.enemy_side(atk.side))
        if atk.flag("targets_all"):                       # chaos / chaos_blinded: every other leader is a target
            ev=[l for l in s.alive(atk.side) if l is not atk]+enemies
            if ev: enemies=ev
        op=[c for c in enemies if not s.untargetable_by(c,atk)]
        return op if op else enemies
    def resolved_style(s, atk):   # battle_sim._resolved_style
        style=atk.style_override if atk.style_override>0 else atk.d.get("style",1)
        for a in atk.abil:
            if a.get("trigger")=="passive_target_style":
                style=int((a.get("params") or {}).get("style",style)); break
        for al in s.alive(atk.side):                      # jackified: allies use the holder's style
            if al is atk: continue
            if any(STA.get(x,(0,[],{}))[2].get("shares_attack_style") for x in al.st):
                style=int(al.d.get("style",1)); break
        if atk.flag("random_attack_style"): style=s.rng.randint(1,9)
        return style
    def pick_from(s, enemies, style):   # battle_sim._pick_from
        if not enemies: return None
        if style==1: return s.rng.choice(enemies)
        keyf={2:lambda l:l.eff_spd(),3:lambda l:l.eff_spd(),4:lambda l:l.hp,5:lambda l:l.hp,
              6:lambda l:l.eff_def(),7:lambda l:l.eff_def(),8:lambda l:l.atk,9:lambda l:l.atk}.get(style)
        if keyf is None: return enemies[0]
        return s._ext(enemies,keyf,style in (2,4,7,8))
    def pick_target(s, atk):
        return s.pick_from(s.target_pool(atk),s.resolved_style(atk))
    def bodyguard(s, atk, tgt):   # battle_sim._bodyguard_redirect (main-loop single attacks only)
        if tgt is None or atk is None or tgt.side==atk.side: return tgt
        for g in s.alive(tgt.side):
            if g is tgt: continue
            for a in g.abil:
                if a.get("trigger")!="passive_bodyguard": continue
                if (a.get("params") or {}).get("attacker","")=="highest_atk":
                    if any(f is not atk and f.atk>atk.atk for f in s.alive(atk.side)): continue
                key=(id(a),)
                if a.get("once_turn") and key in g.ot_turn: continue
                if a.get("once_turn"): g.ot_turn.add(key)
                return g
        return tgt
    def speed_sorted(s):   # _sort_by_speed_desc: ties broken by a fresh random salt per sort
        return sorted(s.all_leaders(),key=lambda l:(-l.eff_spd(),s.rng.random()))
    def run_turn(s):   # battle_sim._run_turn
        for l in s.teams[0]+s.teams[1]: l.ot_turn=set()   # once/turn keys are per turn number in the game
        if s.pending:
            pend=s.pending; s.pending=[]
            for pe in pend:
                pl=pe.get("leader")
                if pl is None or not pl.alive: continue
                s.run_effect(pl,pe.get("effect",""),pe.get("params") or {},pe.get("ctx") or {})
        for l in s.teams[0]+s.teams[1]:
            l.dmg_turn=0; l.hits_turn=0; l.turn_now=s.turn
        for l in s.teams[0]+s.teams[1]:
            if not l.alive: continue
            swaps=[]
            for a in l.abil:
                if a.get("trigger")=="passive_status_heal":
                    sid=(a.get("params") or {}).get("status_id","")
                    if sid in l.st:
                        rem,idx=l.st[sid]; dl=STA[sid][1]
                        swaps.append((int(a["params"].get("amount",0)),int((dl[idx] if idx<len(dl) else {}).get("health",0))))
            if len(s.alive(s.enemy_side(l.side)))<=2 and "soul_bound" in l.st: del l.st["soul_bound"]
            d=s.tick_statuses(l)
            for amt,dm in swaps: d["health"]=int(d.get("health",0))-dm+amt
            s.apply_stat_deltas(l,d)
            s.check_death(l)
        for l in s.speed_sorted():
            if l.alive: s.fire(l,"turn_start",{})
        for atk in s.speed_sorted():
            if not atk.alive: continue
            if atk.flag("blocks_attack"): continue
            pool=s.target_pool(atk)
            if not pool: continue
            style=s.resolved_style(atk)
            if style==STYLE_ALL: s.resolve_multi(atk,pool)
            else:
                tgt=s.pick_from(pool,style)
                if tgt is None: continue
                s.resolve(atk,s.bodyguard(atk,tgt))
            if atk.alive: s.apply_status(atk,"tired")   # _mark_attacked: silent apply_status
        for l in s.speed_sorted():
            if l.alive: s.fire(l,"turn_end",{})
        for l in s.teams[0]+s.teams[1]:                  # end-of-turn stat reverts (attack/defense/speed only)
            for m in l.eot:
                st_=m.get("stat",""); a=int(m.get("amount",0))
                if st_=="attack": l.atk=max(0,min(MAXATK,l.atk+a))
                elif st_=="defense": l.dfn=max(0,min(DEFCAP,l.dfn+a))
                elif st_=="speed": l.spd=max(0,l.spd+a)
            l.eot=[]
        for l in s.teams[0]+s.teams[1]:                  # attacked-last-turn rollover, then the status sweep
            l.wa_last=l.wa_this; l.wa_this=False
            s.sweep_expired(l)
    def over(s): return not s.alive(0) or not s.alive(1)
    def run(s, deckA, deckB, verbose=False):
        s.verbose=verbose
        s.teams=[[],[]]
        for i,c in enumerate(deckA[:3]):
            if c is not None: s.teams[0].append(L(c,0,i))   # empty leader slot (null) is skipped, like battle_sim
        for i,c in enumerate(deckB[:3]):
            if c is not None: s.teams[1].append(L(c,1,i))
        if len(deckB)<4:  # CPU gets 4 seeded supporters in-game; approximate by sampling the pool
            eids={c.get("id") for c in deckB[:3] if c is not None}
            pool=[i for i in ENEMY_SUPP_POOL if i not in eids]
            deckB=list(deckB)+[LEADERS[i] for i in s.rng.sample(pool,4)]
        s.decks=[ [dict(x) for x in deckA[3:7]], [dict(x) for x in deckB[3:7]] ]
        s.disc=[[],[]]
        for side in (0,1): s.shuf[side].shuffle(s.decks[side])
        if verbose:
            for l in s.teams[0]: print(f"  P {l.name[:26]:<27} hp{l.hp} atk{l.atk} def{l.dfn} spd{l.spd} elem{l.elem}")
            for l in s.teams[1]: print(f"  E {l.name[:26]:<27} hp{l.hp} atk{l.atk} def{l.dfn} spd{l.spd} elem{l.elem}")
        while s.turn<30 and not s.over():
            s.turn+=1
            s.drawn_last=s.drawn[:]; s.drawn=[0,0]
            s.run_turn()
            if verbose:
                p=" ".join(f"{l.name[:8]}:{max(0,l.hp)}" for l in s.teams[0])
                e=" ".join(f"{l.name[:8]}:{max(0,l.hp)}" for l in s.teams[1])
                print(f"  T{s.turn}  P[{p}]  E[{e}]")
        # story rule (story_hub._on_returned_from_battle): player wins ONLY if winner==PLAYER,
        # i.e. all enemies dead with a surviving player leader. Timeout / mutual death = defeat.
        return 0 if (not s.alive(1) and s.alive(0)) else 1

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

def winrate(pids, epairs, n=400):
    ed=enemy_deck(epairs)
    w=0
    for seed in range(n):
        pd=player_deck(pids)
        if Sim(seed*7+1).run(pd,ed)==0: w+=1
    return w/n

if __name__=="__main__":
    E={
     "E12":[(457,6),(39,8),(241,7)],
     "E16":[(459,8),(40,10),(458,9)],
     "E18":[(3,10),(645,12),(1,11)],
     "E19":[(2,11),(646,13),(11,12)],
     "E20":[(13,12),(647,13),(24,13)],
     "E21":[(25,13),(601,13),(28,13)],
    }
    soul=[477,483,484]
    for name,dk in E.items():
        print(f"{name}: Soul(477,483,484) winrate = {winrate(soul,dk,300)*100:.0f}%")
    print("unimpl:",sorted(UNIMPL))
