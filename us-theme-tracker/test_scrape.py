import requests
import re

url = 'https://finance.yahoo.com/quote/AAPL'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
try:
    r = requests.get(url, headers=headers, timeout=5)
    html = r.text
    
    # Sector/Industry extraction
    match = re.search(r'class="titleInfo[^"]*"\s*>(.*?)</span>', html)
    if match:
        info_str = match.group(1).strip()
        print("FOUND INFO:", info_str)
        if " / " in info_str:
            industry, sector = info_str.split(" / ", 1)
            print("Industry:", industry)
            print("Sector:", sector)
    else:
        print("titleInfo not found")
except Exception as e:
    print("Error:", e)
