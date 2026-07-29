"""
Trading Dashboard
==================
Real-time web UI for monitoring trading performance.

Features:
1. Live P&L tracking
2. Position status
3. Signal overview
4. Performance charts
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
from pathlib import Path
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from loguru import logger

# Try to import Flask, fall back to simple HTTP server
try:
    from flask import Flask, render_template_string, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


# Dashboard HTML template
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Trading Dashboard</title>
    <style>
        :root {
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --green: #3fb950;
            --red: #f85149;
            --blue: #58a6ff;
            --purple: #a371f7;
            --yellow: #d29922;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }
        
        .header h1 { font-size: 24px; }
        .header .time { color: var(--text-muted); }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }
        
        .card h2 {
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .stat {
            font-size: 32px;
            font-weight: bold;
        }
        
        .stat.positive { color: var(--green); }
        .stat.negative { color: var(--red); }
        
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }
        
        .stat-row:last-child { border-bottom: none; }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-active { background: rgba(63, 185, 80, 0.2); color: var(--green); }
        .status-waiting { background: rgba(210, 153, 34, 0.2); color: var(--yellow); }
        .status-stopped { background: rgba(248, 81, 73, 0.2); color: var(--red); }
        
        .position-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .position-table th, .position-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        
        .position-table th {
            color: var(--text-muted);
            font-weight: normal;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .signal {
            display: flex;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: rgba(88, 166, 255, 0.1);
            border-radius: 8px;
        }
        
        .signal.bullish { background: rgba(63, 185, 80, 0.1); }
        .signal.bearish { background: rgba(248, 81, 73, 0.1); }
        
        .signal-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        .signal-dot.bullish { background: var(--green); }
        .signal-dot.bearish { background: var(--red); }
        .signal-dot.neutral { background: var(--text-muted); }
        
        .chart-placeholder {
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(88, 166, 255, 0.05);
            border-radius: 8px;
            color: var(--text-muted);
        }
        
        .refresh-btn {
            background: var(--blue);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .refresh-btn:hover { opacity: 0.8; }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .live-dot {
            width: 8px; height: 8px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 2s infinite;
            display: inline-block;
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Trading Dashboard</h1>
        <div style="display: flex; align-items: center; gap: 20px;">
            <span class="time" id="time"></span>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>📊 Today's P&L</h2>
            <div class="stat positive" id="daily-pnl">+$0.00</div>
            <div style="color: var(--text-muted); margin-top: 5px;" id="daily-pnl-pct">+0.00%</div>
        </div>
        
        <div class="card">
            <h2>💰 Total Balance</h2>
            <div class="stat" id="balance">$10,000.00</div>
            <div style="color: var(--text-muted); margin-top: 5px;" id="initial">Initial: $10,000</div>
        </div>
        
        <div class="card">
            <h2>📈 Win Rate</h2>
            <div class="stat" id="win-rate">0%</div>
            <div style="color: var(--text-muted); margin-top: 5px;" id="trades">0 trades today</div>
        </div>
        
        <div class="card">
            <h2>🏃 Bot Status</h2>
            <div style="display: flex; align-items: center;">
                <span class="live-dot"></span>
                <span class="status-badge status-active" id="status">ACTIVE</span>
            </div>
            <div style="color: var(--text-muted); margin-top: 10px;" id="next-action">Next: Scanning...</div>
        </div>
    </div>
    
    <div class="grid">
        <div class="card" style="grid-column: span 2;">
            <h2>📋 Open Positions</h2>
            <table class="position-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Qty</th>
                        <th>Entry</th>
                        <th>Current</th>
                        <th>P&L</th>
                        <th>Stop</th>
                    </tr>
                </thead>
                <tbody id="positions">
                    <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No open positions</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📡 Latest Signals</h2>
            <div id="signals">
                <div class="signal bullish">
                    <span class="signal-dot bullish"></span>
                    <span>AAPL: STRONG_BUY (Score: 78)</span>
                </div>
                <div class="signal">
                    <span class="signal-dot neutral"></span>
                    <span>NVDA: HOLD (Score: 52)</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>🌐 Market Regime</h2>
            <div class="stat-row">
                <span>Macro Score</span>
                <span class="positive" id="macro-score">+25</span>
            </div>
            <div class="stat-row">
                <span>Sector Rotation</span>
                <span id="sector">RISK_ON</span>
            </div>
            <div class="stat-row">
                <span>Fear & Greed</span>
                <span id="fear-greed">45 (Neutral)</span>
            </div>
            <div class="stat-row">
                <span>VIX</span>
                <span id="vix">18.5</span>
            </div>
        </div>
        
        <div class="card">
            <h2>📅 Today's Activity</h2>
            <div class="stat-row">
                <span>Scans</span>
                <span id="scans">5</span>
            </div>
            <div class="stat-row">
                <span>Signals Generated</span>
                <span id="signals-count">12</span>
            </div>
            <div class="stat-row">
                <span>Trades Executed</span>
                <span id="trades-executed">2</span>
            </div>
            <div class="stat-row">
                <span>Risk Used</span>
                <span id="risk-used">15%</span>
            </div>
        </div>
        
        <div class="card">
            <h2>⚠️ Alerts</h2>
            <div id="alerts">
                <div style="padding: 10px; background: rgba(210, 153, 34, 0.1); border-radius: 8px; margin: 5px 0;">
                    ⚠️ FOMC meeting in 3 days
                </div>
                <div style="padding: 10px; background: rgba(63, 185, 80, 0.1); border-radius: 8px; margin: 5px 0;">
                    ✅ All systems operational
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('time').textContent = now.toLocaleString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
        
        function refreshData() {
            // In production, this would fetch from the API
            console.log('Refreshing data...');
            // Simulate data update
            fetch('/api/status').then(r => r.json()).then(data => {
                if (data.daily_pnl) {
                    const pnl = data.daily_pnl;
                    const elem = document.getElementById('daily-pnl');
                    elem.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
                    elem.className = 'stat ' + (pnl >= 0 ? 'positive' : 'negative');
                }
            }).catch(() => console.log('API not available'));
        }
        
        setInterval(updateTime, 1000);
        updateTime();
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
'''


class DashboardData:
    """Dashboard data container"""
    def __init__(self):
        self.daily_pnl = 0.0
        self.daily_pnl_pct = 0.0
        self.balance = 10000.0
        self.initial_balance = 10000.0
        self.win_rate = 0.0
        self.trades_today = 0
        self.status = "ACTIVE"
        self.next_action = "Scanning..."
        self.positions = []
        self.signals = []
        self.macro_score = 0
        self.sector_regime = "MIXED"
        self.fear_greed = 50
        self.vix = 20.0
        self.alerts = []


class TradingDashboard:
    """
    Web-based Trading Dashboard
    
    Features:
    - Real-time P&L display
    - Position monitoring
    - Signal visualization
    - Market regime indicators
    """
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.data = DashboardData()
        self._server = None
        self._server_thread = None
        
        # Create static files directory
        self.static_dir = Path(__file__).parent / "dashboard_static"
        self.static_dir.mkdir(exist_ok=True)
        
        # Write HTML file
        (self.static_dir / "index.html").write_text(DASHBOARD_HTML)
    
    def update_pnl(self, daily_pnl: float, daily_pct: float):
        """Update P&L"""
        self.data.daily_pnl = daily_pnl
        self.data.daily_pnl_pct = daily_pct
    
    def update_balance(self, balance: float):
        """Update balance"""
        self.data.balance = balance
    
    def update_positions(self, positions: List[dict]):
        """Update positions"""
        self.data.positions = positions
    
    def update_signals(self, signals: List[dict]):
        """Update signals"""
        self.data.signals = signals
    
    def update_status(self, status: str, next_action: str = ""):
        """Update bot status"""
        self.data.status = status
        if next_action:
            self.data.next_action = next_action
    
    def update_market(self, macro_score: float, sector: str, fg: int, vix: float):
        """Update market indicators"""
        self.data.macro_score = macro_score
        self.data.sector_regime = sector
        self.data.fear_greed = fg
        self.data.vix = vix
    
    def add_alert(self, message: str, alert_type: str = "info"):
        """Add alert"""
        self.data.alerts.append({
            'message': message,
            'type': alert_type,
            'time': datetime.now().isoformat()
        })
        # Keep last 10 alerts
        self.data.alerts = self.data.alerts[-10:]
    
    def get_data_json(self) -> dict:
        """Get dashboard data as JSON"""
        return {
            'daily_pnl': self.data.daily_pnl,
            'daily_pnl_pct': self.data.daily_pnl_pct,
            'balance': self.data.balance,
            'win_rate': self.data.win_rate,
            'trades_today': self.data.trades_today,
            'status': self.data.status,
            'next_action': self.data.next_action,
            'positions': self.data.positions,
            'signals': self.data.signals,
            'macro_score': self.data.macro_score,
            'sector_regime': self.data.sector_regime,
            'fear_greed': self.data.fear_greed,
            'vix': self.data.vix,
            'alerts': self.data.alerts,
            'timestamp': datetime.now().isoformat()
        }
    
    def start(self, open_browser: bool = True):
        """Start dashboard server"""
        if FLASK_AVAILABLE:
            self._start_flask(open_browser)
        else:
            self._start_simple(open_browser)
    
    def _start_flask(self, open_browser: bool):
        """Start Flask server"""
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return render_template_string(DASHBOARD_HTML)
        
        @app.route('/api/status')
        def status():
            return jsonify(self.get_data_json())
        
        logger.info("Starting Flask dashboard on http://localhost:{}", self.port)
        
        if open_browser:
            threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{self.port}')).start()
        
        app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def _start_simple(self, open_browser: bool):
        """Start simple HTTP server"""
        os.chdir(self.static_dir)
        
        handler = SimpleHTTPRequestHandler
        self._server = HTTPServer(('', self.port), handler)
        
        logger.info("Starting simple dashboard on http://localhost:{}", self.port)
        
        if open_browser:
            threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{self.port}')).start()
        
        self._server.serve_forever()
    
    def stop(self):
        """Stop dashboard server"""
        if self._server:
            self._server.shutdown()


# Global instance
_dashboard = None

def get_dashboard(port: int = 8080) -> TradingDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = TradingDashboard(port)
    return _dashboard


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Starting Trading Dashboard...")
    print("Open http://localhost:8080 in your browser")
    print("Press Ctrl+C to stop")
    
    dashboard = TradingDashboard(port=8080)
    
    # Set some demo data
    dashboard.update_pnl(245.50, 2.45)
    dashboard.update_balance(10245.50)
    dashboard.update_market(25, "RISK_ON", 42, 18.5)
    dashboard.add_alert("Bot started successfully", "success")
    
    try:
        dashboard.start(open_browser=True)
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        dashboard.stop()
