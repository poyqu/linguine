"""EXACT replica of the game's seeded CPU supporter selection (story_hub._cpu_supporter_sids).

Verified against Godot 4.x source (core/math/random_pcg.*, thirdparty/misc/pcg.cpp,
core/string/ustring.cpp, core/variant/variant.cpp) and validated in-game: F19 produces
[528, 37, 404, 195] = SL42x7 Guineblade / Big Eyes / Bright Pink Socks / Owl,
exactly matching Paul's observation.

Chain: seed = djb2 String hash of "supporters:<chapter_id>";
RandomPCG seeding = pcg32_srandom_r(seed, (DEFAULT_INC<<1)|1 effective);
randi_range = debiased modulo (pcg32_boundedrand_r);
pool = sorted(all leaders) minus story-exclusive/spoiler subjects, minus the fight's own
leaders, minus #150 whose image file (res://subject150.png) is MISSING from the pck
(ResourceLoader.exists fails -> the game silently drops it).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim

MASK64 = (1 << 64) - 1
PCG_MULT = 6364136223846793005
PCG_DEFAULT_INC = 1442695040888963407
# Subjects whose image PNG is absent from the pck -> ResourceLoader.exists() is false, so the
# game drops them from the CPU-supporter pool. As of the current build EVERY leader has a
# 'Subject N.png.import' in the pck (verified against the exe), so nothing is excluded here.
# (150/686/687/688 were missing in older builds; a patch added their images.) RE-CHECK after
# each patch: re-scan the pck for 'subject N.png.import' and put any leaders lacking one here,
# or the pool size is wrong and every chapter's seeded supporter picks shift.
IMAGE_MISSING = set()

def godot_string_hash(s: str) -> int:
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return h

class GodotRNG:
    def __init__(self, seed: int):
        self.inc = ((PCG_DEFAULT_INC << 1) | 1) & MASK64
        self.state = 0
        self._next()
        self.state = (self.state + seed) & MASK64
        self._next()
    def _next(self) -> int:
        old = self.state
        self.state = (old * PCG_MULT + self.inc) & MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return ((xorshifted >> rot) | (xorshifted << ((32 - rot) & 31))) & 0xFFFFFFFF
    def bounded(self, bound: int) -> int:   # pcg32_boundedrand_r
        threshold = ((1 << 32) - bound) % bound
        while True:
            r = self._next()
            if r >= threshold:
                return r % bound
    def randi_range(self, a: int, b: int) -> int:
        if a == b: return a
        return self.bounded(abs(a - b) + 1) + min(a, b)

# ---- Oct 3 2026 patch: story_hub._cpu_supporter_sids / _build_cpu_deck ----
# pool = every battle leader that IS a skin, minus SkinManager.SPOILER_SUBJECTS, minus any subject with a
# story-exclusive or unobtainable (only DLC / no crate source) skin entry, minus every opponent of the chapter
# (normal AND EXTREME lists, whichever difficulty is played). Then the supporter ABILITY is rewritten per
# difficulty: EXTREME drops/redirects abilities that would weaken the CPU's own team, Normal (and Easy) gives
# every CPU supporter one of four self-debuffs.
import re as _re
_HERE = os.path.dirname(os.path.abspath(__file__))
SPOILER_SUBJECTS = {601, 645, 646, 647}
DLC_SOURCES = {"money", "money2", "money3", "music"}
def _skin_entries():
    sm = open(os.path.join(_HERE, "decompiled", "skin_manager.gd"), encoding="utf-8").read()
    i = sm.index("var skins =[") + len("var skins ="); d = 0; j = i
    while j < len(sm):
        if sm[j] == "[": d += 1
        elif sm[j] == "]":
            d -= 1
            if d == 0: break
        j += 1
    return [(_subject_id_of(a), _re.findall(r'"([^"]+)"', b)) for a, b in
            _re.findall(r'"image":\s*"([^"]*)".*?"crate_sources":\s*(\[[^\]]*\])', sm[i:j + 1], _re.S)]
def _subject_id_of(path):
    """SkinManager.subject_id_of: strips "subject " WITH the space only, so the 31 skins whose image is
    "res://subjectNNN.png" read as -1, are not skins for _cpu_supporter_sids and never become CPU supporters
    (verified in game Oct 4 2026: S2E22 shows exactly [446, 352, 7, 941] with this rule)."""
    base = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if base.lower().startswith("subject "): base = base[8:]
    return int(base) if _re.fullmatch(r"[+-]?\d+", base) else -1
import story_bundle as _SB
_SKINS = [] if _SB.ACTIVE else _skin_entries()
SKIN_SUBJECTS = {sid for sid, _ in _SKINS if sid >= 0}
SUPP_EXCLUDE = set(SPOILER_SUBJECTS) | {sid for sid, cs in _SKINS if "Story" in cs or not [x for x in cs if x not in DLC_SOURCES]}
def _chapter_opponents():
    sd = open(os.path.join(_HERE, "decompiled", "story_data.gd"), encoding="utf-8").read()
    out = {}
    for m in _re.finditer(r'_ch\("((?:F|S\d+E)\d+)"', sd):
        p = sd.find("(", m.start()); depth = 0; instr = False; e = p
        for e in range(p, len(sd)):
            ch = sd[e]
            if ch == '"': instr = not instr
            elif instr: continue
            elif ch == "(": depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0: break
        args, cur, dep, ins = [], "", 0, False   # split top-level args
        for ch in sd[p + 1:e]:
            if ch == '"': ins = not ins
            if not ins and ch in "([{": dep += 1
            if not ins and ch in ")]}": dep -= 1
            if ch == "," and dep == 0 and not ins: args.append(cur); cur = ""
            else: cur += ch
        args.append(cur)
        sids = []
        for k in (6, 8):   # _ch arg 6 = normal opponents, arg 8 = EXTREME opponents
            if len(args) > k:
                for a in _re.findall(r'_opp\((\d+),\s*\d+\)', args[k]):
                    if int(a) not in sids: sids.append(int(a))
        out[m.group(1)] = sids
    return out
CHAPTER_OPPONENTS = {} if _SB.ACTIVE else _chapter_opponents()

def cpu_supporters(chapter_id: str, fight_sids=(), variant=None):
    """the 4 seeded CPU supporter subject ids for a story chapter (story_hub._cpu_supporter_sids).
    fight_sids only matters for chapters story_data doesn't define (the game excludes ALL chapter opponents)."""
    opp = set(CHAPTER_OPPONENTS.get(chapter_id) or fight_sids)
    pool = sorted(i for i in sim.LEADERS
                  if i in SKIN_SUBJECTS and i not in SUPP_EXCLUDE and i not in IMAGE_MISSING and i not in opp)
    rng = GodotRNG(godot_string_hash("supporters:" + chapter_id))
    picks = []
    for i in range(min(4, len(pool))):
        j = rng.randi_range(i, len(pool) - 1)
        pool[i], pool[j] = pool[j], pool[i]
        picks.append(pool[i])
    return picks

