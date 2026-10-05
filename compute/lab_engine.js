// Battle engine - direct port of sim.py (itself a replica of decompiled battle_sim.gd)
"use strict";
const RULES=[
 {eff:[[1,1.4]],neff:[[3,0.4]],res:[[4,0.9]],weak:[[2,1.1]]},
 {eff:[[2,1.4]],neff:[[4,0.6]],res:[[3,0.95]],weak:[[5,1.05]]},
 {eff:[[3,1.8]],neff:[[5,0.1]],res:[[0,0.75]],weak:[[4,1.25]]},
 {eff:[[4,1.8]],neff:[[0,0.2]],res:[[1,0.85]],weak:[[5,1.15]]},
 {eff:[[5,1.2],[1,1.4]],neff:[],res:[[0,0.95]],weak:[[2,1.05]]},
 {eff:[[0,1.2]],neff:[[2,0.8]],res:[[3,0.8]],weak:[[1,1.2]]},
];
const CHART=Array.from({length:6},()=>Array(6).fill(1.0));
for(let e=0;e<6;e++){
  for(const[t,m]of RULES[e].eff)CHART[e][t]=m;
  for(const[t,m]of RULES[e].neff)CHART[e][t]=m;
  for(const[t,m]of RULES[e].res)CHART[t][e]=m;
  for(const[t,m]of RULES[e].weak)CHART[t][e]=m;
}
function catWeak(a,d){for(const[t,]of RULES[d].weak)if(t===a)return true;return false;}
function elemMult(a,d,apex){if(a<0||d<0)return 1.0;if(apex&&catWeak(a,d))return 1.0;return CHART[a][d];}
// STA-BEGIN  DATA_STATUSES: generated from cards.json by gen_js_sta.py (game StatusDef table). Do not hand-edit.
const STA={"chaos":[4,[],{"targets_all":true}],"chaos_blinded":[3,[],{"targets_all":true,"random_attack_style":true,"replaces_status_ids":["chaos"]}],"infected":[4,[{"attack":-5,"speed":-10,"defense":-3},{"attack":-8,"speed":-30,"defense":-6},{"attack":-12,"speed":-60,"defense":-12},{"attack":-15,"speed":-200,"defense":-20}],{}],"soul_bound":[3,[{},{},{"health":-300}],{"hp_floor_1":true}],"soul_protected":[5,[],{"blocks_status_ids":["soul_bound","cursed","stunned","doomed","chaos","chaos_blinded","infected"]}],"jackified":[2,[],{"shares_attack_style":true,"unique_per_team":true}],"horrified":[1,[],{"weak_hit_chance":0.25,"weak_hit_mult":0.2,"weak_needs_stronger_target":true}],"confused":[1,[],{"fizzle_chance":0.1,"fizzle_self_frac":0.3333333333333333}],"very_confused":[1,[],{"fizzle_chance":0.35,"fizzle_self_frac":0.5}],"on_fire":[5,[{"health":-10},{"health":-10},{"health":-10},{"health":-10},{"health":-10}],{}],"poisoned":[5,[{"health":-5},{"health":-15},{"health":-25},{"health":-15},{"health":-5}],{}],"bleeding":[7,[{"health":-5,"defense":-2},{"health":-5,"defense":-2},{"health":-5,"defense":-2},{"health":-5,"defense":-2},{"health":-5,"defense":-2},{"health":-5,"defense":-2},{"health":-5,"defense":-2}],{}],"doomed":[5,[{},{},{},{},{"health":-200}],{}],"blessed":[3,[{"health":5},{"health":15},{"health":20}],{}],"ice_burn":[3,[{"health":-10,"speed":-30},{"health":-10,"speed":-45},{"health":-5,"speed":-100}],{}],"stunned":[1,[{}],{"blocks_attack":true}],"paralyzed":[1,[{"health":-7}],{"blocks_attack":true}],"weak":[1,[{}],{"blocks_block":true}],"slow":[1,[{}],{"override_speed":1}],"frozen":[2,[{},{}],{"override_speed":50}],"strengthened":[1,[{}],{"force_defense":50}],"lucky":[1,[{}],{"doubles_crit":true}],"purified":[2,[{},{}],{"blocks_other":true}],"dizzy":[1,[{}],{"dizzy":true}],"tired":[1,[{}],{"blocks_attack":true}],"cursed":[2,[{},{}],{"recoil":0.3333333333333333}],"stinky":[2,[{"defense":-5,"speed":-20},{"defense":-5,"speed":-20,"attack":5}],{}],"burnout":[3,[{"speed":-50},{"speed":-100},{"speed":-300}],{}]};
// STA-END
const TURN_ONLY=["tired","stunned","paralyzed"];      // RuntimeLeader.TURN_ONLY_STATUSES: cleared at every turn end
const BUFF_STATUSES=["blessed","lucky","strengthened","purified","soul_protected","tired"];   // battle_sim._BUFF_STATUSES
const STYLE_FLIP={2:3,3:2,4:5,5:4,6:7,7:6,8:9,9:8};
const STYLE_ALL=10;                                   // BattleEnums.AttackStyle.ALL: hits every leader in the target pool
const MAXHP=999,MAXATK=199,MINATK=1,DEFCAP=50,OVERHEAL=1.2;
const _own=Object.prototype.hasOwnProperty;
function hasSta(sid){return typeof sid==="string"&&_own.call(STA,sid);}
function staF(sid){return hasSta(sid)?STA[sid][2]:{};}
function _rnd(x){return x>=0?Math.floor(x+0.5):-Math.floor(-x+0.5);}   // GDScript round(): half away from zero
function _g(o,k,d){const v=o?o[k]:undefined;return v===undefined?d:v;}    // python dict.get(k,d)
function _i(v){return Math.trunc(Number(v)||0);}                          // python int()
function _has(o,k){return !!o&&_own.call(o,k);}                           // python `k in dict`
function mulberry32(seed){let a=seed>>>0;return function(){a|=0;a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296;};}
function nameWords(nm){return nm.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);}
function nameHasTag(nm,tag){
  if(!tag)return false;
  const nw=nameWords(nm),ks=tag.toLowerCase().split(" ").filter(Boolean),k=ks.length;
  if(!k)return false;
  for(let i=0;i<=nw.length-k;i++){
    let ok=true;
    for(let j=0;j<k;j++){const w=nw[i+j],t=ks[j];if(w!==t&&!(j===k-1&&w===t+"s")){ok=false;break;}}
    if(ok)return true;
  }
  return false;
}
function defHasTag(d,tag){   // LeaderDef.has_tag: name keyword OR an ability's extra_tags (case-insensitive)
  if(!d)return false;
  if(nameHasTag(d.name||"",tag))return true;
  const low=String(tag||"").toLowerCase();
  if(!low)return false;
  for(const a of d.abilities||[])
    for(const t of ((a&&a.params)||{}).extra_tags||[])if(String(t).toLowerCase()===low)return true;
  return false;
}
// skin_manager.stats_at_level. Season 2 raised MAX_SKIN_LEVEL to 20 (story caps S1=15, S2=20); ability2 unlocks at level 2
const LEVEL_GAINS={3:["spd",10],4:["def",5],5:["hp",10],6:["atk",3],7:["spd",15],8:["def",6],9:["hp",15],10:["atk",5],
  11:["spd",20],12:["def",7],13:["hp",20],14:["atk",7],15:["spd",25],16:["def",8],17:["hp",25],18:["atk",8],19:["spd",30],20:["hp",27]};
