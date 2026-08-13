"""
Real-Time Web Analytics Dashboard Server (v11.3.0 Live Account & Position Sync)
================================================================================
Lightweight HTTP dashboard running on port 8080.
Password-protected with cookie-based session authentication.
Syncs live data with Orchestrator, KIS Broker API, and trades.db.
"""

import http.server
import socketserver
import threading
import sqlite3
import os
import hashlib
import secrets
import time
from urllib.parse import parse_qs, unquote_plus
from datetime import datetime
from loguru import logger

PORT = 8080

# ─── 비밀번호 설정 ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(".env")
except Exception:
    pass

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "0201!")

# 세션 저장소 (메모리): {token: expire_timestamp}
_sessions: dict = {}
SESSION_DURATION = 86400  # 24시간

def _create_session() -> str:
    token = secrets.token_hex(32)
    _sessions[token] = time.time() + SESSION_DURATION
    return token

def _is_valid_session(token: str) -> bool:
    if not token:
        return False
    exp = _sessions.get(token, 0)
    if time.time() > exp:
        _sessions.pop(token, None)
        return False
    return True

def _get_cookie_token(cookie_header: str) -> str:
    for part in (cookie_header or "").split(";"):
        part = part.strip()
        if part.startswith("dash_session="):
            return part[len("dash_session="):]
    return ""

