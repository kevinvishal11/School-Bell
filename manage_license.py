import sqlite3
import sys
from datetime import datetime, timedelta

DB_PATH = "lram.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def view_license():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT value FROM system_settings WHERE key='license_expiry'")
        row = cur.fetchone()
        if row:
            print(f"Current License Expiry: {row[0]}")
        else:
            print("No license expiry set.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def set_license(days_from_now):
    conn = get_conn()
    cur = conn.cursor()
    try:
        new_date = (datetime.now() + timedelta(days=int(days_from_now))).strftime("%Y-%m-%d")
        cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('license_expiry', ?)", (new_date,))
        conn.commit()
        print(f"Success! License updated to expire on: {new_date}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 manage_license.py view       -> View current expiry")
        print("  python3 manage_license.py set <days> -> Set expiry to <days> from now")
        print("Example: python3 manage_license.py set 365")
    else:
        cmd = sys.argv[1]
        if cmd == "view":
            view_license()
        elif cmd == "set" and len(sys.argv) == 3:
            set_license(sys.argv[2])
        else:
            print("Invalid arguments.")
