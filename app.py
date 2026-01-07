# app.py
import os
import sqlite3
import pygame
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import threading
import sys
import time
import shutil

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_writable_dir():
    """ Always use a dedicated folder in the user's home directory for persistence.
    This ensures that updating the EXE doesn't lose data. """
    path = os.path.join(os.path.expanduser("~"), "SchoolBellData")
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

# Data that persists (DB, Uploaded Sounds)
WRITABLE_DIR = get_writable_dir()
DB_PATH = os.path.join(WRITABLE_DIR, "lram.db")
SOUNDS_DIR = os.path.join(WRITABLE_DIR, "sounds")
os.makedirs(SOUNDS_DIR, exist_ok=True)

# Update Flask to use resource_path for templates and static (Bundled assets)
app = Flask(__name__, 
            static_folder=resource_path("static"), 
            template_folder=resource_path("templates"))

# Initialize pygame mixer
try:
    pygame.mixer.init()
    print("Pygame mixer initialized")
except Exception as e:
    print(f"Failed to initialize pygame mixer: {e}")

# DB helper
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# License System and DB Initialization
def init_db():
    # --- Migration Step ---
    safe_db = os.path.join(get_writable_dir(), "lram.db")
    if not os.path.exists(safe_db):
        # Check if an old DB exists in the app folder
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.abspath(os.path.dirname(__file__))
        
        old_db = os.path.join(app_dir, "lram.db")
        if os.path.exists(old_db):
            print(f"Migrating database from {old_db} to {safe_db}")
            try:
                shutil.copy2(old_db, safe_db)
            except Exception as e:
                print(f"Migration failed: {e}")

    conn = get_conn()
    cur = conn.cursor()
    
    # 1. Tables
    cur.execute("""CREATE TABLE IF NOT EXISTS sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    enabled INTEGER DEFAULT 1
                  )""")
                  
    cur.execute("""CREATE TABLE IF NOT EXISTS slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER,
                    slot_no INTEGER,
                    time TEXT DEFAULT '',
                    enabled INTEGER DEFAULT 0,
                    sound_id INTEGER,
                    FOREIGN KEY(section_id) REFERENCES sections(id),
                    FOREIGN KEY(sound_id) REFERENCES sounds(id)
                  )""")
                  
    cur.execute("""CREATE TABLE IF NOT EXISTS sounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    filename TEXT UNIQUE
                  )""")
                  
    cur.execute("""CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                  )""")
    conn.commit()
    
    # 2. Seed Sections (14)
    cur.execute("SELECT COUNT(*) FROM sections")
    section_count = cur.fetchone()[0]
    print(f"Database: Found {section_count} sections.")
    if section_count == 0:
        print("Seeding default sections...")
        for i in range(1, 15):
            cur.execute("INSERT INTO sections (name, enabled) VALUES (?, 1)", (f"Section {i}",))
        conn.commit()
        print("Seeding default sections complete.")
    
    # 3. Seed Slots (48 per section)
    cur.execute("SELECT COUNT(*) FROM slots")
    slot_count = cur.fetchone()[0]
    print(f"Database: Found {slot_count} slots.")
    if slot_count == 0:
        print("Seeding default slots...")
        cur.execute("SELECT id FROM sections")
        section_ids = [r[0] for r in cur.fetchall()]
        for sid in section_ids:
            for s_no in range(1, 49):
                cur.execute("""INSERT INTO slots (section_id, slot_no, time, enabled) 
                               VALUES (?, ?, '', 0)""", (sid, s_no))
        conn.commit()
        print("Seeding default slots complete.")

    # 4. Auto-populate sounds from disk & Seed default sounds
    print("Checking for sound files on disk...")
    # Seed default sounds from bundled directory to Writable sounds dir if it's empty or missing files
    bundled_sounds_dir = resource_path("sounds")
    if os.path.exists(bundled_sounds_dir):
        for f in os.listdir(bundled_sounds_dir):
            if f.lower().endswith(('.wav', '.mp3', '.ogg', '.aif', '.aiff')):
                src = os.path.join(bundled_sounds_dir, f)
                dst = os.path.join(SOUNDS_DIR, f)
                if not os.path.exists(dst):
                    print(f"Seeding default sound: {f}")
                    try:
                        shutil.copy2(src, dst)
                    except Exception as e:
                        print(f"Failed to seed sound {f}: {e}")

    if os.path.exists(SOUNDS_DIR):
        for f in os.listdir(SOUNDS_DIR):
            if f.lower().endswith(('.wav', '.mp3', '.ogg', '.aif', '.aiff')):
                name = f.replace('_', ' ').replace('.wav', '').replace('.mp3', '').replace('.ogg', '').replace('.aiff', '').replace('.aif', '').title()
                cur.execute("INSERT OR IGNORE INTO sounds(name, filename) VALUES(?,?)", (name, f))
        conn.commit()

    # 5. License Expiry & Admin Password
    cur.execute("SELECT value FROM system_settings WHERE key='license_expiry'")
    if not cur.fetchone():
        expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('license_expiry', ?)", (expiry,))
    
    cur.execute("SELECT value FROM system_settings WHERE key='admin_password'")
    if not cur.fetchone():
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('admin_password', 'admin')")
    
    cur.execute("SELECT value FROM system_settings WHERE key='school_name'")
    if not cur.fetchone():
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('school_name', 'POORNA PRAJNA SCHOOL BELL SYSTEM')")

    cur.execute("SELECT value FROM system_settings WHERE key='school_logo'")
    if not cur.fetchone():
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('school_logo', 'static/school-logo.png')")
    
    cur.execute("SELECT value FROM system_settings WHERE key='auto_start'")
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('auto_start', '0')")
    else:
        # Refresh registry on startup to handle path changes (e.g. if app was moved)
        if row["value"] == "1":
            print("Auto-start is enabled, refreshing registry path...")
            set_windows_autostart(True)

    conn.commit()
    conn.close()
    print("Database initialization complete.")

