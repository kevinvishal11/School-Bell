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
    try:
        # 1. Initialize DB
        print("Initializing database...")
        init_license_db()

        # 2. Start Scheduler in background
        print("Starting scheduler...")
        t_sch = threading.Thread(target=scheduler_loop, daemon=True)
        t_sch.start()

        # 3. Start Browser launch thread
        print("Preparing browser launch...")
        t_br = threading.Thread(target=open_browser, daemon=True)
        t_br.start()

        # 4. Run Flask with Waitress (Production Server)
        from waitress import serve
        print("\n" + "="*50)
        print("  SCHOOL BELL SYSTEM IS RUNNING")
        print("  Access at: http://127.0.0.1:8080")
        print("="*50)
        print("\nKeep this window open while using the application.")
        
        serve(app, host="127.0.0.1", port=8080)
    except Exception as e:
        import traceback
        error_msg = f"CRITICAL ERROR AT STARTUP:\n{str(e)}\n\n{traceback.format_exc()}"
        print("\n" + "!"*50)
        print(error_msg)
        print("!"*50)
        
        # Log to file
        with open("crash_log.txt", "w") as f:
            f.write(error_msg)
        
        print("\nAn error occurred. A 'crash_log.txt' file has been created.")
        input("\nPress ENTER to close this window...")
        sys.exit(1)
