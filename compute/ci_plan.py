"""Matrix for the GitHub recompute: every chapter in search_bundle.json (optionally only some seasons).
Usage: python ci_plan.py "1,2"   -> prints {"ch": [...]} ; hardest chapters first so the slowest jobs start early."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
seasons = {s.strip() for s in (sys.argv[1] if len(sys.argv) > 1 else "1,2").split(",")}
B = json.load(open(os.path.join(HERE, "search_bundle.json"), encoding="utf-8"))
chs = [c for c in B["chapters"] if ("1" in seasons and c.startswith("F")) or ("2" in seasons and c.startswith("S2"))]
first = ["S2E20", "S2E21", "S2E22", "F17", "F20", "F21"]
chs.sort(key=lambda c: (c not in first, c))
print(json.dumps({"ch": chs}))
