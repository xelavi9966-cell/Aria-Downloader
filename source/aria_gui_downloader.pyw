import os
import sys
import re
import json
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


class AriaDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aria2 Downloader")
        self.root.geometry("980x760")
        self.root.minsize(900, 650)

        #self.base_dir = os.path.dirname(os.path.abspath(__file__))
        #self.aria_path = os.path.join(self.base_dir, "aria2c.exe")
        #self.config_path = os.path.join(self.base_dir, "aria_gui_config.json")

        if getattr(sys, "frozen", False):
            self.base_dir = sys._MEIPASS
            self.user_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.user_dir = self.base_dir

        self.aria_path = os.path.join(self.base_dir, "aria2c.exe")
        self.config_path = os.path.join(self.user_dir, "aria_gui_config.json")

        self.process = None
        self.is_running = False

        self.url_var = tk.StringVar()
        self.dir_var = tk.StringVar()
        self.filename_var = tk.StringVar()

        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="Done")
        self.speed_var = tk.StringVar(value="Speed: —")
        self.percent_var = tk.StringVar(value="0%")
        self.size_var = tk.StringVar(value="Size: —")
        self.eta_var = tk.StringVar(value="Remains: —")

        self._build_ui()
        self.load_config()
        self.set_idle_progress()

        if not os.path.exists(self.aria_path):
            messagebox.showerror(
                "Error",
                f"Not found aria2c.exe\n\nExpected here:\n{self.aria_path}"
            )

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="Link:").grid(row=0, column=0, sticky="w")
        self.url_entry = tk.Entry(top, textvariable=self.url_var, width=95)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")

        tk.Label(top, text="Folder:").grid(row=1, column=0, sticky="w")
        self.dir_entry = tk.Entry(top, textvariable=self.dir_var, width=75)
        self.dir_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        tk.Button(top, text="Select", command=self.choose_directory, width=12).grid(row=1, column=2, padx=5)

        tk.Label(top, text="File name:").grid(row=2, column=0, sticky="w")
        self.filename_entry = tk.Entry(top, textvariable=self.filename_var, width=95)
        self.filename_entry.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        top.grid_columnconfigure(1, weight=1)

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        self.start_button = tk.Button(btns, text="Start", command=self.start_download, width=14)
        self.start_button.pack(side="left", padx=5)

        self.continue_button = tk.Button(btns, text="Continue", command=self.continue_download, width=14, state="disabled")
        self.continue_button.pack(side="left", padx=5)

        self.stop_button = tk.Button(btns, text="Stop", command=self.stop_download, width=14, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        self.open_folder_button = tk.Button(btns, text="Open Folder", command=self.open_download_folder, width=14)
        self.open_folder_button.pack(side="left", padx=5)

        self.clear_button = tk.Button(btns, text="Clear Log", command=self.clear_log, width=14)
        self.clear_button.pack(side="left", padx=5)

        progress_frame = tk.LabelFrame(self.root, text="Download progress")
        progress_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", padx=10, pady=(10, 8))

        row1 = tk.Frame(progress_frame)
        row1.pack(fill="x", padx=10, pady=2)

        self.status_label = tk.Label(row1, textvariable=self.status_var, anchor="w", font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side="left")

        self.percent_label = tk.Label(row1, textvariable=self.percent_var, anchor="e", font=("Segoe UI", 11, "bold"))
        self.percent_label.pack(side="right")

        row2 = tk.Frame(progress_frame)
        row2.pack(fill="x", padx=10, pady=(2, 2))

        tk.Label(row2, textvariable=self.size_var, anchor="w", width=28).pack(side="left")
        tk.Label(row2, textvariable=self.speed_var, anchor="w", width=22).pack(side="left", padx=(10, 0))

        row3 = tk.Frame(progress_frame)
        row3.pack(fill="x", padx=10, pady=(2, 10))

        self.eta_big_label = tk.Label(
            row3,
            textvariable=self.eta_var,
            anchor="w",
            font=("Segoe UI", 11, "bold")
        )
        self.eta_big_label.pack(side="left")

        tk.Label(self.root, text="Log:").pack(anchor="w", padx=10)

        self.log_box = scrolledtext.ScrolledText(self.root, wrap="word", font=("Consolas", 10))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_box.configure(state="disabled")

    def choose_directory(self):
        folder = filedialog.askdirectory(title="Select a folder to download")
        if folder:
            self.dir_var.set(folder)
            self.save_config()

    def open_download_folder(self):
        folder = self.dir_var.get().strip()
        if not folder:
            messagebox.showwarning("Attention", "First, specify the download folder.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"The folder does not exist:\n{folder}")
            return
        os.startfile(folder)

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def set_idle_progress(self):
        self.progress_var.set(0)
        self.status_var.set("Done")
        self.speed_var.set("Speed: —")
        self.percent_var.set("0%")
        self.size_var.set("Size: —")
        self.eta_var.set("Remains: —")

    def auto_fill_filename_from_url(self):
        if self.filename_var.get().strip():
            return
        url = self.url_var.get().strip()
        if not url:
            return
        candidate = url.split("?")[0].rstrip("/").split("/")[-1]
        if candidate and "." in candidate and len(candidate) < 200:
            self.filename_var.set(candidate)

    def build_command(self, resume=False):
        url = self.url_var.get().strip()
        out_dir = self.dir_var.get().strip()
        filename = self.filename_var.get().strip()

        if not url:
            messagebox.showwarning("Attention", "Insert a link to the file.")
            return None

        if not out_dir:
            messagebox.showwarning("Attention", "Select a folder to download.")
            return None

        if not os.path.exists(self.aria_path):
            messagebox.showerror("Error", f"Not found aria2c.exe:\n{self.aria_path}")
            return None

        if not os.path.isdir(out_dir):
            messagebox.showerror("Error", f"The folder does not exist:\n{out_dir}")
            return None

        cmd = [
            self.aria_path,
            "--console-log-level=notice",
            "--summary-interval=1",
            "--max-tries=0",
            "--retry-wait=5",
            "-x", "1",
            "-s", "1",
            "-k", "1M",
            "-d", out_dir,
        ]

        if resume:
            cmd.append("-c")

        if filename:
            cmd.extend(["-o", filename])

        cmd.append(url)
        return cmd

    def start_download(self):
        if self.is_running:
            return

        self.auto_fill_filename_from_url()
        cmd = self.build_command(resume=False)
        if not cmd:
            return

        self.save_config()

        self.continue_button.config(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("Start download...")
        self.speed_var.set("Speed: —")
        self.percent_var.set("0%")
        self.size_var.set("Size: —")
        self.eta_var.set("Remains: —")
        self.run_process(cmd)

    def continue_download(self):
        if self.is_running:
            return

        self.auto_fill_filename_from_url()
        cmd = self.build_command(resume=True)
        if not cmd:
            return

        self.save_config()

        self.continue_button.config(state="disabled")
        self.status_var.set("Continue downloading...")
        self.run_process(cmd)

    def stop_download(self):
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.log("⏹ Upload stopped by user.")
            except Exception as e:
                self.log(f"Stop error: {e}")

    def run_process(self, cmd):
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.continue_button.config(state="disabled")

        self.log("=" * 100)
        self.log("Launching the command:")
        self.log(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        self.log("=" * 100)

        thread = threading.Thread(target=self._worker, args=(cmd,), daemon=True)
        thread.start()

    def parse_progress_line(self, line):
        # [#abcd12 2.9GiB/5.3GiB(54%) CN:2 DL:337KiB ETA:2h5m2s]
        match = re.search(
            r'(\S+/\S+)\((\d+)%\).*?DL:([^\s]+)(?:\s+ETA:([^\s\]]+))?',
            line
        )
        if match:
            size_text = match.group(1)
            percent = int(match.group(2))
            speed = match.group(3)
            eta_raw = match.group(4) if match.group(4) else "—"

            self.root.after(0, self.update_progress_ui, percent, size_text, speed, eta_raw)
            return True
        return False

    def format_eta(self, eta_raw):
        if not eta_raw or eta_raw == "—":
            return "—"

        hours = 0
        minutes = 0
        seconds = 0

        h = re.search(r'(\d+)h', eta_raw)
        m = re.search(r'(\d+)m', eta_raw)
        s = re.search(r'(\d+)s', eta_raw)

        if h:
            hours = int(h.group(1))
        if m:
            minutes = int(m.group(1))
        if s:
            seconds = int(s.group(1))

        parts = []
        if hours:
            parts.append(f"{hours} ч")
        if minutes:
            parts.append(f"{minutes} min")
        if seconds or not parts:
            parts.append(f"{seconds} sec")

        return " ".join(parts)

    def update_progress_ui(self, percent, size_text, speed, eta_raw):
        eta_text = self.format_eta(eta_raw)

        self.progress_var.set(percent)
        self.percent_var.set(f"{percent}%")
        self.size_var.set(f"Size: {size_text}")
        self.speed_var.set(f"Speed: {speed}")
        self.eta_var.set(f"Remains: {eta_text}")
        self.status_var.set("Loading is underway...")

        self.root.title(f"Aria2 Downloader — {percent}% — {eta_text}")

    def _worker(self, cmd):
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags
            )

            for line in self.process.stdout:
                clean_line = line.rstrip()
                self.root.after(0, self.log, clean_line)
                self.parse_progress_line(clean_line)

            return_code = self.process.wait()

            if return_code == 0:
                self.root.after(0, self.log, "✅ Download completed successfully.")
                self.root.after(0, lambda: self.status_var.set("The download is complete"))
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self.percent_var.set("100%"))
                self.root.after(0, lambda: self.eta_var.set("Remains: 0 сек"))
                self.root.after(0, lambda: self.continue_button.config(state="disabled"))
                self.root.after(0, lambda: self.root.title("Aria2 Downloader — Done"))
            else:
                self.root.after(0, self.log, f"⚠ The process ended with the following code: {return_code}")
                self.root.after(0, self.log, "You can press Continue to dock.")
                self.root.after(0, lambda: self.status_var.set("Loading aborted"))
                self.root.after(0, lambda: self.continue_button.config(state="normal"))
                self.root.after(0, lambda: self.root.title("Aria2 Downloader — Loading aborted"))

        except Exception as e:
            self.root.after(0, self.log, f"❌ Startup error: {e}")
            self.root.after(0, lambda: self.status_var.set("Startup error"))
            self.root.after(0, lambda: self.continue_button.config(state="normal"))
            self.root.after(0, lambda: self.root.title("Aria2 Downloader — Error"))

        finally:
            self.is_running = False
            self.process = None
            self.root.after(0, lambda: self.start_button.config(state="normal"))
            self.root.after(0, lambda: self.stop_button.config(state="disabled"))

    def save_config(self):
        data = {
            "last_url": self.url_var.get().strip(),
            "last_dir": self.dir_var.get().strip(),
            "last_filename": self.filename_var.get().strip(),
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.url_var.set(data.get("last_url", ""))
            self.dir_var.set(data.get("last_dir", ""))
            self.filename_var.set(data.get("last_filename", ""))
        except Exception:
            pass


def main():
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("vista")
    except Exception:
        pass

    app = AriaDownloaderApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(app))
    root.mainloop()


def on_close(app):
    app.save_config()
    if app.is_running and app.process:
        if messagebox.askyesno("Exit", "The download is still underway. Close the program?"):
            try:
                app.process.terminate()
            except Exception:
                pass
            app.root.destroy()
    else:
        app.root.destroy()


if __name__ == "__main__":
    main()