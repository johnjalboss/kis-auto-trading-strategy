import pandas as pd
import sys

file_path = r'C:\Users\wngud\Downloads\한국투자증권_오픈API_전체문서_20260217_030000.xlsx'
try:
    xl = pd.ExcelFile(file_path)
    
    # 1. 해외주식 신고_신저가 (New Highs)
    if '해외주식 신고_신저가' in xl.sheet_names:
        df1 = xl.parse('해외주식 신고_신저가')
        q1 = df1[df1.iloc[:, 0] == 'Request Query Parameter'].iloc[:, 1:7]
        print("=== 해외주식 신고_신저가 ===")
        print(q1.dropna(how='all').to_string())
        
    # 2. 해외주식 거래대금순위 (Top Traded Value)
    if '해외주식 거래대금순위' in xl.sheet_names:
        df2 = xl.parse('해외주식 거래대금순위')
        q2 = df2[df2.iloc[:, 0] == 'Request Query Parameter'].iloc[:, 1:7]
        print("\n=== 해외주식 거래대금순위 ===")
        print(q2.dropna(how='all').to_string())
        
    # 3. 해외주식 매수체결강도상위 (Buying Power/Momentum)
    if '해외주식 매수체결강도상위' in xl.sheet_names:
        df3 = xl.parse('해외주식 매수체결강도상위')
        q3 = df3[df3.iloc[:, 0] == 'Request Query Parameter'].iloc[:, 1:7]
        print("\n=== 해외주식 매수체결강도상위 ===")
        print(q3.dropna(how='all').to_string())
        
except Exception as e:
    print("Error:", e)