def init_license_db():
    # Deprecated: use init_db() instead. Keeping for backward compatibility if needed.
    init_db()

def check_license():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_settings WHERE key='license_expiry'")
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return {"status": "error", "days_left": 0, "expiry_date": ""}
        
    expiry_str = row["value"]
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
        now = datetime.now()
        days_left = (expiry_date - now).days
        
        if days_left < 0:
            return {"status": "expired", "days_left": days_left, "expiry_date": expiry_str}
        elif days_left <= 15:
            return {"status": "warning", "days_left": days_left, "expiry_date": expiry_str}
        else:
            return {"status": "active", "days_left": days_left, "expiry_date": expiry_str}
    except:
        return {"status": "error", "days_left": 0, "expiry_date": ""}

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

# Serve uploaded sound files
@app.route("/sounds/<path:filename>")
def serve_sound(filename):
    return send_from_directory(SOUNDS_DIR, filename)

@app.route("/api/sections")
def api_sections():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sections ORDER BY id")
    secs = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(secs)

@app.route("/api/set_section_enabled", methods=["POST"])
def api_set_section_enabled():
    data = request.json
    section_id = data.get("section_id")
    enabled = 1 if data.get("enabled") else 0
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE sections SET enabled=? WHERE id=?", (enabled, section_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/update_section_name", methods=["POST"])
def api_update_section_name():
    data = request.json
    section_id = data.get("section_id")
    name = data.get("name")
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE sections SET name=? WHERE id=?", (name, section_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/sounds")
def api_sounds():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sounds ORDER BY id")
    sounds = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(sounds)

