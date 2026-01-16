import sys
import threading
import time

# Try to import Windows-specific libraries
try:
    if sys.platform == "win32":
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        from comtypes import CLSCTX_ALL
        WINDOWS_LIBS_AVAILABLE = True
    else:
        WINDOWS_LIBS_AVAILABLE = False
except ImportError:
    WINDOWS_LIBS_AVAILABLE = False

_original_volumes = {}
_muted_sessions = []
_ducking_lock = threading.Lock()

def duck_others():
    """Mutes all other audio sessions on Windows except the current process."""
    if not WINDOWS_LIBS_AVAILABLE:
        return

    with _ducking_lock:
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                # Skip our propia process if possible, though usually mixer processes are separate
                # In most cases, muting the 'System' session or others is fine.
                if not volume.GetMute():
                    volume.SetMute(1, None)
                    _muted_sessions.append(volume)
            print(f"Windows Ducking: Muted {len(_muted_sessions)} sessions.")
        except Exception as e:
            print(f"Windows Ducking error (mute): {e}")

def unduck_others():
    """Unmutes previously muted audio sessions."""
    if not WINDOWS_LIBS_AVAILABLE:
        return

    with _ducking_lock:
        try:
            count = 0
            for volume in _muted_sessions:
                volume.SetMute(0, None)
                count += 1
            _muted_sessions.clear()
            print(f"Windows Ducking: Unmuted {count} sessions.")
        except Exception as e:
            print(f"Windows Ducking error (unmute): {e}")
            _muted_sessions.clear() # Clear anyway to avoid double mute issues
