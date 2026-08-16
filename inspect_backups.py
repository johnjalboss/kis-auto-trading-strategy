import sqlite3, glob

for db_file in glob.glob("*.db"):
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"=== {db_file} ===")
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                cnt = cur.fetchone()[0]
                print(f"  Table '{t}': {cnt} rows")
            except Exception as e:
                print(f"  Table '{t}': Error ({e})")
        conn.close()
    except Exception as err:
        print(f"Error opening {db_file}: {err}")
