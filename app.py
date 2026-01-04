# app.py
import os
import sqlite3
import pygame
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import threading
import sys
import time

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_writable_dir():
    """ Get the directory where the EXE is located (for DB and logs) """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

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

# License System Helpers
def init_license_db():
    conn = get_conn()
    cur = conn.cursor()
    # Create system_settings table if not exists
    cur.execute("""CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                  )""")
    # Check if license_expiry exists
    cur.execute("SELECT value FROM system_settings WHERE key='license_expiry'")
    if not cur.fetchone():
        # Default expiry: 1 year from now
        expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('license_expiry', ?)", (expiry,))
    
    # Check if admin_password exists
    cur.execute("SELECT value FROM system_settings WHERE key='admin_password'")
    if not cur.fetchone():
        cur.execute("INSERT INTO system_settings (key, value) VALUES ('admin_password', 'admin')")
    
    conn.commit()
    conn.close()

def check_license():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_settings WHERE key='license_expiry'")
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return {"status": "error", "days_left": 0}
        
    expiry_str = row["value"]
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
        now = datetime.now()
        days_left = (expiry_date - now).days
        
        if days_left < 0:
            return {"status": "expired", "days_left": days_left}
        elif days_left <= 15:
            return {"status": "warning", "days_left": days_left}
        else:
            return {"status": "active", "days_left": days_left}
    except:
        return {"status": "error", "days_left": 0}

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
        init_license_db()
        # Start scheduler thread
        t = threading.Thread(target=scheduler_loop, daemon=True)
        t.start()

    app.run(host="0.0.0.0", port=5050, debug=debug_mode)
