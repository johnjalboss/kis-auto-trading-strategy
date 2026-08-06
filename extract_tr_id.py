import pandas as pd
import json

file_path = r'C:\Users\wngud\Downloads\한국투자증권_오픈API_전체문서_20260217_030000.xlsx'
try:
    xl = pd.ExcelFile(file_path)
    res = {}
    for sheet in ['해외주식 신고_신저가', '해외주식 거래대금순위']:
        df = xl.parse(sheet)
        tr_id = ""
        for i in range(len(df)):
            if str(df.iloc[i, 1]) == 'tr_id':
                tr_id = str(df.iloc[i, 5])
                break
        res[sheet] = tr_id
    with open('tr_ids.json', 'w') as f:
        json.dump(res, f)
except Exception as e:
    print("⚠️ [extract_tr_id.py] Fallback triggered:", e)
