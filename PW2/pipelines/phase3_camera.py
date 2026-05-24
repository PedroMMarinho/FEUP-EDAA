import cv2
import time
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import pandas as pd
from itertools import product

from pipelines.phase1_image import run_algorithm
from utils.macros import ALGORITHMS, LIB, OUTPUT_STATS_DIR 

class LiveQuantizationApp:
    def __init__(self, root, auto_benchmark: bool = False, samples_per_config: int = 8, warmup_frames: int = 2):
        self.root = root
        self.root.title("Live Camera Quantization")
        self.auto_benchmark = auto_benchmark
        self.samples_per_config = samples_per_config
        self.warmup_frames = warmup_frames
        self.max_valid_fps = 31.0
        self.closing = False
        
        self.current_algo = ALGORITHMS[0]
        self.current_colors = 8
        self.current_res = "640x480"
        self.res_changed = True
        self.running = True
        self.benchmark_configs = []
        self.benchmark_index = 0
        self.samples_in_current_config = 0
        self.warmup_frames_remaining = 0
        
        self.latest_pil_image = None
        self.latest_fps = 0
        self.fps_samples = []

        self.color_options = [8, 16, 32, 64, 128, 256]
        self.res_options = ["320x240", "640x480", "800x600", "1280x720", "1920x1080"]
        self.algo_options = [algo for algo in ALGORITHMS if algo != "Shader-Acerola"]

        if self.auto_benchmark:
            self.benchmark_resolutions = ["1920x1080"]
            self.benchmark_configs = [
                {"Resolution": resolution, "Target Colors": colors, "Algorithm": algorithm}
                for resolution, colors, algorithm in product(self.benchmark_resolutions, self.color_options, self.algo_options)
            ]
        
        self.control_frame = tk.Frame(root, pady=10)
        self.control_frame.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(self.control_frame, text="Algorithm:").pack(side=tk.LEFT, padx=(10, 2))
        self.algo_cb = ttk.Combobox(self.control_frame, values=ALGORITHMS, state="readonly", width=15)
        self.algo_cb.current(0)
        self.algo_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.algo_cb.bind("<<ComboboxSelected>>", self.on_change)
        
        ttk.Label(self.control_frame, text="Colors:").pack(side=tk.LEFT, padx=(0, 2))
        self.color_cb = ttk.Combobox(self.control_frame, values=self.color_options, state="readonly", width=5)
        self.color_cb.current(0)
        self.color_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.color_cb.bind("<<ComboboxSelected>>", self.on_change)
        
        ttk.Label(self.control_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0, 2))
        self.res_cb = ttk.Combobox(self.control_frame, values=self.res_options, state="readonly", width=10)
        self.res_cb.current(1)
        self.res_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.res_cb.bind("<<ComboboxSelected>>", self.on_change)

        if self.auto_benchmark:
            self.algo_cb.configure(state="disabled")
            self.color_cb.configure(state="disabled")
            self.res_cb.configure(state="disabled")
            self._apply_config(self.benchmark_configs[0], sync_controls=False)
            self._sync_controls_to_state()

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

    def _sync_controls_to_state(self):
        if self.current_algo in ALGORITHMS:
            self.algo_cb.current(ALGORITHMS.index(self.current_algo))
        if self.current_colors in self.color_options:
            self.color_cb.current(self.color_options.index(self.current_colors))
        if self.current_res in self.res_options:
            self.res_cb.current(self.res_options.index(self.current_res))

    def _apply_config(self, config, sync_controls: bool = True):
        self.current_algo = config["Algorithm"]
        self.current_colors = int(config["Target Colors"])
        if config["Resolution"] != self.current_res:
            self.current_res = config["Resolution"]
            self.res_changed = True
            self.warmup_frames_remaining = self.warmup_frames
        if self.current_algo == "Octree-Live":
            LIB.reset_live_palette()
        if sync_controls:
            self.root.after(0, self._sync_controls_to_state)

    def _advance_benchmark_config(self) -> bool:
        self.benchmark_index += 1
        if self.benchmark_index >= len(self.benchmark_configs):
            return False

        self.samples_in_current_config = 0
        self._apply_config(self.benchmark_configs[self.benchmark_index], sync_controls=True)
        return True

    def camera_worker_loop(self):
        """This runs entirely in the background, smashing through frames as fast as possible."""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
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
                processed_array = run_algorithm(self.current_algo, frame_rgb, self.current_colors)
                
                if processed_array is None:
                    processed_array = frame_rgb
            except Exception:
                processed_array = frame_rgb

            current_time = time.time()
            fps = 1.0 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time

            self.latest_fps = fps
            if self.auto_benchmark:
                if self.warmup_frames_remaining > 0:
                    self.warmup_frames_remaining -= 1
                else:
                    if fps > self.max_valid_fps:
                        continue

                    self.fps_samples.append({
                        "Algorithm": self.current_algo,
                        "Resolution": self.current_res,
                        "Target Colors": self.current_colors,
                        "FPS": fps,
                    })
                    self.samples_in_current_config += 1
                    if self.samples_in_current_config >= self.samples_per_config:
                        if not self._advance_benchmark_config():
                            self.running = False
                            self.root.after(0, self.on_closing)
                            break
            
            if not self.auto_benchmark:
                self.fps_samples.append({
                    "Algorithm": self.current_algo,
                    "Resolution": self.current_res,
                    "Target Colors": self.current_colors,
                    "FPS": fps,
                })
            
            self.latest_pil_image = Image.fromarray(processed_array)

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
        if self.closing:
            return

        self.closing = True
        self.running = False
        if self.capture_thread.is_alive() and threading.current_thread() != self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        self.save_fps_summary()
        self.root.destroy()

    def save_fps_summary(self):
        if not self.auto_benchmark:
            return

        if not self.fps_samples:
            return

        stats_dir = OUTPUT_STATS_DIR / "camera_fps"
        stats_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(self.fps_samples)
        summary_df = (
            df.groupby(["Algorithm", "Resolution", "Target Colors"], as_index=False)
            .agg(Avg_FPS=("FPS", "mean"), Sample_Count=("FPS", "size"))
            .sort_values(["Resolution", "Target Colors", "Algorithm"])
        )

        output_file = stats_dir / "live_camera_fps_summary.csv"
        summary_df.to_csv(output_file, index=False)
        print(f"Saved FPS summary to: {output_file}")

def process_live_camera(auto_benchmark: bool = False, samples_per_config: int = 20, warmup_frames: int = 2):
    root = tk.Tk()
    app = LiveQuantizationApp(
        root,
        auto_benchmark=auto_benchmark,
        samples_per_config=samples_per_config,
        warmup_frames=warmup_frames,
    )
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    print("--- Live feed closed ---")

