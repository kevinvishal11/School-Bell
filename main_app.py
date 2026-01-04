import os
import sys
import webbrowser
import threading
import time

# Note: We move heavy imports inside the try block to catch crashes during library loading

def open_browser():
    """Wait for the server to start and then open the browser."""
    time.sleep(3)
    print("Launching browser: http://127.0.0.1:5050")
    webbrowser.open("http://127.0.0.1:5050")

if __name__ == "__main__":
    print("-" * 50)
    print("SCHOOL BELL SYSTEM STARTING...")
    print("-" * 50)
    
    try:
        # Import app logic inside try block to catch import-time errors
        print("Loading application modules...")
        from app import app, init_license_db, scheduler_loop, get_writable_dir
        
        WDIR = get_writable_dir()
        
        # 1. Initialize DB
        print(f"Initializing database at: {WDIR}...")
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
        port = 5050
        print("\n" + "="*50)
        print("  SYSTEM IS ONLINE")
        print(f"  Access at: http://127.0.0.1:{port}")
        print("="*50)
        print("\nDO NOT CLOSE THIS WINDOW. Minimize it instead.")
        
        serve(app, host="127.0.0.1", port=port)
    except Exception as e:
        import traceback
        error_msg = f"CRITICAL ERROR AT STARTUP:\n{str(e)}\n\n{traceback.format_exc()}"
        print("\n" + "!"*50)
        print(error_msg)
        print("!"*50)
        
        # Log to file in writable dir
        try:
            from app import get_writable_dir
            log_path = os.path.join(get_writable_dir(), "crash_log.txt")
            with open(log_path, "w") as f:
                f.write(error_msg)
            print(f"\nAn error occurred. A 'crash_log.txt' file has been created at:\n{log_path}")
        except:
            print("\nCould not create crash_log.txt file.")
            
        print(f"\nPossible fix: Close any other apps using port 5050.")
        input("\nPress ENTER to close this window...")
        sys.exit(1)
