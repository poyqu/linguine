"""Compatibility shim: card data helpers only (see cards_data.py). The Python battle engine was retired on
Oct 5 2026: all battles run on lab_engine.js (the site's engine) via fastsim.py / verify/battles.js."""
from cards_data import *
from cards_data import _rnd
class Sim:
    def __init__(self, *a, **k):
        raise RuntimeError("The Python battle engine is retired: use fastsim.run (lab_engine.js under Node). "
                           "Old code: sim_engine_legacy.py (not kept in sync with game patches).")