@app.route("/api/slots/<int:section_id>")
def api_slots(section_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT sl.id, sl.section_id, sl.slot_no, sl.time, sl.enabled, sl.sound_id,
                   snd.filename, snd.name as sound_name
                   FROM slots sl LEFT JOIN sounds snd ON sl.sound_id = snd.id
                   WHERE sl.section_id=? ORDER BY sl.slot_no""", (section_id,))
    slots = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(slots)

@app.route("/api/update_slot", methods=["POST"])
def api_update_slot():
    data = request.json
    slot_id = data.get("id")
    time_val = data.get("time", "")
    sound_id = data.get("sound_id")
    enabled = 1 if data.get("enabled") else 0
    section_id = data.get("section_id", None)
    conn = get_conn()
    cur = conn.cursor()
    if section_id is None:
        cur.execute("UPDATE slots SET time=?, sound_id=?, enabled=? WHERE id=?", (time_val, sound_id, enabled, slot_id))
    else:
        cur.execute("UPDATE slots SET time=?, sound_id=?, enabled=?, section_id=? WHERE id=?", (time_val, sound_id, enabled, section_id, slot_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/upload_sound", methods=["POST"])
def api_upload_sound():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "file missing"}), 400
    f = request.files['file']
    filename = f.filename
    if not (filename.lower().endswith(('.wav', '.mp3', '.ogg', '.aif', '.aiff'))):
        return jsonify({"success": False, "error": "Only .wav, .mp3, .ogg, .aif, and .aiff files allowed"}), 400
        
    name = request.form.get("name") or f.filename
    filename = f.filename
    safe_path = os.path.join(SOUNDS_DIR, filename)
    f.save(safe_path)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO sounds(name, filename) VALUES(?,?)", (name, filename))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "filename": filename})

# IMPORTANT: This no longer starts playback on the server.
# Instead it returns the URL the client should play.
@app.route("/api/play_slot/<int:slot_id>", methods=["POST"])
def api_play_slot(slot_id):
    conn = get_conn()
    cur = conn.cursor()
    print(f"api_play_slot: {slot_id}")
    try:
        # join slots->sounds to get filename
        cur.execute("""SELECT snd.filename
                       FROM slots sl
                       LEFT JOIN sounds snd ON sl.sound_id = snd.id
                       WHERE sl.id = ?""", (slot_id,))
        row = cur.fetchone()
        if not row or not row["filename"]:
            return jsonify({"success": False, "error": "No sound file"}), 404

        filename = row["filename"]
        # ensure file exists on disk before returning URL
        safe_path = os.path.join(SOUNDS_DIR, filename)
        if not os.path.exists(safe_path):
            print(f"api_play_slot: file missing on disk: {safe_path}")
            return jsonify({"success": False, "error": "File missing on server"}), 404

        url = f"/sounds/{filename}"
        
        # Play on server (Raspberry Pi)
        try:
            print(f"Playing on server: {safe_path}")
            if pygame.mixer.get_init():
                pygame.mixer.music.load(safe_path)
                pygame.mixer.music.play()
            else:
                print("Pygame mixer not initialized")
        except Exception as e:
            print(f"Server playback error: {e}")

        return jsonify({"success": True, "url": url})
    except Exception as e:
        print("api_play_slot ERROR:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

# stop_sound now only used for coordinating server-side scheduler (if any).
@app.route("/api/stop_sound", methods=["POST"])
def api_stop_sound():
    # If you have server-side scheduler state to toggle, do it here.
    print("api_stop_sound called")
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            print("Server playback stopped")
    except Exception as e:
        print(f"Server stop error: {e}")
    return jsonify({"success": True})

@app.route("/api/active_alarms")
def api_active_alarms():
    now = datetime.now()
    def hm_to_minutes(hm):
        if not hm: return None
        try:
            h, m = hm.split(":")
            return int(h)*60 + int(m)
        except:
            return None

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT sl.id, sl.section_id, sl.slot_no, sl.time, sl.enabled, snd.filename, s.name as section_name
                   FROM slots sl
                   LEFT JOIN sounds snd ON sl.sound_id=snd.id
                   LEFT JOIN sections s ON s.id=sl.section_id
                   WHERE sl.enabled=1 AND sl.time<>'' AND s.enabled=1""")
    rows = cur.fetchall()
    upcoming = []
    now_minutes = now.hour*60 + now.minute
    for r in rows:
        mins = hm_to_minutes(r["time"])
        if mins is None: continue
        diff = (mins - now_minutes) if mins >= now_minutes else (24*60 - (now_minutes - mins))
        upcoming.append((diff, dict(r)))
    upcoming.sort(key=lambda x: x[0])
    result = []
    for diff, row in upcoming[:20]:
        next_dt = now + timedelta(minutes=diff)
        result.append({
            "slot": row,
            "minutes_from_now": diff,
            "next_at": next_dt.strftime("%Y-%m-%d %H:%M")
        })
    conn.close()
    # print("Active alrams", result);
    # print("Active alrams", result);
    return jsonify(result)

@app.route("/api/license_status")
def api_license_status():
    status = check_license()
    return jsonify(status)

