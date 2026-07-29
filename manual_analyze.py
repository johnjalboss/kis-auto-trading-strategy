from composite_signal import get_composite_engine
if __name__ == "__main__":
    engine = get_composite_engine()
    sig = engine.analyze("SOFI")
    print(f"ANALYSIS_RESULT|{sig.composite_score}|{sig.action}|{sig.summary}")
