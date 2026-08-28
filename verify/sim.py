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
# id: (duration, [per-turn deltas], flags)
STA={
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
 "chaos":(4,[{},{},{},{}],{"targets_all":True}),   # attacker targets ALL leaders (not self)
}
MAXHP=999; MAXATK=199

class L:
    __slots__=("d","side","slot","hp","mhp","atk","dfn","spd","elem","apex","abil","name","st","og","ot_turn","dmg_turn","alive","lvl","announced","eot")
    def __init__(s,d,side,slot):
        s.d=d; s.side=side; s.slot=slot
        s.hp=d["hp"]; s.mhp=d["hp"]; s.atk=d["atk"]; s.dfn=d["def"]; s.spd=d["spd"]
        s.elem=d.get("element",-1); s.apex=d.get("apex",False)
        s.abil=d.get("abilities",[]); s.name=d["name"]; s.lvl=d.get("level",1)
        s.st={}   # status_id -> [remaining_ticks, tick_index]
        s.og=set(); s.ot_turn=set(); s.dmg_turn=0; s.alive=True; s.announced=False; s.eot=[]
    def eff_def(s):
        fd=-1
        for sid in s.st:
            f=STA.get(sid,(0,[],{}))[2]
            if "force_defense" in f: fd=max(fd,f["force_defense"])
        return fd if fd>=0 else s.dfn
    def eff_spd(s):
        ov=-1
        for sid in s.st:
            f=STA.get(sid,(0,[],{}))[2]
            if "override_speed" in f: ov=f["override_speed"]
        return ov if ov>=0 else s.spd
    def flag(s,name):
        for sid in s.st:
            if STA.get(sid,(0,[],{}))[2].get(name): return True
        return False
    def immune(s,sid):
        for a in s.abil:
            if a.get("trigger")=="passive_immunity":
                p=a.get("params",{})
                x=p.get("status_id") or p.get("status_ids")
                if x=="all" or (isinstance(x,str) and x==sid) or (isinstance(x,list) and sid in x): return True
        return False
    def has_passive(s,trig):
        return any(a.get("trigger")==trig for a in s.abil)

def apply_player_level(card, lvl=10):
    c=dict(card); bonus={"hp":0,"atk":0,"spd":0,"def":0}
    for lv in range(2,lvl+1):
        if lv==3: bonus["spd"]+=10
        elif lv==4: bonus["def"]+=5
        elif lv==5: bonus["hp"]+=10
        elif lv==6: bonus["atk"]+=3
        elif lv==7: bonus["spd"]+=15
        elif lv==8: bonus["def"]+=6
        elif lv==9: bonus["hp"]+=15
        elif lv==10: bonus["atk"]+=5
    c["hp"]=min(MAXHP,card["hp"]+bonus["hp"]); c["atk"]=min(MAXATK,card["atk"]+bonus["atk"])
    c["spd"]=card["spd"]+bonus["spd"]; c["def"]=min(50,card["def"]+bonus["def"])
    c["level"]=lvl
    # skin_manager.get_cumulative_stats unlocks ability2 at level 2 (NOT 10); story_hub.
    # _apply_level_bonuses then keeps abilities[0] always and the rest only once unlocked
    if lvl < 2: c["abilities"]=list(card.get("abilities",[]))[:1]
    return c

def apply_enemy_level(card, lvl):
    c=dict(card); k=lvl-1
    c["hp"]=min(MAXHP,card["hp"]+18*k); c["spd"]=card["spd"]+8*k
    c["def"]=min(50,card["def"]+2*k); c["atk"]=min(MAXATK,card["atk"]+4*k)
    c["level"]=lvl
    return c

def enemy_card(cid, lvl):
    base = BOSSES[cid] if cid in BOSSES else LEADERS[cid]
    c = apply_enemy_level(base, lvl)
    if "element" not in c: c["element"]=LEADERS.get(cid,{}).get("element",-1)
    return c

