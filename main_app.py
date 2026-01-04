import os
import sys
import webbrowser
import threading
import time

# Note: We move heavy imports inside the try block to catch crashes during library loading

def open_browser():
    """Wait for the server to start and then open the browser."""
    time.sleep(3)
    print("Launching browser: http://127.0.0.1:8080")
    webbrowser.open("http://127.0.0.1:8080")

if __name__ == "__main__":
    print("-" * 50)
    print("SCHOOL BELL SYSTEM STARTING...")
    print("-" * 50)
    
    try:
        # Import app logic inside try block to catch import-time errors (like pygame init)
        print("Loading application modules...")
        from app import app, init_license_db, scheduler_loop
        
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
        print("  SYSTEM IS ONLINE")
        print("  Access at: http://127.0.0.1:8080")
        print("="*50)
        print("\nDO NOT CLOSE THIS WINDOW. Minimize it instead.")
        
        serve(app, host="127.0.0.1", port=8080)
    except Exception as e:
        import traceback
        error_msg = f"CRITICAL ERROR AT STARTUP:\n{str(e)}\n\n{traceback.format_exc()}"
        print("\n" + "!"*50)
        print(error_msg)
        print("!"*50)
        
        # Log to file
        try:
            with open("crash_log.txt", "w") as f:
                f.write(error_msg)
            print("\nAn error occurred. A 'crash_log.txt' file has been created.")
        except:
            print("\nCould not create crash_log.txt file.")
            
        print("\nPossible fix: Close any other apps using port 8080.")
        input("\nPress ENTER to close this window...")
        sys.exit(1)
