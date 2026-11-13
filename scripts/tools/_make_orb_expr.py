import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json

addrs = []
for i in (10, 11):
    addrs.extend(json.load(open(f"name_part_{i:02d}.json", encoding="utf-8")))
body = r"""
(async()=>{
  const addrs = __ADDRS__;
  const names = {};
  const bad = [];
  for (let i = 0; i < addrs.length; i += 40) {
    const r = await fetch('https://orbmarkets.io/api/tags/resolve', {
      method: 'POST', credentials: 'include',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({addresses: addrs.slice(i, i + 40)})
    });
    if (!r.ok) { bad.push(r.status); continue; }
    const j = await r.json();
    for (const [k, v] of Object.entries(j.tags || {})) if (v && v.name) names[k] = v.name;
  }
  window.__orb = Object.assign(window.__orb || {}, names);
  return JSON.stringify({n: addrs.length, named: Object.keys(names).length, total: Object.keys(window.__orb).length, bad, names});
})()
""".replace("__ADDRS__", json.dumps(addrs, separators=(",", ":")))
open("_orb_expr.js", "w", encoding="utf-8").write(body)
print(len(addrs), len(body))