UNIMPL=set()
class Sim:
    def __init__(s, seed):
        s.rng=random.Random(seed); s.turn=0; s.teams=[[],[]]; s.depth=0; s.pending=[]
        s.chain=0                      # _chain_depth (max 5) for nested trigger fires
        s.drawn=[0,0]; s.drawn_last=[0,0]   # supporters drawn this/last turn per side
        s._stat_gain_by_supporter=False     # true only while a supporter card's own ability runs
    def enemy_side(s,side): return 1-side
    def alive(s,side): return [l for l in s.teams[side] if l.alive]
    def all_leaders(s): return [l for l in s.teams[0]+s.teams[1] if l.alive]
    # ---- status ----
    def inflict(s, tgt, sid, src=None):
        if tgt is None or not tgt.alive: return False
        if sid not in STA: return False
        if sid!="purified" and tgt.immune(sid): return False
        for x in tgt.st:            # purified (blocks_other) blocks any different status
            if STA[x][2].get("blocks_other") and sid!=x: return False
        mult=1                      # passive_status_duration multiplies listed statuses on this leader
        for a in tgt.abil:
            if a.get("trigger")=="passive_status_duration":
                p=a.get("params",{})
                if sid in (p.get("status_ids") or []): mult=int(p.get("mult",2))
        if sid in tgt.st:           # re-application: turns_elapsed=0 -> full duration again, NO trigger
            tgt.st[sid]=[STA[sid][0]*mult,0]; return False
        tgt.st[sid]=[STA[sid][0]*mult,0]
        if s.depth<24:              # fresh application fires reaction + broadcast
            s.depth+=1
            s.fire(tgt,"on_status_applied",{"affected":tgt,"status_id":sid})
            for l in s.all_leaders(): s.fire(l,"on_any_status_applied",{"affected":tgt,"status_id":sid})
            s.depth-=1
            s.checkdeath(None)
        return True
    def cleanse(s, tgt, sid):
        if tgt and sid in tgt.st: del tgt.st[sid]
    # ---- death ----
    def die(s, victim, killer=None, is_attack=False):
        if victim.announced: return
        victim.alive=False; victim.hp=0; victim.announced=True
        s.fire(victim,"on_death",{"killer":killer,"fallen":victim},force=True)
        if is_attack and killer is not None:
            s.fire(killer,"on_kill",{"fallen":victim,"victim":victim})
        s.broadcast("on_any_death",{"fallen":victim,"killer":killer})
        living=s.alive(victim.side)
        for al in living: s.fire(al,"on_ally_killed",{"fallen":victim})
        if len(living)==1: s.fire(living[0],"on_last_standing",{"fallen":victim})
    def checkdeath(s, killer=None, is_attack=False):
        # sweep all leaders whose hp dropped to 0 (from ticks/recoil/loss) and announce
        for l in s.teams[0]+s.teams[1]:
            if l.hp<=0 and not l.announced: s.die(l,killer,is_attack)
    def tick_statuses(s, l):
        expire=[]
        for sid in list(l.st.keys()):
            rem,idx=l.st[sid]
            deltas=STA[sid][1]
            d=deltas[idx] if idx < len(deltas) else {}
            for k,v in d.items():
                if k=="health": l.hp = min(l.mhp,l.hp+v) if v>0 else l.hp+v
                elif k=="attack": l.atk=max(0,min(MAXATK,l.atk+v))
                elif k=="defense": l.dfn=max(0,l.dfn+v)
                elif k=="speed": l.spd=max(0,l.spd+v)
            l.st[sid][1]+=1; l.st[sid][0]-=1
            if l.st[sid][0]<=0: expire.append(sid)
        for sid in expire: del l.st[sid]
    # ---- stat mod ----
    def mod(s,l,stat,amt):
        if not l.alive: return
        if stat=="health": l.hp = min(l.mhp,l.hp+amt) if amt>0 else l.hp+amt
        elif stat=="attack": l.atk=max(0,min(MAXATK,l.atk+amt))
        elif stat=="defense": l.dfn=max(0,l.dfn+amt)
        elif stat=="speed": l.spd=max(0,l.spd+amt)
        if amt>0:
            if stat=="attack": s.fire(l,"on_boost",{"stat":stat,"amount":amt})
            s.fire(l,"on_stat_gain",{"stat":stat,"amount":amt})
            s.broadcast("on_any_stat_gain",{"gainer":l,"stat":stat,"amount":amt,"by_supporter":s._stat_gain_by_supporter})
        if l.hp<=0: s.checkdeath()
    # ---- targeting for effects ----
    def sel(s, self_l, key, ctx):
        if key in ctx and hasattr(ctx[key],"alive"): return ctx[key]
        if key=="self": return self_l
        allies=s.alive(self_l.side); enemies=s.alive(s.enemy_side(self_l.side))
        d={"random_ally":allies,"random_enemy":enemies}
        if key in d:
            pool=d[key]; return s.rng.choice(pool) if pool else None
        SUP={"fastest":("spd",True),"slowest":("spd",False),"highest_hp":("hp",True),"lowest_hp":("hp",False),
             "highest_def":("dfn",True),"lowest_def":("dfn",False),"highest_atk":("atk",True),"lowest_atk":("atk",False)}
        for suf,(pool,isenemy) in (("_ally",0),("_enemy",1)) if False else []:
            pass
        for stem,(attr,hi) in SUP.items():
            for suf,pool in (("_ally",allies),("_enemy",enemies),("_overall",allies+enemies)):
                if key==stem+suf:
                    if not pool: return None
                    keyf=lambda l:(l.eff_spd() if attr=="spd" else l.eff_def() if attr=="dfn" else getattr(l,attr))
                    return (max if hi else min)(pool,key=keyf)
        return None
    # ---- conditions ----
    def cond(s, self_l, cname, cp, ctx):
        if not cname: return True
        if cname=="self_hp_at_or_below": return self_l.hp<=cp.get("value",0)
        if cname=="self_hp_above": return self_l.hp>cp.get("value",0)
        if cname=="self_stat_at_least":
            v={"health":self_l.hp,"attack":self_l.atk,"defense":self_l.eff_def(),"speed":self_l.eff_spd()}[cp["stat"]]; return v>=cp.get("value",0)
        if cname=="self_stat_at_most":
            v={"health":self_l.hp,"attack":self_l.atk,"defense":self_l.eff_def(),"speed":self_l.eff_spd()}[cp["stat"]]; return v<=cp.get("value",0)
        if cname=="turn_equals": return s.turn==cp.get("value")
        if cname=="turn_in_set": return s.turn in cp.get("values",[])
        if cname=="self_has_status": return cp.get("status_id") in self_l.st
        if cname=="self_no_statuses": return len(self_l.st)==0
        if cname=="target_has_status":
            t=ctx.get("target"); return t is not None and cp.get("status_id") in t.st
        if cname in("ally_has_tag","any_leader_has_tag"):
            tag=cp.get("tag","")
            pool=s.alive(self_l.side) if cname=="ally_has_tag" else s.all_leaders()
            return any(name_has_tag(l.name,tag) for l in pool)
        if cname=="ally_has_any_tag":
            return any(any(name_has_tag(l.name,t) for t in cp.get("tags",[])) for l in s.alive(self_l.side))
        if cname=="enemies_count_at_least": return len(s.alive(s.enemy_side(self_l.side)))>=cp.get("value",0)
        if cname=="allies_count_at_least": return len(s.alive(self_l.side))>=cp.get("value",0)
        if cname=="self_is_fastest":
            return self_l.eff_spd()>=max(l.eff_spd() for l in s.all_leaders())
        if cname=="self_is_slowest":
            return self_l.eff_spd()<=min(l.eff_spd() for l in s.all_leaders())
        if cname=="target_hp_above_self":
            t=ctx.get("target"); return t is not None and t.hp>self_l.hp
        if cname=="allies_with_hp_above_at_least":
            n=sum(1 for l in s.alive(self_l.side) if l.hp>cp.get("value",0)); return n>=cp.get("count",0)
        if cname=="self_damage_this_turn_above": return self_l.dmg_turn>cp.get("value",0)
        if cname=="ctx_status_equals": return ctx.get("status_id")==cp.get("status_id")
        if cname=="ctx_status_in": return ctx.get("status_id") in cp.get("status_ids",[])
        if cname=="ctx_is_enemy":
            t=ctx.get(cp.get("key","")); return t is not None and t.side!=self_l.side
        if cname=="ctx_flag": return bool(ctx.get(cp.get("key","")))
        if cname in("drawn_card_has_tag","ctx_card_has_any_tag"):
            card=ctx.get("card");
            if card is None: return False
            tags=cp.get("tags",[]) or [cp.get("tag","")]
            return any(name_has_tag(card["name"],t) for t in tags)
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
            t=ctx.get("target"); return t is not None and any(name_has_tag(t.name,tg) for tg in cp.get("tags",[]))
        if cname=="allies_count_at_most": return len(s.alive(self_l.side))<=cp.get("value",1)
        if cname=="enemy_has_status":
            return any(cp.get("status_id") in f.st for f in s.alive(s.enemy_side(self_l.side)))
        if cname=="leaders_with_tag_at_least":
            return sum(1 for l in s.all_leaders() if name_has_tag(l.name,cp.get("tag","")))>=cp.get("value",1)
        if cname=="fallen_has_tag":
            f=ctx.get("fallen"); return f is not None and name_has_tag(f.name,cp.get("tag",""))
        if cname=="fallen_has_any_tag":
            f=ctx.get("fallen"); return f is not None and any(name_has_tag(f.name,tg) for tg in cp.get("tags",[]))
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
            return any(name_has_tag(l.name,cp.get("tag","")) and cp.get("status_id") in l.st for l in pool)
        if cname=="side_has_any_tag":
            return any(any(name_has_tag(a.name,t) for t in cp.get("tags",[])) for a in s.alive(self_l.side))
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
            t=ctx.get("target"); return t is not None and name_has_tag(t.name,cp.get("tag",""))
        if cname=="target_has_status_any":
            t=ctx.get("target"); return t is not None and any(sd in t.st for sd in cp.get("status_ids",[]))
        if cname=="attacker_has_tag":
            a=ctx.get("attacker"); return a is not None and name_has_tag(a.name,cp.get("tag",""))
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
            l=_ctxl(cp.get("key","attacker")); return l is not None and name_has_tag(l.name,cp.get("tag",""))
        if cname=="ctx_has_any_tag":
            l=_ctxl(cp.get("key","attacker")); return l is not None and any(name_has_tag(l.name,t) for t in cp.get("tags",[]))
        if cname=="ctx_stat_equals": return str(ctx.get("stat",""))==str(cp.get("stat",""))
        if cname=="ctx_amount_at_least": return ctx.get("amount",0)>=cp.get("value",0)
        if cname=="ctx_amount_equals": return ctx.get("amount",0)==cp.get("value",0)
        if cname=="ctx_card_has_tag":
            card=ctx.get("card"); return card is not None and name_has_tag(card["name"],cp.get("tag",""))
        if cname=="no_supporters_drawn": return s.drawn[self_l.side]==0
        if cname=="opp_no_supporters_drawn": return s.drawn[s.enemy_side(self_l.side)]==0
        if cname=="this_turn_self_drew_at_least": return s.drawn[self_l.side]>=cp.get("value",1)
        if cname=="this_turn_opp_drew_at_least": return s.drawn[s.enemy_side(self_l.side)]>=cp.get("value",1)
        if cname=="last_turn_self_drew_at_least": return s.drawn_last[self_l.side]>=cp.get("value",1)
        if cname=="last_turn_self_drew_none": return s.drawn_last[self_l.side]==0
        if cname=="last_turn_opp_drew_at_least": return s.drawn_last[s.enemy_side(self_l.side)]>=cp.get("value",1)
        if cname=="last_turn_opp_drew_none": return s.drawn_last[s.enemy_side(self_l.side)]==0
        UNIMPL.add("cond:"+cname); return False
    # ---- effects ----
    def run_effect(s, self_l, eff, p, ctx):
        if not eff: return
        if eff=="multi_effect":
            for e in p.get("effects",[]): s.run_effect(self_l,e["effect"],e.get("params",{}),ctx)
            return
        if eff=="gain_stat": s.mod(self_l,p["stat"],p.get("amount",0)); return
        if eff=="lose_stat": s.mod(self_l,p["stat"],-p.get("amount",0)); return
        if eff in("gain_stat_target","lose_stat_target"):
            t=s.sel(self_l,p.get("target",""),ctx);
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
                if (not tags) or any(name_has_tag(l.name,t) for t in tags): s.mod(l,p["stat"],p.get("amount",0))
            return
        if eff=="lose_stat_all_allies":
            for l in s._ally_pool(self_l,p): s.mod(l,p["stat"],-p.get("amount",0))
            return
        if eff=="gain_stat_allies_with_status":
            sid=p.get("status_id") or p.get("has_status","")
            for l in s.alive(self_l.side):
                if (not sid) or sid in l.st: s.mod(l,p["stat"],p.get("amount",0))
            return
        if eff=="damage_target":
            t=s.sel(self_l,p.get("target","self"),ctx)
            if t is not None:
                t.hp-=min(t.hp,max(0,p.get("amount",0)))
                s.checkdeath(self_l)
            return
        if eff=="damage_all_enemies":
            amt=p.get("amount",0)
            if amt>0:
                for l in s.alive(s.enemy_side(self_l.side)): l.hp-=min(l.hp,amt)
                s.checkdeath(self_l)
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
            if self_l.hp>0: self_l.hp=0
            s.checkdeath(); return
        if eff=="set_stat":
            v=p.get("value",0); stt=p.get("stat","")
            if stt=="health": self_l.hp=min(self_l.mhp,v)
            elif stt=="attack": self_l.atk=max(0,min(MAXATK,v))
            elif stt=="defense": self_l.dfn=max(0,v)
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
                if (not tags) or any(name_has_tag(l.name,t) for t in tags):
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
                if (not tags) or any(name_has_tag(l.name,t) for t in tags): s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_all_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            for l in s.all_leaders():
                if (not tags) or any(name_has_tag(l.name,t) for t in tags): s.inflict(l,p.get("status_id"),self_l)
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
            for l in s.all_leaders(): s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_allies_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            for l in s.alive(self_l.side):
                if (not tags) or any(name_has_tag(l.name,t) for t in tags):
                    s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="inflict_status_filtered":
            for l in s._filtered(self_l,p.get("side","enemy"),p.get("filter",{})):
                s.inflict(l,p.get("status_id"),self_l)
            return
        if eff=="cleanse_status":
            t=s.sel(self_l,p.get("target","self"),ctx); s.cleanse(t,p.get("status_id")); return
        if eff=="survive_at_1": return  # handled in take_damage
        if eff=="schedule_next_turn":
            s.pending.append({"leader":self_l,"effect":p.get("effect"),"params":p.get("params",{})}); return
        if eff=="lose_stat_all_enemies":
            for l in s.alive(s.enemy_side(self_l.side)): s.mod(l,p["stat"],-p.get("amount",0))
            return
        if eff=="gain_stat_per_leader_with_tag":
            tags=p.get("tags") or ([p["tag"]] if p.get("tag") else [])
            scope=p.get("scope","all")
            pool=s.alive(self_l.side) if scope=="ally" else s.alive(s.enemy_side(self_l.side)) if scope=="enemy" else s.all_leaders()
            amt=p.get("amount",0); tot=sum(amt for l in pool if any(name_has_tag(l.name,str(t)) for t in tags))
            if tot>0: s.mod(self_l,p["stat"],tot)
            return
        if eff=="gain_stat_per_ally_alive":
            tot=p.get("amount",0)*len(s.alive(self_l.side))
            if tot>0: s.mod(self_l,p["stat"],tot)
            return
        if eff in("gain_stat_filtered","lose_stat_filtered"):
            sign=1 if eff.startswith("gain") else -1
            for l in s._filtered(self_l,p.get("side","ally"),p.get("filter",{})):
                s.mod(l,p["stat"],sign*p.get("amount",0))
            return
        if eff=="damage_filtered":
            amt=p.get("amount",0)
            if amt>0:
                for l in s._filtered(self_l,p.get("side","enemy"),p.get("filter",{})): l.hp-=amt
                s.checkdeath(self_l)
            return
        if eff=="gain_stat_per_leader_with_status":
            sid=p.get("status_id","")
            side=p.get("side","all")
            pool=s.alive(self_l.side) if side=="ally" else s.alive(s.enemy_side(self_l.side)) if side=="enemy" else s.all_leaders()
            n=sum(1 for l in pool if (sid and sid in l.st) or (not sid and l.st))
            if n>0: s.mod(self_l,p["stat"],p.get("amount",0)*n)
            return
        if eff=="draw2_hat_chain":
            cards2=[]
            for _ in range(2):
                c2=s._draw_single(self_l)
                if c2 is not None: cards2.append(c2)
            if not any(name_has_tag(c2["name"],"hat") for c2 in cards2): return
            enemies=s.alive(s.enemy_side(self_l.side))
            if not enemies: return
            slow=min(enemies,key=lambda l:l.eff_spd())
            slow.hp-=min(slow.hp,22)
            if slow.hp<=0: s.checkdeath(self_l); return
            if slow.hp<150:
                s.inflict(slow,"poisoned",self_l); s.inflict(slow,"paralyzed",self_l)
                if slow.eff_def()<20:
                    s.inflict(slow,"weak",self_l)
                    s.mod(slow,"attack",-10)
            return
        if eff=="draw_supporter":
            for _ in range(p.get("count",1)):
                if s._draw_single(self_l) is None: break
            return
        if eff=="draw_supporter_per_ally_with_tag":
            tag=p.get("tag",""); cnt=p.get("count",1)
            n=sum(1 for a in s.alive(self_l.side) if tag=="" or name_has_tag(a.name,tag))
            for _ in range(n*cnt):
                if s._draw_single(self_l) is None: break
            return
        if eff=="draw_supporter_per_enemy_with_tag":
            tag=p.get("tag",""); cnt=p.get("count",1)
            n=sum(1 for a in s.alive(s.enemy_side(self_l.side)) if name_has_tag(a.name,tag))
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
                if (not tags) or any(name_has_tag(card["name"],t) for t in tags):
                    th=p.get("then",{})
                    if th: s.run_effect(self_l,th.get("effect",""),th.get("params",{}),ctx)
            return
        if eff=="draw_supporter_with_tag_status":
            card=s._draw_single(self_l)
            tags=p.get("tags",[]) or ([p["tag"]] if p.get("tag") else [])
            sid=p.get("status_id","")
            if card is not None and sid and ((not tags) or any(name_has_tag(card["name"],t) for t in tags)):
                for al in s.alive(self_l.side): s.inflict(al,sid,self_l)
            return
        if eff=="draw_supporter_or_penalty":
            cnt=p.get("count",1); tags=p.get("tags",[]); pen=p.get("penalty",{}); had=(not tags)
            for _ in range(cnt):
                card=s._draw_single(self_l)
                if card is None: break
                if tags and any(name_has_tag(card["name"],t) for t in tags): had=True
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
            if "tag" in filt and not name_has_tag(l.name,filt["tag"]): continue
            if "tags" in filt and not any(name_has_tag(l.name,t) for t in filt["tags"]): continue
            if "has_status" in filt and filt["has_status"] not in l.st: continue
            if "hp_min" in filt and l.hp<filt["hp_min"]: continue
            if "hp_max" in filt and l.hp>filt["hp_max"]: continue
            out.append(l)
        return out
    def _draw_single(s, owner):
        deck=s.decks[owner.side]; disc=s.disc[owner.side]
        if not deck:
            if not disc: return None
            s.rng.shuffle(disc); deck.extend(disc); disc.clear()
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
        if not force and not l.alive: return
        s.chain+=1
        try: s._fire_inner(l,trig,ctx)
        finally: s.chain-=1
    def _fire_inner(s, l, trig, ctx):
        for i,a in enumerate(l.abil):
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
    # ---- attack ----
    def dmg_bonus(s, atk, tgt):
        tot=0; ctx={"target":tgt,"attacker":atk}
        for a in atk.abil:
            if a.get("trigger")!="passive_damage_bonus": continue
            if not s.cond(atk,a.get("condition",""),a.get("cond_params",{}),ctx): continue
            p=a.get("params",{})
            tot+=p.get("amount",0)
            tot+=p.get("per_self_status",0)*len(atk.st)
            if tgt is not None: tot+=p.get("per_target_status",0)*len(tgt.st)
        return tot
    def resolve(s, atk, tgt):
        if not atk.alive or tgt is None or not tgt.alive: return
        s.broadcast("on_any_attack",{"attacker":atk,"target":tgt})
        s.broadcast("on_any_attacked",{"attacked":tgt,"attacker":atk,"target":tgt})
        if not atk.alive or not tgt.alive: return
        if atk.flag("dizzy") and s.rng.random()<0.5:
            s.fire(atk,"on_attack",{"target":tgt,"damage":0,"missed":True})
            s.fire(atk,"on_blocked_or_dodged",{"target":tgt})
            return
        dmg=atk.atk
        em=elem_mult(atk.elem,tgt.elem,tgt.apex)
        if abs(em-1.0)>1e-9: dmg=max(0,int(round(dmg*em)))
        crit=0.1*(2 if atk.flag("doubles_crit") else 1)
        if s.rng.random()<crit:
            dmg+=5; s.fire(atk,"on_crit",{"target":tgt})
            for al in s.alive(atk.side): s.fire(al,"on_ally_crit",{"crit_leader":atk,"target":tgt})
        dmg=max(0,dmg+s.dmg_bonus(atk,tgt))
        dfv=tgt.eff_def()
        dodge=(dfv/4.0)/100.0; block=(dfv/2.0)/100.0
        pd=sum(a.get("params",{}).get("amount",0)/100.0 for a in tgt.abil if a.get("trigger")=="passive_dodge")
        dodge=min(0.95,dodge+pd)
        if atk.has_passive("passive_unblockable"): dodge=block=0.0
        blocks_disabled=tgt.flag("blocks_block")
        roll=s.rng.random()
        dodged=(not blocks_disabled) and roll<dodge
        blocked=(not dodged) and (not blocks_disabled) and roll<(dodge+block)
        if not dodged:                     # passive_force_dodge (optionally once/game, optional stat gain)
            for a in tgt.abil:
                if a.get("trigger")!="passive_force_dodge": continue
                kk=(id(a),)
                if a.get("once_game") and kk in tgt.og: continue
                dodged=True; blocked=False
                if a.get("once_game"): tgt.og.add(kk)
                p=a.get("params",{})
                if "stat" in p: s.mod(tgt,p["stat"],p.get("amount",0))
                break
        s.fire(atk,"on_attack",{"target":tgt,"damage":0 if dodged else dmg})
        if dodged:
            s.fire(atk,"on_blocked_or_dodged",{"target":tgt})
            s.fire(tgt,"on_attacked",{"attacker":atk,"dodged":True,"blocked":False,"damage":0,"dodged_flag":True})
            return
        if blocked: dmg//=2; s.fire(atk,"on_blocked_or_dodged",{"target":tgt})
        if not atk.alive or not tgt.alive: return
        pre=tgt.hp
        actual=min(pre,dmg)
        tgt.hp-=dmg; tgt.dmg_turn+=actual
        # element recoil: Blobgob(2) attacking Monblonkin(5) recoils 0.3*base_atk
        if atk.elem==2 and tgt.elem==5:
            atk.hp-=int(round(atk.atk*0.3))
        # curse recoil on attacker (fraction of actual damage dealt)
        for sid in atk.st:
            fr=STA[sid][2].get("recoil")
            if fr: atk.hp-=int(actual*fr)
        survived = tgt.hp>0
        # on_miracle survive_at_1
        if tgt.hp<=0:
            for a in tgt.abil:
                if a.get("trigger")=="on_miracle" and a.get("effect")=="survive_at_1":
                    kk=(id(a),)
                    if not (a.get("once_game") and kk in tgt.og):
                        tgt.hp=1; tgt.og.add(kk); survived=True
                        s.fire(tgt,"on_miracle",{"attacker":atk})  # fire the paired buff
                        break
        if tgt.hp<=0:
            s.die(tgt,atk,is_attack=True)
        else:
            s.fire(tgt,"on_attacked",{"attacker":atk,"damage":actual,"blocked":blocked,"dodged":False})
            s.fire(tgt,"on_damaged",{"attacker":atk,"damage":actual})
            s.fire(tgt,"on_survive",{"attacker":atk})
        if atk.hp<=0: s.checkdeath()
    def _ally_pool(s, self_l, p):     # allies, optionally excluding the caster (exclude_self param)
        pool=s.alive(self_l.side)
        return [a for a in pool if a is not self_l] if p.get("exclude_self") else pool
    def pick_target(s, atk):
        enemies=s.alive(s.enemy_side(atk.side))
        if any(STA[x][2].get("targets_all") for x in atk.st):   # chaos: attack all leaders except self
            enemies=[l for l in s.alive(atk.side) if l is not atk]+enemies
        if not enemies: return None
        style=atk.d.get("style",1)
        for a in atk.abil:
            if a.get("trigger")=="passive_target_style": style=a.get("params",{}).get("style",style)
        if style==1: return s.rng.choice(enemies)
        keyf={2:lambda l:l.eff_spd(),3:lambda l:l.eff_spd(),4:lambda l:l.hp,5:lambda l:l.hp,
              6:lambda l:l.eff_def(),7:lambda l:l.eff_def(),8:lambda l:l.atk,9:lambda l:l.atk}[style]
        hi= style in(2,4,7,8)
        return (max if hi else min)(enemies,key=keyf)
    def run_turn(s):
        # pending
        for pe in s.pending:
            if pe["leader"].alive: s.run_effect(pe["leader"],pe["effect"],pe["params"],{})
        s.pending=[]
        for l in s.all_leaders(): l.dmg_turn=0; l.ot_turn=set()
        for l in list(s.all_leaders()): s.tick_statuses(l)
        s.checkdeath()
        order=sorted(s.all_leaders(),key=lambda l:-l.eff_spd())
        for l in order:
            if l.alive: s.fire(l,"turn_start",{})
        order=sorted(s.all_leaders(),key=lambda l:-l.eff_spd())
        for atk in order:
            if not atk.alive: continue
            if atk.flag("blocks_attack"): continue
            tgt=s.pick_target(atk)
            if tgt is None: continue
            s.resolve(atk,tgt)          # dizzy-miss handled inside (fires miss triggers)
            if s.over(): return
            if atk.alive and "tired" not in atk.st:      # _mark_attacked: silent, no triggers
                atk.st["tired"]=[STA["tired"][0],0]
        order=sorted(s.all_leaders(),key=lambda l:-l.eff_spd())
        for l in order:
            if l.alive: s.fire(l,"turn_end",{})
        for l in s.teams[0]+s.teams[1]:                  # end-of-turn stat reverts
            for m in getattr(l,"eot",[]):
                if m["stat"]=="attack": l.atk=max(0,min(MAXATK,l.atk+m["amount"]))
                elif m["stat"]=="defense": l.dfn=max(0,l.dfn+m["amount"])
                elif m["stat"]=="speed": l.spd=max(0,l.spd+m["amount"])
                elif m["stat"]=="health": l.hp=min(l.mhp,l.hp+m["amount"]) if m["amount"]>0 else l.hp+m["amount"]
            l.eot=[]
        s.checkdeath()
    def over(s): return not s.alive(0) or not s.alive(1)
    def run(s, deckA, deckB, verbose=False):
        s.verbose=verbose
        s.teams=[[],[]]
        for i,c in enumerate(deckA[:3]): s.teams[0].append(L(c,0,i))
        for i,c in enumerate(deckB[:3]): s.teams[1].append(L(c,1,i))
        if len(deckB)<4:  # CPU gets 4 seeded supporters in-game; approximate by sampling the pool
            eids={c.get("id") for c in deckB[:3]}
            pool=[i for i in ENEMY_SUPP_POOL if i not in eids]
            deckB=list(deckB)+[LEADERS[i] for i in s.rng.sample(pool,4)]
        s.decks=[ [dict(x) for x in deckA[3:7]], [dict(x) for x in deckB[3:7]] ]
        s.disc=[[],[]]
        for side in (0,1): s.rng.shuffle(s.decks[side])
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

def player_deck(ids, supporters=()):
    d=[apply_player_level(LEADERS[i]) for i in ids]
    for i in supporters: d.append(dict(LEADERS[i]))  # supporters: only .supporter ability matters
    return d
# story-exclusive/spoiler subjects excluded from the CPU supporter pool (skin_manager)
STORY_EXCL={506,510,531,541,545,561,565,570,594,601,615,616,617,635,645,646,647}
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
