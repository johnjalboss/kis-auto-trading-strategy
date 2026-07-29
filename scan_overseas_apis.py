import pandas as pd
import os

excel_path = r"C:\Users\wngud\Downloads\한국투자증권_오픈API_전체문서_20260217_030000.xlsx"

def scan_overseas():
    if not os.path.exists(excel_path):
        print("Excel file not found!")
        return

    print("=" * 70)
    print("Scanning KIS API Sheet for Overseas (US) Stock Market Data APIs...")
    print("=" * 70)

    # Load only the first sheet which lists all APIs (the API index sheet)
    df_index = pd.read_excel(excel_path, sheet_name=0)
    
    # Fill NaN and convert columns to string
    df_index = df_index.fillna("")
    for col in df_index.columns:
        df_index[col] = df_index[col].astype(str)

    # Search query
    # Look for rows containing '해외' or 'overseas' or '미국' in any column
    mask = df_index.apply(lambda row: row.str.contains('해외|미국|overseas|foreign|america|nasd|nyse', case=False).any(), axis=1)
    df_overseas = df_index[mask]
    
    print(f"Found {len(df_overseas)} potential Overseas/US Stock APIs.")
    print("\nTop 30 identified Overseas APIs:")
    for idx, row in df_overseas.head(30).iterrows():
        # Clean printed columns
        api_category = row.iloc[1]
        api_name = row.iloc[2]
        api_id = row.iloc[3]
        tr_id = row.iloc[4]
        method = row.iloc[6]
        url = row.iloc[7]
        print(f"[{api_category}] {api_name} -> ID: {api_id} | TR: {tr_id} | {method} {url}")
        
if __name__ == "__main__":
    scan_overseas()
