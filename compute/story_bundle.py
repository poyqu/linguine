"""Story data the team search needs, as ONE json file (search_bundle.json), so the search can run where the
decompiled game files aren't available (GitHub Actions). Everything in it is already public on the site:
chapter enemies, the CPU's 4 supporter cards per chapter + difficulty (with the story ability rewrites), which
cards come from crates, and which story rewards each chapter unlocks.

  python story_bundle.py      # (local, after extraction) writes search_bundle.json from the decompiled files

Bundle mode is ON when SEARCH_BUNDLE=1 or decompiled/story_data.gd is missing; then story_search, s2_search,
team_s2 and godot_seed read this file instead of parsing the game scripts."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "search_bundle.json")
ACTIVE = os.environ.get("SEARCH_BUNDLE") == "1" or not os.path.exists(os.path.join(HERE, "decompiled", "story_data.gd"))
B = json.load(open(PATH, encoding="utf-8")) if ACTIVE else None

def pairs(lst): return [tuple(x) for x in lst]

def make():
    import story_search as SS, s2_search as S, team_s2 as T, godot_seed as G
    chs = sorted(set(SS.CHAPTERS_ALL) | set(T.NORMAL), key=SS.chapter_key)
    out = {"chapters": {}, "crate": sorted(S.CRATE), "byid": {str(k): v for k, v in S.byid.items()}, "rewards": {k: [list(n), list(h)] for k, (n, h) in S.REWARDS.items()},
           "csupp": {}}
    for ch in chs:
        out["chapters"][ch] = {"hard": [list(p) for p in SS.CHAPTERS_ALL.get(ch, [])],
                               "normal": [list(p) for p in T.NORMAL.get(ch, [])]}
        for diff in ("hard", "normal"):
            out["csupp"][f"{ch}:{diff}"] = G.cpu_supporter_cards(ch, [], diff)
    json.dump(out, open(PATH, "w", encoding="utf-8"))
    print(f"search_bundle.json: {len(chs)} chapters, {len(out['crate'])} crate cards, {os.path.getsize(PATH)//1024} KB")

if __name__ == "__main__":
    make()
