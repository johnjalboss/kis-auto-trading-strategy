import pandas as pd
import urllib.request
import io

def fetch_wikipedia_list(url, table_index=0, column_name="Symbol"):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; trading-bot/1.0)"}
    )
    try:
        html = urllib.request.urlopen(req, timeout=15).read()
        tables = pd.read_html(io.BytesIO(html))
        df = tables[table_index]
        symbols = df[column_name].astype(str).str.replace(".", "", regex=False).str.replace("-", "", regex=False).tolist()
        return sorted(list(set([s.strip().upper() for s in symbols if s and s.strip() and s != 'nan'])))
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return []

print("Fetching S&P 500...")
sp500 = fetch_wikipedia_list("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", 0, "Symbol")
print(f"Fetched {len(sp500)} S&P 500 symbols.")

print("Fetching S&P 400...")
sp400 = fetch_wikipedia_list("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies", 0, "Symbol")
print(f"Fetched {len(sp400)} S&P 400 symbols.")

print("Fetching S&P 600...")
sp600 = fetch_wikipedia_list("https://en.wikipedia.org/wiki/List_of_S%26P_600_companies", 0, "Symbol")
print(f"Fetched {len(sp600)} S&P 600 symbols.")

# Output files
with open("universe_lists.txt", "w", encoding="utf-8") as f:
    f.write("SP500_STATIC = [\n")
    for i in range(0, len(sp500), 10):
        chunk = sp500[i:i+10]
        f.write("    " + ", ".join(f'"{s}"' for s in chunk) + ",\n")
    f.write("]\n\n")

    # Extra growth tech/fintech/crypto
    extra_growth = ["PLTR", "CRWD", "SNOW", "NET", "DDOG", "ZS", "MDB", "CFLT", 
                    "COIN", "MSTR", "SOFI", "HOOD", "AFRM", "RIVN", "LCID", "QS", 
                    "RKLB", "ASTS", "SHOP", "MELI", "SE", "CPNG", "BROS", "CAVA"]
    
    # We take all S&P 400 stocks (400), first 250 S&P 600 stocks (250), and extra growth
    additional = sorted(list(set(sp400 + sp600[:250] + extra_growth)))
    # Remove any that are already in S&P 500
    additional = [s for s in additional if s not in sp500]

    f.write("additional_russell = [\n")
    for i in range(0, len(additional), 10):
        chunk = additional[i:i+10]
        f.write("    " + ", ".join(f'"{s}"' for s in chunk) + ",\n")
    f.write("]\n")

print("Done. Created universe_lists.txt")
print(f"S&P 500: {len(sp500)}")
print(f"Additional Russell: {len(additional)}")
print(f"Total: {len(set(sp500 + additional))}")
