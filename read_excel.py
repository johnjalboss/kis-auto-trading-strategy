import pandas as pd

file_path = r'C:\Users\wngud\Downloads\한국투자증권_오픈API_전체문서_20260217_030000.xlsx'
try:
    xl = pd.ExcelFile(file_path)
    
    with open('kis_api_docs_summary.txt', 'w', encoding='utf-8') as f:
        f.write("Sheets: " + str(xl.sheet_names) + "\n\n")
        
        for sheet in xl.sheet_names:
            if '해외주식' in sheet:
                df = xl.parse(sheet).head(20)
                f.write(f"\n--- Sheet: {sheet} ---\n")
                f.write(df.to_string(index=False) + "\n")
except Exception as e:
    with open('kis_api_docs_summary.txt', 'w', encoding='utf-8') as f:
        f.write("Error: " + str(e))
