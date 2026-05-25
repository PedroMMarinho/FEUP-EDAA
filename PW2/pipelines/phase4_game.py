import sys
import time
import threading
import numpy as np
import tkinter as tk
from tkinter import ttk
import ctypes
import cv2
import pandas as pd

from pipelines.phase1_image import run_algorithm, get_next_csv_path
from utils.macros import ALGORITHMS, OUTPUT_STATS_DIR 

if sys.platform == "win32":
    import pygetwindow as gw
    import dxcam
    import pyvirtualcam
    
# --- Windows API Constants ---
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_HWNDPARENT = -8

class GhostOverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quantizer Controls")
        self.root.geometry("300x150")
        self.root.attributes("-topmost", True)
        
        self.current_algo = ALGORITHMS[0]
        self.current_colors = 8
        self.current_target = "" 
        self.running = True
        self.frame_count = 0  

        # VCam is None until we find a VALID game window
        self.vcam = None

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

        ttk.Button(root, text="Run FPS Benchmark", command=self.start_benchmark).pack(pady=(10,0))
        self.benchmark_mode = False

        self.algo_cb.bind("<<ComboboxSelected>>", self.on_change)
        self.color_cb.bind("<<ComboboxSelected>>", self.on_change)
        self.window_cb.bind("<<ComboboxSelected>>", self.on_window_change)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.overlay_title = "GhostGameOverlay_1337"
        self.capture_thread = threading.Thread(target=self.screen_worker_loop, daemon=False)
        self.capture_thread.start()

    def start_benchmark(self):
        if not self.current_target:
            print("Please select a target game first to start capturing.")
            return
        print("Benchmark requested... Waiting for capture loop to begin sequence.")
        self.benchmark_mode = True

    def on_window_change(self, event):
        self.current_target = self.window_cb.get()

    def refresh_windows(self):
        titles = [t for t in gw.getAllTitles() if t.strip()]
        self.window_cb['values'] = titles
        if self.current_target in titles:
            self.window_cb.set(self.current_target)
        else:
            self.window_cb.set("")
            self.current_target = ""

    def on_change(self, event):
        self.current_algo = self.algo_cb.get()
        self.current_colors = int(self.color_cb.get())

    def screen_worker_loop(self):
        camera = dxcam.create()
        last_region = None
        prev_time = time.time()
        window_created = False

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
                
                left = max(0, target_win.left)
                top = max(0, target_win.top)
                right = min(screen_width, target_win.right)
                bottom = min(screen_height, target_win.bottom)

                capture_w = right - left
                capture_h = bottom - top

                # --- NEW: ANTI-CRASH EVEN RESOLUTION ENFORCER ---
                # Force width and height to be strictly divisible by 2
                if capture_w % 2 != 0:
                    capture_w -= 1
                    right -= 1
                if capture_h % 2 != 0:
                    capture_h -= 1
                    bottom -= 1

                # Now the region is guaranteed to be safe for OBS
                current_region = (left, top, right, bottom)

                # --- NEW: ANTI-GHOST WINDOW PROTECTION ---
                # If the window is smaller than 400x300, it's fake. Ignore it.
                if capture_w < 400 or capture_h < 300:
                    time.sleep(0.1)
                    continue

                current_region = (left, top, right, bottom)

                if not window_created:
                    cv2.namedWindow(self.overlay_title, cv2.WINDOW_NORMAL)
                    cv2.setWindowProperty(self.overlay_title, cv2.WND_PROP_TOPMOST, 1)
                    cv2.imshow(self.overlay_title, np.zeros((100, 100, 3), dtype=np.uint8))
                    cv2.waitKey(1)
                    
                    self.hwnd = ctypes.windll.user32.FindWindowW(None, self.overlay_title)
                    
                    style = ctypes.windll.user32.GetWindowLongW(self.hwnd, GWL_STYLE)
                    ctypes.windll.user32.SetWindowLongW(self.hwnd, GWL_STYLE, style & ~WS_CAPTION & ~WS_THICKFRAME)
                    
                    ex_style = ctypes.windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
                    ctypes.windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
                    ctypes.windll.user32.SetLayeredWindowAttributes(self.hwnd, 0, 255, 2)
                    ctypes.windll.user32.SetWindowDisplayAffinity(self.hwnd, WDA_EXCLUDEFROMCAPTURE)
                    
                    game_hwnd = target_win._hWnd
                    try:
                        ctypes.windll.user32.SetWindowLongPtrW(self.hwnd, GWL_HWNDPARENT, game_hwnd)
                    except AttributeError:
                        ctypes.windll.user32.SetWindowLongW(self.hwnd, GWL_HWNDPARENT, game_hwnd)
                    
                    window_created = True

                if current_region != last_region:
                    if camera.is_capturing: camera.stop()
                    camera.start(region=current_region, target_fps=60)
                    last_region = current_region
                    
                    cv2.resizeWindow(self.overlay_title, capture_w, capture_h)
                    cv2.moveWindow(self.overlay_title, left, top)
                    
                    ctypes.windll.user32.SetWindowPos(
                        self.hwnd, HWND_TOPMOST, left, top, capture_w, capture_h, 
                        SWP_SHOWWINDOW
                    )
                    
                    # Lock the Virtual Camera to the EXACT size of the game
                    if self.vcam is not None:
                        self.vcam.close()
                    self.vcam = pyvirtualcam.Camera(width=capture_w, height=capture_h, fps=60)
                    print(f"Virtual Camera locked to game resolution: {capture_w}x{capture_h}")

                if self.benchmark_mode:
                    self.run_benchmark(camera, capture_w, capture_h)
                    self.benchmark_mode = False
                    continue

            except Exception:
                time.sleep(0.01)
                continue

            t_dx = time.perf_counter()
            frame_rgb = camera.grab()
            t_dx_end = time.perf_counter()
            
            if frame_rgb is None: continue

            algo = self.current_algo
            colors = self.current_colors

            # --- PROFILING: Algorithm & Hidden Conversions ---
            # Fix #1: Force contiguous memory BEFORE the timer so C++ doesn't have to copy it
            frame_rgb = np.ascontiguousarray(frame_rgb)

            t_algo_start = time.perf_counter()
            try:
                # 1. Time the actual C++ execution
                processed_pil = run_algorithm(algo, frame_rgb, colors)
                t_cpp_end = time.perf_counter() 

                if processed_pil is None: 
                    final_frame = frame_rgb
                else:
                    # 2. Time the PIL -> NumPy conversion penalty
                    final_frame = np.array(processed_pil)
                    
            except Exception as e:
                final_frame = frame_rgb
                t_cpp_end = time.perf_counter()
                
            t_algo_end = time.perf_counter()

            current_time = time.time()
            fps = 1.0 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time

            frame_h, frame_w = final_frame.shape[:2]

            #cv2.rectangle(final_frame, (frame_w - 120, 10), (frame_w - 10, 50), (0, 0, 0), -1)
            cv2.putText(final_frame, f"FPS: {int(fps)}", (frame_w - 110, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            t_cv2 = time.perf_counter()
            cv2.imshow(self.overlay_title, cv2.cvtColor(final_frame, cv2.COLOR_RGB2BGR))
            
            if hasattr(self, 'hwnd'):
                ctypes.windll.user32.SetWindowPos(
                    self.hwnd, HWND_TOPMOST, 0, 0, 0, 0, 
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
            cv2.waitKey(1) 
            t_cv2_end = time.perf_counter()

            # --- ZERO RESIZE VCAM ---
            t_vcam = time.perf_counter()
            if self.vcam is not None:
                self.vcam.send(final_frame)
            t_vcam_end = time.perf_counter()
            
            self.frame_count += 1
            if self.frame_count % 60 == 0:
                dx_ms = (t_dx_end - t_dx) * 1000
                
                # Split the algo time into Math vs Conversion
                cpp_ms = (t_cpp_end - t_algo_start) * 1000
                numpy_convert_ms = (t_algo_end - t_cpp_end) * 1000
                
                cv2_ms = (t_cv2_end - t_cv2) * 1000
                vcam_ms = (t_vcam_end - t_vcam) * 1000
                total_loop_ms = 1000.0 / fps if fps > 0 else 0
                
                print(f"[Worker] DXCam: {dx_ms:.1f}ms | C++ Math: {cpp_ms:.1f}ms | NP Copy: {numpy_convert_ms:.1f}ms | OpenCV: {cv2_ms:.1f}ms | VCam: {vcam_ms:.1f}ms | Loop: {total_loop_ms:.1f}ms")
            
        if camera.is_capturing: camera.stop()

    def run_benchmark(self, camera, w, h):
        print(f"\n--- Starting Live FPS Benchmark ({w}x{h}) ---")
        results = []
        colors_to_test = [8, 16, 32, 64, 128, 256]
        frames_per_test = 60 # Run 60 frames per configuration
        
        for algo in ALGORITHMS:
            for colors in colors_to_test:
                print(f"Benchmarking {algo} @ {colors} colors...")
                
                # Warmup frames
                for _ in range(10):
                    frame_rgb = camera.grab()
                    if frame_rgb is not None:
                        frame_rgb = np.ascontiguousarray(frame_rgb)
                        try:
                            run_algorithm(algo, frame_rgb, colors)
                        except Exception:
                            pass
                
                total_cpp_ms = 0
                total_loop_ms = 0
                valid_frames = 0
                
                for _ in range(frames_per_test):
                    t_loop_start = time.perf_counter()
                    
                    frame_rgb = camera.grab()
                    if frame_rgb is None:
                        time.sleep(0.01)
                        continue
                        
                    frame_rgb = np.ascontiguousarray(frame_rgb)
                    
                    t_cpp_start = time.perf_counter()
                    try:
                        processed_pil = run_algorithm(algo, frame_rgb, colors)
                    except Exception:
                        processed_pil = None
                    t_cpp_end = time.perf_counter()
                    
                    if processed_pil is not None:
                        final_frame = np.array(processed_pil)
                    else:
                        final_frame = frame_rgb
                        
                    # Emulate standard pipeline flow
                    cv2.imshow(self.overlay_title, cv2.cvtColor(final_frame, cv2.COLOR_RGB2BGR))
                    cv2.waitKey(1)
                    if self.vcam is not None:
                        self.vcam.send(final_frame)
                    
                    t_loop_end = time.perf_counter()
                    
                    total_cpp_ms += (t_cpp_end - t_cpp_start) * 1000
                    total_loop_ms += (t_loop_end - t_loop_start) * 1000
                    valid_frames += 1
                
                if valid_frames > 0:
                    avg_cpp_ms = total_cpp_ms / valid_frames
                    avg_full_ms = total_loop_ms / valid_frames
                    avg_fps = 1000.0 / avg_full_ms if avg_full_ms > 0 else 0
                    
                    results.append({
                        'Resolution': f"{w}x{h}",
                        'Algorithm': algo,
                        'Colors': colors,
                        'Avg FPS': avg_fps,
                        'Avg Full Loop (ms)': avg_full_ms,
                        'Avg C++ Math (ms)': avg_cpp_ms
                    })
                    print(f"  -> {avg_fps:.1f} FPS | Math: {avg_cpp_ms:.1f} ms | Loop: {avg_full_ms:.1f} ms")
                    
        out_dir = OUTPUT_STATS_DIR / "camera_fps"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = get_next_csv_path(out_dir, "live_camera_fps")
        
        df = pd.DataFrame(results)
        df.to_csv(out_path, index=False)
        print(f"\n--- Benchmark Complete! Saved to {out_path.name} ---")

    def on_closing(self):
        self.running = False
        if hasattr(self, 'capture_thread') and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
            
        cv2.destroyAllWindows()
        if self.vcam is not None:
            try:
                self.vcam.close()
            except Exception:
                pass
            
        self.root.destroy()

def process_game():
    print("--- Starting Phase 4: Ultimate Ghost Overlay ---")
    root = tk.Tk()
    app = GhostOverlayApp(root)
    root.mainloop()
    print("--- Game capture closed ---")