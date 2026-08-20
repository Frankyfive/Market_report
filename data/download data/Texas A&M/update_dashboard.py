"""
Texas Market Dashboard Generator
Reads CSVs from this folder and writes texas_market_dashboard.html
Run manually or via scheduled task to refresh the dashboard.
"""

import csv
import json
import os
from datetime import datetime

FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT  = os.path.join(FOLDER, "texas_market_dashboard.html")

FILES = {
    "Texas":       "Texas.csv",
    "DFW":         "dfw.csv",
    "Austin":      "austin.csv",
    "San Antonio": "san antonio.csv",
    "El Paso":     "el paso.csv",
}

# ── helpers ──────────────────────────────────────────────────────────────────

def load_csv(name):
    path = os.path.join(FOLDER, name)
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["_date"] = datetime.strptime(row["Date"].strip('"'), "%Y-%m-%d")
                rows.append(row)
            except Exception:
                pass
    rows.sort(key=lambda r: r["_date"], reverse=True)
    return rows

def fval(row, key, default=0):
    try: return float(row[key].strip('"').strip())
    except: return default

def ival(row, key, default=0):
    try: return int(float(row[key].strip('"').strip()))
    except: return default

def month_label(dt):
    return dt.strftime("%b-%y")

def fmt_dollar(n):
    if n >= 1e9:  return f"${n/1e9:.2f}B"
    if n >= 1e6:  return f"${n/1e6:.1f}M"
    return f"${n:,.0f}"

def fmt_num(n):
    return f"{int(n):,}"

def fmt_pct(n, sign=True):
    s = "+" if (sign and n >= 0) else ""
    return f"{s}{n:.1f}%"

# ── load data ─────────────────────────────────────────────────────────────────

data = {}
for market, fname in FILES.items():
    data[market] = load_csv(fname)

# ── latest month ──────────────────────────────────────────────────────────────

tx      = data["Texas"]
tx0     = tx[0]
as_of   = tx0["_date"].strftime("%B %Y")

tx_kpis = {
    "sales":     ival(tx0, "Sales"),
    "sales_yoy": fval(tx0, "Sales YoY%") * 100,
    "volume":    fval(tx0, "Dollar Volume"),
    "vol_yoy":   fval(tx0, "Dollar Volume YoY%") * 100,
    "med_price": ival(tx0, "Median Price"),
    "avg_price": ival(tx0, "Average Price"),
    "listings":  ival(tx0, "Active Listings EOM"),
    "inventory": fval(tx0, "Months Inventory"),
}

metro_keys = ["DFW", "Austin", "San Antonio", "El Paso"]
metro_kpis = {}
for m in metro_keys:
    r = data[m][0]
    metro_kpis[m] = {
        "sales":     ival(r, "Sales"),
        "sales_yoy": fval(r, "Sales YoY%") * 100,
        "volume":    fval(r, "Dollar Volume"),
        "med_price": ival(r, "Median Price"),
        "avg_price": ival(r, "Average Price"),
        "listings":  ival(r, "Active Listings EOM"),
        "inventory": fval(r, "Months Inventory"),
    }

# ── last 18 months for charts ─────────────────────────────────────────────────

N = 18

def series(market, key, pct=False, n=N):
    rows = data[market][:n][::-1]
    vals = [round(fval(r, key) * (100 if pct else 1), 2) for r in rows]
    return vals

def labels_for(market, n=N):
    rows = data[market][:n][::-1]
    return [month_label(r["_date"]) for r in rows]

chart_labels = labels_for("Texas")

chart_data = {
    "labels": chart_labels,
    "tx": {
        "sales":    series("Texas", "Sales"),
        "medPrice": series("Texas", "Median Price"),
        "inv":      series("Texas", "Months Inventory"),
        "yoy":      series("Texas", "Sales YoY%", pct=True),
    },
    "dfw": {
        "sales":    series("DFW", "Sales"),
        "medPrice": series("DFW", "Median Price"),
        "inv":      series("DFW", "Months Inventory"),
        "yoy":      series("DFW", "Sales YoY%", pct=True),
    },
    "austin": {
        "sales":    series("Austin", "Sales"),
        "medPrice": series("Austin", "Median Price"),
        "inv":      series("Austin", "Months Inventory"),
        "yoy":      series("Austin", "Sales YoY%", pct=True),
    },
    "sa": {
        "sales":    series("San Antonio", "Sales"),
        "medPrice": series("San Antonio", "Median Price"),
        "inv":      series("San Antonio", "Months Inventory"),
        "yoy":      series("San Antonio", "Sales YoY%", pct=True),
    },
    "ep": {
        "sales":    series("El Paso", "Sales"),
        "medPrice": series("El Paso", "Median Price"),
        "inv":      series("El Paso", "Months Inventory"),
        "yoy":      series("El Paso", "Sales YoY%", pct=True),
    },
}

