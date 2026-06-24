# US Stock Fine-Grained Theme Tracker (Quant Grade)

This application is a desktop quant dashboard to track and capture early-stage stock market themes in the US stock market (e.g., Optical Interconnects, SMR/Nuclear, NAND Memory, Cannabis, Weight Loss Drugs, AI Power Transformers, Space Tech, CRISPR) at an extremely fine granularity.

It scales its analysis universe to **3,000+ US stocks** and features a **True vs. False Signal Validation Engine** to filter out speculative pumps, dead cat bounces, and market noise.

---

## Key Features

1. **54 Predefined Fine-Grained Themes**:
   - Spans semiconductors, AI software, grid infrastructure, clean energy, space tech, biotech, material mining, and consumer trends.
   - Dual-language UI support (Korean labels for readability).
2. **Hybrid Theme Classification Engine**:
   - **Pre-mapped DB**: Covers ~500 major stocks.
   - **Regular Expression Keywords (Fast Path)**: Analyzes company descriptions of 2,500+ stocks in milliseconds.
   - **Gemini LLM (Precision Path)**: Automatically analyzes complex business summaries to assign tags or categorize new listings on-demand.
3. **True vs. False Signal Validation Engine**:
   - **Theme Breadth**: Measures if stocks are rising together (Breadth > 60% = True Breakout). Filters out single-stock spikes.
   - **Volume Sustainability**: Measures the median Relative Volume (RVOL). Institutional footprints require sustained volume (RVOL > 1.5) over multiple days.
   - **Trend Alignment**: Verifies if the theme is trading above a rising 20-day Moving Average or flagging as a Dead Cat Bounce under a declining 50-day MA.
   - **Signal Quality Gauge**: Color-coded probability gauges (0-100%) for visual clarity.
4. **Premium Dark Slate Dashboard**:
   - Interactive Treemap Heatmap colored by performance.
   - Sortable Leaderboard with custom progress bars.
   - Stock Performance Matrix charts.

---

## Quant Signal Classification Table

| Signal Status | Breadth | Volume (RVOL) | Trend Setup | Action / Label |
|---|---|---|---|---|
| 🟢 **True Signal (Institutional)** | High (\( >60\% \)) | Sustained (\( >1.5 \)) | Above 20-day MA | **High Conviction Breakout** |
| 🟡 **Pump / Speculative** | Low (\( <30\% \)) | 1-day spike, no follow | Overextended | **High Risk Chasing / False Signal** |
| 🔴 **Dead Cat Bounce** | Medium | Low/Medium | Below declining 50D MA | **Counter-trend Trap / False Signal** |
| 🔵 **Consolidating / Noise** | Low | Low (\( <1.0 \)) | Flat | **Inactive / No Signal** |

---

## Installation & Launch

### Prerequisites
- Python 3.9+
- Windows OS (PowerShell)

### Quick Start
1. Open PowerShell.
2. Navigate to this project folder.
3. Run the launcher script:
   ```powershell
   ./run_app.ps1
   ```

### Quick Start Inside Streamlit (First Launch)
Once the Streamlit window opens in your browser, perform the following steps in the sidebar control panel to initialize the database:
1. Click **Download Tickers List**: Downloads the latest listings from NASDAQ FTP (NYSE & NASDAQ).
2. Click **Fetch Company Profiles (Batch 50)**: Downloads descriptions for initial tickers.
3. Click **Auto-Classify (Regex Keyword)**: Scans company summaries and maps tickers to the 54 themes.
4. Click **Download Prices (Batch 200)**: Downloads daily price/volume historical data.
5. Click **Compute Theme Metrics**: Runs the scoring calculations.

To use the **Gemini API** for dynamic classification:
- Enter your Gemini API Key in the sidebar text box.
- Go to the **AI Classifier & Scanner** tab.
- Enter any new ticker (e.g., `PLTR` or `MSTR`) and click **Run Classification Engine**.
