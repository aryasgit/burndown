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
<title>burndown</title><style>
:root{
  --bg:#0a0a0a;--card:#0f0f0f;--line:#1c1c1c;
  --text:#f4f4f4;--text2:#cfcfcf;--dim:#8a8a8a;--faint:#7a7a7a;
  --ghost:#23231f;--grn:#3dd07a;--neon:#5cf0a0;--red:#ff6b6b;--amber:#ffbf47;
  color-scheme:dark}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased;
  font:14px/1.55 ui-monospace,'SF Mono',Menlo,Consolas,monospace;
  max-width:800px;margin:0 auto;padding:40px 22px 64px}
.tight{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;letter-spacing:-.03em;font-weight:500}
.top{display:flex;justify-content:space-between;align-items:center;
  margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid var(--line)}
.brand{font-size:20px}.brand b{font-weight:600}
.sub{color:var(--dim);font-size:12px;margin-left:4px}
.live{color:var(--grn);font-size:11px;letter-spacing:.08em;text-transform:uppercase;display:flex;align-items:center;gap:8px}
.live .dot{width:7px;height:7px;border-radius:50%;background:var(--neon);box-shadow:0 0 12px rgba(92,240,160,.85),0 0 4px rgba(92,240,160,1);animation:p 2s ease-in-out infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.35}}
.card{background:var(--card);border:1px solid #2a2a2a;border-radius:8px;padding:20px 22px;margin:11px 0;box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 12px 32px -16px rgba(0,0,0,.75)}
.k{color:var(--faint);font-size:10.5px;text-transform:uppercase;letter-spacing:.16em;margin-bottom:13px}
.big{font-size:31px;line-height:1}
.sec{color:var(--dim);font-weight:400;font-size:.46em;letter-spacing:0}
.bar{height:8px;border-radius:4px;background:var(--ghost);overflow:hidden;margin:17px 0 9px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.03)}
.fill{height:100%;background:linear-gradient(90deg,var(--grn),var(--neon));border-radius:4px;transition:width .5s;box-shadow:0 0 10px rgba(61,208,122,.6),0 0 3px rgba(92,240,160,.9)}
.pct{color:var(--dim);font-size:12px}
.row{display:flex;gap:11px}.row>.card{flex:1}
.proj{color:var(--dim);font-size:12px;margin-top:11px}
.split{display:flex;gap:34px;flex-wrap:wrap;margin-top:2px}
.pill{font-size:12px;color:var(--dim)}.pill .tag{color:var(--faint)}
.pill b{font-size:20px;display:block;margin-top:6px;color:var(--text);font-weight:400}
.chart{display:flex;align-items:flex-end;gap:5px;height:64px;margin-top:4px}
.chart div{flex:1;background:linear-gradient(180deg,var(--neon),#2ea866);border-radius:3px 3px 1px 1px;min-height:4px;transition:height .4s;box-shadow:0 0 9px rgba(61,208,122,.22)}
table{width:100%;border-collapse:collapse}
td{padding:9px 0;border-bottom:1px solid var(--line);font-size:13px;color:var(--text2)}
tr:last-child td{border-bottom:none}
td.n{text-align:right;color:var(--grn)}
.foot{color:var(--faint);font-size:11.5px;margin-top:26px;letter-spacing:.02em}
.ok{color:var(--grn);text-shadow:0 0 18px rgba(61,208,122,.55)}.warn{color:var(--red);text-shadow:0 0 18px rgba(255,107,107,.45)}
td.n{text-shadow:0 0 14px rgba(61,208,122,.35)}
</style></head><body>
<div class=top>
  <div><span class="brand tight"><b>burndown</b></span><span class=sub id=sub>loading…</span></div>
  <div class=live><span class=dot></span><span>live · 127.0.0.1</span></div>
</div>
<div class=card><div class=k id=spentk>spent / budget</div>
  <div class="big tight" id=spent>—</div>
  <div class=bar><div class=fill id=fill style=width:0></div></div>
  <div class=pct id=pct></div></div>
<div class=row>
  <div class=card><div class=k>burn rate · last 24h</div><div class="big tight" id=burn>—</div></div>
  <div class=card><div class=k>runway</div><div class="big tight" id=runway>—</div><div class=proj id=proj></div></div>
</div>
<div class=card><div class=k>credit pool vs interactive</div>
  <div class=split><div class=pill>programmatic <span class=tag>(credit pool)</span><b id=prog>—</b></div>
  <div class=pill>interactive <span class=tag>(subscription)</span><b id=inter>—</b></div></div></div>
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
  f.style.background=frac>=1?'linear-gradient(90deg,#ff6b6b,#ff9b9b)':frac>=.8?'linear-gradient(90deg,#ffbf47,#ffd98a)':'linear-gradient(90deg,#3dd07a,#5cf0a0)';
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
