import os
import sys
import threading
import time

# Note: We move heavy imports inside the try block to catch crashes during library loading

if __name__ == "__main__":
    print("-" * 50)
    print("SCHOOL BELL DESKTOP SYSTEM STARTING...")
    print("-" * 50)
    
    try:
        # Import app logic
        print("Loading application modules...")
        from app import app, init_db, scheduler_loop, get_writable_dir
        
        WDIR = get_writable_dir()
        print(f"Data folder: {WDIR}")
        
        # 1. Initialize DB
        print(f"Opening database...")
        init_db()

        # 2. Start Scheduler in background
        print("Starting scheduler...")
        t_sch = threading.Thread(target=scheduler_loop, daemon=True)
        t_sch.start()

        # 3. Start Flask server in a thread
        from waitress import serve
        port = 5050
        flask_thread = threading.Thread(
            target=serve, 
            args=(app,), 
            kwargs={'host': '127.0.0.1', 'port': port}, 
            daemon=True
        )
        flask_thread.start()
        print(f"Backend Ready at http://127.0.0.1:{port}")

        # 4. Start Native GUI Window
        import webview
        
        icon_path = os.path.join(os.path.abspath("."), "icon.ico")
        if not os.path.exists(icon_path):
             icon_path = os.path.join(os.path.abspath("."), "icon.png")

        print("Launching Desktop Window...")
        window = webview.create_window(
            'School Bell Control System', 
            f'http://127.0.0.1:{port}',
            width=1000,
            height=700,
            min_size=(800, 600)
        )
        
        # Start the GUI
        webview.start()
        # Execution stops here until window is closed
        print("Application closed by user.")
        sys.exit(0)

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
        
        # Only wait for input if we have a console
        if sys.stdin and sys.stdin.isatty():
            input("\nPress ENTER to close this window...")
        else:
            # For noconsole apps, wait a bit so use can see log if capture
            time.sleep(10)
        sys.exit(1)
