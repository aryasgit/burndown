"""
burndown/serve.py — optional LOCAL web dashboard.

This is the only part of burndown that opens a socket, and it binds to
**127.0.0.1 only** (loopback) — a local UI, never a network service. It makes no
outbound connections, serves a fully self-contained page (no external scripts or
fonts), and is off by default. Start it with `burndown serve`. See SECURITY.md.
"""
from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config as cfgmod
from .aggregate import build_snapshot
from .forecast import build_forecast
from .logs import iter_events


def snapshot_data(cfg=None) -> dict:
    """Recompute everything from disk (reloads config too, so live edits show)."""
    cfg = cfg or cfgmod.load()
    snap = build_snapshot(iter_events(cfg.log_dirs), cfg, scope=cfg.scope)
    fc = build_forecast(snap, cfg)
    return {
        "period": snap.period, "resets": snap.period_end.strftime("%b %d"),
        "scope": cfg.scope, "budget_unit": cfg.budget_unit,
        "currency2": cfg.currency2, "currency2_symbol": cfg.currency2_symbol, "fx_rate": cfg.fx_rate,
        "spent": fc.spent, "budget": fc.budget, "pct": fc.pct_used,
        "burn_per_day": fc.burn_per_day, "avg_per_day": fc.avg_per_day,
        "runway_days": fc.runway_days, "remaining_days": fc.remaining_days,
        "exhaustion": fc.exhaustion_date.strftime("%b %d") if fc.exhaustion_date else None,
        "projected": fc.projected_period_total, "will_exceed": fc.will_exceed,
        "programmatic": snap.spent_programmatic, "interactive": snap.spent_interactive,
        "by_project": sorted(snap.by_project.items(), key=lambda x: -x[1])[:8],
        "by_day": [[d, v] for d, v in sorted(snap.by_day.items())][-14:],
        "events": snap.events, "tokens": snap.tokens,
    }


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the terminal quiet
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/data.json"):
            try:
                self._send(200, "application/json", json.dumps(snapshot_data()).encode())
            except Exception as e:  # never crash the server on a bad read
                self._send(500, "application/json", json.dumps({"error": str(e)}).encode())
        elif self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", _HTML.encode())
        else:
            self._send(404, "text/plain", b"not found")


def serve(port: int = 8787, open_browser: bool = True) -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"burndown dashboard → {url}   (local only · ctrl-c to stop)")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        httpd.server_close()


