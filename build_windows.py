import os
import subprocess
import sys

# Name of the executable
APP_NAME = "SchoolBellApp"

# Command to run PyInstaller
# --onefile: Bundle everything into a single EXE
# --add-data: Include templates, static, and sounds
# --noconsole: Hide the console window (change to "" to show console)
CONSOLE_FLAG = "--console" # Use --noconsole for production if you don't want logs

cmd = [
    "pyinstaller",
    "--clean",
    "--onefile",
    CONSOLE_FLAG,
    "--name", APP_NAME,
    "--icon", "icon.png",
    "--add-data", f"templates{os.pathsep}templates",
    "--add-data", f"static{os.pathsep}static",
    "--add-data", f"sounds{os.pathsep}sounds",
    "main_app.py"
]

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
