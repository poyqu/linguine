"""CI verifier for Builds submissions. Reads the issue body from ISSUE_BODY, validates the team
(well-formed, crate-legal, not a duplicate), re-simulates its story efficiency, and on success
appends it to ../builds.json. Always writes result.md (the comment) and sets GITHUB_OUTPUT status."""
import sim, json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CRATE = set(json.load(open(os.path.join(HERE, "crate_ids.json"))))
DECKS = json.load(open(os.path.join(HERE, "enemy_decks.json")))
BUILDS_PATH = os.path.join(ROOT, "builds.json")
BUILDS = json.load(open(BUILDS_PATH)) if os.path.exists(BUILDS_PATH) else []

def sig(leaders, supp):
    return ",".join(map(str, sorted(leaders))) + "|" + ",".join(map(str, sorted(supp)))

def eff(leaders, supp, n=250):
    tot = 0.0
    for ed in DECKS.values():
        w = 0
        for s in range(n):
            pd = sim.player_deck(list(leaders), list(supp))
            if sim.Sim(s * 13 + 5).run(pd, [dict(c) for c in ed]) == 0:
                w += 1
        tot += w / n
    return tot / len(DECKS)

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

    e = round(eff(leaders, supp), 3)
    entry = {"leaders": leaders, "supp": supp, "by": by,
             "date": datetime.date.today().isoformat(), "eff": e}
    BUILDS.append(entry)
    BUILDS.sort(key=lambda b: -b.get("eff", 0))
    json.dump(BUILDS, open(BUILDS_PATH, "w"), indent=1)
    names = " + ".join(sim.LEADERS[i]["name"].replace("Linguine", "L.") for i in leaders)
    finish("accepted",
           f"Verified and added to the Builds board.\n\n**{names}** by **{by}** - "
           f"**{e*100:.0f}%** story efficiency (mean win rate across all 21 EXTREME chapters, re-simulated here).")

if __name__ == "__main__":
    try:
        main()
    except Reject as r:
        finish("rejected", f"Sorry, this submission wasn't added: {r}")
    except SystemExit:
        raise
    except Exception as ex:
        finish("error", f"The verifier hit an unexpected error: `{ex}`. Ping the maintainer.")