_HTML = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Burndown</title><style>
:root{color-scheme:dark}
*{box-sizing:border-box;margin:0}
body{background:#0a0c10;color:#e8eaed;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:760px;margin:0 auto;padding:32px 20px 60px}
.top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:22px}
h1{font-size:20px;letter-spacing:-.02em}.muted{color:#7a828c;font-size:13px}
.card{background:#12151b;border:1px solid #20252e;border-radius:12px;padding:20px;margin:12px 0}
.big{font-size:30px;font-weight:700;letter-spacing:-.02em}.sec{color:#7a828c;font-weight:400;font-size:.62em}
.k{color:#7a828c;font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.bar{height:12px;border-radius:6px;background:#20252e;overflow:hidden;margin:12px 0 6px}
.fill{height:100%;background:#3dd07a;transition:width .4s}
.row{display:flex;gap:12px}.row>.card{flex:1}
.split{display:flex;gap:18px;flex-wrap:wrap}
.pill{font-size:13px}.pill b{font-size:18px;display:block;margin-top:2px}
.chart{display:flex;align-items:flex-end;gap:4px;height:64px;margin-top:8px}
.chart div{flex:1;background:#2b6cff;border-radius:3px 3px 0 0;min-height:2px;opacity:.85}
table{width:100%;border-collapse:collapse}td{padding:6px 0;border-bottom:1px solid #1a1f27;font-size:14px}
td.n{text-align:right;color:#7fd1a8}
.warn{color:#ff6b6b}.ok{color:#3dd07a}
.foot{color:#4a525c;font-size:12px;margin-top:20px}
</style></head><body>
<div class=top><h1>Burndown</h1><div class=muted id=sub>loading…</div></div>
<div class=card><div class=k id=spentk>spent this period</div>
  <div class=big id=spent>—</div>
  <div class=bar><div class=fill id=fill style=width:0></div></div>
  <div class=muted id=pct></div></div>
<div class=row>
  <div class=card><div class=k>burn rate (last 24h)</div><div class=big id=burn>—</div></div>
  <div class=card><div class=k>runway</div><div class=big id=runway>—</div><div class=muted id=proj></div></div>
</div>
<div class=card><div class=k>credit pool vs interactive</div>
  <div class=split><div class=pill>programmatic <span class=muted>(credit pool)</span><b id=prog>—</b></div>
  <div class=pill>interactive <span class=muted>(subscription)</span><b id=inter>—</b></div></div></div>
<div class=card><div class=k>last 14 days</div><div class=chart id=chart></div></div>
<div class=card><div class=k>top projects</div><table id=projects></table></div>
<div class=foot id=foot></div>
<script>
let D={};
const usd=x=>'$'+(+x).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
function dual(x){if(D.budget_unit==='tokens')return Math.round(x).toLocaleString()+' tok';
  let s=usd(x);if(D.currency2&&D.fx_rate){let c=(x*D.fx_rate);s+=' <span class=sec>≈ '+(D.currency2_symbol||D.currency2+' ')+Math.round(c).toLocaleString()+'</span>';}return s;}
function render(d){D=d;
  document.getElementById('sub').textContent=d.period+' · resets '+d.resets+(d.scope!=='all'?' · '+d.scope:'');
  document.getElementById('spentk').textContent=d.budget?'spent / budget':'spent this period';
  document.getElementById('spent').innerHTML=d.budget?dual(d.spent)+' <span class=sec>/ '+dual(d.budget)+'</span>':dual(d.spent);
  let frac=d.budget?Math.min(d.spent/d.budget,1):0;
  let f=document.getElementById('fill');f.style.width=(frac*100)+'%';
  f.style.background=frac>=1?'#ff6b6b':frac>=.8?'#ffbf47':'#3dd07a';
  document.getElementById('pct').innerHTML=d.budget?(d.pct.toFixed(0)+'% used'):'<span class=muted>set a budget with: burndown budget &lt;amount&gt;</span>';
  document.getElementById('burn').innerHTML=dual(d.burn_per_day)+' <span class=sec>/day</span>';
  let rw=document.getElementById('runway');
  if(d.budget&&d.runway_days!=null){if(d.runway_days<=0){rw.innerHTML='<span class=warn>exhausted</span>';}
    else{let within=d.runway_days<d.remaining_days;rw.innerHTML='<span class="'+(within?'warn':'ok')+'">'+d.runway_days.toFixed(1)+' days</span> <span class=sec>'+(d.exhaustion||'')+'</span>';}
    document.getElementById('proj').innerHTML='projected '+dual(d.projected)+(d.will_exceed?' <span class=warn>OVER</span>':'');}
  else{rw.innerHTML='<span class=muted>—</span>';document.getElementById('proj').textContent='';}
  document.getElementById('prog').innerHTML=dual(d.programmatic);
  document.getElementById('inter').innerHTML=dual(d.interactive);
  let mx=Math.max(1,...d.by_day.map(x=>x[1]));
  document.getElementById('chart').innerHTML=d.by_day.map(x=>'<div title="'+x[0]+': '+usd(x[1])+'" style=height:'+(x[1]/mx*100)+'%></div>').join('');
  document.getElementById('projects').innerHTML=d.by_project.map(p=>'<tr><td>'+p[0].slice(0,40)+'</td><td class=n>'+usd(p[1])+'</td></tr>').join('')||'<tr><td>—</td></tr>';
  document.getElementById('foot').textContent=d.events.toLocaleString()+' billable msgs · '+d.tokens.toLocaleString()+' tokens · 100% local, loopback only — no data leaves your machine.';
}
function tick(){fetch('/data.json').then(r=>r.json()).then(render).catch(()=>{});}
tick();setInterval(tick,5000);
</script></body></html>"""