function applyPlayerLevel(card,lvl){
  lvl=Math.max(1,Math.min(20,Math.trunc(Number(lvl==null?10:lvl))||1));
  const b={hp:0,atk:0,spd:0,def:0};
  for(let lv=2;lv<=lvl;lv++){const s=LEVEL_GAINS[lv];if(s)b[s[0]]+=s[1];}
  const c=Object.assign({},card,{hp:Math.min(MAXHP,card.hp+b.hp),atk:Math.min(MAXATK,card.atk+b.atk),
    spd:card.spd+b.spd,def:Math.min(50,card.def+b.def),level:lvl});
  // skin_manager.get_cumulative_stats unlocks ability2 at level 2 (NOT 10), and
  // story_hub._apply_level_bonuses keeps abilities[0] plus the rest once unlocked
  if(lvl<2)c.abilities=(card.abilities||[]).slice(0,1);
  return c;
}
function enemyLevelBonus(lvl,season=1){   // story_hub._enemy_level_bonus -> [hp, spd, def, atk]
  if(season>=2&&lvl>=8){const n=lvl-8;return[50+17*n,70+15*n,10+n,15+4*n];}   // S2_BASE_LEVEL=8, S2_BASE + n*S2_STEP
  const k=lvl-1;return[18*k,8*k,2*k,4*k];
}
// battle deck (story_hub._build_cpu_deck) always uses the S1 per-level curve; the S2 curve is preview-only
function applyEnemyLevel(card,lvl,season=1){
  const c=Object.assign({},card);
  if(lvl>1){
    const[h,sp,d,a]=enemyLevelBonus(lvl,1);
    c.hp=Math.min(MAXHP,card.hp+h);c.spd=card.spd+sp;
    c.def=Math.min(50,card.def+d);c.atk=Math.min(MAXATK,card.atk+a);
  }
  c.level=lvl;
  return c;
}
class RL{ // runtime leader
  constructor(d,side,slot){
    this.d=d;this.side=side;this.slot=slot;
    this.hp=d.hp;this.mhp=d.hp;this.atk=d.atk;this.dfn=d.def;this.spd=d.spd;
    this.elem=d.element==null?-1:d.element;this.apex=!!d.apex;
    this.abil=d.abilities||[];this.name=d.name;this.lvl=d.level||1;
    this.allReadyTurn=0;   // RuntimeLeader.all_ready_turn (passive_all_cooldown, v183)
    this.pendingBonus=0;   // RuntimeLeader.pending_bonus_damage (gamble_attack jackpot, applied to the current hit)
    this.st=Object.create(null);   // status_id -> [remaining, tick_index]; insertion order == the game's statuses list order
    this.og=new Set();this.ot=new Set();this.dmgTurn=0;this.alive=true;this.announced=false;this.eot=[];
    this.waThis=false;this.waLast=false;this.turnNow=0;this.styleOverride=0;this.hitsTurn=0;this.echoGuard=false;
  }
  effDef(){   // RuntimeLeader.effective_defense: the FIRST status with force_defense wins; capped at 50
    for(const sid in this.st){const v=staF(sid).force_defense;if(v!=null&&v>=0)return Math.min(v,DEFCAP);}
    return Math.min(this.dfn,DEFCAP);
  }
  effSpd(){   // effective_speed: the FIRST status with override_speed wins
    for(const sid in this.st){const v=staF(sid).override_speed;if(v!=null&&v>=0)return v;}
    return this.spd;
  }
  flag(n){for(const sid in this.st)if(staF(sid)[n])return true;return false;}
  immune(sid){   // RuntimeLeader.is_immune_to (also_immune on any ability; passive_immunity may be turn-gated)
    for(const a of this.abil){
      const p=a.params||{};
      for(const x of p.also_immune||[])if(x==="all"||x===sid)return true;
      if(a.trigger==="passive_immunity"){
        const turns=p.turns||[];
        if(turns.length&&!turns.includes(this.turnNow))continue;
        const x=_g(p,"status_id","");
        if(x==="all"||x===sid)return true;
        for(const y of p.status_ids||[])if(y==="all"||y===sid)return true;
      }
    }
    return false;
  }
  hasPassive(t){return this.abil.some(a=>a.trigger===t);}
  hasTag(tag){return defHasTag(this.d,tag);}
  hasHpFloor(){for(const sid in this.st)if(staF(sid).hp_floor_1)return true;return false;}
  takeDamage(amount){   // RuntimeLeader.take_damage: hp floor (soul_bound), marks dead immediately
    if(!(amount>0))return 0;
    let taken=Math.min(this.hp,amount);
    if(this.hasHpFloor()&&taken>=this.hp)taken=Math.max(0,this.hp-1);
    this.hp-=taken;this.dmgTurn+=taken;
    if(this.hp<=0){this.hp=0;this.alive=false;}
    return taken;
  }
}
class Sim{
  constructor(seed,log,story=true){this.story=story;this.rng=mulberry32(seed);this.turn=0;this.teams=[[],[]];this.depth=0;this.pending=[];this.log=log||null;
    this.chainD=0;this.drawn=[0,0];this.drawnLast=[0,0];this._statGainBySupporter=false;
    this.shuf=[mulberry32((seed^0x9E3779B9)>>>0),mulberry32((seed^0x85EBCA6B)>>>0)];}  // per-side deck shuffle, decoupled from battle RNG
  L(msg){if(this.log)this.log.push(msg);}
  choice(arr){return arr[Math.floor(this.rng()*arr.length)];}
  randint(a,b){return a+Math.floor(this.rng()*(b-a+1));}
  shuffle(arr,rng){rng=rng||this.rng;for(let i=arr.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[arr[i],arr[j]]=[arr[j],arr[i]];}}
  enemySide(s){return 1-s;}
  alive(s){return this.teams[s].filter(l=>l.alive);}
  allL(){return this.teams[0].concat(this.teams[1]).filter(l=>l.alive);}
  everyL(){return this.teams[0].concat(this.teams[1]);}
  // ---- status ----
  durMult(t,sid){   // RuntimeLeader._status_duration_mult
    for(const a of t.abil)
      if(a.trigger==="passive_status_duration"&&((a.params||{}).status_ids||[]).includes(sid))return _i(_g(a.params,"mult",2));
    return 1;
  }
  applyStatus(t,sid){   // RuntimeLeader.apply_status (raw: no blocks/unique/replacement/triggers)
    if(!t||!hasSta(sid))return false;
    if(sid!=="purified"&&t.immune(sid))return false;
    for(const x in t.st)if(staF(x).blocks_other&&sid!==x)return false;
    if(sid in t.st){t.st[sid]=[STA[sid][0]*this.durMult(t,sid),0];return false;}   // refresh, NO trigger
    t.st[sid]=[STA[sid][0]*this.durMult(t,sid),0];
    return true;
  }
  _replace(t,sid){   // _enforce_replacements: drop statuses this one overrides
    const reps=staF(sid).replaces_status_ids||[];
    for(const x of Object.keys(t.st))if(x!==sid&&reps.includes(x))delete t.st[x];
  }
  inflict(t,sid,src,notify=true){   // battle_sim._apply_status_notify
    if(!t||!hasSta(sid))return false;
    if(!notify){const ok=this.applyStatus(t,sid);if(ok)this.L(`    ${t.name} → [${sid}]`);return ok;}
    for(const x in t.st)if((staF(x).blocks_status_ids||[]).includes(sid))return false;   // _status_blocked (soul_protected)
    if(staF(sid).unique_per_team)                      // _enforce_unique_per_team runs BEFORE apply, even if it fails
      for(const o of this.alive(t.side))if(o!==t&&(sid in o.st))delete o.st[sid];
    if(!this.applyStatus(t,sid)){
      if(sid in t.st)this._replace(t,sid);
      return false;
    }
    this._replace(t,sid);
    this.L(`    ${t.name} → [${sid}]`);
    if(TURN_ONLY.includes(sid)){                        // turn-only statuses tick once immediately on inflict
      const e=t.st[sid],dl=STA[sid][1],dd=e[1]<dl.length?dl[e[1]]:{};
      e[1]++;e[0]--;
      if(dd&&Object.keys(dd).length)this.applyStatDeltas(t,dd);   // no death check here (game: silent death possible)
    }
    if(this.depth<24){this.depth++;this.fire(t,"on_status_applied",{affected:t,status_id:sid});this.depth--;}
    this.broadcast("on_any_status_applied",{affected:t,status_id:sid});
    return true;
  }
  cleanse(t,sid){if(t&&(sid in t.st))delete t.st[sid];}
  // ---- death ----
  die(v,killer,isAtk){   // battle_sim._kill + _handle_death_ripple
    v.alive=false;v.hp=0;
    if(v.announced)return;
    v.announced=true;
    this.L(`    💀 ${v.name} died`);
    this.fire(v,"on_death",{killer:killer||null},true);
    if(isAtk&&killer){
      this.fire(killer,"on_kill",{victim:v});
      this.broadcast("on_any_kill",{killer,victim:v});
    }
    this.broadcast("on_any_death",{fallen:v});
    const living=this.alive(v.side);
    for(const al of living)this.fire(al,"on_ally_killed",{fallen:v});
    if(living.length===1)this.fire(living[0],"on_last_standing",{fallen:v});
  }
  checkDeath(l,killer,isAtk){   // battle_sim._check_death
    if(l&&(!l.alive||l.hp<=0)&&!l.announced)this.die(l,killer,isAtk);
  }
  sweep(killer,isAtk){   // sweep, for effects that can kill several leaders
    for(const l of this.everyL())if((!l.alive||l.hp<=0)&&!l.announced)this.die(l,killer,isAtk);
  }
  // ---- ticks / stat changes ----
  applyStatDeltas(l,d){   // battle_sim._apply_stat_deltas (heal caps at max_hp; attack floor 0; no death check)
    if(!d)return;
    if(_has(d,"health")){const a=_i(d.health);if(a<0)l.takeDamage(-a);else l.hp=Math.min(l.hp+a,l.mhp);}
    if(_has(d,"attack"))l.atk=Math.max(0,Math.min(MAXATK,l.atk+_i(d.attack)));
    if(_has(d,"defense"))l.dfn=Math.max(0,Math.min(DEFCAP,l.dfn+_i(d.defense)));
    if(_has(d,"speed"))l.spd=Math.max(0,l.spd+_i(d.speed));
  }
  tickStatuses(l){   // RuntimeLeader.tick_statuses: sum this tick's deltas and advance. NO removal.
    const tot={};
    for(const sid of Object.keys(l.st)){
      const e=l.st[sid],dl=STA[sid][1],d=e[1]<dl.length?dl[e[1]]:{};
      for(const k in d)tot[k]=(tot[k]||0)+_i(d[k]);
      e[1]++;e[0]--;
    }
    return tot;
  }
  sweepExpired(l){   // end of turn: clear_turn_markers + sweep_expired_statuses
    for(const sid of Object.keys(l.st))if(TURN_ONLY.includes(sid)||l.st[sid][0]<=0)delete l.st[sid];
  }
  mod(l,stat,amt){   // battle_sim._modify_stat
    if(stat==="health"){
      if(amt<0)l.takeDamage(-amt);
      else l.hp=Math.min(l.hp+amt,Math.floor(l.mhp*OVERHEAL));   // overheal up to 120% max hp
    }else if(stat==="attack"){
      l.atk=Math.max(MINATK,Math.min(MAXATK,l.atk+amt));
      if(amt>0&&this.depth<24){this.depth++;this.fire(l,"on_boost",{});this.depth--;}
    }else if(stat==="defense")l.dfn=Math.max(0,Math.min(DEFCAP,l.dfn+amt));
    else if(stat==="speed")l.spd=Math.max(0,l.spd+amt);
    if(amt>0){
      if(this.depth<24){this.depth++;this.fire(l,"on_stat_gain",{stat,amount:amt});this.depth--;}
      this.broadcast("on_any_stat_gain",{gainer:l,stat,amount:amt,by_supporter:this._statGainBySupporter});
    }
    this.checkDeath(l);
  }
  // ---- targeting for effects ----
  sel(self,key,ctx){
    if(ctx&&ctx[key] instanceof RL)return ctx[key];
    if(key==="self")return self;
    const allies=this.alive(self.side),enemies=this.alive(this.enemySide(self.side));
    if(key==="random_ally")return allies.length?this.choice(allies):null;
    if(key==="random_enemy")return enemies.length?this.choice(enemies):null;
    if(key==="random_any"||key==="random_leader"){const p=allies.concat(enemies);return p.length?this.choice(p):null;}
    const SUP={fastest:["spd",1],slowest:["spd",0],highest_hp:["hp",1],lowest_hp:["hp",0],
      highest_def:["dfn",1],lowest_def:["dfn",0],highest_atk:["atk",1],lowest_atk:["atk",0]};
    for(const stem in SUP){
      const[attr,hi]=SUP[stem];
      for(const[suf,pool]of[["_ally",allies],["_enemy",enemies],["_overall",allies.concat(enemies)]]){
        if(key===stem+suf){
          const kf=l=>attr==="spd"?l.effSpd():attr==="dfn"?l.effDef():l[attr];
          return this.ext(pool,kf,hi);
        }
      }
    }
    return null;
  }
  ext(pool,kf,hi){// game _extremum: random pick among all leaders tied at the best value
    if(!pool.length)return null;
    let best=kf(pool[0]);for(const l of pool){const v=kf(l);if(hi?v>best:v<best)best=v;}
    const ties=pool.filter(l=>kf(l)===best);return ties.length===1?ties[0]:this.choice(ties);
  }
  // ---- conditions ----
  cond(self,cn,cp,ctx){
    cp=cp||{};ctx=ctx||{};
    if(!cn)return true;
    const t=ctx.target;
    switch(cn){
      case"self_hp_at_or_below":return self.hp<=(cp.value||0);
      case"self_hp_above":return self.hp>(cp.value||0);
      case"self_stat_at_least":return({health:self.hp,attack:self.atk,defense:self.dfn,speed:self.spd})[cp.stat]>=_i(cp.value);// game reads RAW def/spd here
      case"self_stat_at_most":return({health:self.hp,attack:self.atk,defense:self.dfn,speed:self.spd})[cp.stat]<=_i(cp.value);
      case"turn_equals":return this.turn===_i(_g(cp,"value",1));
      case"turn_in_set":return(cp.values||[]).includes(this.turn);
      case"self_has_status":return cp.status_id in self.st;
      case"self_no_statuses":return Object.keys(self.st).length===0;
      case"target_has_status":{const tt=this.sel(self,cp.target||(_has(ctx,"victim")?"victim":"target"),ctx);return!!tt&&(cp.status_id in tt.st);}// default: "victim" if the ctx has one, else "target" (Oct 3 2026 patch)
      case"story_mode":return!!this.story;
      case"target_is_apex":{const tt=ctx.target;return!!tt&&!!tt.apex;}
      case"ally_has_tag":return this.alive(self.side).some(l=>l!==self&&l.hasTag(cp.tag||""));  // excludes self (game: ally!=self_l)
      case"any_leader_has_tag":return this.allL().some(l=>l.hasTag(cp.tag||""));
      case"ally_has_any_tag":return this.alive(self.side).some(l=>l!==self&&(cp.tags||[]).some(tg=>l.hasTag(tg)));  // excludes self
      case"enemies_count_at_least":return this.alive(this.enemySide(self.side)).length>=_i(_g(cp,"value",1));
      case"enemies_count_at_most":return this.alive(this.enemySide(self.side)).length<=(cp.value||0);
      case"allies_count_at_least":return this.alive(self.side).length>=_i(_g(cp,"value",1));
      case"allies_count_at_most":return this.alive(self.side).length<=(cp.value!=null?cp.value:1);
      case"self_is_fastest":return self.effSpd()>=Math.max(...this.allL().map(l=>l.effSpd()));
      case"self_is_slowest":return self.effSpd()<=Math.min(...this.allL().map(l=>l.effSpd()));
      case"target_hp_above_self":return!!t&&t.hp>self.hp;
      case"target_hp_above":return!!t&&t.hp>(cp.value||0);
      case"target_level_at_least":return!!t&&t.lvl>=(cp.value||0);
      case"target_level_at_most":return!!t&&t.lvl<=(cp.value!=null?cp.value:999);
      case"target_has_any_tag":return!!t&&(cp.tags||[]).some(tg=>t.hasTag(tg));
      case"allies_with_hp_above_at_least":return this.alive(self.side).filter(l=>l.hp>(cp.value||0)).length>=_i(_g(cp,"count",1));
      case"self_damage_this_turn_above":return self.dmgTurn>(cp.value||0);
      case"ctx_status_equals":return ctx.status_id===cp.status_id;
      case"ctx_status_in":return(cp.status_ids||[]).includes(ctx.status_id);
      case"ctx_is_enemy":{const x=ctx[cp.key||"attacker"];return x instanceof RL&&x.side!==self.side;}// game default key "attacker"
      case"ctx_flag":return!!ctx[cp.key||""];
      case"drawn_card_has_tag":case"ctx_card_has_any_tag":{
        const card=ctx.card;if(!card)return false;
        const tags=(cp.tags&&cp.tags.length)?cp.tags:[cp.tag||""];
        return tags.some(tg=>defHasTag(card,tg));
      }
      case"all_of":return(cp.conds||[]).every(c=>this.cond(self,c.condition,c.params||{},ctx));
      case"any_of":return(cp.conds||[]).some(c=>this.cond(self,c.condition,c.params||{},ctx));
      case"not_cond":return!this.cond(self,cp.condition||"",cp.params||{},ctx);
      case"enemy_has_status":return this.alive(this.enemySide(self.side)).some(f=>cp.status_id in f.st);
      case"leaders_with_tag_at_least":return this.allL().filter(l=>l.hasTag(cp.tag||"")).length>=(cp.value!=null?cp.value:1);
      case"fallen_has_tag":{const f=ctx.fallen;return!!f&&f.hasTag(cp.tag||"");}
      case"fallen_has_any_tag":{const f=ctx.fallen;return!!f&&(cp.tags||[]).some(tg=>f.hasTag(tg));}
      case"damage_at_least":case"incoming_damage_at_least":return(ctx.damage||0)>=(cp.value||0);
      case"random_chance":return this.rng()<(cp.chance!=null?cp.chance:0.5);
      case"target_no_statuses":return!!t&&Object.keys(t.st).length===0;
      case"target_has_any_status":return!!t&&Object.keys(t.st).length>0;
      case"target_status_count_at_least":return!!t&&Object.keys(t.st).length>=(cp.value!=null?cp.value:1);
      case"self_status_count_at_least":return Object.keys(self.st).length>=(cp.value!=null?cp.value:1);
      // ---- full registry parity (audited vs battle_sim.gd) ----
      case"self_hp_below":return self.hp<(cp.value||0);
      case"self_hp_fraction_below":return self.hp/Math.max(self.mhp,1)<(cp.value!=null?cp.value:0.5);
      case"self_stat_above":return(({attack:self.atk,defense:self.effDef(),speed:self.effSpd(),health:self.hp})[cp.stat]||0)>(cp.value||0);
      case"self_stat_below":return(({attack:self.atk,defense:self.effDef(),speed:self.effSpd(),health:self.hp})[cp.stat]||0)<(cp.value||0);
      case"self_defense_at_least":return self.effDef()>=(cp.value||0);
      case"self_has_any_status":return Object.keys(self.st).length>0;
      case"self_has_all_statuses":return(cp.statuses||[]).every(sd=>sd in self.st);
      case"self_is_fastest_ally":return this.alive(self.side).every(a=>a===self||a.effSpd()<=self.effSpd());
      case"self_is_slowest_ally":return this.alive(self.side).every(a=>a===self||a.effSpd()>=self.effSpd());
      case"self_not_fastest":return this.allL().some(l=>l!==self&&l.effSpd()>self.effSpd());
      case"self_is_least_attack_alive":return this.alive(self.side).every(a=>a===self||a.atk>=self.atk);
      case"self_is_most_attack_alive":return this.alive(self.side).every(a=>a===self||a.atk<=self.atk);
      case"ally_has_status":return this.alive(self.side).some(a=>a!==self&&(cp.status_id in a.st));
      case"ally_hp_above":return this.alive(self.side).some(a=>a!==self&&a.hp>(cp.value||0));
      case"ally_attack_at_least":return this.alive(self.side).some(a=>a!==self&&a.atk>=(cp.value||0));
      case"ally_defense_at_least":return this.alive(self.side).some(a=>a!==self&&a.effDef()>=(cp.value||0));
      case"ally_status_count_above":return this.alive(self.side).some(a=>a!==self&&Object.keys(a.st).length>(cp.value||0));
      case"allies_all_have_status":{
        const allies=this.alive(self.side);
        if(allies.length<(cp.min_count!=null?cp.min_count:1))return false;
        return allies.every(a=>cp.status_id in a.st);
      }
      case"any_leader_has_status":{
        const pool=cp.side==="ally"?this.alive(self.side):cp.side==="enemy"?this.alive(this.enemySide(self.side)):this.allL();
        return pool.some(l=>cp.status_id in l.st);
      }
      case"enemy_has_any_status":return this.alive(this.enemySide(self.side)).some(f=>Object.keys(f.st).length>0);
      case"enemy_has_all_statuses":return this.alive(this.enemySide(self.side)).some(f=>(cp.statuses||[]).every(sd=>sd in f.st));
      case"enemies_with_status_count_at_least":return this.alive(this.enemySide(self.side)).filter(f=>cp.status_id in f.st).length>=(cp.value!=null?cp.value:1);
      case"enemy_min_def_above_ally_max_def":{
        const al=this.alive(self.side),en=this.alive(this.enemySide(self.side));
        if(!al.length||!en.length)return false;
        return Math.min(...en.map(e=>e.effDef()))>Math.max(...al.map(a=>a.effDef()));
      }
      case"leader_with_tag_and_status":{
        const pool=cp.side==="ally"?this.alive(self.side):cp.side==="enemy"?this.alive(this.enemySide(self.side)):this.allL();
        return pool.some(l=>l.hasTag(cp.tag||"")&&(cp.status_id in l.st));
      }
      case"side_has_any_tag":return this.alive(self.side).some(a=>(cp.tags||[]).some(tg=>a.hasTag(tg)));
      case"total_leaders_equals":return this.allL().length===(cp.value||0);
      case"turn_at_or_after":return this.turn>=(cp.value!=null?cp.value:1);
      case"turn_in_range":return this.turn>=(cp.min!=null?cp.min:1)&&this.turn<=(cp.max!=null?cp.max:99);
      case"turn_every":{
        const frm=cp.from!=null?cp.from:1,n=Math.max(1,cp.n!=null?cp.n:1);
        return this.turn>=frm&&(this.turn-frm)%n===0;
      }
      case"target_hp_below":return!!t&&t.hp<(cp.value||0);
      case"target_hp_fraction_below":return!!t&&t.hp/Math.max(t.mhp,1)<(cp.value!=null?cp.value:0.5);
      case"target_defense_below_self":return!!t&&t.effDef()<self.effDef();
      case"target_attack_below_self":return!!t&&t.atk<self.atk;
      case"target_slower_than_self":return!!t&&t.effSpd()<self.effSpd();
      case"target_has_tag":return!!t&&t.hasTag(cp.tag||"");
      case"target_has_status_any":return!!t&&(cp.status_ids||[]).some(sd=>sd in t.st);
      case"attacker_has_tag":{const a=ctx.attacker;return!!a&&a.hasTag(cp.tag||"");}
      case"attacker_hp_at_least":{const a=ctx.attacker;return!!a&&a.hp>=(cp.value||0);}
      case"attacker_hp_at_most":{const a=ctx.attacker;return!!a&&a.hp<=(cp.value||0);}
      case"attacker_speed_at_least":{const a=ctx.attacker;return!!a&&a.effSpd()>=(cp.value||0);}
      case"attacker_speed_at_most":{const a=ctx.attacker;return!!a&&a.effSpd()<=(cp.value||0);}
      case"fallen_has_status":{const f=ctx.fallen;return!!f&&(cp.status_id in f.st);}
      case"ctx_is_self":{const l=ctx[cp.key||"affected"];return l instanceof RL&&l===self;}
      case"ctx_not_self":{const l=ctx[cp.key||"affected"];return l instanceof RL&&l!==self;}
      case"ctx_is_ally":{const l=ctx[cp.key||"attacker"];return l instanceof RL&&l.side===self.side;}
      case"ctx_has_status":{const l=ctx[cp.key||"affected"];return l instanceof RL&&(cp.status_id in l.st);}
      case"ctx_has_tag":{const l=ctx[cp.key||"attacker"];return l instanceof RL&&l.hasTag(cp.tag||"");}
      case"ctx_has_any_tag":{const l=ctx[cp.key||"attacker"];return l instanceof RL&&(cp.tags||[]).some(tg=>l.hasTag(tg));}
      case"ctx_stat_equals":return String(ctx.stat||"")===String(cp.stat||"");
      case"ctx_amount_at_least":return(ctx.amount||0)>=(cp.value||0);
      case"ctx_amount_equals":return(ctx.amount||0)===(cp.value||0);
      case"ctx_card_has_tag":{const card=ctx.card;return!!card&&defHasTag(card,cp.tag||"");}
      case"no_supporters_drawn":return this.drawn[self.side]===0;
      case"opp_no_supporters_drawn":return this.drawn[this.enemySide(self.side)]===0;
      case"this_turn_self_drew_at_least":return this.drawn[self.side]>=(cp.value!=null?cp.value:1);
      case"this_turn_opp_drew_at_least":return this.drawn[this.enemySide(self.side)]>=(cp.value!=null?cp.value:1);
      case"last_turn_self_drew_at_least":return this.drawnLast[self.side]>=(cp.value!=null?cp.value:1);
      case"last_turn_self_drew_none":return this.drawnLast[self.side]===0;
      case"last_turn_opp_drew_at_least":return this.drawnLast[this.enemySide(self.side)]>=(cp.value!=null?cp.value:1);
      case"last_turn_opp_drew_none":return this.drawnLast[this.enemySide(self.side)]===0;
      // ---- Season 2 conditions ----
      case"ally_element_is":return this.alive(self.side).some(a=>a!==self&&_i(a.elem)===_i(_g(cp,"element",-1)));
      case"attacker_attack_above_self":{const a=ctx.attacker;return!!a&&a.atk>self.atk;}
      case"target_attack_above_self":return!!t&&t.atk>self.atk;
      case"target_faster_than_self":return!!t&&t.effSpd()>self.effSpd();
      case"target_element_is":return!!t&&_i(t.elem)===_i(_g(cp,"element",-1));
      case"ctx_hp_below":{const l=ctx[String(_g(cp,"key","damaged"))];return l instanceof RL&&l.hp<_i(cp.value);}
      case"ctx_status_harmful":{const sid=String(ctx.status_id||"");return sid!==""&&!BUFF_STATUSES.includes(sid);}
      case"self_def_above_all_enemies":{
        const foes=this.alive(this.enemySide(self.side));
        return foes.length>0&&foes.every(f=>f.effDef()<self.effDef());
      }
      case"self_not_attacked_last_turn":return!self.waLast;
      case"target_had_status":return(ctx.pre_statuses||[]).includes(String(_g(cp,"status_id","")));
      case"target_had_any_status":{const pre=ctx.pre_statuses||[];return(cp.status_ids||[]).some(x=>pre.includes(String(x)));}
      case"target_is_extreme":{
        if(!t)return false;
        const stat=String(_g(cp,"stat","speed")),wmax=String(_g(cp,"want","max"))==="max";
        const val=l=>stat==="speed"?l.effSpd():stat==="defense"?l.effDef():stat==="attack"?l.atk:l.hp;
        const tv=val(t);
        return!this.alive(t.side).some(o=>(wmax&&val(o)>tv)||(!wmax&&val(o)<tv));
      }
      default:return false;
    }
  }
  filtered(self,side,filt){
    filt=filt||{};
    let pool;
    if(side==="enemy")pool=this.alive(this.enemySide(self.side));
    else if(side==="all")pool=this.allL();
    else pool=this.alive(self.side);
    return pool.filter(l=>{
      if(filt.faster_than_self&&l.effSpd()<=self.effSpd())return false;
      if(_has(filt,"tag")&&!l.hasTag(filt.tag))return false;
      if(_has(filt,"tags")&&!(filt.tags||[]).some(t=>l.hasTag(t)))return false;
      if(_has(filt,"has_status")&&!(filt.has_status in l.st))return false;
      if(_has(filt,"hp_min")&&l.hp<filt.hp_min)return false;
      if(_has(filt,"hp_max")&&l.hp>filt.hp_max)return false;
      if(_has(filt,"speed_eq")&&l.effSpd()!==_i(filt.speed_eq))return false;// game _filter_match: effective_speed
      if(_has(filt,"speed_min")&&l.effSpd()<_i(filt.speed_min))return false;
      if(_has(filt,"speed_max")&&l.effSpd()>_i(filt.speed_max))return false;
      if(_has(filt,"def_min")&&l.effDef()<_i(filt.def_min))return false;// effective_defense
      if(_has(filt,"def_max")&&l.effDef()>_i(filt.def_max))return false;
      if(_has(filt,"atk_min")&&l.atk<_i(filt.atk_min))return false;// raw attack
      if(_has(filt,"atk_max")&&l.atk>_i(filt.atk_max))return false;
      return true;
    });
  }
  runSub(self,sub,ctx){   // battle_sim._run_sub
    if(sub&&typeof sub==="object"&&!Array.isArray(sub))this.runEffect(self,String(_g(sub,"effect","")),sub.params||{},ctx);
  }
  // ---- effects ----
  runEffect(self,eff,p,ctx){
    p=p||{};ctx=ctx||{};
    if(!eff)return;
    const tagsOf=()=>(p.tags&&p.tags.length)?p.tags:(p.tag?[p.tag]:[]);
    switch(eff){
      // ---- Oct 3 2026 patch effects ----
      case"gain_stat_random":{
        const amt=this.randint(_i(_g(p,"min",0)),_i(_g(p,"max",0))),stat=String(_g(p,"stat","health"));
        if(stat==="health"&&amt>0){self.hp+=amt;this.L(`    🎲 ${self.name.slice(0,22)} rolls +${amt} health`);}   // raw add: no overheal cap, no triggers
        else if(amt!==0){this.L(`    🎲 ${self.name.slice(0,22)} rolls ${amt} ${stat}`);this.mod(self,stat,amt);}
        return;
      }
      case"gamble_attack":{
        if(!ctx.missed&&this.rng()<+_g(p,"bonus_chance",0)){self.pendingBonus+=_i(_g(p,"bonus",0));this.L(`    🎰 ${self.name.slice(0,22)} hits the jackpot: +${_i(_g(p,"bonus",0))} damage`);}
        if(this.rng()<+_g(p,"doom_chance",0)){
          this.L(`    🎰 ${self.name.slice(0,22)}'s gamble backfires!`);
          for(const al of this.alive(self.side))this.mod(al,"health",-_i(_g(p,"doom",0)));
        }
        return;
      }
      // ---- Season 2 effects (battle_sim._register_extended3) ----
      case"bonus_hit":{
        let tgt;
        if(String(_g(p,"target","target"))==="random_other_enemy"){
          const main=ctx.target;
          const pool=this.alive(this.enemySide(self.side)).filter(f=>f!==main);
          if(!pool.length)return;
          tgt=this.choice(pool);
        }else tgt=ctx.target;
        if(!tgt||!tgt.alive||!self.alive)return;
        tgt.takeDamage(_rnd(self.atk*Number(_g(p,"mult",0.5))));this.checkDeath(tgt,self);return;
      }
      case"chance_branch":
        this.runSub(self,this.rng()<Number(_g(p,"chance",0.5))?_g(p,"then",{}):_g(p,"else",{}),ctx);return;
      case"random_choice":{
        const ch=p.choices||[];
        if(ch.length)this.runSub(self,this.choice(ch),ctx);
        return;
      }
      case"on_pick":{
        let pool=this.filtered(self,String(_g(p,"side","ally")),p.filter||{});
        if(p.exclude_self)pool=pool.filter(x=>x!==self);
        if(!pool.length)return;
        const pick=String(_g(p,"mode","random"))==="min_hp"?this.ext(pool,l=>l.hp,false):this.choice(pool);
        const c2=Object.assign({},ctx,{picked:pick});
        for(const sub of p.effects||[])this.runSub(self,sub,c2);
        return;
      }
      case"set_style":{
        const cur=self.styleOverride>0?self.styleOverride:(self.d.style||1);
        const mode=String(_g(p,"mode",""));
        if(mode==="random")self.styleOverride=this.randint(1,9);
        else if(mode==="copy_random_enemy"){
          const foes=this.alive(this.enemySide(self.side));
          if(foes.length){
            const f=this.choice(foes),fs=f.styleOverride>0?f.styleOverride:(f.d.style||1);
            if(fs!==STYLE_ALL)self.styleOverride=fs;
          }
        }else if(mode==="flip")self.styleOverride=_i(_has(STYLE_FLIP,cur)?STYLE_FLIP[cur]:cur);
        return;
      }
      case"random_element":self.elem=this.randint(0,5);return;
      case"swap_stats":{
        if(String(_g(p,"a",""))==="attack"&&String(_g(p,"b",""))==="defense"){
          const a_=self.atk,d_=self.dfn;
          self.atk=Math.max(MINATK,Math.min(MAXATK,d_));self.dfn=Math.max(0,Math.min(DEFCAP,a_));
        }
        return;
      }
      case"steal_ctx_stat":{
        const g=ctx[String(_g(p,"key","gainer"))],stt=String(ctx.stat||"");
        if(!(g instanceof RL)||!stt)return;
        const amt=Math.min(_i(_g(p,"amount",0)),_i(ctx.amount||0));
        if(amt>0){this.mod(g,stt,-amt);this.mod(self,stt,amt);}
        return;
      }
      case"gain_stat_scaled_from":{
        const src=ctx[String(_g(p,"key","victim"))];
        if(!(src instanceof RL))return;
        const stt=String(_g(p,"stat","attack"));
        const base=({attack:src.atk,defense:src.dfn,speed:src.spd,health:src.mhp})[stt]||0;
        const amt=_rnd(base*Number(_g(p,"frac",0.25)));
        if(amt>0)this.mod(self,stt,amt);
        return;
      }
      case"echo_stat_gain":{
        if(self.echoGuard)return;
        const stt=String(ctx.stat||"");
        if(!stt)return;
        self.echoGuard=true;
        try{this.mod(self,stt,_i(_g(p,"amount",1)));}finally{self.echoGuard=false;}
        return;
      }
      case"survive_at_hp":{
        const who=this.sel(self,String(_g(p,"key","self")),ctx);
        if(!who)return;
        const inc=_i(ctx.incoming||0);
        who.hp=Math.min(inc+_i(_g(p,"hp",1)),MAXHP);who.mhp=Math.min(Math.max(who.mhp,who.hp),MAXHP);
        this.L(`    ✨ ${who.name.slice(0,22)} braces to survive`);
        return;
      }
      case"heal_to_fraction":{
        const want=Math.floor(self.mhp*Number(_g(p,"frac",0.75)));
        if(want>self.hp)this.mod(self,"health",want-self.hp);
        return;
      }
      case"cleanse_ctx_status":{
        const who=this.sel(self,String(_g(p,"target","self")),ctx),sid=String(ctx.status_id||"");
        if(who&&sid&&(sid in who.st))delete who.st[sid];
        return;
      }
      case"cleanse_status_all":{
        const sid=String(_g(p,"status_id",""));
        for(const w of this.everyL())if(w.alive&&(sid in w.st))delete w.st[sid];
        return;
      }
      case"schedule_status_next_turn":{
        const who=this.sel(self,String(_g(p,"target","target")),ctx);
        if(!who)return;
        const pre=ctx.pre_statuses||[];
        for(const sid of p.status_ids||[])
          if((String(sid) in who.st)||pre.includes(String(sid)))
            this.pending.push({leader:self,effect:"inflict_status_alive",
              params:{status_id:String(sid),target:"sched_target"},ctx:{sched_target:who}});
        return;
      }
      case"inflict_status_alive":{
        const who=this.sel(self,String(_g(p,"target","target")),ctx),sid=String(_g(p,"status_id",""));
        if(who&&who.alive&&hasSta(sid))this.inflict(who,sid,self);
        return;
      }
      case"gain_stat_per_enemy_alive":{
        const tot=_i(_g(p,"amount",0))*this.alive(this.enemySide(self.side)).length;
        if(tot>0)this.mod(self,String(_g(p,"stat","")),tot);
        return;
      }
      // ---- core effects ----
      case"multi_effect":for(const e of p.effects||[])this.runEffect(self,e.effect||"",e.params||{},ctx);return;
      case"gain_stat":this.mod(self,p.stat,p.amount||0);return;
      case"lose_stat":this.mod(self,p.stat,-(p.amount||0));return;
      case"gain_stat_target":case"lose_stat_target":{
        const t=this.sel(self,p.target||"self",ctx);// game default target "self"
        if(t)this.mod(t,p.stat,(p.amount||0)*(eff.startsWith("gain")?1:-1));
        return;
      }
      case"conditional":{   // faithful to game: multi_effect passes only params, so a nested conditional no-ops
        if(p.condition&&!this.cond(self,p.condition,p.condition_params||{},ctx))return;
        if(p.effect)this.runEffect(self,p.effect,p.params||{},ctx);
        return;
      }
      case"inflict_random_status_each":{
        const pool=(p.pool&&p.pool.length)?p.pool:["poisoned","bleeding","cursed","slow","dizzy","weak","stunned","on_fire","stinky","paralyzed"];
        if(!pool.length)return;
        const pl=p.scope==="enemy"?this.alive(this.enemySide(self.side)):p.scope==="all"?this.allL():this.alive(self.side);
        for(const l of pl)this.inflict(l,this.choice(pool),self);
        return;
      }
      case"gain_stat_all_allies":for(const l of this._allyPool(self,p))this.mod(l,p.stat,p.amount||0);return;
      case"gain_stat_all_enemies":for(const l of this.alive(this.enemySide(self.side)))this.mod(l,p.stat,p.amount||0);return;
      case"lose_stat_all_enemies":for(const l of this.alive(this.enemySide(self.side)))this.mod(l,p.stat,-(p.amount||0));return;
      case"gain_stat_allies_with_tag":case"gain_stat_all_allies_with_tag":{
        const tags=tagsOf();// empty tags => ALL allies (game battle_sim.gd:712-724)
        for(const l of this.alive(self.side)){
          if(p.exclude_self&&l===self)continue;
          if(!tags.length||tags.some(t=>l.hasTag(t)))this.mod(l,p.stat,p.amount||0);
        }
        return;
      }
      case"inflict_status":this.inflict(this.sel(self,p.target||"self",ctx),p.status_id,self);return;
      case"inflict_status_all_enemies":for(const l of this.alive(this.enemySide(self.side)))this.inflict(l,p.status_id,self);return;
      case"inflict_status_all_allies":for(const l of this._allyPool(self,p))this.inflict(l,p.status_id,self);return;
      case"inflict_status_all":   // lazy dead check (a reaction can kill a later leader)
        for(const l of this.everyL())if(l.alive)this.inflict(l,p.status_id,self);
        return;
      case"inflict_status_allies_with_tag":{
        const tags=tagsOf();
        for(const l of this.alive(self.side))
          if(!tags.length||tags.some(t=>l.hasTag(t)))this.inflict(l,p.status_id,self);
        return;
      }
      case"inflict_status_filtered":{
        for(const l of this.filtered(self,p.side||"enemy",p.filter))this.inflict(l,p.status_id,self);
        return;
      }
      case"inflict_status_enemies_with_tag":{
        const tags=tagsOf();// empty tags => ALL enemies
        for(const l of this.alive(this.enemySide(self.side)))if(!tags.length||tags.some(t=>l.hasTag(t)))this.inflict(l,p.status_id,self);
        return;
      }
      case"inflict_status_all_with_tag":{
        const tags=tagsOf();// empty tags => ALL leaders
        for(const l of this.everyL())   // game iterates all_leaders() and checks .dead lazily
          if(l.alive&&(!tags.length||tags.some(t=>l.hasTag(t))))this.inflict(l,p.status_id,self);
        return;
      }
      case"inflict_random_status":{
        const pool=(p.pool&&p.pool.length)?p.pool:["poisoned","bleeding","cursed","slow","dizzy","weak","stunned","on_fire","stinky","paralyzed"];
        const t=this.sel(self,p.target||"random_enemy",ctx);// game default "random_enemy"; only draw RNG if target present
        if(t)this.inflict(t,this.choice(pool),self);
        return;
      }
      case"cleanse_status":this.cleanse(this.sel(self,p.target||"self",ctx),p.status_id);return;
      case"cleanse_status_allies_with_tag":{
        const tags=tagsOf();// empty tag => ALL allies
        const sids=(p.status_ids&&p.status_ids.length)?p.status_ids:(p.status_id?[p.status_id]:[]);// supports status_ids array
        for(const l of this.alive(self.side))if(!tags.length||tags.some(t=>l.hasTag(t)))for(const sd of sids)this.cleanse(l,sd);
        return;
      }
      case"survive_at_1":{   // fired from on_miracle; the pending takeDamage(incoming) then leaves 1 hp
        const inc=_i(ctx.incoming||0);
        self.hp=Math.min(inc+1,MAXHP);self.mhp=Math.min(Math.max(self.mhp,self.hp),MAXHP);
        this.L(`    ✨ ${self.name.slice(0,22)} miracle: survives at 1`);
        return;
      }
      case"kill_self":
        if(self.hp>0)self.takeDamage(self.hp);
        this.checkDeath(self);return;
      case"set_stat":{
        const v=p.value||0;
        if(p.stat==="health"){self.hp=Math.max(0,Math.min(self.mhp,v));if(self.hp<=0)this.checkDeath(self);}// game: then _check_death
        else if(p.stat==="attack")self.atk=Math.max(0,Math.min(MAXATK,v));
        else if(p.stat==="defense")self.dfn=Math.max(0,Math.min(DEFCAP,v));
        else if(p.stat==="speed")self.spd=Math.max(0,v);
        return;
      }
      case"schedule_next_turn":this.pending.push({leader:self,effect:p.effect,params:p.params||{}});return;
      case"gain_stat_per_leader_with_tag":{
        const tags=tagsOf();
        const pool=p.scope==="ally"?this.alive(self.side):p.scope==="enemy"?this.alive(this.enemySide(self.side)):this.allL();
        let tot=0;const amt=p.amount||0;
        for(const l of pool)if(!(p.exclude_self&&l===self)&&tags.some(t=>l.hasTag(String(t))))tot+=amt;
        if(tot>0)this.mod(self,p.stat,tot);
        return;
      }
      case"gain_stat_per_ally_alive":{
        const tot=(p.amount||0)*this.alive(self.side).length;
        if(tot>0)this.mod(self,p.stat,tot);
        return;
      }
      case"gain_stat_per_leader_with_status":{
        const pool=p.side==="ally"?this.alive(self.side):p.side==="enemy"?this.alive(this.enemySide(self.side)):this.allL();
        const n=pool.filter(l=>!!p.status_id&&(p.status_id in l.st)).length;// game has_status: empty matches NONE
        if(n>0)this.mod(self,p.stat,(p.amount||0)*n);
        return;
      }
      case"gain_stat_filtered":case"lose_stat_filtered":{
        const sign=eff.startsWith("gain")?1:-1;
        for(const l of this.filtered(self,p.side||(sign>0?"ally":"enemy"),p.filter))this.mod(l,p.stat,sign*(p.amount||0));
        return;
      }
      case"damage_target":{
        const t=this.sel(self,p.target||"self",ctx);// game default target "self"
        if(t){t.takeDamage(_i(_g(p,"amount",0)));this.checkDeath(t,self);}
        return;
      }
      case"damage_all_enemies":{
        const amt=_i(_g(p,"amount",0));
        if(amt>0)for(const l of this.alive(this.enemySide(self.side))){l.takeDamage(amt);this.checkDeath(l,self);}
        return;
      }
      case"damage_filtered":{
        const amt=_i(_g(p,"amount",0));
        if(amt>0)for(const l of this.filtered(self,p.side||"enemy",p.filter)){l.takeDamage(amt);this.checkDeath(l,self);}
        return;
      }
      case"lose_stat_all_allies":
        for(const l of this._allyPool(self,p))this.mod(l,p.stat,-(p.amount||0));return;
      case"gain_stat_allies_with_status":{
        const sid=p.status_id||p.has_status||"";
        for(const l of this.alive(self.side))
          if(sid in l.st)this.mod(l,p.stat,p.amount||0);// game has_status(sid): empty matches NONE
        return;
      }
      case"inflict_status_allies_with_any_status":
        for(const l of this.alive(self.side))if(Object.keys(l.st).length)this.inflict(l,p.status_id,self);
        return;
      case"inflict_status_enemies_with_status":{
        const need=p.has_status||"";
        for(const l of this.alive(this.enemySide(self.side)))
          if(!need||(need in l.st))this.inflict(l,p.status_id,self);
        return;
      }
      case"lose_stat_all_enemies_eot":{
        for(const l of this.alive(this.enemySide(self.side))){
          this.mod(l,p.stat,-(p.amount||0));l.eot.push({stat:p.stat,amount:p.amount||0});
        }
        return;
      }
      case"draw2_hat_chain":{
        const cards2=[];
        for(let i=0;i<2;i++){const c2=this.drawSingle(self);if(c2!=null)cards2.push(c2);}
        if(!cards2.some(c2=>defHasTag(c2,"hat")))return;
        const en=this.alive(this.enemySide(self.side));
        if(!en.length)return;
        const slow=this.ext(en,l=>l.effSpd(),false);
        slow.takeDamage(22);
        if(!slow.alive){this.checkDeath(slow,self);return;}
        if(slow.hp<150){
          this.applyStatus(slow,"poisoned");this.applyStatus(slow,"paralyzed");
          if(slow.effDef()<20){this.applyStatus(slow,"weak");this.mod(slow,"attack",-10);}
        }
        return;
      }
      case"draw_supporter":{
        for(let i=0;i<(p.count||1);i++)if(this.drawSingle(self)==null)break;
        return;
      }
      case"draw_supporter_per_ally_with_tag":{
        const tag=p.tag||"",cnt=p.count||1;
        const n=this.alive(self.side).filter(a=>!tag||a.hasTag(tag)).length;
        for(let i=0;i<n*cnt;i++)if(this.drawSingle(self)==null)break;
        return;
      }
      case"draw_supporter_per_enemy_with_tag":{
        const n=this.alive(this.enemySide(self.side)).filter(a=>a.hasTag(p.tag||"")).length;
        for(let i=0;i<n*(p.count||1);i++)if(this.drawSingle(self)==null)break;
        return;
      }
      case"draw_supporter_per_leader_with_status":{
        const sid=p.status_id||"";
        const pool=p.side==="ally"?this.alive(self.side):p.side==="enemy"?this.alive(this.enemySide(self.side)):this.allL();
        const n=pool.filter(l=>sid?(sid in l.st):Object.keys(l.st).length>0).length;
        for(let i=0;i<n*(p.count||1);i++)if(this.drawSingle(self)==null)break;
        return;
      }
      case"draw_supporter_per_doomed":{
        const n=this.allL().filter(l=>"doomed"in l.st).length;
        for(let i=0;i<n;i++)if(this.drawSingle(self)==null)break;
        return;
      }
      case"draw_supporter_tag_chain":{
        const card=this.drawSingle(self);
        if(card!=null){
          const tags=tagsOf();
          if(!tags.length||tags.some(t=>defHasTag(card,t))){
            const th=p.then||{};
            if(th.effect)this.runEffect(self,th.effect,th.params||{},ctx);
          }
        }
        return;
      }
      case"draw_supporter_with_tag_status":{
        const card=this.drawSingle(self);
        const tags=tagsOf();
        if(card!=null&&p.status_id&&(!tags.length||tags.some(t=>defHasTag(card,t))))
          for(const al of this.alive(self.side))this.inflict(al,p.status_id,self,false);// game applies via apply_status (no triggers)
        return;
      }
      case"draw_supporter_or_penalty":{
        const tags=p.tags||[];let had=!tags.length;
        for(let i=0;i<(p.count||1);i++){
          const card=this.drawSingle(self);
          if(card==null)break;
          if(tags.length&&tags.some(t=>defHasTag(card,t)))had=true;
        }
        if(!had&&p.penalty&&p.penalty.effect)this.runEffect(self,p.penalty.effect,p.penalty.params||{},ctx);
        return;
      }
      case"extra_attack":{
        const xt=ctx.target;
        if(xt&&self.alive&&xt.alive)this.resolve(self,xt);
        return;
      }
      case"refresh_target_random_status":{
        const t=this.sel(self,p.target||"target",ctx);// game honors p.target (default "target")
        if(t){const ks=Object.keys(t.st);if(ks.length){
          const sid=this.choice(ks);
          let mult=1;// preserve passive_status_duration multiplier
          for(const a of t.abil)if(a.trigger==="passive_status_duration"&&(((a.params||{}).status_ids)||[]).includes(sid))mult=_i(_g(a.params,"mult",2));
          t.st[sid]=[STA[sid][0]*mult,0];
        }}
        return;
      }
      default:
        if(eff.startsWith("draw_supporter"))this.drawSingle(self);
        return;
    }
  }
  drawSingle(owner){
    const deck=this.decks[owner.side],disc=this.disc[owner.side];
    if(!deck.length){
      if(!disc.length)return null;
      this.shuffle(disc,this.shuf[owner.side]);deck.push(...disc);disc.length=0;
    }
    if(!deck.length)return null;
    const card=deck.shift();
    this.drawn[owner.side]++;
    this.L(`    ${owner.name.slice(0,22)} drew [${card.name.slice(0,28)}]`);
    const sab=card.supporter;
    if(sab){
      const _prevBS=this._statGainBySupporter;this._statGainBySupporter=true;   // stat gains inside a supporter's ability are "by supporter"
      this.runEffect(owner,sab.effect||"",sab.params||{},{card});
      this._statGainBySupporter=_prevBS;
    }
    disc.push(card);
    if(this.depth<24){
      this.depth++;
      for(const al of this.alive(owner.side))this.fire(al,"on_supporter_drawn",{card});
      for(const foe of this.alive(this.enemySide(owner.side)))this.fire(foe,"on_opp_supporter_drawn",{card});
      for(const l of this.allL())this.fire(l,"on_any_supporter_drawn",{card,drawer_side:owner.side});
      this.depth--;
    }
    return card;
  }
  // ---- triggers ----
  fire(l,trig,ctx,force){
    if(this.chainD>=5)return;   // game _MAX_CHAIN_DEPTH
    if(!l.alive&&!(force||trig==="on_death"))return;
    this.chainD++;
    try{this._fireInner(l,trig,ctx);}finally{this.chainD--;}
  }
  _fireInner(l,trig,ctx){
    for(const a of l.abil){
      if(a.trigger!==trig)continue;
      if(a.once_game&&l.og.has(a))continue;
      if(a.once_turn&&l.ot.has(a))continue;
      if(!this.cond(l,a.condition||"",a.cond_params||{},ctx))continue;
      if(a.once_game)l.og.add(a);
      if(a.once_turn)l.ot.add(a);
      this.runEffect(l,a.effect||"",a.params||{},ctx);
    }
  }
  broadcast(trig,ctx){
    if(this.depth>=24)return;
    this.depth++;
    for(const l of this.allL())this.fire(l,trig,ctx);
    this.depth--;
  }
  // ---- attack ----
  dmgBonus(atk,tgt){   // _compute_attack_damage_bonus (+ every alive teammate's passive_team_damage_bonus)
    let tot=0;const ctx={target:tgt,attacker:atk};
    for(const a of atk.abil){
      if(a.trigger!=="passive_damage_bonus")continue;
      if(!this.cond(atk,a.condition||"",a.cond_params||{},ctx))continue;
      const p=a.params||{};
      tot+=_i(_g(p,"amount",0));
      const ps=_i(_g(p,"per_self_status",0));
      if(ps)tot+=ps*Object.keys(atk.st).length;
      const pt=_i(_g(p,"per_target_status",0));
      if(pt&&tgt)tot+=pt*Object.keys(tgt.st).length;
      if(tgt){
        const ve=p.vs_element||{};if(_has(ve,String(tgt.elem)))tot+=_i(ve[String(tgt.elem)]);
        const vt=p.vs_tags||{};for(const k in vt)if(tgt.hasTag(String(k)))tot+=_i(vt[k]);
        const pl=_i(_g(p,"per_target_level",0));if(pl)tot+=pl*tgt.lvl;
      }
    }
    for(const mate of this.alive(atk.side))
      for(const a of mate.abil)
        if(a.trigger==="passive_team_damage_bonus"&&this.cond(mate,a.condition||"",a.cond_params||{},ctx))
          tot+=_i(_g(a.params||{},"amount",0));
    return tot;
  }
  statusIds(l){return l?Object.keys(l.st):[];}
  critMult(atk,tgt){
    let m=1.0;const ctx={target:tgt,attacker:atk};
    for(const a of atk.abil)
      if(a.trigger==="passive_crit_mult"&&this.cond(atk,a.condition||"",a.cond_params||{},ctx))
        m*=Number(_g(a.params||{},"mult",1.0));
    return m;
  }
  critBonus(atk){
    let s=0;for(const a of atk.abil)if(a.trigger==="passive_crit_bonus")s+=_i(_g(a.params||{},"amount",0));return s;
  }
  attackMults(atk,tgt,dmg){   // _apply_attack_mults (chance is ALWAYS rolled, even at 1.0)
    const ctx={target:tgt,attacker:atk};
    for(const a of atk.abil){
      if(a.trigger!=="passive_attack_mult")continue;
      if(a.once_game&&atk.og.has(a))continue;
      if(!this.cond(atk,a.condition||"",a.cond_params||{},ctx))continue;
      const p=a.params||{};
      if(this.rng()>=Number(_g(p,"chance",1.0)))continue;
      let mult=Number(_g(p,"mult",1.0));
      if(_has(p,"min")&&_has(p,"max")){const lo=Number(p.min),hi=Number(p.max);mult=lo+(hi-lo)*this.rng();}
      dmg=Math.max(0,_rnd(dmg*mult));
      if(a.once_game)atk.og.add(a);
      const ss=_g(p,"self_status","");
      if(ss)this.inflict(atk,ss,atk);
    }
    return dmg;
  }
  modIncoming(atk,tgt,dmg){   // _mod_incoming (target's passive_damage_taken)
    if(!tgt)return dmg;
    const ctx={attacker:atk,target:tgt};
    for(const a of tgt.abil){
      if(a.trigger!=="passive_damage_taken")continue;
      if(!this.cond(tgt,a.condition||"",a.cond_params||{},ctx))continue;
      const p=a.params||{};
      if(p.first_hit_only&&tgt.hitsTurn>0)continue;
      let flat=_i(_g(p,"flat",0));
      const at=p.ally_tags||[];
      if(at.length){
        for(const al of this.alive(tgt.side)){
          if(al===tgt)continue;
          if(at.some(t=>al.hasTag(String(t)))){flat+=_i(_g(p,"ally_tag_flat",0));break;}
        }
      }
      if(flat)dmg=Math.max(0,dmg+flat);
      if(_has(p,"mult"))dmg=Math.max(0,_rnd(dmg*Number(p.mult)));
      if(_has(p,"cap"))dmg=Math.min(dmg,_i(p.cap));
      if(_has(p,"round_down")){const r=_i(p.round_down);if(r>0)dmg=Math.floor(dmg/r)*r;}
    }
    return dmg;
  }
  shareDamage(tgt,dmg){   // _share_damage (an ally with passive_share_damage soaks part of the hit)
    if(dmg<=0)return dmg;
    for(const g of this.alive(tgt.side)){
      if(g===tgt)continue;
      for(const a of g.abil){
        if(a.trigger!=="passive_share_damage")continue;
        const p=a.params||{};
        if(this.sel(g,String(_g(p,"protect","lowest_hp_ally")),{})!==tgt)continue;
        const part=Math.floor(dmg*Number(_g(p,"frac",0.5)));
        if(part<=0)continue;
        this.L(`    🛡 ${g.name.slice(0,22)} soaks ${part} for ${tgt.name.slice(0,22)}`);
        g.takeDamage(part);this.checkDeath(g);
        return dmg-part;
      }
    }
    return dmg;
  }
  fizzleChance(atk){let fz=0;for(const x in atk.st){const fc=Number(staF(x).fizzle_chance||0);if(fc>0)fz+=fc;}return fz;}
  resolve(atk,tgt){   // battle_sim._resolve_attack
    const pre=this.statusIds(tgt);
    tgt.waThis=true;
    this.broadcast("on_any_attack",{attacker:atk,target:tgt});
    this.broadcast("on_any_attacked",{attacked:tgt,attacker:atk,target:tgt});
    if(!atk.alive||!tgt.alive)return;
    if(atk.flag("dizzy")&&this.rng()<0.5){
      this.L(`    😵 ${atk.name.slice(0,22)} too dizzy`);
      this.fire(atk,"on_attack",{target:tgt,damage:0,missed:true,pre_statuses:pre});
      this.fire(atk,"on_blocked_or_dodged",{target:tgt});
      return;
    }
    const fz=this.fizzleChance(atk);
    if(fz>0&&this.rng()<fz){                       // confused / very_confused: the attack fizzles
      const pick=this.rng()*fz;let frac=0,acc=0;
      for(const x in atk.st){
        const fc=Number(staF(x).fizzle_chance||0);
        if(fc<=0)continue;
        acc+=fc;
        if(pick<acc){frac=Number(staF(x).fizzle_self_frac||0);break;}
      }
      const rc=Math.floor(atk.atk*frac);
      this.L(`    🌀 ${atk.name.slice(0,22)}'s attack fizzles${rc>0?` (-${rc} self)`:""}`);
      if(rc>0)this.mod(atk,"health",-rc);
      this.broadcast("on_any_fizzle",{attacker:atk,target:tgt});
      this.fire(atk,"on_attack",{target:tgt,damage:0,missed:true,pre_statuses:pre});
      this.fire(atk,"on_blocked_or_dodged",{target:tgt});
      return;
    }
    const elemBase=atk.atk;let dmg=atk.atk;
    const em=elemMult(atk.elem,tgt.elem,tgt.apex);
    if(Math.abs(em-1.0)>1e-9)dmg=Math.max(0,_rnd(dmg*em));
    const crit=0.1*(atk.flag("doubles_crit")?2:1)*this.critMult(atk,tgt);
    let isCrit=false;
    if(this.rng()<crit){
      dmg+=5+this.critBonus(atk);isCrit=true;
      this.fire(atk,"on_crit",{target:tgt});
      for(const al of this.alive(atk.side))this.fire(al,"on_ally_crit",{crit_leader:atk,target:tgt});
    }
    const b=this.dmgBonus(atk,tgt);
    if(b)dmg=Math.max(0,dmg+b);
    dmg=this.attackMults(atk,tgt,dmg);
    for(const x of Object.keys(atk.st)){             // horrified: weak hit vs a stronger target
      const f=staF(x),wc=Number(f.weak_hit_chance||0);
      if(wc<=0)continue;
      if(f.weak_needs_stronger_target&&tgt.atk<=atk.atk)continue;
      if(this.rng()<wc){dmg=Math.max(0,_rnd(dmg*Number(_g(f,"weak_hit_mult",1.0))));this.L(`    😱 ${atk.name.slice(0,22)} lands a weak hit`);break;}
    }
    const dfv=tgt.effDef();
    let dodge=(dfv/4)/100,block=(dfv/2)/100;
    let pd=0;
    for(const a of tgt.abil)if(a.trigger==="passive_dodge")pd+=Number(_g(a.params||{},"amount",0))/100;
    dodge=Math.min(0.95,dodge+pd);
    const nob=tgt.flag("blocks_block");
    if(atk.hasPassive("passive_unblockable")){dodge=0;block=0;}
    const roll=this.rng();
    let dodged=!nob&&roll<dodge;
    let blocked=!dodged&&!nob&&roll<dodge+block;
    if(!dodged){                        // passive_force_dodge (optional stat gain / inflict on attacker)
      for(const a of tgt.abil){
        if(a.trigger!=="passive_force_dodge")continue;
        if(a.once_game&&tgt.og.has(a))continue;
        dodged=true;blocked=false;
        if(a.once_game)tgt.og.add(a);
        const p=a.params||{};
        if(_has(p,"stat"))this.mod(tgt,p.stat,_i(_g(p,"amount",0)));
        const ia=_g(p,"inflict_attacker","");
        if(ia)this.inflict(atk,ia,tgt);
        break;
      }
    }
    if(blocked)dmg=Math.floor(dmg/2);   // game halves BEFORE firing on_attack (battle_sim.gd:266-270)
    atk.pendingBonus=0;
    this.fire(atk,"on_attack",{target:tgt,damage:dodged?0:dmg,pre_statuses:pre});
    if(atk.pendingBonus){if(!dodged)dmg=Math.max(0,dmg+atk.pendingBonus);atk.pendingBonus=0;}
    if(dodged){
      this.L(`    💨 ${tgt.name.slice(0,22)} dodged ${atk.name.slice(0,22)}`);
      this.fire(atk,"on_blocked_or_dodged",{target:tgt});
      this.fire(tgt,"on_attacked",{attacker:atk,dodged:true,blocked:false,damage:0});
      return;
    }
    if(blocked)this.fire(atk,"on_blocked_or_dodged",{target:tgt});
    dmg=this.modIncoming(atk,tgt,dmg);
    dmg=this.shareDamage(tgt,dmg);
    if(dmg>=tgt.hp)this.fire(tgt,"on_miracle",{attacker:atk,incoming:dmg});
    if(dmg>=tgt.hp){
      for(const al of this.alive(tgt.side)){
        if(al===tgt)continue;
        this.fire(al,"on_ally_miracle",{ally:tgt,attacker:atk,incoming:dmg});
        if(dmg<tgt.hp){this.L(`    ✨ ${al.name.slice(0,22)} saves ${tgt.name.slice(0,22)}`);break;}
      }
    }
    if(!atk.alive||!tgt.alive)return;
    const actual=tgt.takeDamage(dmg);
    if(actual>0)tgt.hitsTurn++;
    this.L(`    ${atk.name.slice(0,22)} hit ${tgt.name.slice(0,22)} for ${actual}${isCrit?" (crit)":""}${blocked?" (blocked)":""} (${tgt.hp} left)`);
    if(atk.elem===2&&tgt.elem===5){                 // Element.recoil_fraction: Blobgob -> Monblonkin 0.3
      const rc=_rnd(elemBase*0.3);
      if(rc>0)this.mod(atk,"health",-rc);
    }
    if(tgt.alive){
      this.fire(tgt,"on_attacked",{attacker:atk,dodged:false,blocked,damage:actual,crit:isCrit});
      this.fire(tgt,"on_damaged",{attacker:atk,damage:actual});
      this.fire(tgt,"on_survive",{attacker:atk,damage:actual});
      if(actual>0&&tgt.alive)this.broadcast("on_any_damaged",{damaged:tgt,attacker:atk,damage:actual});
    }else this.die(tgt,atk,true);
    for(const x of Object.keys(atk.st)){             // cursed: self-damage from damage dealt (AFTER target triggers)
      const fr=staF(x).recoil||0;
      if(fr>0){
        const sd=Math.trunc(actual*fr);
        if(sd>0){
          atk.takeDamage(sd);
          if(!atk.alive){this.checkDeath(atk);return;}
        }
      }
    }
  }
  resolveMulti(atk,pool){   // battle_sim._resolve_multi_attack (AttackStyle.ALL)
    const tg=pool.filter(t=>t&&t.alive);
    if(!tg.length)return;
    for(const t of tg)t.waThis=true;
    this.broadcast("on_any_attack",{attacker:atk,target:tg[0]});
    for(const t of tg)this.broadcast("on_any_attacked",{attacked:t,attacker:atk,target:t});
    if(!atk.alive)return;
    if(atk.flag("dizzy")&&this.rng()<0.5){
      this.L(`    😵 ${atk.name.slice(0,22)} too dizzy`);
      this.fire(atk,"on_attack",{target:tg[0],damage:0,missed:true});
      this.fire(atk,"on_blocked_or_dodged",{target:tg[0]});
      return;
    }
    const fz=this.fizzleChance(atk);
    if(fz>0&&this.rng()<fz){                       // a multi-attack fizzle costs no HP
      this.L(`    🌀 ${atk.name.slice(0,22)}'s attack fizzles`);
      this.broadcast("on_any_fizzle",{attacker:atk,target:tg[0]});
      this.fire(atk,"on_attack",{target:tg[0],damage:0,missed:true});
      this.fire(atk,"on_blocked_or_dodged",{target:tg[0]});
      return;
    }
    const hits=[];
    for(const t of tg){                              // no crit / dodge / block / weak-hit / share / miracle on multi-hits
      const eb=atk.atk;let d=atk.atk;
      const em=elemMult(atk.elem,t.elem,t.apex);
      if(Math.abs(em-1.0)>1e-9)d=Math.max(0,_rnd(d*em));
      const b=this.dmgBonus(atk,t);
      if(b)d=Math.max(0,d+b);
      d=this.attackMults(atk,t,d);
      d=this.modIncoming(atk,t,d);
      hits.push([t,d,eb,this.statusIds(t),0]);
    }
    for(const h of hits){
      h[4]=h[0].takeDamage(h[1]);
      if(h[4]>0)h[0].hitsTurn++;
      this.L(`    ${atk.name.slice(0,22)} hits ${h[0].name.slice(0,22)} for ${h[4]} (all-out) (${h[0].hp} left)`);
    }
    for(const h of hits){
      if(!atk.alive)break;
      if(h[0].alive)this.fire(atk,"on_attack",{target:h[0],damage:h[4],missed:false,pre_statuses:h[3]});
    }
    for(const h of hits){
      const t=h[0];
      if(atk.elem===2&&t.elem===5){
        const rc=_rnd(h[2]*0.3);
        if(rc>0)this.mod(atk,"health",-rc);
      }
      if(t.alive){
        this.fire(t,"on_attacked",{attacker:atk,dodged:false,blocked:false,damage:h[4],crit:false});
        this.fire(t,"on_damaged",{attacker:atk,damage:h[4]});
        this.fire(t,"on_survive",{attacker:atk,damage:h[4]});
        if(h[4]>0)this.broadcast("on_any_damaged",{damaged:t,attacker:atk,damage:h[4]});
      }
      this.checkDeath(t,atk,true);
    }
    this.checkDeath(atk);
  }
  _allyPool(self,p){const pool=this.alive(self.side);return p.exclude_self?pool.filter(a=>a!==self):pool;}
  // ---- targeting ----
  untargetableBy(cand,atk){   // passive_untargetable_by: healthy enough + attacker carries a listed tag
    for(const a of cand.abil){
      if(a.trigger!=="passive_untargetable_by")continue;
      const p=a.params||{};
      if(cand.hp<=cand.mhp*Number(_g(p,"hp_frac_above",0.0)))continue;
      if((p.tags||[]).some(t=>atk.hasTag(String(t))))return true;
    }
    return false;
  }
  targetPool(atk){   // battle_sim._target_pool
    let enemies=this.alive(this.enemySide(atk.side));
    if(atk.flag("targets_all")){                     // chaos / chaos_blinded: every other leader is a target
      const ev=this.alive(atk.side).filter(l=>l!==atk).concat(enemies);
      if(ev.length)enemies=ev;
    }
    const op=enemies.filter(c=>!this.untargetableBy(c,atk));
    return op.length?op:enemies;
  }
  resolvedStyle(atk){   // battle_sim._resolved_style
    let style=atk.styleOverride>0?atk.styleOverride:(atk.d.style||1);
    for(const a of atk.abil)
      if(a.trigger==="passive_target_style"){style=_i(_g(a.params||{},"style",style));break;}
    for(const al of this.alive(atk.side)){          // jackified: allies use the holder's style
      if(al===atk)continue;
      if(Object.keys(al.st).some(x=>staF(x).shares_attack_style)){style=_i(al.d.style||1);break;}
    }
    if(atk.flag("random_attack_style"))style=this.randint(1,9);
    if(style===STYLE_ALL&&this.turn<atk.allReadyTurn){const cd=this.allCooldown(atk);if(cd)style=_i(_g(cd.params||{},"fallback_style",4));}   // attack-all on cooldown (v183)
    return style;
  }
  allCooldown(atk){for(const a of atk.abil)if(a.trigger==="passive_all_cooldown")return a;return null;}   // battle_sim._all_cooldown
  pickFrom(enemies,style){   // battle_sim._pick_from
    if(!enemies.length)return null;
    if(style===1)return this.choice(enemies);
    const kf={2:l=>l.effSpd(),3:l=>l.effSpd(),4:l=>l.hp,5:l=>l.hp,6:l=>l.effDef(),7:l=>l.effDef(),8:l=>l.atk,9:l=>l.atk}[style];
    if(!kf)return enemies[0];
    return this.ext(enemies,kf,[2,4,7,8].includes(style));   // random pick among ties (game _extremum)
  }
  pickTarget(atk){return this.pickFrom(this.targetPool(atk),this.resolvedStyle(atk));}
  bodyguard(atk,tgt){   // battle_sim._bodyguard_redirect (main-loop single attacks only)
    if(!tgt||!atk||tgt.side===atk.side)return tgt;
    for(const g of this.alive(tgt.side)){
      if(g===tgt)continue;
      for(const a of g.abil){
        if(a.trigger!=="passive_bodyguard")continue;
        if(_g(a.params||{},"attacker","")==="highest_atk"){
          if(this.alive(atk.side).some(f=>f!==atk&&f.atk>atk.atk))continue;
        }
        if(a.once_turn&&g.ot.has(a))continue;
        if(a.once_turn)g.ot.add(a);
        return g;
      }
    }
    return tgt;
  }
  orderBySpeed(){// _sort_by_speed_desc: ties broken by a fresh random salt per sort
    return this.allL().map(l=>[l,this.rng()]).sort((a,b)=>(b[0].effSpd()-a[0].effSpd())||(a[1]-b[1])).map(x=>x[0]);
  }
  runTurn(){   // battle_sim._run_turn
    for(const l of this.everyL())l.ot=new Set();   // once/turn keys are per turn number in the game
    if(this.pending.length){
      const pend=this.pending;this.pending=[];
      for(const pe of pend){
        const pl=pe.leader;
        if(!pl||!pl.alive)continue;
        this.runEffect(pl,pe.effect||"",pe.params||{},pe.ctx||{});
      }
    }
    for(const l of this.everyL()){l.dmgTurn=0;l.hitsTurn=0;l.turnNow=this.turn;}
    for(const l of this.everyL()){
      if(!l.alive)continue;
      const swaps=[];
      for(const a of l.abil){
        if(a.trigger==="passive_status_heal"){
          const sid=_g(a.params||{},"status_id","");
          if(sid in l.st){
            const e=l.st[sid],dl=STA[sid][1],dd=e[1]<dl.length?dl[e[1]]:{};
            swaps.push([_i(_g(a.params,"amount",0)),_i(_g(dd,"health",0))]);
          }
        }
      }
      if(this.alive(this.enemySide(l.side)).length<=2&&("soul_bound" in l.st))delete l.st["soul_bound"];
      const d=this.tickStatuses(l);
      for(const[amt,dm]of swaps)d.health=_i(d.health||0)-dm+amt;
      this.applyStatDeltas(l,d);
      this.checkDeath(l);
    }
    for(const l of this.orderBySpeed())if(l.alive)this.fire(l,"turn_start",{});
    for(const atk of this.orderBySpeed()){
      if(!atk.alive)continue;
      if(atk.flag("blocks_attack")){this.L(`    ${atk.name.slice(0,22)} can't attack`);continue;}
      const pool=this.targetPool(atk);
      if(!pool.length)continue;
      const style=this.resolvedStyle(atk);
      if(style===STYLE_ALL){this.resolveMulti(atk,pool);const cd=this.allCooldown(atk);if(cd)atk.allReadyTurn=this.turn+1+_i(_g(cd.params||{},"cooldown",1));}
      else{
        const tgt=this.pickFrom(pool,style);
        if(!tgt)continue;
        const bg=this.bodyguard(atk,tgt);
        if(bg!==tgt)this.L(`    🛡 ${bg.name.slice(0,22)} steps in front of ${tgt.name.slice(0,22)}`);
        this.resolve(atk,bg);
      }
      if(atk.alive)this.applyStatus(atk,"tired");   // _mark_attacked: silent apply_status
    }
    for(const l of this.orderBySpeed())if(l.alive)this.fire(l,"turn_end",{});
    for(const l of this.everyL()){                   // end-of-turn stat reverts (attack/defense/speed only)
      for(const m of l.eot){
        const st=m.stat||"",a=_i(m.amount);
        if(st==="attack")l.atk=Math.max(0,Math.min(MAXATK,l.atk+a));
        else if(st==="defense")l.dfn=Math.max(0,Math.min(DEFCAP,l.dfn+a));
        else if(st==="speed")l.spd=Math.max(0,l.spd+a);
      }
      l.eot=[];
    }
    for(const l of this.everyL()){                   // attacked-last-turn rollover, then the status sweep
      l.waLast=l.waThis;l.waThis=false;
      this.sweepExpired(l);
    }
  }
  over(){return!this.alive(0).length||!this.alive(1).length;}
  run(deckA,deckB){
    this.teams=[[],[]];
    deckA.slice(0,3).forEach((c,i)=>{if(c)this.teams[0].push(new RL(c,0,i));});   // null slot = empty (battle_sim skips it)
    deckB.slice(0,3).forEach((c,i)=>{if(c)this.teams[1].push(new RL(c,1,i));});
    this.decks=[deckA.slice(3,7).map(x=>Object.assign({},x)),deckB.slice(3,7).map(x=>Object.assign({},x))];
    this.disc=[[],[]];
    this.shuffle(this.decks[0],this.shuf[0]);this.shuffle(this.decks[1],this.shuf[1]);
    while(this.turn<30&&!this.over()){
      this.turn++;
      this.drawnLast=this.drawn.slice();this.drawn=[0,0];
      this.L(`── Turn ${this.turn} ──`);
      this.runTurn();
    }
    // story rule: player wins ONLY by killing all enemies within 30 turns
    return(!this.alive(1).length&&this.alive(0).length)?0:1;
  }
}
