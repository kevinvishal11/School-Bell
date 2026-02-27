import tkinter as tk
from tkinter import messagebox
import qrcode
from PIL import Image, ImageTk
import io
import json
from device_manager import DeviceManager

class DeviceInfoWindow:
    def __init__(self, master=None):
        self.device_id = "Loading..."
        self.qr_payload = "{}"
        
        # Fetch enriched info from API (Port 5050)
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:5050/api/device_info", timeout=2) as response:
                data = json.loads(response.read().decode())
                self.device_id = data.get("device_id", "Unknown")
                self.qr_payload = data.get("qr_payload", "{}")
        except Exception as e:
            print(f"Could not connect to API for enriched info: {e}")
            # Fallback to local device_id
            self.dm = DeviceManager()
            self.device_id = self.dm.get_device_id()
            self.qr_payload = self.dm.get_qr_payload()
        
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)
            
        self.root.title("Device Information")
        self.root.geometry("400x550")
        self.root.set_property = (False, False) # Disable resizing
        self.root.resizable(False, False)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Header
        header = tk.Label(self.root, text="School Bell Device ID", font=("Helvetica", 16, "bold"), pady=20)
        header.pack()
        
        # Device ID Display
        id_frame = tk.Frame(self.root, pady=10)
        id_frame.pack(fill="x", padx=20)
        
        id_label = tk.Label(id_frame, text="Device ID:", font=("Helvetica", 10, "bold"))
        id_label.pack(anchor="w")
        
        self.id_text = tk.Entry(id_frame, font=("Courier", 10), justify="center")
        self.id_text.insert(0, self.device_id)
        self.id_text.config(state="readonly")
        self.id_text.pack(fill="x", pady=5)
        
        # Copy Button
        copy_btn = tk.Button(id_frame, text="Copy Device ID", command=self._copy_to_clipboard, 
                             bg="#4CAF50", fg="white", font=("Helvetica", 10, "bold"), pady=5)
        copy_btn.pack(pady=5)
        
        # QR Code Display
        qr_frame = tk.Frame(self.root, pady=20)
        qr_frame.pack()
        
        qr_label = tk.Label(qr_frame, text="Scan to Pair", font=("Helvetica", 10, "italic"))
        qr_label.pack(pady=5)
        
        self.qr_img_label = tk.Label(qr_frame)
        self.qr_img_label.pack()
        self._generate_qr()
        
        # Close Button
        close_btn = tk.Button(self.root, text="Close", command=self.root.destroy, pady=5, padx=20)
        close_btn.pack(side="bottom", pady=20)

    def _generate_qr(self):
        """Generates the QR code image and displays it."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.qr_payload)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to PhotoImage for Tkinter
            img = img.resize((250, 250), Image.Resampling.LANCZOS)
            self.qr_photo = ImageTk.PhotoImage(img)
            self.qr_img_label.config(image=self.qr_photo)
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate QR code: {e}")

    def _copy_to_clipboard(self):
        """Copies the device ID to the system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.device_id)
        self.root.update() # Keeps it in clipboard after window closes
        messagebox.showinfo("Copied", "Device ID copied to clipboard!")

    def run(self):
        self.root.mainloop()

def show_device_info():
    app = DeviceInfoWindow()
    app.run()

if __name__ == "__main__":
    show_device_info()
