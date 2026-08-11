"""CI verifier for Builds submissions. Reads the issue body from ISSUE_BODY, validates the team
(well-formed, crate-legal, not a duplicate, correct supporter count for its category), computes
its metric, and on success appends it to ../builds.json. Story builds are scored by mean win rate
across the 21 EXTREME chapters. PvP builds cross-validate: a round-robin among ALL PvP builds is
re-run on every accept, so every PvP build's standing adjusts as the pool grows. Always writes
result.md (the comment) and sets GITHUB_OUTPUT status."""
import sim, json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CRATE = set(json.load(open(os.path.join(HERE, "crate_ids.json"))))
DECKS = json.load(open(os.path.join(HERE, "enemy_decks.json")))
BUILDS_PATH = os.path.join(ROOT, "builds.json")
BUILDS = json.load(open(BUILDS_PATH)) if os.path.exists(BUILDS_PATH) else []

def sig(leaders, supp):
    return ",".join(map(str, sorted(leaders))) + "|" + ",".join(map(str, sorted(supp)))

def story_eff(leaders, supp, n=250):
    tot = 0.0
    for ed in DECKS.values():
        w = 0
        for s in range(n):
            pd = sim.player_deck(list(leaders), list(supp))
            if sim.Sim(s * 13 + 5).run(pd, [dict(c) for c in ed]) == 0:
                w += 1
        tot += w / n
    return tot / len(DECKS)

def pvp_league(builds, n=120):
    """Round-robin among all PvP builds; sets each build's 'pvp' (win fraction) and 'rec' [W,L,D].
    timeout = draw. Each unordered pair plays once and is credited to both sides."""
    k = len(builds)
    if k < 2:
        for b in builds:
            b["pvp"], b["rec"] = None, [0, 0, 0]
        return
    decks = [sim.player_deck(list(b["leaders"]), list(b.get("supp", []))) for b in builds]
    W = [0]*k; L = [0]*k; D = [0]*k; N = [0]*k
    for i in range(k):
        for j in range(i + 1, k):
            for s in range(n):
                S = sim.Sim(s * 13 + 5)
                S.run([dict(c) for c in decks[i]], [dict(c) for c in decks[j]])
                a0, a1 = len(S.alive(0)), len(S.alive(1))
                if a1 == 0 and a0 > 0:   W[i] += 1; L[j] += 1
                elif a0 == 0 and a1 > 0: L[i] += 1; W[j] += 1
                else:                    D[i] += 1; D[j] += 1
                N[i] += 1; N[j] += 1
    for idx, b in enumerate(builds):
        b["pvp"] = round(W[idx] / N[idx], 3) if N[idx] else None
        b["rec"] = [W[idx], L[idx], D[idx]]

def finish(status, comment):
    open(os.path.join(HERE, "result.md"), "w", encoding="utf-8").write(comment)
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"status={status}\n")
    print(f"[{status}] {comment}")
    raise SystemExit(0)

class Reject(Exception):
    pass

def main():
    body = os.environ.get("ISSUE_BODY", "")
    m = re.search(r"```json\s*(\{.*?\})\s*```", body, re.S)
    if not m:
        raise Reject("I couldn't find a team block in this issue. Please submit through the Sandbox's **Submit current team** button so the format is correct.")
    try:
        data = json.loads(m.group(1))
    except Exception:
        raise Reject("the team block wasn't valid JSON.")
    leaders = data.get("leaders") or []
    supp = data.get("supp") or []
    by = str(data.get("by") or "").strip()
    cat = str(data.get("for") or "story").lower()

    if cat not in ("story", "pvp", "both"):
        raise Reject("category must be **story**, **pvp**, or **both**.")
    if not isinstance(leaders, list) or len(leaders) != 3:
        raise Reject("a build needs exactly **3 leaders**.")
    if not isinstance(supp, list) or len(supp) > 4:
        raise Reject("supporters must be **0 to 4** cards.")
    try:
        leaders = [int(x) for x in leaders]; supp = [int(x) for x in supp]
    except Exception:
        raise Reject("card ids must be numbers.")
    if len(set(leaders)) != 3:
        raise Reject("the 3 leaders must be different cards.")
    if set(leaders) & set(supp):
        raise Reject("a card can't be both a leader and a supporter.")
    if len(set(supp)) != len(supp):
        raise Reject("supporters must be different cards.")
    if cat in ("pvp", "both") and len(supp) != 4:
        raise Reject("**PvP builds need exactly 4 supporters** (the ranked-PvP rule).")
    if not re.match(r"^[A-Za-z0-9_. -]{2,24}$", by):
        raise Reject("username must be 2-24 letters, numbers, or _ . -")
    for i in leaders + supp:
        if i not in sim.LEADERS:
            raise Reject(f"card #{i} doesn't exist.")
        if i not in CRATE:
            raise Reject(f"**{sim.LEADERS[i]['name']}** isn't crate-obtainable. Builds must use generally-available cards only.")

    s = sig(leaders, supp)
    for b in BUILDS:
        if sig(b["leaders"], b.get("supp", [])) == s:
            raise Reject(f"that exact team is already on the board, discovered by **{b['by']}**. First to discover keeps it.")

    entry = {"leaders": leaders, "supp": supp, "by": by,
             "date": datetime.date.today().isoformat(), "for": cat}
    if cat in ("story", "both"):
        entry["eff"] = round(story_eff(leaders, supp), 3)
    BUILDS.append(entry)
    if cat in ("pvp", "both"):
        pvp_builds = [b for b in BUILDS if b.get("for") in ("pvp", "both")]
        pvp_league(pvp_builds)   # mutates entries in-place (they are refs into BUILDS)

    json.dump(BUILDS, open(BUILDS_PATH, "w"), indent=1)

    names = " + ".join(sim.LEADERS[i]["name"].replace("Linguine", "L.") for i in leaders)
    bits = []
    if entry.get("eff") is not None:
        bits.append(f"**{entry['eff']*100:.0f}%** story efficiency")
    if entry.get("pvp") is not None:
        rec = entry.get("rec", [0,0,0])
        bits.append(f"**{entry['pvp']*100:.0f}%** PvP win rate ({rec[0]}-{rec[1]}-{rec[2]}) against the current build pool")
    metric = " and ".join(bits) if bits else "added"
    extra = ""
    if cat in ("pvp", "both"):
        extra = "\n\nAll PvP standings were re-run to include this team."
    finish("accepted",
           f"Verified and added to the Builds board.\n\n**{names}** by **{by}** ({cat}) - {metric}.{extra}")

if __name__ == "__main__":
    try:
        main()
    except Reject as r:
        finish("rejected", f"Sorry, this submission wasn't added: {r}")
    except SystemExit:
        raise
    except Exception as ex:
        finish("error", f"The verifier hit an unexpected error: `{ex}`. Ping the maintainer.")
