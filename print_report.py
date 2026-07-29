import reporter
import time

def main():
    try:
        r = reporter.PerformanceReporter()
        print("--- DAILY REPORT TEXT ---")
        print(r.generate_daily_report())
        print("--- END ---")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
