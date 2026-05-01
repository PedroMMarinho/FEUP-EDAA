import sys
import time
import threading
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import ctypes
import cv2

from pipelines.phase1_image import run_algorithm
from utils.macros import ALGORITHMS 

if sys.platform == "win32":
    import pygetwindow as gw
    import dxcam
    import pyvirtualcam
    
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WDA_EXCLUDEFROMCAPTURE = 0x00000011

# --- Windows API Constants ---
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WDA_EXCLUDEFROMCAPTURE = 0x00000011

class GhostOverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quantizer Controls")
        self.root.geometry("300x150")
        self.root.attributes("-topmost", True)
        
        # Safe state variables for cross-thread reading
        self.current_algo = ALGORITHMS[0]
        self.current_colors = 8
        self.current_target = "" 
        self.running = True
        self.latest_frame = None

        self.vcam = pyvirtualcam.Camera(width=1920, height=1080, fps=60)
        print(f"Virtual camera ready: {self.vcam.device}")

        # --- Setup Controls ---
        ttk.Label(root, text="Algorithm:").pack(pady=(5,0))
        self.algo_cb = ttk.Combobox(root, values=ALGORITHMS, state="readonly")
        self.algo_cb.current(0)
        self.algo_cb.pack()
        
        ttk.Label(root, text="Colors:").pack(pady=(5,0))
        self.color_cb = ttk.Combobox(root, values=[8, 16, 32, 64, 128, 256], state="readonly")
        self.color_cb.current(0)
        self.color_cb.pack()

        ttk.Label(root, text="Target Game:").pack(pady=(5,0))
        self.window_cb = ttk.Combobox(root, state="readonly")
        self.window_cb.pack()
        self.refresh_windows()

        # Bindings to safely update variables when the user clicks
        self.algo_cb.bind("<<ComboboxSelected>>", self.on_change)
        self.color_cb.bind("<<ComboboxSelected>>", self.on_change)
        self.window_cb.bind("<<ComboboxSelected>>", self.on_window_change)

        # --- The Ghost Overlay ---
        self.overlay = tk.Toplevel(self.root)
        self.overlay_title = "GhostGameOverlay_1337"
        self.overlay.title(self.overlay_title)
        
        self.overlay.overrideredirect(True) 
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg='black')

        self.video_label = tk.Label(self.overlay, bg="black")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        # Wait 100ms for Tkinter to draw the window, then ghost it
        self.root.after(100, self.make_click_through)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start Threads
        self.capture_thread = threading.Thread(target=self.screen_worker_loop, daemon=True)
        self.capture_thread.start()

        self.update_ui()

    def make_click_through(self):
        hwnd = ctypes.windll.user32.FindWindowW(None, self.overlay_title)
        if hwnd:
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
            ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, 2)
            
            # Keep this active so DXCAM grabs the game, not the overlay itself
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            print("Overlay is invisible to mouse and screen capture!")

    def on_window_change(self, event):
        """Safely update target variable for the background thread."""
        self.current_target = self.window_cb.get()

    def refresh_windows(self):
        titles = [t for t in gw.getAllTitles() if t.strip()]
        self.window_cb['values'] = titles
        if titles: 
            self.window_cb.current(0)
            self.current_target = titles[0]

    def on_change(self, event):
        """Safely update algorithm variables for the background thread."""
        self.current_algo = self.algo_cb.get()
        self.current_colors = int(self.color_cb.get())

    def screen_worker_loop(self):
        camera = dxcam.create()
        last_region = None
        prev_time = time.time()

        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        while self.running:
            target_title = self.current_target 
            
            if not target_title:
                time.sleep(0.1)
                continue
            
            try:
                windows = gw.getWindowsWithTitle(target_title)
                if not windows:
                    time.sleep(0.1)
                    continue
                
                target_win = windows[0]
                if target_win.width <= 10 or target_win.height <= 10:
                    time.sleep(0.1)
                    continue

                # ==========================================
                # NEW: CLAMP THE REGION TO SCREEN BOUNDS
                # ==========================================
                left = max(0, target_win.left)
                top = max(0, target_win.top)
                right = min(screen_width, target_win.right)
                bottom = min(screen_height, target_win.bottom)

                # Failsafe: If the window is somehow minimized or completely off-screen
                if right <= left or bottom <= top:
                    time.sleep(0.1)
                    continue

                current_region = (left, top, right, bottom)

                if current_region != last_region:
                    if camera.is_capturing: camera.stop()
                    # DXCam will now gladly accept this since it's strictly on-screen
                    camera.start(region=current_region, target_fps=60)
                    last_region = current_region
                    
                    # Update overlay geometry to match the clamped region!
                    capture_w = right - left
                    capture_h = bottom - top
                    self.overlay_geometry = f"{capture_w}x{capture_h}+{left}+{top}"

            except Exception:
                time.sleep(0.01)
                continue

            frame_rgb = camera.grab()
            if frame_rgb is None: continue

            # ==========================================
            # UPDATE: Use the clamped width/height, NOT the window width/height
            # ==========================================
            target_w = capture_w
            target_h = capture_h
            algo = self.current_algo
            colors = self.current_colors

            try:
                if "Acerola" in algo:

                    processed_pil = run_algorithm(algo, frame_rgb, colors)
                    final_frame = np.array(processed_pil)
                
                else:
                    frame_small = cv2.resize(frame_rgb, (600, 400), interpolation=cv2.INTER_AREA)
                    
                    processed_pil = run_algorithm(algo, frame_small, colors)
                    if processed_pil is None: processed_pil = frame_small
                    processed_array = np.array(processed_pil)
                    
                    final_frame = cv2.resize(processed_array, (target_w, target_h), interpolation=cv2.INTER_NEAREST)

            except Exception as e:
                print(f"Algorithm error: {e}")
                final_frame = frame_rgb

            current_time = time.time()
            fps = 1.0 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time

            cv2.rectangle(final_frame, (target_w - 120, 10), (target_w - 10, 50), (0, 0, 0), -1)
            cv2.putText(final_frame, f"FPS: {int(fps)}", (target_w - 110, 35), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            self.latest_frame = final_frame
            final_resized = cv2.resize(final_frame, (1920, 1080), interpolation=cv2.INTER_NEAREST)
            self.vcam.send(final_resized)
            
        if camera.is_capturing: camera.stop()

    def update_ui(self):
        if hasattr(self, 'overlay_geometry'):
            self.overlay.geometry(self.overlay_geometry)

        if self.latest_frame is not None:
            img_pil = Image.fromarray(self.latest_frame)
            imgtk = ImageTk.PhotoImage(image=img_pil)
            self.video_label.imgtk = imgtk 
            self.video_label.configure(image=imgtk)

        # Updated to 16ms to match a smooth 60 FPS refresh rate
        self.root.after(16, self.update_ui)

    def on_closing(self):
        self.running = False
        self.vcam.close()
        self.root.destroy()

def process_game():
    print("--- Starting Phase 4: Ultimate Ghost Overlay ---")
    root = tk.Tk()
    app = GhostOverlayApp(root)
    root.mainloop()
    print("--- Game capture closed ---")