# ── helper: signed arrow ──────────────────────────────────────────────────────

def arrow(n):
    return ("&#9650;" if n >= 0 else "&#9660;")

def sign_class(n):
    return "positive" if n >= 0 else "negative"

# ── build HTML ────────────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Texas Real Estate Market Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
  .header{{background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);border-bottom:1px solid #334155;padding:20px 32px;display:flex;justify-content:space-between;align-items:center}}
  .header h1{{font-size:22px;font-weight:700;color:#f1f5f9}}
  .header p{{font-size:13px;color:#64748b;margin-top:3px}}
  .badge{{background:#14b8a6;color:#fff;font-size:11px;font-weight:600;padding:4px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:.5px}}
  .date-badge{{background:#1e293b;border:1px solid #334155;color:#94a3b8;font-size:12px;padding:4px 12px;border-radius:6px}}
  .container{{padding:24px 32px;max-width:1400px;margin:0 auto}}
  .section-title{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#64748b;margin-bottom:14px;margin-top:28px;display:flex;align-items:center;gap:8px}}
  .section-title::after{{content:'';flex:1;height:1px;background:#1e293b}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}}
  .kpi-card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px 18px;position:relative;overflow:hidden}}
  .kpi-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px}}
  .kpi-card.teal::before{{background:#14b8a6}}.kpi-card.blue::before{{background:#3b82f6}}
  .kpi-card.purple::before{{background:#a855f7}}.kpi-card.orange::before{{background:#f97316}}
  .kpi-card.rose::before{{background:#f43f5e}}.kpi-card.amber::before{{background:#f59e0b}}
  .kpi-label{{font-size:11px;color:#64748b;font-weight:500;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
  .kpi-value{{font-size:22px;font-weight:700;color:#f1f5f9;line-height:1}}
  .kpi-sub{{font-size:12px;margin-top:6px;font-weight:500}}
  .positive{{color:#22c55e}}.negative{{color:#f43f5e}}.neutral{{color:#64748b}}
  .chart-grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  .chart-card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px}}
  .chart-title{{font-size:13px;font-weight:600;color:#cbd5e1;margin-bottom:4px}}
  .chart-subtitle{{font-size:11px;color:#475569;margin-bottom:16px}}
  .chart-wrap{{position:relative;height:200px}}
  .chart-wrap.tall{{height:240px}}
  .metro-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
  .metro-card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px}}
  .metro-name{{font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:4px}}
  .metro-tag{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:#475569;margin-bottom:14px}}
  .metro-stat{{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #0f172a}}
  .metro-stat:last-child{{border-bottom:none}}
  .metro-stat-label{{font-size:11px;color:#64748b}}
  .metro-stat-value{{font-size:12px;font-weight:600;color:#e2e8f0}}
  .metro-header-accent{{height:3px;border-radius:2px;margin-bottom:14px}}
  .legend{{display:flex;gap:20px;margin-bottom:14px;flex-wrap:wrap}}
  .legend-item{{display:flex;align-items:center;gap:6px;font-size:11px;color:#94a3b8}}
  .legend-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
  .updated{{font-size:10px;color:#334155;text-align:center;padding:16px 0 8px}}
  @media(max-width:1100px){{.kpi-grid{{grid-template-columns:repeat(3,1fr)}}.metro-grid{{grid-template-columns:repeat(2,1fr)}}}}
  @media(max-width:700px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}.chart-grid-2{{grid-template-columns:1fr}}.metro-grid{{grid-template-columns:1fr}}.container{{padding:16px}}}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Texas Real Estate Market Dashboard</h1>
    <p>Statewide overview with Austin, DFW, San Antonio &amp; El Paso breakdowns</p>
  </div>
  <div style="display:flex;align-items:center;gap:10px">
    <span class="badge">Auto-Updated</span>
    <span class="date-badge">Through {as_of}</span>
  </div>
</div>

<div class="container">

  <div class="section-title">Texas Statewide Overview &mdash; {as_of}</div>

  <div class="kpi-grid">
    <div class="kpi-card teal">
      <div class="kpi-label">Closed Sales</div>
      <div class="kpi-value">{fmt_num(tx_kpis['sales'])}</div>
      <div class="kpi-sub {sign_class(tx_kpis['sales_yoy'])}">{arrow(tx_kpis['sales_yoy'])} {fmt_pct(tx_kpis['sales_yoy'])} YoY</div>
    </div>
    <div class="kpi-card blue">
      <div class="kpi-label">Dollar Volume</div>
      <div class="kpi-value">{fmt_dollar(tx_kpis['volume'])}</div>
      <div class="kpi-sub {sign_class(tx_kpis['vol_yoy'])}">{arrow(tx_kpis['vol_yoy'])} {fmt_pct(tx_kpis['vol_yoy'])} YoY</div>
    </div>
    <div class="kpi-card purple">
      <div class="kpi-label">Median Price</div>
      <div class="kpi-value">${tx_kpis['med_price']:,}</div>
      <div class="kpi-sub neutral">Avg: ${tx_kpis['avg_price']:,}</div>
    </div>
    <div class="kpi-card orange">
      <div class="kpi-label">Avg Sale Price</div>
      <div class="kpi-value">${tx_kpis['avg_price']:,}</div>
      <div class="kpi-sub neutral">Median: ${tx_kpis['med_price']:,}</div>
    </div>
    <div class="kpi-card amber">
      <div class="kpi-label">Active Listings</div>
      <div class="kpi-value">{fmt_num(tx_kpis['listings'])}</div>
      <div class="kpi-sub neutral">End of Month</div>
    </div>
    <div class="kpi-card rose">
      <div class="kpi-label">Months Inventory</div>
      <div class="kpi-value">{tx_kpis['inventory']:.2f}</div>
      <div class="kpi-sub neutral">Balanced Market</div>
    </div>
  </div>

  <div class="chart-grid-2" style="margin-top:16px">
    <div class="chart-card">
      <div class="chart-title">Closed Sales &mdash; Texas Statewide</div>
      <div class="chart-subtitle">Monthly closed sales, {N}-month trend</div>
      <div class="chart-wrap"><canvas id="txSalesChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Months of Inventory &mdash; Texas</div>
      <div class="chart-subtitle">Supply trend (6 mo = balanced market)</div>
      <div class="chart-wrap"><canvas id="txInvChart"></canvas></div>
    </div>
  </div>

  <div class="chart-grid-2" style="margin-top:16px">
    <div class="chart-card">
      <div class="chart-title">Sales YoY Growth &mdash; Texas</div>
      <div class="chart-subtitle">Year-over-year change in closed sales (%)</div>
      <div class="chart-wrap"><canvas id="txYoyChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Median Price &mdash; Texas</div>
      <div class="chart-subtitle">Monthly median sale price ($)</div>
      <div class="chart-wrap"><canvas id="txPriceChart"></canvas></div>
    </div>
  </div>

  <div class="section-title" style="margin-top:32px">Metro Market Comparison &mdash; {as_of}</div>

  <div class="metro-grid">
"""

# metro cards
metro_cfg = {
    "DFW":         {"color": "#3b82f6", "tag": "Largest Texas Market"},
    "Austin":      {"color": "#14b8a6", "tag": "High-Value Market"},
    "San Antonio": {"color": "#f97316", "tag": "Strong YoY Growth"},
    "El Paso":     {"color": "#a855f7", "tag": "Most Affordable Market"},
}

for m in metro_keys:
    k  = metro_kpis[m]
    cfg= metro_cfg[m]
    html += f"""
    <div class="metro-card">
      <div class="metro-header-accent" style="background:{cfg['color']}"></div>
      <div class="metro-name">{m}</div>
      <div class="metro-tag">{cfg['tag']}</div>
      <div class="metro-stat"><span class="metro-stat-label">Closed Sales</span>
        <span class="metro-stat-value">{fmt_num(k['sales'])} <span class="{sign_class(k['sales_yoy'])}" style="font-size:10px">{arrow(k['sales_yoy'])} {fmt_pct(k['sales_yoy'])}</span></span></div>
      <div class="metro-stat"><span class="metro-stat-label">Dollar Volume</span>
        <span class="metro-stat-value">{fmt_dollar(k['volume'])}</span></div>
      <div class="metro-stat"><span class="metro-stat-label">Median Price</span>
        <span class="metro-stat-value">${k['med_price']:,}</span></div>
      <div class="metro-stat"><span class="metro-stat-label">Avg Price</span>
        <span class="metro-stat-value">${k['avg_price']:,}</span></div>
      <div class="metro-stat"><span class="metro-stat-label">Active Listings</span>
        <span class="metro-stat-value">{fmt_num(k['listings'])}</span></div>
      <div class="metro-stat"><span class="metro-stat-label">Months Inventory</span>
        <span class="metro-stat-value">{k['inventory']:.2f}</span></div>
    </div>"""

html += """
  </div>

  <div class="chart-grid-2" style="margin-top:16px">
    <div class="chart-card">
      <div class="chart-title">Closed Sales by Metro</div>
      <div class="chart-subtitle">Monthly closed sales comparison</div>
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div>DFW</div>
        <div class="legend-item"><div class="legend-dot" style="background:#14b8a6"></div>Austin</div>
        <div class="legend-item"><div class="legend-dot" style="background:#f97316"></div>San Antonio</div>
        <div class="legend-item"><div class="legend-dot" style="background:#a855f7"></div>El Paso</div>
      </div>
      <div class="chart-wrap tall"><canvas id="metroSalesChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Months of Inventory by Metro</div>
      <div class="chart-subtitle">Supply levels, 18-month trend</div>
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div>DFW</div>
        <div class="legend-item"><div class="legend-dot" style="background:#14b8a6"></div>Austin</div>
        <div class="legend-item"><div class="legend-dot" style="background:#f97316"></div>San Antonio</div>
        <div class="legend-item"><div class="legend-dot" style="background:#a855f7"></div>El Paso</div>
      </div>
      <div class="chart-wrap tall"><canvas id="metroInvChart"></canvas></div>
    </div>
  </div>

  <div class="chart-card" style="margin-top:16px">
    <div class="chart-title">Sales YoY Growth by Metro</div>
    <div class="chart-subtitle">Year-over-year change in closed sales (%)</div>
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div>DFW</div>
      <div class="legend-item"><div class="legend-dot" style="background:#14b8a6"></div>Austin</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f97316"></div>San Antonio</div>
      <div class="legend-item"><div class="legend-dot" style="background:#a855f7"></div>El Paso</div>
    </div>
    <div class="chart-wrap" style="height:210px"><canvas id="metroYoyChart"></canvas></div>
  </div>

  <div class="chart-card" style="margin-top:16px;margin-bottom:32px">
    <div class="chart-title">Median Sale Price by Metro</div>
    <div class="chart-subtitle">Monthly median price comparison ($)</div>
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div>DFW</div>
      <div class="legend-item"><div class="legend-dot" style="background:#14b8a6"></div>Austin</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f97316"></div>San Antonio</div>
      <div class="legend-item"><div class="legend-dot" style="background:#a855f7"></div>El Paso</div>
    </div>
    <div class="chart-wrap" style="height:210px"><canvas id="metroPriceChart"></canvas></div>
  </div>

</div>
"""

html += f"""
<div class="updated">Dashboard auto-generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")} &mdash; data through {as_of}</div>

<script>
const D = {json.dumps(chart_data)};
Chart.defaults.color='#64748b';
Chart.defaults.borderColor='#1e293b';
Chart.defaults.font.family="'Segoe UI',system-ui,sans-serif";
Chart.defaults.font.size=11;

const TT = (extra={{}}) => ({{
  backgroundColor:'#0f172a',borderColor:'#334155',borderWidth:1,
  titleColor:'#f1f5f9',bodyColor:'#94a3b8',padding:10,...extra
}});
const XSCALE = {{grid:{{color:'#1e293b'}},ticks:{{maxRotation:45,font:{{size:10}}}}}};
const YSCALE = (cb) => ({{grid:{{color:'#1e293b'}},ticks:{{callback:cb}}}});

const fmtK = v => v>=1000?(v/1000).toFixed(0)+'K':v;
const fmtP = v => (v>=0?'+':'')+v.toFixed(1)+'%';
const fmtPr= v => '$'+(v/1000).toFixed(0)+'K';
const fmtI = v => v.toFixed(2);

// TX Sales
new Chart('txSalesChart',{{type:'bar',data:{{labels:D.labels,datasets:[{{
  label:'Closed Sales',data:D.tx.sales,
  backgroundColor:D.labels.map((_,i)=>i===D.labels.length-1?'#14b8a6':'#14b8a620'),
  borderColor:'#14b8a6',borderWidth:1,borderRadius:3
}}]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>`  Sales: ${{c.raw.toLocaleString()}}`}}}}}},
  scales:{{x:XSCALE,y:YSCALE(fmtK)}}}}}});

// TX Inventory
new Chart('txInvChart',{{type:'line',data:{{labels:D.labels,datasets:[
  {{label:'Months Inventory',data:D.tx.inv,borderColor:'#f59e0b',backgroundColor:'#f59e0b15',fill:true,tension:.3,pointRadius:2,borderWidth:2}},
  {{label:'Balanced (6)',data:D.labels.map(()=>6),borderColor:'#334155',borderDash:[4,4],borderWidth:1,pointRadius:0,fill:false}}
]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>c.dataset.label==='Balanced (6)'?null:`  ${{c.dataset.label}}: ${{fmtI(c.raw)}} mo`}}}}}},
  scales:{{x:XSCALE,y:YSCALE(fmtI)}}}}}});

// TX YoY
new Chart('txYoyChart',{{type:'bar',data:{{labels:D.labels,datasets:[{{
  label:'YoY %',data:D.tx.yoy,
  backgroundColor:D.tx.yoy.map(v=>v>=0?'#22c55e30':'#f43f5e30'),
  borderColor:D.tx.yoy.map(v=>v>=0?'#22c55e':'#f43f5e'),borderWidth:1,borderRadius:3
}}]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>`  YoY: ${{fmtP(c.raw)}}`}}}}}},
  scales:{{x:XSCALE,y:YSCALE(fmtP)}}}}}});

// TX Price
new Chart('txPriceChart',{{type:'line',data:{{labels:D.labels,datasets:[{{
  label:'Median Price',data:D.tx.medPrice,borderColor:'#a855f7',backgroundColor:'#a855f715',fill:true,tension:.3,pointRadius:2,borderWidth:2
}}]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>`  Median: $${{c.raw.toLocaleString()}}`}}}}}},
  scales:{{x:XSCALE,y:YSCALE(fmtPr)}}}}}});

// Metro Sales
new Chart('metroSalesChart',{{type:'line',data:{{labels:D.labels,datasets:[
  {{label:'DFW',        data:D.dfw.sales,   borderColor:'#3b82f6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'Austin',     data:D.austin.sales, borderColor:'#14b8a6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'San Antonio',data:D.sa.sales,    borderColor:'#f97316',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'El Paso',    data:D.ep.sales,    borderColor:'#a855f7',tension:.3,pointRadius:1,borderWidth:2,fill:false}}
]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>`  ${{c.dataset.label}}: ${{c.raw.toLocaleString()}}`}}}}}},
  scales:{{x:XSCALE,y:YSCALE(fmtK)}}}}}});

// Metro Inventory
new Chart('metroInvChart',{{type:'line',data:{{labels:D.labels,datasets:[
  {{label:'DFW',        data:D.dfw.inv,   borderColor:'#3b82f6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'Austin',     data:D.austin.inv, borderColor:'#14b8a6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'San Antonio',data:D.sa.inv,    borderColor:'#f97316',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'El Paso',    data:D.ep.inv,    borderColor:'#a855f7',tension:.3,pointRadius:1,borderWidth:2,fill:false}}
]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>`  ${{c.dataset.label}}: ${{fmtI(c.raw)}} mo`}}}}}},
  scales:{{x:XSCALE,y:{{...YSCALE(v=>v.toFixed(1)+' mo'),min:2}}}}}}}});

