import os
import time
import json
import psutil
from datetime import datetime

# Optional: Try to import rich for better UI, fallback to standard prints
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align
    RICH_ENABLED = True
    console = Console()
except ImportError:
    RICH_ENABLED = False

def get_latest_state():
    """Read the latest health state dumped by the bot"""
    try:
        with open("health_state.json", "r") as f:
            return json.load(f)
    except Exception:
        return None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_fallback_dashboard():
    """Standard print dashboard if rich is not installed"""
    while True:
        clear_screen()
        state = get_latest_state()
        print("="*60)
        print(f"🤖 KIS AUTO-TRADING BOT DASHBOARD | {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        if not state:
            print("❌ Bot state not found. Is the bot running?")
            time.sleep(2)
            continue
            
        print("\n📊 SYSTEM STATUS")
        print(f"API: {state.get('api_status', 'UNKNOWN')}")
        print(f"CPU: {state.get('cpu_percent', 0)}% | Mem: {state.get('memory_percent', 0)}%")
        
        print("\n💰 P&L OVERVIEW")
        pnl = state.get('net_pnl', 0)
        pnl_pct = state.get('pnl_pct', 0) * 100
        pnl_color = "🟢" if pnl >= 0 else "🔴"
        print(f"Daily Net P&L: {pnl_color} ${pnl:,.2f} ({pnl_pct:+.2f}%)")
        print(f"Win Rate: {state.get('win_rate', 0)*100:.1f}% ({state.get('wins', 0)}W/{state.get('losses', 0)}L)")
        
        print("\n📈 CURRENT POSITIONS")
        positions = state.get('positions', [])
        if not positions:
            print("  No active positions.")
        else:
            for p in positions:
                ppnl = p.get('pnl_pct', 0) * 100
                pc = "🟢" if ppnl >= 0 else "🔴"
                print(f"  {p['symbol']:6s} | Qty: {p['quantity']:<4} | Entry: ${p['entry_price']:.2f} | P&L: {pc} {ppnl:+.2f}%")
                
        print("\n🌍 MACRO REGIME")
        print(f"Regime: {state.get('current_regime', 'UNKNOWN')}")
        
        print("\n" + "="*60)
        print("Press Ctrl+C to exit. Auto-refreshing every 2s...")
        time.sleep(2)

def render_rich_dashboard():
    """Beautiful rich terminal UI"""
    from rich.text import Text
    
    def generate_layout():
        state = get_latest_state()
        if not state:
            return Panel(Text("Bot state not found. Waiting for bot to boot...", justify="center", style="yellow"), title="KIS Bot Offline")

        # 1. System Panel
        sys_text = Text()
        sys_text.append(f"📡 API Status: {state.get('api_status', 'UNKNOWN')}\n")
        sys_text.append(f"💻 CPU: {state.get('cpu_percent', 0)}% | Memory: {state.get('memory_percent', 0)}%")
        sys_panel = Panel(sys_text, title="[bold blue]System Health", border_style="blue")

        # 2. PnL Panel
        pnl = state.get('net_pnl', 0)
        pnl_pct = state.get('pnl_pct', 0) * 100
        pnl_color = "green" if pnl >= 0 else "red"
        pnl_text = Text()
        pnl_text.append(f"Net P&L: ", style="bold")
        pnl_text.append(f"${pnl:,.2f} ( {pnl_pct:+.2f}% )\n", style=f"bold {pnl_color}")
        pnl_text.append(f"Win Rate: {state.get('win_rate', 0)*100:.1f}% ({state.get('wins', 0)}W/{state.get('losses', 0)}L)")
        pnl_panel = Panel(pnl_text, title="[bold green]Daily Performance", border_style="green")
        
        # 3. Macro Panel
        regime = state.get('current_regime', 'UNKNOWN')
        reg_color = "red" if "BEAR" in regime else "green"
        macro_panel = Panel(Text(f"{regime}", style=f"bold {reg_color}", justify="center"), title="[bold Magenta]Macro Regime", border_style="magenta")

        # 4. Positions Table
        table = Table(show_header=True, header_style="bold yellow", expand=True)
        table.add_column("Symbol", style="cyan")
        table.add_column("Qty", justify="right")
        table.add_column("Entry $", justify="right")
        table.add_column("Current $", justify="right")
        table.add_column("P&L %", justify="right")
        
        positions = state.get('positions', [])
        if not positions:
            table.add_row("No Active Positions", "", "", "", "")
        else:
            for p in positions:
                ppnl = p.get('pnl_pct', 0) * 100
                color = "green" if ppnl >= 0 else "red"
                table.add_row(
                    p.get('symbol', 'N/A'),
                    str(p.get('quantity', 0)),
                    f"${p.get('entry_price', 0):.2f}",
                    f"${p.get('current_price', 0):.2f}",
                    f"[{color}]{ppnl:+.2f}%[/{color}]"
                )
        pos_panel = Panel(table, title="[bold cyan]Active Positions", border_style="cyan")

        # Layout Assembly
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="positions", ratio=2)
        )
        layout["header"].update(Panel(Text(f"KIS QUANT ORCHESTRATOR DASHBOARD | {datetime.now().strftime('%H:%M:%S')}", justify="center", style="bold white on blue")))
        
        main_row = Layout()
        main_row.split_row(
            Layout(pnl_panel),
            Layout(macro_panel),
            Layout(sys_panel)
        )
        layout["main"].update(main_row)
        layout["positions"].update(pos_panel)

        return layout

    with Live(generate_layout(), refresh_per_second=2, screen=True) as live:
        while True:
            live.update(generate_layout())
            time.sleep(0.5)

if __name__ == "__main__":
    try:
        if RICH_ENABLED:
            render_rich_dashboard()
        else:
            render_fallback_dashboard()
    except KeyboardInterrupt:
        print("\nDashboard Exited.")
