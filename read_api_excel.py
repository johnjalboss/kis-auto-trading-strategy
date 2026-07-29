import pandas as pd
import os

excel_path = r"C:\Users\wngud\Downloads\한국투자증권_오픈API_전체문서_20260217_030000.xlsx"

def analyze_excel():
    if not os.path.exists(excel_path):
        print("Excel file not found!")
        return

    # 1. Read sheet names to understand structure
    print("=" * 60)
    print("Analyzing KIS API Excel Sheets...")
    print("=" * 60)
    
    xl = pd.ExcelFile(excel_path)
    print(f"Sheets found ({len(xl.sheet_names)}):")
    for name in xl.sheet_names[:10]:  # Show first 10 sheets
        print(f" - {name}")
    
    if len(xl.sheet_names) > 10:
        print(f" ... and {len(xl.sheet_names) - 10} more.")
        
    print("\n" + "=" * 60)
    print("Searching for useful market data API specifications...")
    print("=" * 60)

    # Let's inspect the first sheet as a sample
    first_sheet = xl.sheet_names[0]
    df = xl.parse(first_sheet, nrows=20)
    print(f"\nFirst sheet '{first_sheet}' head:")
    print(df.to_string())

if __name__ == "__main__":
    analyze_excel()
