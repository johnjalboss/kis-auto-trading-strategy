import pandas as pd
import json
import traceback

file_path = r'C:\Users\wngud\Downloads\한국투자증권_오픈API_전체문서_20260217_030000.xlsx'
try:
    xl = pd.ExcelFile(file_path)
    res = {}
    
    # We want to find exact API info for:
    # 1. 해외주식 신고_신저가
    # 2. 해외주식 거래대금순위
    target_sheets = ['해외주식 신고_신저가', '해외주식 거래대금순위']
    
    for sheet_name in target_sheets:
        if sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name)
            
            # Find tr_id in Request Header section
            tr_id = "UNKNOWN"
            header_section = False
            for i, row in df.iterrows():
                val0 = str(row.iloc[0]).strip()
                if val0 == 'Request Header':
                    header_section = True
                elif val0 == 'Request Query Parameter':
                    break # Stop looking for header
                
                if header_section:
                    if str(row.iloc[1]).strip() == 'tr_id':
                        tr_id = str(row.iloc[5]).strip()
                        
            # Find parameters in Request Query Parameter section
            params = []
            param_section = False
            for i, row in df.iterrows():
                val0 = str(row.iloc[0]).strip()
                if val0 == 'Request Query Parameter':
                    param_section = True
                elif val0 == 'Request Body Parameter' or val0 == 'Response Header':
                    break # Stop looking for query params
                
                if param_section:
                    param_name = str(row.iloc[1]).strip()
                    if param_name != 'nan' and param_name != 'Element':
                        params.append({
                            'name': param_name,
                            'desc': str(row.iloc[2]).strip(),
                            'type': str(row.iloc[3]).strip(),
                            'req': str(row.iloc[4]).strip(),
                            'notes': str(row.iloc[6]).strip()
                        })
                        
            res[sheet_name] = {'tr_id': tr_id, 'params': params}

    print(json.dumps(res, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error occurred:")
    traceback.print_exc()
