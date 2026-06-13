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


# A fully self-contained, editorial dashboard — no cards, no external resources.
# Hairline-ruled, runway-led, the same dark/Inter-Tight/mono language as the landing.
_HTML = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>burndown</title><style>
:root{
  --bg:#0a0a0a;--text:#f4f4f4;--text2:#cfcfcf;--dim:#8a8a8a;--faint:#6f6f6f;
  --line:#191919;--line2:#272727;--ghost:#222;--grn:#3dd07a;--red:#ff6b6b;--amber:#ffbf47;
  color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased;
  font:13.5px/1.55 ui-monospace,'SF Mono',Menlo,Consolas,monospace}
.wrap{max-width:700px;margin:0 auto;padding:36px 26px 72px}
.display{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;letter-spacing:-.03em;font-weight:500}
.eb{font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:var(--faint)}
.c2{font-size:.55em;color:var(--dim);font-weight:400;letter-spacing:0}
.ok{color:var(--grn)}.warn{color:var(--red)}

/* header */
.top{display:flex;align-items:center;gap:14px;padding-bottom:20px;border-bottom:1px solid var(--line)}
.brand{font-family:system-ui,sans-serif;font-weight:600;font-size:16px;letter-spacing:-.02em;display:flex;align-items:center;gap:9px}
.brand .g{width:13px;height:13px;border:1.5px solid var(--text);border-radius:3px;position:relative;overflow:hidden}
.brand .g::after{content:"";position:absolute;left:0;right:0;bottom:0;height:42%;background:var(--text)}
.top .meta{color:var(--dim);font-size:11.5px}
.top .live{margin-left:auto;color:var(--grn);font-size:10px;text-transform:uppercase;letter-spacing:.14em;display:flex;align-items:center;gap:7px}
.top .live i{width:6px;height:6px;border-radius:50%;background:var(--grn);box-shadow:0 0 8px rgba(61,208,122,.7);animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}

/* hero — runway (or spent) */
.hero{padding:42px 0 32px}
.hero .eb{margin-bottom:18px}
.hero-row{display:flex;align-items:baseline;gap:20px;flex-wrap:wrap}
.hero-num{font-size:78px;line-height:.82;color:var(--text)}
.hero-num .unit{font-size:.32em;color:var(--dim);margin-left:.14em}
.hero-tag{font-size:13.5px}
.hero-sub{color:var(--dim);font-size:12.5px;margin-top:20px}
.hero-sub .mono2{color:var(--text2)}

/* gauge */
.gauge{padding:24px 0;border-top:1px solid var(--line)}
.track{height:6px;background:var(--ghost);border-radius:3px;overflow:hidden}
.track .fill{height:100%;background:var(--grn);border-radius:3px;transition:width .6s cubic-bezier(.2,.8,.2,1)}
.gauge .gl{margin-top:13px;color:var(--dim);font-size:12px}
.gauge .gl b{color:var(--text);font-weight:400}

/* sections */
.sec{padding:26px 0;border-top:1px solid var(--line)}
.sec .eb{margin-bottom:20px}

/* hairline columns (stats + split) */
.cols{display:grid;gap:22px}
.cols.three{grid-template-columns:repeat(3,1fr)}
.cols.two{grid-template-columns:repeat(2,1fr)}
.col{border-top:1px solid var(--line2);padding-top:15px}
.col .ck{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--faint);margin-bottom:12px}
.col .cv{font-size:25px;line-height:1;color:var(--text)}
.col .cv .per{font-size:.42em;color:var(--dim);margin-left:.15em}
.col .cx{color:var(--faint);font-size:11px;margin-top:10px}

/* chart */
.chart{display:flex;align-items:flex-end;gap:6px;height:58px}
.chart div{flex:1;background:rgba(61,208,122,.32);border-radius:2px 2px 0 0;min-height:4px;transition:height .5s}
.chart div:last-child{background:var(--grn)}

/* projects */
.prow{display:flex;justify-content:space-between;align-items:baseline;padding:11px 0;border-bottom:1px solid var(--line);font-size:13px}
.prow:last-child{border-bottom:none}
.prow .pn{color:var(--text2)}
.prow .pv{color:var(--grn)}
.prow .pv .c2{color:var(--dim)}