# ─── 로그인 페이지 HTML ──────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔐 Quant Master Dashboard Login</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .card {
            background: rgba(22, 27, 34, 0.98);
            border: 1px solid #30363d;
            border-radius: 16px;
            padding: 48px 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 24px 64px rgba(0,0,0,0.6);
        }
        .logo { text-align: center; font-size: 44px; margin-bottom: 8px; }
        .title { text-align: center; font-size: 20px; font-weight: 700; color: #58a6ff; margin-bottom: 4px; }
        .subtitle { text-align: center; font-size: 13px; color: #8b949e; margin-bottom: 10px; }
        .live-badge { text-align: center; margin-bottom: 32px; }
        .live-badge span {
            display: inline-block;
            background: rgba(35,134,54,0.2);
            border: 1px solid #238636;
            color: #3fb950;
            font-size: 11px;
            padding: 3px 12px;
            border-radius: 20px;
            font-weight: 600;
        }
        label { display: block; font-size: 12px; color: #8b949e; font-weight: 700;
                text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
        input[type=password] {
            width: 100%; padding: 14px 16px;
            background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
            color: #f0f6fc; font-size: 16px; font-family: inherit;
            outline: none; transition: border-color 0.2s, box-shadow 0.2s; margin-bottom: 24px;
        }
        input[type=password]:focus {
            border-color: #58a6ff;
            box-shadow: 0 0 0 3px rgba(88,166,255,0.15);
        }
        button {
            width: 100%; padding: 14px;
            background: linear-gradient(135deg, #238636, #2ea043);
            border: none; border-radius: 8px;
            color: white; font-size: 15px; font-weight: 700;
            cursor: pointer; transition: all 0.2s; font-family: inherit;
        }
        button:hover {
            background: linear-gradient(135deg, #2ea043, #3fb950);
            transform: translateY(-1px);
            box-shadow: 0 8px 24px rgba(46,160,67,0.4);
        }
        .error {
            background: rgba(248,81,73,0.1);
            border: 1px solid rgba(248,81,73,0.4);
            border-radius: 8px; color: #f85149;
            padding: 12px 16px; font-size: 13px;
            margin-bottom: 20px; text-align: center;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">⚡</div>
        <div class="title">Quant Bot Dashboard</div>
        <div class="subtitle">Ultra Institutional Trading System v11</div>
        <div class="live-badge"><span>● 24/7 LIVE</span></div>
        {ERROR_BLOCK}
        <form method="POST" action="/login">
            <label>Password</label>
            <input type="password" name="password" placeholder="비밀번호를 입력하세요" autofocus>
            <button type="submit">🔓 접속하기</button>
        </form>
    </div>
</body>
</html>"""

# ─── 대시보드 메인 HTML ──────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Institutional Ultra Quant Master Live Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #21262d; padding-bottom: 15px; margin-bottom: 20px; }
        .title { font-size: 24px; font-weight: bold; color: #58a6ff; }
        .badge { background-color: #238636; color: white; padding: 5px 12px; border-radius: 12px; font-size: 14px; font-weight: bold; }
        .header-right { display: flex; gap: 12px; align-items: center; }
        .logout-btn { background: #21262d; border: 1px solid #30363d; color: #8b949e; padding: 6px 14px; border-radius: 8px; font-size: 13px; cursor: pointer; text-decoration: none; font-weight: 600; }
        .logout-btn:hover { color: #f85149; border-color: #f85149; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .card { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
        .card-label { font-size: 12px; color: #8b949e; margin-bottom: 5px; text-transform: uppercase; font-weight: 600; }
        .card-value { font-size: 24px; font-weight: bold; color: #f0f6fc; }
        .card-sub { font-size: 13px; color: #3fb950; margin-top: 5px; font-weight: 600; }
        table { width: 100%; border-collapse: collapse; background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; margin-bottom: 25px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #21262d; }
        th { background-color: #21262d; color: #8b949e; font-size: 12px; text-transform: uppercase; }
        tr:hover { background-color: #1c2128; }
        .positive { color: #3fb950; font-weight: bold; }
        .negative { color: #f85149; font-weight: bold; }
        .neutral { color: #8b949e; }
        .logs-box { background-color: #090d16; border: 1px solid #30363d; border-radius: 8px; padding: 15px; font-family: monospace; font-size: 12px; height: 220px; overflow-y: auto; color: #8b949e; line-height: 1.5; }
    </style>
    <script>setTimeout(function(){ window.location.reload(); }, 10000);</script>
</head>
<body>
    <div class="header">
        <div class="title">⚡ v11.3 Ultra Quant Master Live Dashboard</div>
        <div class="header-right">
            <div class="badge">● 24/7 RUNNING</div>
            <a href="/logout" class="logout-btn">로그아웃</a>
        </div>
    </div>
    <div class="cards">
        <div class="card">
            <div class="card-label">Total Account Equity</div>
            <div class="card-value">${EQUITY}</div>
            <div class="card-sub">↑ Real-Time KIS Balance</div>
        </div>
        <div class="card">
            <div class="card-label">Available Buying Power</div>
            <div class="card-value">${CASH}</div>
            <div class="card-sub">Orderable Cash</div>
        </div>
        <div class="card">
            <div class="card-label">Active Open Positions</div>
            <div class="card-value">{POS_COUNT} 종목</div>
            <div class="card-sub">Portfolio Allocation Active</div>
        </div>
        <div class="card">
            <div class="card-label">System & Regime Status</div>
            <div class="card-value" style="font-size:18px">{REGIME}</div>
            <div class="card-sub">Session: {SESSION} | Risk: {RISK_LEVEL}</div>
        </div>
    </div>
    
    <div style="font-size:16px;font-weight:bold;margin-bottom:10px;color:#58a6ff;">📈 Current Open Positions</div>
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Avg Entry Price</th>
                <th>Current Price</th>
                <th>Unrealized PnL ($)</th>
                <th>PnL (%)</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>{POSITIONS_ROWS}</tbody>
    </table>

    <div style="font-size:16px;font-weight:bold;margin-bottom:10px;color:#58a6ff;">🔁 Recent Closed Trades & Execution Log</div>
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Price</th>
                <th>PnL ($)</th>
                <th>PnL (%)</th>
                <th>Strategy Reason</th>
            </tr>
        </thead>
        <tbody>{TRADES_ROWS}</tbody>
    </table>

    <div style="font-size:16px;font-weight:bold;margin-bottom:10px;color:#58a6ff;">📜 Live Execution Stream Logs</div>
    <div class="logs-box">{LOGS_HTML}</div>
</body>
</html>"""


class DashboardRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # 콘솔 로그 억제

    def _get_token(self) -> str:
        return _get_cookie_token(self.headers.get("Cookie", ""))

    def _redirect(self, location: str, extra_headers: list = None):
        self.send_response(302)
        self.send_header("Location", location)
        if extra_headers:
            for k, v in extra_headers:
                self.send_header(k, v)
        self.end_headers()

    def _serve_html(self, html: str, status: int = 200):
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        token = self._get_token()

        if self.path == "/logout":
            _sessions.pop(token, None)
            self._redirect("/login", [("Set-Cookie", "dash_session=; Max-Age=0; Path=/")])
            return

        if self.path == "/login":
            self._serve_html(LOGIN_HTML.replace("{ERROR_BLOCK}", ""))
            return

        if not _is_valid_session(token):
            self._redirect("/login")
            return

        if self.path in ["/", "/index.html"]:
            self._serve_html(render_dashboard_html())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            params = parse_qs(body)
            pw = unquote_plus(params.get("password", [""])[0])

            if pw == DASHBOARD_PASSWORD:
                token = _create_session()
                self._redirect("/", [
                    ("Set-Cookie", f"dash_session={token}; Max-Age={SESSION_DURATION}; Path=/; HttpOnly")
                ])
            else:
                error = '<div class="error">❌ 비밀번호가 올바르지 않습니다.</div>'
                self._serve_html(LOGIN_HTML.replace("{ERROR_BLOCK}", error))
        else:
            self.send_error(405)


def render_dashboard_html() -> str:
    """Fetches real-time DB, KIS API, and Orchestrator data to render HTML dashboard"""
    equity = 0.0
    cash = 0.0
    risk_level = "NORMAL"
    regime = "BULL_NORMAL"
    session = "REGULAR_MARKET"
    
    pos_rows = ""
    trades_rows = ""
    logs_html = "System initializing..."
    pos_count = 0

    # 1. Fetch live balance and positions directly using Trader API
    trader_obj = None
    live_positions = []
    try:
        from trader import Trader
        trader_obj = Trader()
        cash = trader_obj.get_buying_power()
        live_positions = trader_obj.get_positions()
    except Exception as e:
        logger.debug(f"Trader live fetch error: {e}")

    try:
        from orchestrator import get_orchestrator
        orch = get_orchestrator()
        if orch and hasattr(orch, 'state') and orch.state:
            regime = getattr(orch.state, 'current_regime', 'BULL_NORMAL')
            risk_level = getattr(orch.state, 'global_risk_level', 'NORMAL')
        if orch and hasattr(orch, 'get_current_session'):
            session = orch.get_current_session()
    except Exception as e:
        logger.debug(f"Orchestrator state bypass: {e}")

    pos_total_val = 0.0

    # 2. Render Open Positions (Prefer Live KIS Broker positions over DB)
    if live_positions:
        pos_count = len(live_positions)
        for p in live_positions:
            sym = p.symbol
            qty = p.quantity
            entry_p = p.avg_price
            curr_p = p.current_price if p.current_price > 0 else entry_p

            pnl_usd = (curr_p - entry_p) * qty
            pnl_pct = ((curr_p - entry_p) / entry_p * 100.0) if entry_p > 0 else 0.0
            pos_total_val += (curr_p * qty)

            cls_name = "positive" if pnl_pct >= 0 else "negative"
            sign = "+" if pnl_pct >= 0 else ""

            pos_rows += (
                f"<tr>"
                f"<td><b>{sym}</b></td>"
                f"<td>{qty}주</td>"
                f"<td>${entry_p:.2f}</td>"
                f"<td>${curr_p:.2f}</td>"
                f"<td class='{cls_name}'>${pnl_usd:+,.2f}</td>"
                f"<td class='{cls_name}'>{sign}{pnl_pct:.2f}%</td>"
                f"<td>🟢 KIS Live Holding</td>"
                f"</tr>"
            )
    else:
        # Fallback to trades.db positions table if API temporary offline
        try:
            db_path = "trades.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT symbol, quantity, avg_price FROM positions")
                db_positions = cur.fetchall()
                pos_count = len(db_positions)

                if db_positions:
                    for p in db_positions:
                        sym, qty, entry_p = p[0], p[1], float(p[2])
                        curr_p = entry_p
                        if trader_obj:
                            try:
                                live_p = trader_obj.get_price(sym)
                                if live_p > 0:
                                    curr_p = live_p
                            except Exception:
                                pass

                        pnl_usd = (curr_p - entry_p) * qty
                        pnl_pct = ((curr_p - entry_p) / entry_p * 100.0) if entry_p > 0 else 0.0
                        pos_total_val += (curr_p * qty)

                        cls_name = "positive" if pnl_pct >= 0 else "negative"
                        sign = "+" if pnl_pct >= 0 else ""

                        pos_rows += (
                            f"<tr>"
                            f"<td><b>{sym}</b></td>"
                            f"<td>{qty}주</td>"
                            f"<td>${entry_p:.2f}</td>"
                            f"<td>${curr_p:.2f}</td>"
                            f"<td class='{cls_name}'>${pnl_usd:+,.2f}</td>"
                            f"<td class='{cls_name}'>{sign}{pnl_pct:.2f}%</td>"
                            f"<td>🟢 DB Active Holding</td>"
                            f"</tr>"
                        )
                else:
                    pos_rows = "<tr><td colspan='7' style='text-align:center;color:#8b949e;'>📭 현재 보유 중인 포지션이 없습니다.</td></tr>"
                conn.close()
        except Exception as e:
            logger.debug(f"Dashboard DB query error: {e}")
            pos_rows = "<tr><td colspan='7' style='text-align:center;color:#8b949e;'>📭 현재 보유 중인 포지션이 없습니다.</td></tr>"

    # Query trades table (Recent 15 closed/executed trades)
    try:
        db_path = "trades.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT created_at, symbol, side, quantity, price, pnl, pnl_pct, reason "
                "FROM trades ORDER BY id DESC LIMIT 15"
            )
            trades = cur.fetchall()
            if trades:
                for t in trades:
                    t_time, sym, side, qty, price, pnl, pnl_pct, reason = t
                    pnl = pnl or 0.0
                    pnl_pct = pnl_pct or 0.0
                    cls_name = "positive" if pnl >= 0 else "negative" if pnl < 0 else "neutral"
                    side_badge = f"<span style='color:{'#3fb950' if side=='BUY' else '#f85149'};font-weight:bold;'>{side}</span>"
                    
                    trades_rows += (
                        f"<tr>"
                        f"<td>{t_time}</td>"
                        f"<td><b>{sym}</b></td>"
                        f"<td>{side_badge}</td>"
                        f"<td>{qty}</td>"
                        f"<td>${price:.2f}</td>"
                        f"<td class='{cls_name}'>${pnl:+,.2f}</td>"
                        f"<td class='{cls_name}'>{pnl_pct:+.2f}%</td>"
                        f"<td>{reason}</td>"
                        f"</tr>"
                    )
            else:
                trades_rows = "<tr><td colspan='8' style='text-align:center;color:#8b949e;'>📭 거래 기록이 없습니다.</td></tr>"
            conn.close()
    except Exception as e:
        logger.debug(f"Trades query error: {e}")
        trades_rows = "<tr><td colspan='8' style='text-align:center;color:#8b949e;'>📭 거래 기록이 없습니다.</td></tr>"

    # Total Equity = Available Cash + Open Positions Market Value (No dummy fallbacks!)
    equity = cash + pos_total_val
    if equity <= 0 and cash <= 0:
        try:
            from trader import Trader
            t = Trader()
            cash = t.get_buying_power()
            equity = cash + pos_total_val
        except Exception:
            pass

    # 3. Read live activity log tail
    log_paths = ["logs/trading_bot.log", "logs/bot_runner.log"]
    for lp in log_paths:
        if os.path.exists(lp):
            try:
                with open(lp, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-20:]
                    clean_lines = []
                    for line in lines:
                        l = line.strip().replace("<", "&lt;").replace(">", "&gt;")
                        clean_lines.append(l)
                    logs_html = "<br>".join(clean_lines)
                    break
            except Exception:
                pass

    html = HTML_TEMPLATE.replace("{EQUITY}", f"{equity:,.2f}")
    html = html.replace("{CASH}", f"{cash:,.2f}")
    html = html.replace("{POS_COUNT}", str(pos_count))
    html = html.replace("{SESSION}", str(session))
    html = html.replace("{RISK_LEVEL}", str(risk_level))
    html = html.replace("{REGIME}", str(regime))
    html = html.replace("{POSITIONS_ROWS}", pos_rows)
    html = html.replace("{TRADES_ROWS}", trades_rows)
    html = html.replace("{LOGS_HTML}", logs_html)
    return html


def start_dashboard_server():
    """Starts background Web Dashboard HTTP server on port 8080"""
    def _run():
        try:
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("", PORT), DashboardRequestHandler) as httpd:
                logger.info(f"🌐 [WEB_DASHBOARD] Password-protected dashboard at http://0.0.0.0:{PORT}")
                httpd.serve_forever()
        except Exception as e:
            logger.debug(f"Dashboard server startup error (port {PORT}): {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()


if __name__ == "__main__":
    logger.info(f"🚀 Starting Standalone Web Dashboard Server on Port {PORT}...")
    print(f"🔐 Password: {DASHBOARD_PASSWORD}")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardRequestHandler) as httpd:
        print(f"🌐 Server running on http://0.0.0.0:{PORT}")
        httpd.serve_forever()
