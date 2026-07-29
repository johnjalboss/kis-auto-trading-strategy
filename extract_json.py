import pandas as pd
import json

file_path = r'C:\Users\wngud\Downloads\한국투자증권_오픈API_전체문서_20260217_030000.xlsx'
try:
    xl = pd.ExcelFile(file_path)
    res = {}
    for sheet in ['해외주식 신고_신저가', '해외주식 거래대금순위']:
        if sheet in xl.sheet_names:
            df = xl.parse(sheet)
            req = df[df.iloc[:, 0] == 'Request Query Parameter']
            # Get TR_ID as well (from Request Header where Unnamed: 1 == 'tr_id')
            tr_id_row = df[(df.iloc[:, 0] == 'Request Header') | (df.iloc[:, 0].isna())]
            tr_id = tr_id_row[tr_id_row.iloc[:, 1] == 'tr_id'].iloc[0, 5] if len(tr_id_row[tr_id_row.iloc[:, 1] == 'tr_id']) > 0 else 'Unknown'
            
            params = []
            for _, row in req.iterrows():
                params.append({
                    'param': row.iloc[1],
                    'desc_kr': row.iloc[2],
                    'req': row.iloc[4],
                    'desc': row.iloc[6]
                })
            res[sheet] = {'TR_ID': tr_id, 'Params': params}
            
    with open('api_extract.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(e)
