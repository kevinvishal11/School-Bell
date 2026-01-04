import os
import sys
import webbrowser
import threading
import time
from app import app, init_license_db, scheduler_loop

def open_browser():
    """Wait for the server to start and then open the browser."""
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8080")

if __name__ == "__main__":
    # 1. Initialize DB
    init_license_db()

    # 2. Start Scheduler in background
    t_sch = threading.Thread(target=scheduler_loop, daemon=True)
    t_sch.start()

    # 3. Start Browser launch thread
    t_br = threading.Thread(target=open_browser, daemon=True)
    t_br.start()

    # 4. Run Flask with Waitress (Production Server)
    from waitress import serve
    print("School Bell Server starting on http://127.0.0.1:8080")
    print("Browser will open automatically in 2 seconds...")
    serve(app, host="127.0.0.1", port=8080)
