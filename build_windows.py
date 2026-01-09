import os
import subprocess
import sys

# Name of the executable
APP_NAME = "SchoolBell"

# Convert PNG to ICO if needed
if os.path.exists("icon.png"):
    try:
        from PIL import Image
        img = Image.open("icon.png")
        icon_path = "icon.ico"
        img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print("Successfully created icon.ico")
    except Exception as e:
        print(f"Warning: Could not create icon.ico: {e}")
        icon_path = "icon.png" # Fallback
else:
    icon_path = None

# Command to run PyInstaller
# --onedir: Standard professional folder structure
# --noupx: DISABLING UPX to fix "Failed to load Python DLL" on Windows 11
# --console: Temporarily enabling console to see startup errors if it still fails
CONSOLE_FLAG = "--console" 

cmd = [
    "pyinstaller",
    "--clean",
    "--onedir",
    "--noupx",
    CONSOLE_FLAG,
    "--name", APP_NAME,
    "--collect-all", "webview",
    "--collect-all", "pystray",
    "--collect-all", "PIL",
    "--hidden-import", "clr",
    "--hidden-import", "pystray",
    "--hidden-import", "PIL.Image",
]

if icon_path and os.path.exists(icon_path):
    cmd.extend(["--icon", icon_path])

cmd.extend([
    "--add-data", f"templates{os.pathsep}templates",
    "--add-data", f"static{os.pathsep}static",
    "--add-data", f"sounds{os.pathsep}sounds",
    "main_app.py"
])

print(f"Running command: {' '.join(cmd)}")

try:
    subprocess.check_call(cmd)
    print("\n" + "="*50)
    print(f"BUILD SUCCESSFUL!")
    print(f"You can find your executable in the 'dist' folder.")
    print("="*50)
except subprocess.CalledProcessError as e:
    print(f"\nBUILD FAILED: {e}")
except Exception as e:
    print(f"\nAn error occurred: {e}")
