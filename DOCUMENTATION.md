# School Bell App - Developer & Build Documentation

This documentation provides instructions on how to set up the development environment, run the app locally, build the Windows executable, and generate the installation package.

## 1. Prerequisites

Before running or building the app, ensure you have the following installed:
- **Python 3.x**
- **Pip** (Python package installer)
- **Inno Setup 6** (Only required if you are building the Windows Setup Installer). *Expected path: `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` or `C:\Program Files\Inno Setup 6\ISCC.exe`*

Ensure your `venv` is activated and the following dependencies are installed.

```bash
# Recommended dependencies based on imports
pip install flask pywebview pystray Pillow qrcode waitress pyinstaller
```

---

## 2. Running for Development

To run the application locally without compiling it:

```bash
# Activate your virtual environment first (if applicable)
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Run the main entry point
python main_app.py
```

`main_app.py` handles:
1. Booting the Flask server on `http://127.0.0.1:5050` (via `waitress`).
2. Spawning the scheduler loop in the background.
3. Managing the System Tray Icon.
4. Launching the native GUI window via `webview`.

---

## 3. Building the Windows Executable (`.exe`)

To compile the application into a standalone Windows Executable (`.exe`), a PyInstaller build script has been provided.

**Script**: `build_windows.py`

This script configures `pyinstaller` with the necessary flags (`--onefile`, `--noconsole`, `--noupx`) and automatically bundles required assets like HTML templates, sounds, and static files. It also converting the `icon.png` to `.ico` for the application automatically if needed.

### How to Build
```bash
python build_windows.py
```

### Output
If the build succeeds, the compiled single executable will be located in the `dist/` directory as `SchoolBell.exe`.

---

## 4. Building the Setup Installer

To create a professional setup installer that users can double-click to install the app on their system:

**Script**: `make_installer.bat`

This Windows Batch script combines two steps:
1. Compiles the app using PyInstaller (executes `build_windows.py`).
2. Uses **Inno Setup (ISCC.exe)** with the instructions from `installer.iss` to wrap the `.exe` into a setup package.

### How to Build the Installer
Open a Windows Command Prompt or PowerShell in the root directory and run:
```cmd
make_installer.bat
```

### Output
If successful, the final `SchoolBell_Setup.exe` will be generated in the `Output/` directory.

---

## 5. Installing the Application via Script (Optional)

If you are using the PowerShell installation scripts rather than the Inno Setup executable, use the provided batch wrapper to bypass execution limits safely.

**Script**: `run_installer.bat`

This simply triggers `install.ps1` with the required execution policy for environments that prevent standard PowerShell scripts from running directly.

### How to run
Simply double click on `run_installer.bat` within Windows Explorer, or execute it from the Command Prompt:
```cmd
run_installer.bat
```

---

## Troubleshooting Native Builds
- **Failed to Load Python DLL**: Ensure that `--noupx` is enabled during the `pyinstaller` command (handled inside `build_windows.py`) to prevent Windows 11 compatibility issues.
- **Port 5050 already in use**: The app runs locally on port 5050. If you encounter crashes at the startup, make sure no background processes are locking this port.
- **Missing Inno Setup**: `make_installer.bat` will warn you if `ISCC.exe` is not found. You will need to manually open `installer.iss` in the Inno Setup GUI and click "Compile".
