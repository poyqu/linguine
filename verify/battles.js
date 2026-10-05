// Battle runner on lab_engine.js (the site's engine, the ONLY battle engine since Oct 5 2026). Used by the
// pipeline (fastsim.py) and by the builds verifier (copied to the site repo as verify/battles.js).
// One JSON line in -> one JSON line out:
//   job   {ek, ed?, trio?, lv?, supp?, pd?, n, sa, sb, story?}
//         player side = pd (ready deck) or trio at level lv + supp; enemy side = ed, cached under key ek
//         battle k is seeded sa*k+sb; story=false is PvP (story-only abilities off)
//   reply {w, l, d, f}  wins / losses (team wiped) / draws (timeout or both wiped), and fit = s2_search's score
//         (win: 1 + 0.3*(1 - turns/30), loss: 0.8*(1 - enemy hp left / start))
"use strict";
const fs = require("fs"), vm = require("vm"), path = require("path"), readline = require("readline");
const HERE = __dirname;
const ctx = { console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(HERE, "lab_engine.js"), "utf8") + "\n;globalThis.Sim=Sim;globalThis.applyPlayerLevel=applyPlayerLevel;", ctx);
const RAW = JSON.parse(fs.readFileSync(path.join(HERE, "cards.json"), "utf8")).leaders;
const L = {};
for (const k in RAW) L[k] = Object.assign({ id: +k }, RAW[k]);
const DECKS = {};
const rl = readline.createInterface({ input: process.stdin });
rl.on("line", line => {
  const j = JSON.parse(line);
  if (j.ed) DECKS[j.ek] = j.ed;
  const ed = DECKS[j.ek];
  const pd = j.pd || j.trio.map(id => ctx.applyPlayerLevel(L[id], j.lv)).concat((j.supp || []).map(id => Object.assign({}, L[id])));
  const ehp = ed.slice(0, 3).reduce((a, c) => a + (c ? c.hp : 0), 0);
  let w = 0, l = 0, d = 0, f = 0;
  for (let k = 0; k < j.n; k++) {
    const S = new ctx.Sim((j.sa * k + j.sb) >>> 0, null, j.story !== false);
    S.run(pd.map(x => x && Object.assign({}, x)), ed.map(x => x && Object.assign({}, x)));
    const a0 = S.alive(0).length, a1 = S.alive(1).length;
    if (a1 === 0 && a0 > 0) { w++; f += 1 + 0.3 * Math.max(0, 1 - S.turn / 30); }
    else {
      if (a0 === 0 && a1 > 0) l++; else d++;
      let left = 0; for (const x of S.teams[1]) left += Math.max(0, x.hp); f += 0.8 * Math.max(0, 1 - left / ehp);
    }
  }
  process.stdout.write(JSON.stringify({ w, l, d, f }) + "\n");
});
