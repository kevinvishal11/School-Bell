import os
import json
import uuid
import sys

class DeviceManager:
    def __init__(self):
        self.device_id = None
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, "device.json")
        self._initialize()

    def _get_config_dir(self):
        """Returns the directory to store the device configuration."""
        if sys.platform == "win32":
            app_data = os.environ.get("APPDATA")
            if not app_data:
                app_data = os.path.expanduser("~\\AppData\\Roaming")
            return os.path.join(app_data, "SchoolBell")
        elif sys.platform == "darwin":
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "SchoolBell")
        else:
            # Fallback for Linux or other platforms
            return os.path.join(os.path.expanduser("~"), ".config", "SchoolBell")

    def _initialize(self):
        """Initializes the device ID: loads existing or generates a new one."""
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating config directory: {e}")

        if os.path.exists(self.config_file):
            self.device_id = self._load_device_id()
        
        if not self.device_id:
            self.device_id = self._generate_device_id()
            self._save_device_id()

    def _load_device_id(self):
        """Loads the device ID from the JSON file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    device_id = data.get("device_id")
                    if device_id:
                        return device_id
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading device_id (possible corruption): {e}")
            # If corrupted, we might want to backup and regenerate, 
            # but requirements say "must never change". 
            # However, if it's unreadable, we have to handle it.
        return None

    def _generate_device_id(self):
        """Generates a new UUID."""
        return str(uuid.uuid4())

    def _save_device_id(self):
        """Saves the device ID to the JSON file."""
        try:
            data = {"device_id": self.device_id}
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error saving device_id: {e}")

    def get_device_id(self):
        """Returns the current device ID."""
        return self.device_id

    def get_qr_payload(self):
        """Returns the JSON payload for the QR code."""
        return json.dumps({
            "app": "school-bell",
            "device_id": self.device_id
        })

if __name__ == "__main__":
    # Quick test
    dm = DeviceManager()
    print(f"Device ID: {dm.get_device_id()}")
    print(f"QR Payload: {dm.get_qr_payload()}")