# STORY_EASY_DEBUFFS parsed by _supporter_from_sentence ("your" = the CPU's own team): CPU self-debuffs
EASY_DEBUFFS = [
    {"effect": "lose_stat_target", "params": {"stat": "attack", "amount": 2, "target": "highest_atk_ally"}},
    {"effect": "lose_stat_target", "params": {"stat": "speed", "amount": 25, "target": "fastest_ally"}},
    {"effect": "lose_stat_target", "params": {"stat": "defense", "amount": 4, "target": "highest_def_ally"}},
    {"effect": "lose_stat_target", "params": {"stat": "health", "amount": 5, "target": "highest_hp_ally"}},
]
def extreme_supporter(card):
    """story_hub._extreme_supporter_ability: a lose_stat_target that doesn't target enemies is dropped, unless
    it targets *_overall and its sentence says " Leader is decreased" (case-sensitive): then it is re-parsed
    with " Enemy Leader is decreased", i.e. the same debuff aimed at the player's team."""
    s = card.get("supporter")
    if not s or s.get("effect") != "lose_stat_target": return s
    t = str((s.get("params") or {}).get("target", ""))
    if t.endswith("_enemy"): return s
    if t.endswith("_overall") and " Leader is decreased" in (card.get("stext_desc") or ""):
        return {"effect": "lose_stat_target", "params": dict(s["params"], target=t[:-len("_overall")] + "_enemy")}
    return None
def story_supporter_card(card, difficulty):
    c = dict(card)
    c["supporter"] = extreme_supporter(card) if difficulty == "hard" else dict(EASY_DEBUFFS[int(card.get("id", 0)) % 4])
    return c
def cpu_supporter_cards(chapter_id, fight_sids=(), difficulty="hard"):
    """the CPU's 4 supporter cards as the game builds them for this chapter + difficulty ("hard" = EXTREME)"""
    if _SB.ACTIVE: return [dict(c) for c in _SB.B["csupp"][f"{chapter_id}:{'hard' if difficulty == 'hard' else 'normal'}"]]
    return [story_supporter_card(sim.LEADERS[x], difficulty) for x in cpu_supporters(chapter_id, fight_sids)]

if __name__ == "__main__":
    HARD = {
     "F12": [457,39,241], "F16": [459,40,458], "F18": [3,645,1],
     "F19": [2,646,11], "F20": [13,647,24], "F21": [25,601,28],
    }
    # pre-Oct-3 picks were validated in-game (F19 -> [528,37,404,195]); the patch changed the pool, re-validate in game
    for ch, sids in HARD.items():
        p = cpu_supporters(ch, sids)
        names = [f"#{x} {sim.LEADERS[x]['name'][:34]}" + (" [▸"+sim.LEADERS[x].get('supporter',{}).get('effect','')+"]" if sim.LEADERS[x].get('supporter') else "") for x in p]
        print(f"{ch}: " + " | ".join(names))
