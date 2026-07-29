import reporter
import time
from loguru import logger

def main():
    try:
        r = reporter.PerformanceReporter()
        print("Sending Yearly Report...")
        r.send_yearly_report()
        time.sleep(2) # Buffer
        
        print("Sending Daily Summary...")
        r.send_daily_summary()
        
        print("Waiting for background threads (10s)...")
        time.sleep(10)
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