@app.route("/api/renew_license", methods=["POST"])
def api_renew_license():
    data = request.json
    password = data.get("password")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_settings WHERE key='admin_password'")
    row = cur.fetchone()
    
    if not row or row["value"] != password:
        conn.close()
        return jsonify({"success": False, "error": "Invalid password"}), 401
        
    # renew for 1 year
    new_expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    cur.execute("UPDATE system_settings SET value=? WHERE key='license_expiry'", (new_expiry,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_expiry": new_expiry})

@app.route("/api/set_license_custom", methods=["POST"])
def api_set_license_custom():
    data = request.json
    password = data.get("password")
    custom_date = data.get("date") # YYYY-MM-DD
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_settings WHERE key='admin_password'")
    row = cur.fetchone()
    
    if not row or row["value"] != password:
        conn.close()
        return jsonify({"success": False, "error": "Invalid password"}), 401
    
    # Validate date format roughly
    try:
        datetime.strptime(custom_date, "%Y-%m-%d")
    except:
        conn.close()
        return jsonify({"success": False, "error": "Invalid date format"}), 400

    cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('license_expiry', ?)", (custom_date,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_expiry": custom_date})

@app.route("/api/verify_admin", methods=["POST"])
def api_verify_admin():
    data = request.json
    password = data.get("password")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_settings WHERE key='admin_password'")
    row = cur.fetchone()
    conn.close()
    
    if not row or row["value"] != password:
        return jsonify({"success": False, "error": "Invalid password"}), 401
        
    return jsonify({"success": True})

@app.route("/api/school_info")
def api_school_info():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM system_settings WHERE key IN ('school_name', 'school_logo', 'auto_start')")
    rows = cur.fetchall()
    info = {r["key"]: r["value"] for r in rows}
    conn.close()
    return jsonify(info)

def set_windows_autostart(enabled):
    """
    Manages multiple Windows auto-start methods: Task Scheduler (Primary), 
    Registry (Secondary), and Startup Folder (Fallback).
    """
    if sys.platform != "win32":
        return True, "Auto-start only supported on Windows"
        
    try:
        import subprocess
        app_name = "SchoolBell"
        
        # Determine current executable path
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            exe_path = f'"{sys.executable}" "{os.path.join(app_dir, "main_app.py")}"'

        # Ensure exe_path is quoted correctly for commands
        quoted_exe = f'"{exe_path.strip(\'"\')}"'

        # --- Method 1: Task Scheduler (The most reliable "At Boot/Logon" method) ---
        try:
            if enabled:
                # Create a task that runs at logon with highest privileges
                # Use /it to make it interactive (show the window)
                cmd = f'schtasks /create /tn "{app_name}" /tr {quoted_exe} /sc onlogon /rl highest /f'
                subprocess.run(cmd, shell=True, capture_output=True)
            else:
                subprocess.run(f'schtasks /delete /tn "{app_name}" /f', shell=True, capture_output=True)
        except Exception as e:
            print(f"Task Scheduler sync failed: {e}")

        # --- Method 2: Registry (PowerShell approach) ---
        try:
            if enabled:
                ps_reg_cmd = f'New-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "{app_name}" -Value {quoted_exe} -PropertyType String -Force'
                subprocess.run(["powershell", "-Command", ps_reg_cmd], capture_output=True)
            else:
                ps_reg_cmd = f'Remove-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "{app_name}" -ErrorAction SilentlyContinue'
                subprocess.run(["powershell", "-Command", ps_reg_cmd], capture_output=True)
        except Exception as e:
            print(f"Registry sync failed: {e}")

        # --- Method 3: Startup Folder Shortcut ---
        try:
            startup_path = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            shortcut_path = os.path.join(startup_path, f"{app_name}.lnk")
            if enabled:
                work_dir = os.path.dirname(os.path.abspath(__file__))
                ps_sc_cmd = f"$s=(New-Object -COM WScript.Shell).CreateShortcut('{shortcut_path}');$s.TargetPath={quoted_exe};$s.WorkingDirectory='{work_dir}';$s.Save()"
                subprocess.run(["powershell", "-Command", ps_sc_cmd], capture_output=True)
            else:
                if os.path.exists(shortcut_path): os.remove(shortcut_path)
        except Exception as e:
            print(f"Startup folder sync failed: {e}")

        return True, "Auto-start synchronized"
    except Exception as e:
        print(f"Auto-start master error: {e}")
        return False, str(e)

