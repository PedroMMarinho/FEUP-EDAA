import cv2
import time
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from pipelines.phase1_image import run_algorithm
from utils.macros import ALGORITHMS, LIB 

class LiveQuantizationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live Camera Quantization")
        
        self.current_algo = ALGORITHMS[0]
        self.current_colors = 8
        self.current_res = "640x480"
        self.res_changed = True
        self.running = True
        
        self.latest_pil_image = None
        self.latest_fps = 0
        
        self.control_frame = tk.Frame(root, pady=10)
        self.control_frame.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(self.control_frame, text="Algorithm:").pack(side=tk.LEFT, padx=(10, 2))
        self.algo_cb = ttk.Combobox(self.control_frame, values=ALGORITHMS, state="readonly", width=15)
        self.algo_cb.current(0)
        self.algo_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.algo_cb.bind("<<ComboboxSelected>>", self.on_change)
        
        color_options = [8, 16, 32, 64, 128, 256]
        ttk.Label(self.control_frame, text="Colors:").pack(side=tk.LEFT, padx=(0, 2))
        self.color_cb = ttk.Combobox(self.control_frame, values=color_options, state="readonly", width=5)
        self.color_cb.current(0)
        self.color_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.color_cb.bind("<<ComboboxSelected>>", self.on_change)
        
        res_options = ["320x240", "640x480", "800x600", "1280x720", "1920x1080"]
        ttk.Label(self.control_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0, 2))
        self.res_cb = ttk.Combobox(self.control_frame, values=res_options, state="readonly", width=10)
        self.res_cb.current(1)
        self.res_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.res_cb.bind("<<ComboboxSelected>>", self.on_change)

        self.fps_label = ttk.Label(self.control_frame, text="FPS: 0", font=("Arial", 18, "bold"), foreground="green")
        self.fps_label.pack(side=tk.RIGHT, padx=20)
        
        self.video_label = tk.Label(root)
        self.video_label.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        self.root.bind('<q>', lambda event: self.on_closing())
        self.root.bind('<Q>', lambda event: self.on_closing())
        
        self.capture_thread = threading.Thread(target=self.camera_worker_loop, daemon=True)
        self.capture_thread.start()

        self.update_ui()

    def on_change(self, event):
        """Updates state variables. The background thread will read these instantly."""
        self.current_algo = self.algo_cb.get()
        self.current_colors = int(self.color_cb.get())
        
        if self.current_algo == "Octree-Live":
            LIB.reset_live_palette()

        new_res = self.res_cb.get()
        if new_res != self.current_res:
            self.current_res = new_res
            self.res_changed = True

    def camera_worker_loop(self):
        """This runs entirely in the background, smashing through frames as fast as possible."""
        cap = cv2.VideoCapture(0)
        prev_time = time.time()

        while self.running:
            if self.res_changed:
                w, h = map(int, self.current_res.split('x'))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                self.res_changed = False

            ret, frame = cap.read()
            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            try:
                processed_pil = run_algorithm(self.current_algo, frame_rgb, self.current_colors)
                if processed_pil is None:
                    processed_pil = frame_rgb
            except Exception:
                processed_pil = frame_rgb

            current_time = time.time()
            fps = 1.0 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time

            self.latest_fps = fps
            self.latest_pil_image = Image.fromarray(processed_pil)

        cap.release()

    def update_ui(self):
        """This runs in the main thread and just updates the screen with whatever is ready."""
        if self.latest_pil_image is not None:
            self.fps_label.config(text=f"FPS: {int(self.latest_fps)}")

            imgtk = ImageTk.PhotoImage(image=self.latest_pil_image)
            self.video_label.imgtk = imgtk 
            self.video_label.configure(image=imgtk)

        self.root.after(5, self.update_ui)

    def on_closing(self):
        """Kills the background thread and destroys the window."""
        self.running = False
        self.root.destroy()

def process_live_camera():
    root = tk.Tk()
    app = LiveQuantizationApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    print("--- Live feed closed ---")

