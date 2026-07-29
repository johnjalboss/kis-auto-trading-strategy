"""
Generate HTML dashboard from bot data JSON.
Usage: python generate_dashboard.py <input.json> <output.html>
"""
import json
import sys
from datetime import datetime

# Read data
if len(sys.argv) < 2:
    # Module imported without arguments — skip execution
    data = {"status": "OFFLINE", "positions": [], "buying_power": 0,
            "total_value": 0, "total_pnl": 0, "errors": "?",
            "log": "No input file", "timestamp": ""}
else:
    try:
        # Try multiple encodings (PowerShell > redirect creates UTF-16LE)
        content = None
        for enc in ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le']:
            try:
                with open(sys.argv[1], 'r', encoding=enc) as f:
                    content = f.read().strip()
                if content:
                    # Strip any null bytes that might remain
                    content = content.replace('\x00', '').strip()
                    data = json.loads(content)
                    break
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        if content is None or not content:
            raise ValueError("Could not read file with any encoding")
    except Exception as e:
        data = {"status": "OFFLINE", "positions": [], "buying_power": 0, 
                "total_value": 0, "total_pnl": 0, "errors": "?", 
                "log": f"Error: {e}", "timestamp": ""}

status = data.get("status", "OFFLINE")
bp = data.get("buying_power", 0)
tv = data.get("total_value", 0)
pnl = data.get("total_pnl", 0)
pnl_pct = (pnl / (tv - pnl) * 100) if (tv - pnl) > 0 else 0
avg_pnl_pct = data.get("avg_daily_pnl_pct", 0)

