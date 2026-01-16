import sqlite3
import os

# Get path to database
path = os.path.join(os.path.expanduser("~"), "SchoolBellData", "lram.db")

if os.path.exists(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    
    # Check if admin_password exists
    cur.execute("SELECT * FROM system_settings WHERE key='admin_password'")
    if cur.fetchone():
        print("Updating existing admin_password...")
        cur.execute("UPDATE system_settings SET value='Vishal@#2026$' WHERE key='admin_password'")
    else:
        print("Inserting new admin_password...")
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('admin_password', 'Vishal@#2026$')")
    
    conn.commit()
    conn.close()
    print("Database updated successfully.")
else:
    print(f"Database not found at {path}")
