import os
import sys
import threading
import time
import ctypes
import subprocess
from PIL import Image
try:
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pystray = None

# Note: We move heavy imports inside the try block to catch crashes during library loading

if __name__ == "__main__":
    # 0. PRIMITIVE LOGGING (No heavy imports allowed here)
    try:
        log_dir = os.path.join(os.path.expanduser("~"), "SchoolBellData")
        if not os.path.exists(log_dir): os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "boot_log.txt"), "a") as f:
            f.write(f"\n[{time.ctime()}] BOOT: App triggered. Args: {sys.argv}")
    except: pass

    # Parse arguments
    is_startup = "--startup" in sys.argv

    # Ensure working directory is set to the folder containing this file
    app_base_path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_base_path)

    # Windows background execution fix
    if sys.platform == "win32":
        print("Applying Windows background execution optimization...")
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_AWAYMODE_REQUIRED = 0x00000040
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
        except Exception as e:
            print(f"Non-critical: Could not set execution state: {e}")

    try:
        # Import app logic
        print("Loading application modules...")
        from app import app, init_db, scheduler_loop, get_writable_dir
        from device_manager import DeviceManager
        
        # Initialize Device Manager (Ensures ID exists)
        dm = DeviceManager()
        print(f"Device ID: {dm.get_device_id()}")
        
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
        
        icon_path = os.path.join(app_base_path, "icon.ico")
        if not os.path.exists(icon_path):
             icon_path = os.path.join(app_base_path, "icon.png")

        window = webview.create_window(
            'School Bell Control System', 
            f'http://127.0.0.1:{port}',
            width=1000,
            height=700,
            min_size=(800, 600),
            hidden=is_startup
        )

        # Tray Icon Logic
        tray_icon = None
        def quit_app(icon, item):
            print("Quitting application...")
            icon.stop()
            os._exit(0)

        def show_window(icon, item):
            window.show()

        if pystray and os.path.exists(icon_path):
            try:
                image = Image.open(icon_path)
                def show_device_info_ui(icon, item):
                    from device_ui import DeviceInfoWindow
                    # Launch in a separate thread to not block tray
                    def _launch():
                        try:
                            app = DeviceInfoWindow()
                            app.run()
                        except Exception as e:
                            print(f"UI Error: {e}")
                    threading.Thread(target=_launch, daemon=True).start()

                menu = pystray.Menu(
                    item('Open Control Panel', show_window, default=True),
                    item('Show Device Info', show_device_info_ui),
                    item('Exit', quit_app)
                )
                tray_icon = pystray.Icon("SchoolBell", image, "School Bell System", menu)
                threading.Thread(target=tray_icon.run, daemon=True).start()
            except Exception as te:
                print(f"Tray icon error: {te}")

        def on_closing():
            # Instead of closing, just hide the window
            window.hide()
            return False # Prevents destruction

        window.events.closing += on_closing

        # Start the GUI
        # FORCE Edge/WebView2 for Windows 11 compatibility
        try:
            webview.start(None, None, gui='edgechromium' if sys.platform == 'win32' else None)
        except:
            webview.start() # Fallback
            
        print("Main window hidden/closed. App running in background (Tray).")
        # Keep main thread alive for the tray icon if needed, 
        # but webview.start() usually blocks until the window is destroyed.
        # Since we prevent destruction, we might need a loop here.
        while True:
            time.sleep(1)

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