@app.route("/api/update_school_info", methods=["POST"])
def api_update_school_info():
    data = request.json
    password = data.get("password")
    school_name = data.get("school_name")
    school_logo = data.get("school_logo")
    auto_start = data.get("auto_start") # '1' or '0'

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_settings WHERE key='admin_password'")
    row = cur.fetchone()
    
    if not row or row["value"] != password:
        conn.close()
        return jsonify({"success": False, "error": "Invalid password"}), 401
    
    if school_name:
        cur.execute("UPDATE system_settings SET value=? WHERE key='school_name'", (school_name,))
    if school_logo:
        cur.execute("UPDATE system_settings SET value=? WHERE key='school_logo'", (school_logo,))
    
    if auto_start is not None:
        # Update registry
        success, msg = set_windows_autostart(auto_start == "1")
        if success:
            cur.execute("UPDATE system_settings SET value=? WHERE key='auto_start'", (auto_start,))
        else:
            # If registry fail, still return error but maybe we can ignore it if non-critical
            print(f"Failed to update auto-start in registry: {msg}")

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/upload_logo", methods=["POST"])
def api_upload_logo():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "file missing"}), 400
    
    password = request.form.get("password")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_settings WHERE key='admin_password'")
    pw_row = cur.fetchone()
    if not pw_row or pw_row["value"] != password:
        conn.close()
        return jsonify({"success": False, "error": "Invalid password"}), 401
    
    f = request.files['file']
    filename = "logo_" + f.filename
    # Define a custom location for logos to avoid confusion with bell sounds
    LOGOS_DIR = os.path.join(WRITABLE_DIR, "logos")
    os.makedirs(LOGOS_DIR, exist_ok=True)
    
    safe_path = os.path.join(LOGOS_DIR, filename)
    f.save(safe_path)
    
    # We'll serve this via a new route or just return the static path if it's in static
    # But since it's in WRITABLE_DIR, we need a route
    logo_url = f"/api/logos/{filename}"
    
    cur.execute("UPDATE system_settings SET value=? WHERE key='school_logo'", (logo_url,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "logo_url": logo_url})

@app.route("/api/logos/<path:filename>")
def serve_logo(filename):
    LOGOS_DIR = os.path.join(WRITABLE_DIR, "logos")
    return send_from_directory(LOGOS_DIR, filename)


def scheduler_loop():
    print("Scheduler thread started")
    last_minute = None
    while True:
        try:
            now = datetime.now()
            current_hm = now.strftime("%H:%M")
            if current_hm != last_minute:
                # Check license first
                lic = check_license()
                if lic["status"] == "expired":
                    print("License expired. Skipping scheduler.")
                    last_minute = current_hm
                    time.sleep(1)
                    continue

                # New minute, check for alarms
                conn = get_conn()
                cur = conn.cursor()
                # Query logic similar to api_active_alarms or specialized for exact match
                cur.execute("""SELECT sl.id, sl.sound_id, snd.filename 
                               FROM slots sl
                               JOIN sections s ON sl.section_id = s.id
                               LEFT JOIN sounds snd ON sl.sound_id = snd.id
                               WHERE sl.time = ? AND sl.enabled = 1 AND s.enabled = 1""", (current_hm,))
                rows = cur.fetchall()
                conn.close()

                if rows:
                    print(f"Scheduler found {len(rows)} slots for {current_hm}")
                    # Just play the first valid one found for now
                    played = False
                    for row in rows:
                        if played: break
                        filename = row['filename']
                        if filename:
                            safe_path = os.path.join(SOUNDS_DIR, filename)
                            if os.path.exists(safe_path):
                                print(f"Scheduler playing: {safe_path}")
                                try:
                                    if pygame.mixer.get_init():
                                        pygame.mixer.music.load(safe_path)
                                        pygame.mixer.music.play()
                                        played = True
                                    else:
                                        print("Scheduler: Pygame mixer not initialized")
                                except Exception as e:
                                    print(f"Scheduler playback error: {e}")
                            else:
                                print(f"Scheduler: file missing {safe_path}")
                
                last_minute = current_hm
        except Exception as e:
            print(f"Scheduler loop error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    # In debug mode, Flask's reloader spawns a child process.
    # We want the scheduler to run only in the process that handles requests (the child).
    # If debug is False, there is only one process, so we run the scheduler there.
    debug_mode = True

    if not debug_mode or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init_db()
        # Start scheduler thread
        t = threading.Thread(target=scheduler_loop, daemon=True)
        t.start()

    app.run(host="0.0.0.0", port=5050, debug=debug_mode)
