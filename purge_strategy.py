import re

def purge_strategy():
    with open('strategy.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove _orb_cache
    content = re.sub(r'        self\._orb_cache: Dict\[str, dict\] = \{\}.*?\n', '', content)

    # 2. Remove VWAP and Intraday bonus from _calc_entry_confidence
    content = re.sub(r'        # ================================\n        # VWAP.*?score \+= 8  # VWAP.*?\n', '', content, flags=re.DOTALL)
    content = re.sub(r'        #  Intraday Confirmation Bonus.*?score \+= intraday_bonus\n.*?except Exception as e:\n.*?logger\.debug\("Intraday confirmation error: \{\}", e\)\n', '', content, flags=re.DOTALL)

    # 3. Remove _calc_intraday_confirmation method entirely
    content = re.sub(r'    def _calc_intraday_confirmation\(self, symbol: str\) -> int:.*?    def check_exit', '    def check_exit', content, flags=re.DOTALL)

    # 4. Remove VWAP exit logic from time-based exit
    content = re.sub(r'            # VWAP 붕괴.*?except Exception:\n                pass\n', '', content, flags=re.DOTALL)

    # 5. Remove _check_intraday_reversal method
    content = re.sub(r'    def _check_intraday_reversal\(self.*?    def _check_stop_loss', '    def _check_stop_loss', content, flags=re.DOTALL)

    with open('strategy.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    purge_strategy()
    print("Strategy purge complete")