// Metro YoY
new Chart('metroYoyChart',{{type:'line',data:{{labels:D.labels,datasets:[
  {{label:'DFW',        data:D.dfw.yoy,   borderColor:'#3b82f6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'Austin',     data:D.austin.yoy, borderColor:'#14b8a6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'San Antonio',data:D.sa.yoy,    borderColor:'#f97316',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'El Paso',    data:D.ep.yoy,    borderColor:'#a855f7',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'0%',data:D.labels.map(()=>0),borderColor:'#334155',borderDash:[4,4],borderWidth:1,pointRadius:0,fill:false}}
]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>c.dataset.label==='0%'?null:`  ${{c.dataset.label}}: ${{fmtP(c.raw)}}`}}}}}},
  scales:{{x:XSCALE,y:YSCALE(fmtP)}}}}}});

// Metro Price
new Chart('metroPriceChart',{{type:'line',data:{{labels:D.labels,datasets:[
  {{label:'DFW',        data:D.dfw.medPrice,   borderColor:'#3b82f6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'Austin',     data:D.austin.medPrice, borderColor:'#14b8a6',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'San Antonio',data:D.sa.medPrice,    borderColor:'#f97316',tension:.3,pointRadius:1,borderWidth:2,fill:false}},
  {{label:'El Paso',    data:D.ep.medPrice,    borderColor:'#a855f7',tension:.3,pointRadius:1,borderWidth:2,fill:false}}
]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},tooltip:{{...TT(),callbacks:{{label:c=>`  ${{c.dataset.label}}: $${{c.raw.toLocaleString()}}`}}}}}},
  scales:{{x:XSCALE,y:YSCALE(fmtPr)}}}}}});
</script>
</body>
</html>"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Dashboard written to: {OUTPUT}")
print(f"Data through: {as_of}")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