.foot{color:var(--faint);font-size:11px;margin-top:32px;letter-spacing:.02em}
</style></head><body>
<div class=wrap>

  <div class=top>
    <div class=brand><span class=g></span>burndown</div>
    <div class=meta id=meta>loading…</div>
    <div class=live><i></i><span>live</span></div>
  </div>

  <div class=hero>
    <div class=eb id=heroEb>Runway</div>
    <div class=hero-row>
      <div class="hero-num display" id=heroNum>—</div>
      <div class=hero-tag id=heroTag></div>
    </div>
    <div class=hero-sub id=heroSub></div>
  </div>

  <div class=gauge id=gauge>
    <div class=track><div class=fill id=fill style=width:0></div></div>
    <div class=gl id=gaugeLabel></div>
  </div>

  <div class=sec>
    <div class=eb>This period</div>
    <div class="cols three">
      <div class=col><div class=ck>Burn / day</div><div class="cv display" id=burn>—</div><div class=cx>last 24h</div></div>
      <div class=col><div class=ck>Spent</div><div class="cv display" id=spent>—</div><div class=cx id=spentx>so far</div></div>
      <div class=col><div class=ck>Projected</div><div class="cv display" id=proj>—</div><div class=cx>by reset</div></div>
    </div>
  </div>

  <div class=sec>
    <div class=eb>Credit pool vs interactive</div>
    <div class="cols two">
      <div class=col><div class=ck>Programmatic · credit pool</div><div class="cv display" id=prog>—</div><div class=cx>SDK / headless runs — the June-2026 pool</div></div>
      <div class=col><div class=ck>Interactive · subscription</div><div class="cv display" id=inter>—</div><div class=cx>≈ value at API rates</div></div>
    </div>
  </div>

  <div class=sec>
    <div class=eb>Last 14 days</div>
    <div class=chart id=chart></div>
  </div>

  <div class=sec>
    <div class=eb>Top projects</div>
    <div id=projects></div>
  </div>

  <div class=foot id=foot></div>

</div>
<script>
var $=function(id){return document.getElementById(id);};
var D={};
function esc(s){return String(s).replace(/[&<>]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}
function usd(x){return '$'+(+x).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});}
function dual(x){
  if(D.budget_unit==='tokens') return Math.round(x).toLocaleString()+' tok';
  var s=usd(x);
  if(D.currency2 && D.fx_rate){
    s+=' <span class=c2>≈ '+(D.currency2_symbol||(D.currency2+' '))+Math.round(x*D.fx_rate).toLocaleString()+'</span>';
  }
  return s;
}
function render(d){
  D=d;
  $('meta').textContent=d.period+' · resets '+d.resets+(d.scope!=='all'?' · '+d.scope:'');

  // hero: runway when a budget is set, otherwise the period spend
  if(d.budget && d.runway_days!=null){
    $('heroEb').textContent='Runway';
    $('gauge').style.display='';
    var frac=Math.min(d.spent/d.budget,1);
    var f=$('fill'); f.style.width=(frac*100)+'%';
    f.style.background=frac>=1?'var(--red)':frac>=.85?'var(--amber)':'var(--grn)';
    $('gaugeLabel').innerHTML='<b>'+dual(d.spent)+'</b> of '+dual(d.budget)+' budget · '+d.pct.toFixed(0)+'% used';
    if(d.runway_days<=0){
      $('heroNum').innerHTML='0 <span class=unit>days</span>'; $('heroNum').className='hero-num display warn';
      $('heroTag').textContent='budget exhausted'; $('heroTag').className='hero-tag warn';
      $('heroSub').innerHTML=dual(d.spent)+' of '+dual(d.budget)+' spent — over budget.';
    } else {
      var within=d.runway_days<d.remaining_days;
      $('heroNum').innerHTML=Math.round(d.runway_days)+' <span class=unit>days</span>';
      $('heroNum').className='hero-num display'+(within?' warn':'');
      $('heroTag').innerHTML=within?'↘ runs dry before reset':'✓ lasts the period';
      $('heroTag').className='hero-tag '+(within?'warn':'ok');
      $('heroSub').innerHTML='runs dry '+(d.exhaustion||'—')+' at the current pace · '+d.pct.toFixed(0)+'% of budget used';
    }
  } else {
    $('heroEb').textContent='Spent this period';
    $('heroNum').innerHTML=usd(d.spent); $('heroNum').className='hero-num display';
    $('heroTag').textContent=''; $('heroTag').className='hero-tag';
    $('heroSub').innerHTML='set a budget for a runway — <span class=mono2>burndown budget &lt;amount&gt;</span>';
    $('gauge').style.display='none';
  }

  $('burn').innerHTML=dual(d.burn_per_day)+'<span class=per>/day</span>';
  $('spent').innerHTML=dual(d.spent);
  $('proj').innerHTML=dual(d.projected)+(d.will_exceed?' <span class=warn style=font-size:.5em>over</span>':'');
  $('prog').innerHTML=dual(d.programmatic);
  $('inter').innerHTML=dual(d.interactive);

  var mx=Math.max.apply(null,[1].concat(d.by_day.map(function(x){return x[1];})));
  $('chart').innerHTML=d.by_day.map(function(x){
    return '<div title="'+x[0]+': '+usd(x[1])+'" style="height:'+Math.max(4,x[1]/mx*100)+'%"></div>';
  }).join('');

  $('projects').innerHTML=d.by_project.map(function(p){
    return '<div class=prow><span class=pn>'+esc(p[0]).slice(0,44)+'</span><span class=pv>'+dual(p[1])+'</span></div>';
  }).join('')||'<div class=prow><span class=pn>—</span></div>';

  $('foot').textContent=d.events.toLocaleString()+' msgs · '+d.tokens.toLocaleString()+' tokens · 100% local, loopback only — nothing leaves your machine.';
}
function tick(){fetch('/data.json').then(function(r){return r.json();}).then(render).catch(function(){});}
tick();setInterval(tick,5000);
</script></body></html>"""
