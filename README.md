# Linguine Sandbox

A fan-made battle analysis tool for **Silly Linguine Cat Simulator Deluxe Online**.

**Live: https://cat.poyqu.me**

It's a single, self-contained web page that replicates the game's battle logic so you can build teams, simulate fights, find the best team against any opponent, and share teams with a community board, without spending a single SL$.

> Unofficial fan project. The engine is a replica of the game's rules, but its randomness differs from the real game, so every win rate here is a **statistical estimate**, not an exact prediction.

---

## What it does

The page has five tabs.

### Team & Battle
- Build a team of **3 leaders + up to 4 supporters** and pick an enemy: a story chapter (EXTREME or normal) or a **custom trio**.
- **Run** simulates hundreds of battles and reports the win rate, average kill turn, and a loss autopsy. **Watch one battle** replays a single fight turn by turn.
- **Search best team vs this enemy** brute-forces strong teams against the current enemy. Options let you choose the card pool (crate only / all skins), search depth (a **quick** mode that runs on phones), and battles per team.
- **Story win rates** grades your team across all 21 EXTREME chapters. **PvP vs meta teams** fights your team head to head against a field of meta decks (needs a full 3 leaders + 4 supporters).
- **Team codes**: paste a code from the game's *Copy Team ID* button to load a team, or export your current team as a shareable code (see below).
- Save teams locally, and load any listed team into your team or **as the enemy** to fight it.

### Cards
Browse every card with filters for element, ability trigger/effect, status, support ability, obtainability source, rarity, and Apex. Sort by any stat, mark favorites for the optimizer, and read exact abilities with in-game-style status colors.

### Recommended
The best **crate-obtainable** team for each of the 21 EXTREME chapters. One team (chad + Leuitenant + Static + TV) clears most of the mode; a few bosses get their own crate teams.

### Builds
A community board of player-submitted teams (see [Community Builds](#community-builds)).

### Help
Combat rules, the damage formula, the full element chart, and exact status values, all generated from the same data the simulator uses.

---

## Team codes

The sandbox reads and writes the game's own team codes (the 51-digit string behind the game's **Copy Team ID** button), so you can move teams between the game and the sandbox:

- **Import** a code to load it as your team or **as the enemy** (great for fighting a friend's team).
- **Export** your current team to a code you can share.

Find it under **Team & Battle → Team code**.

---

## Community Builds

The **Builds** tab is a shared board of teams other players discovered, credited to whoever submitted each one first. It has two categories:

- **Story** builds rank by win rate across the 21 EXTREME chapters. They can't use story-reward skins (those are locked behind the very progress they'd help with), but DLC and event cards are fine.
- **PvP** builds allow any skin and fight each other in a round-robin **league** that re-runs on every new entry, so standings shift as the pool grows. PvP builds need exactly 4 supporters.

### Submitting a build
Build a team in the sandbox, open the **Builds** tab, enter a username, and hit **Submit**. That opens a pre-filled GitHub issue; press **Submit new issue** to finish.

Every submission is **verified automatically** by a GitHub Action ([`verify/verify.py`](verify/verify.py)) before it lands:
- the team must be well-formed and use allowed cards,
- it must not already be on the board (first to discover keeps it),
- and its win rate is **re-simulated by the engine**, so nobody can submit a faked result.

If it passes, it's added to [`builds.json`](builds.json), the issue is closed, and the board updates within a minute.

---

## How it works

- The whole app is **one self-contained HTML file** (`index.html`) served from GitHub Pages. No backend, no tracking, nothing to install.
- The battle engine is a faithful port of the decompiled game logic (damage, statuses, triggers, supporter draws, the 30-turn kill rule, story enemy scaling, and seeded CPU supporters), cross-validated against the game.
- Heavy searches run in parallel across your device's CPU cores using Web Workers.
- The Builds board is the only shared state: the site loads `builds.json` at runtime, and the verification Action commits to it, so new builds appear without rebuilding the page.

---

## Disclaimer

This is an unofficial, non-commercial fan project and is not affiliated with the game's developer. Results are simulated estimates. Card data and rules are derived from the game for interoperability only.