errors = data.get("errors", "?")
log = data.get("log", "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
ts = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

status_color = "#3fb950" if status == "active" else "#f85149"
pnl_color = "#3fb950" if pnl >= 0 else "#f85149"
pnl_sign = "+" if pnl >= 0 else ""

avg_pnl_color = "#3fb950" if avg_pnl_pct >= 0 else "#f85149"
avg_pnl_sign = "+" if avg_pnl_pct >= 0 else ""

# Position rows
pos_rows = ""
for p in data.get("positions", []):
    pc = "#3fb950" if p["pnl_pct"] >= 0 else "#f85149"
    ps = "+" if p["pnl_pct"] >= 0 else ""
    unrealized = (p["current"] - p["entry"]) * p["qty"]
    us = "+" if unrealized >= 0 else ""
    pos_rows += f'''<tr>
        <td style="font-weight:bold;color:#58a6ff">{p["symbol"]}</td>
        <td>{p["qty"]}</td>
        <td>${p["entry"]:.2f}</td>
        <td>${p["current"]:.2f}</td>
        <td style="color:{pc};font-weight:bold">{ps}{p["pnl_pct"]:.2f}% (<b>{us}${abs(unrealized):.2f}</b>)</td>
        <td>{us}${abs(unrealized):.2f}</td>
        <td>${p["value"]:.2f}</td>
    </tr>'''

if not pos_rows:
    pos_rows = '<tr><td colspan="7" style="text-align:center;color:#8b949e;padding:20px">No positions</td></tr>'

html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>KIS Trading Bot Dashboard</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0d1117; color:#c9d1d9; padding:30px; min-height:100vh }}
.header {{ display:flex; justify-content:space-between; align-items:center; padding-bottom:15px; border-bottom:1px solid #30363d; margin-bottom:20px }}
.header h1 {{ font-size:22px }}
.grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:15px; margin-bottom:20px }}
.card {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px; transition:border-color 0.2s }}
.card:hover {{ border-color:#58a6ff }}
.card h3 {{ font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px }}
.big {{ font-size:28px; font-weight:bold }}
table {{ width:100%; border-collapse:collapse }}
th,td {{ padding:12px 14px; text-align:left; border-bottom:1px solid #21262d }}
th {{ color:#8b949e; font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:600 }}
.log {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:18px;
      font-family:Consolas,'Courier New',monospace; font-size:11px; line-height:1.7; 
      max-height:350px; overflow-y:auto; margin-top:20px; word-wrap:break-word }}
.status {{ display:inline-flex; align-items:center; gap:8px; padding:5px 16px; border-radius:20px; font-size:12px; font-weight:bold }}
.dot {{ width:8px; height:8px; border-radius:50%; animation:pulse 2s infinite }}
.btn-group {{ display:flex; gap:8px; margin-bottom:15px }}
.btn {{ background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:6px 14px; border-radius:6px; 
       font-size:11px; font-weight:600; cursor:pointer; transition:all 0.2s }}
.btn:hover {{ background:#30363d; border-color:#8b949e }}
.btn.active {{ background:#238636; border-color:#2ea043; color:white }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}
.footer {{ text-align:center; color:#484f58; margin-top:25px; font-size:11px }}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head><body>

<div class="header">
  <h1>🚀 KIS Auto-Trading Bot</h1>
  <div>
    <span class="status" style="background:rgba({'63,185,80' if status=='active' else '248,81,73'},0.15);color:{status_color}">
      <span class="dot" style="background:{status_color}"></span>{status.upper()}
    </span>
    <span style="color:#8b949e;margin-left:15px;font-size:13px">{ts}</span>
  </div>
</div>

<div class="grid">
  <div class="card">
    <h3>💰 Total Portfolio</h3>
    <div class="big">${tv:,.2f}</div>
  </div>
  <div class="card">
    <h3>📈 Avg Daily Return (CAGR)</h3>
    <div class="big" style="color:{avg_pnl_color}">{avg_pnl_sign}{avg_pnl_pct:.2f}%</div>
    <div style="color:#8b949e;margin-top:4px;font-size:11px">Compound daily growth</div>
  </div>
  <div class="card">
    <h3>📊 Today's Net P&L</h3>
    <div class="big" style="color:{pnl_color}">{pnl_sign}${abs(pnl):,.2f}</div>
    <div style="color:{pnl_color};margin-top:4px;font-size:13px">{pnl_sign}{pnl_pct:.2f}%</div>
  </div>
  <div class="card">
    <h3>💵 Buying Power</h3>
    <div class="big">${bp:,.2f}</div>
  </div>
  <div class="card">
    <h3>⚠️ Fatal Errors</h3>
    <div class="big" style="color:{'#3fb950' if errors=='0' else '#f85149'}">{errors}</div>
  </div>
</div>

<div class="card" style="margin-bottom:20px">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px">
    <h3>📈 Historical Performance (Daily P&L)</h3>
    <div class="btn-group">
      <button class="btn" onclick="updateTimeframe(7, this)">1W</button>
      <button class="btn active" onclick="updateTimeframe(30, this)">1M</button>
      <button class="btn" onclick="updateTimeframe(180, this)">6M</button>
      <button class="btn" onclick="updateTimeframe(365, this)">1Y</button>
    </div>
  </div>
  <div style="height:350px; width:100%">
    <canvas id="pnlChart"></canvas>
  </div>
</div>

<div class="card">
  <h3>📋 Open Positions</h3>
  <table>
    <thead><tr><th>Symbol</th><th>Qty</th><th>Entry</th><th>Current</th><th>P&L %</th><th>Unrealized</th><th>Value</th></tr></thead>
    <tbody>{pos_rows}</tbody>
  </table>
</div>

<div class="log">
  <div style="color:#8b949e;font-weight:bold;margin-bottom:10px">📜 Recent Server Log</div>
  {log}
</div>

<div class="footer">
  봇현황.bat 을 다시 더블클릭하면 새로고침됩니다 | Oracle Server: 141.148.172.12
</div>

<script>
  const fullHistoryData = {json.dumps(data.get("history", []))};
  let myChart = null;

  function updateTimeframe(days, btn) {{
    document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const filteredData = fullHistoryData.slice(-days);
    const labels = filteredData.map(d => d.date);
    const pnlData = filteredData.map(d => d.net_pnl || 0);

    // Cumulative P&L
    let cumulativeOffset = fullHistoryData
      .slice(0, fullHistoryData.length - filteredData.length)
      .reduce((a, b) => a + (b.net_pnl || 0), 0);
    let cumPnL = [];
    let runSum = cumulativeOffset;
    for (const v of pnlData) {{
      runSum += v;
      cumPnL.push(runSum);
    }}

    const positiveColor = 'rgba(63, 185, 80, 0.75)';
    const negativeColor = 'rgba(248, 81, 73, 0.75)';
    const positiveBorder = 'rgb(63, 185, 80)';
    const negativeBorder = 'rgb(248, 81, 73)';
    const bgColors = pnlData.map(v => v >= 0 ? positiveColor : negativeColor);
    const borderColors = pnlData.map(v => v >= 0 ? positiveBorder : negativeBorder);

    const ctx = document.getElementById('pnlChart').getContext('2d');

    // Gradient for cumulative line
    const gradient = ctx.createLinearGradient(0, 0, 0, 350);
    gradient.addColorStop(0, 'rgba(88, 166, 255, 0.3)');
    gradient.addColorStop(1, 'rgba(88, 166, 255, 0.0)');

    const config = {{
      data: {{
        labels: labels,
        datasets: [
          {{
            type: 'line',
            label: '누적 수익',
            data: cumPnL,
            borderColor: '#58a6ff',
            backgroundColor: gradient,
            borderWidth: 2.5,
            pointRadius: days > 60 ? 0 : 4,
            pointHoverRadius: 6,
            pointBackgroundColor: '#58a6ff',
            pointBorderColor: '#0d1117',
            pointBorderWidth: 2,
            tension: 0.35,
            fill: true,
            yAxisID: 'y1',
            order: 1
          }},
          {{
            type: 'bar',
            label: '일일 순손익',
            data: pnlData,
            backgroundColor: bgColors,
            borderColor: borderColors,
            borderWidth: 1.5,
            borderRadius: 4,
            borderSkipped: false,
            yAxisID: 'y',
            order: 2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
          mode: 'index',
          intersect: false
        }},
        plugins: {{
          legend: {{
            labels: {{
              color: '#c9d1d9',
              font: {{ size: 12 }},
              usePointStyle: true,
              pointStyleWidth: 10,
              padding: 20
            }}
          }},
          tooltip: {{
            backgroundColor: 'rgba(22, 27, 34, 0.95)',
            borderColor: '#30363d',
            borderWidth: 1,
            titleColor: '#c9d1d9',
            bodyColor: '#8b949e',
            padding: 12,
            callbacks: {{
              label: function(ctx) {{
                const v = ctx.parsed.y;
                const sign = v >= 0 ? '+' : '';
                return ` ${{ctx.dataset.label}}: ${{sign}}$${{v.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}`;
              }}
            }}
          }}
        }},
        scales: {{
          y: {{
            type: 'linear',
            display: true,
            position: 'left',
            grid: {{ color: 'rgba(48, 54, 61, 0.6)', lineWidth: 1 }},
            ticks: {{
              color: '#8b949e',
              font: {{ size: 11 }},
              callback: v => (v >= 0 ? '+' : '') + '$' + v.toLocaleString()
            }},
            title: {{ display: true, text: '일일 손익', color: '#484f58', font: {{ size: 11 }} }}
          }},
          y1: {{
            type: 'linear',
            display: true,
            position: 'right',
            grid: {{ drawOnChartArea: false }},
            ticks: {{
              color: '#58a6ff',
              font: {{ size: 11 }},
              callback: v => '$' + v.toLocaleString()
            }},
            title: {{ display: true, text: '누적 수익', color: '#58a6ff', font: {{ size: 11 }} }}
          }},
          x: {{
            grid: {{ color: 'rgba(48, 54, 61, 0.4)', lineWidth: 1 }},
            ticks: {{
              color: '#8b949e',
              font: {{ size: 10 }},
              maxRotation: 45,
              minRotation: 30,
              autoSkip: true,
              maxTicksLimit: 14
            }}
          }}
        }},
        animation: {{
          duration: 400,
          easing: 'easeInOutQuart'
        }}
      }}
    }};

    if (!myChart) {{
      myChart = new Chart(ctx, config);
    }} else {{
      myChart.data.labels = labels;
      myChart.data.datasets[0].data = cumPnL;
      myChart.data.datasets[0].pointRadius = days > 60 ? 0 : 4;
      myChart.data.datasets[1].data = pnlData;
      myChart.data.datasets[1].backgroundColor = bgColors;
      myChart.data.datasets[1].borderColor = borderColors;
      myChart.update();
    }}
  }}

  if (fullHistoryData && fullHistoryData.length > 0) {{
    const initialBtn = document.querySelectorAll('.btn')[1];
    updateTimeframe(30, initialBtn);
  }} else {{
    document.getElementById('pnlChart').parentElement.innerHTML =
      '<div style="color:#8b949e;text-align:center;padding-top:100px;">📭 아직 데이터가 없습니다. 첫 거래 후 그래프가 생성됩니다.</div>';
  }}
</script>

</body></html>'''

output_path = sys.argv[2]
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Dashboard saved to {output_path}")
