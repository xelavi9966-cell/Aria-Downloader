import os
import sys
import re
import json
import time
import threading
import subprocess
import tkinter as tk
from urllib.parse import urlparse, parse_qs
from tkinter import filedialog, messagebox, scrolledtext, ttk

import requests

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class AriaDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aria2 Downloader")

        try:
            icon_path = resource_path("app_icon.ico")
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print("Icon load error:", e)

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

        # civitai download
        self.civitai_mode_var = tk.BooleanVar(value=False)
        self.civitai_api_var = tk.StringVar()
        # ----------------

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

        self.civitai_mode_check = tk.Checkbutton(
            top,
            text="Civitai download (API)",
            variable=self.civitai_mode_var,
            command=self.save_config
        )
        self.civitai_mode_check.grid(row=3, column=0, sticky="w")

        self.civitai_api_entry = tk.Entry(
            top,
            textvariable=self.civitai_api_var,
            width=95,
            show="*"
        )
        self.civitai_api_entry.grid(row=3, column=1, padx=5, pady=5, sticky="we")
        self.civitai_api_entry.bind("<FocusOut>", lambda e: self.save_config())
        self.civitai_api_entry.bind("<Return>", lambda e: self.save_config())

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

        # Civitai download
    def is_civitai_url(self, url):
        if not url:
            return False
        host = urlparse(url).netloc.lower()
        return "civitai.com" in host

    def extract_civitai_version_id(self, url):
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        query = parse_qs(parsed.query)

        m = re.search(r'/api/download/models/(\d+)', parsed.path)
        if m:
            return m.group(1)

        if "modelVersionId" in query and query["modelVersionId"]:
            return query["modelVersionId"][0]

        return None

    def get_civitai_download_info(self, url, api_key):
        version_id = self.extract_civitai_version_id(url)
        if not version_id:
            raise Exception(
                "Could not determine modelVersionId from the Civitai link.\n"
                "Use a link containing ?modelVersionId=... or a direct /api/download/models/... link."
            )

        api_url = f"https://civitai.com/api/v1/model-versions/{version_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Aria2-Downloader/1.0"
        }

        resp = requests.get(api_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Civitai API returned status {resp.status_code} for model version request.")

        data = resp.json()

        files = data.get("files", [])
        if not files:
            raise Exception("No downloadable files were found in this Civitai model version.")

        selected_file = None
        for f in files:
            if f.get("downloadUrl"):
                selected_file = f
                break

        if not selected_file:
            raise Exception("Could not find downloadUrl in Civitai API response.")

        download_url = selected_file.get("downloadUrl")
        filename = selected_file.get("name") or ""

        return {
            "download_url": download_url,
            "filename": filename,
            "version_id": version_id
        }

    def start_civitai_download(self):
        if self.is_running:
            return

        url = self.url_var.get().strip()
        out_dir = self.dir_var.get().strip()
        api_key = self.civitai_api_var.get().strip()
        filename = self.filename_var.get().strip()

        if not url:
            messagebox.showwarning("Attention", "Insert a Civitai link.")
            return

        if not out_dir:
            messagebox.showwarning("Attention", "Select a folder to download.")
            return

        if not os.path.isdir(out_dir):
            messagebox.showerror("Error", f"The folder does not exist:\n{out_dir}")
            return

        if not api_key:
            messagebox.showwarning("Attention", "Enter the Civitai API key.")
            return

        try:
            info = self.get_civitai_download_info(url, api_key)

            if not filename:
                filename = info["filename"]
                if filename:
                    self.filename_var.set(filename)

            self.save_config()

            self.continue_button.config(state="disabled")
            self.progress_var.set(0)
            self.status_var.set("Start Civitai download...")
            self.speed_var.set("Speed: —")
            self.percent_var.set("0%")
            self.size_var.set("Size: —")
            self.eta_var.set("Remains: —")

            thread = threading.Thread(
                target=self._civitai_worker,
                args=(info["download_url"], out_dir, filename or info["filename"], api_key),
                daemon=True
            )
            self.is_running = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.continue_button.config(state="disabled")

            self.log("=" * 100)
            self.log("Launching Civitai Python download mode")
            self.log(f"Civitai version ID: {info['version_id']}")
            self.log(f"Resolved file: {filename or info['filename']}")
            self.log("=" * 100)

            thread.start()

        except Exception as e:
            messagebox.showerror("Civitai error", str(e))
            self.log(f"❌ Civitai preparation error: {e}")

    def _civitai_worker(self, download_url, out_dir, filename, api_key):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Aria2-Downloader/1.0"
            }

            with requests.get(download_url, headers=headers, stream=True, allow_redirects=True, timeout=60) as resp:
                if resp.status_code != 200:
                    raise Exception(f"Download request failed with status {resp.status_code}")

                total = int(resp.headers.get("Content-Length", 0))
                final_name = filename.strip() if filename else ""

                if not final_name:
                    cd = resp.headers.get("Content-Disposition", "")
                    m = re.search(r'filename="?([^"]+)"?', cd)
                    if m:
                        final_name = m.group(1)
                    else:
                        final_name = "civitai_download.bin"

                save_path = os.path.join(out_dir, final_name)

                downloaded = 0
                chunk_size = 1024 * 256
                start_time = time.time()
                last_ui_update = 0

                self.root.after(0, lambda: self.status_var.set("Loading is underway..."))
                self.root.after(0, lambda: self.root.title("Aria2 Downloader — Civitai mode"))

                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not self.is_running:
                            raise Exception("Download stopped by user.")

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            now = time.time()
                            elapsed = max(now - start_time, 0.001)
                            speed_bps = downloaded / elapsed
                            speed_text = f"{self._format_bytes(speed_bps)}/s"

                            if total > 0:
                                percent = int(downloaded * 100 / total)
                                size_text = f"{self._format_bytes(downloaded)} / {self._format_bytes(total)}"

                                remaining_bytes = max(total - downloaded, 0)
                                if speed_bps > 0:
                                    eta_seconds = remaining_bytes / speed_bps
                                    eta_text = self._format_eta(eta_seconds)
                                else:
                                    eta_text = "—"
                            else:
                                percent = 0
                                size_text = self._format_bytes(downloaded)
                                eta_text = "—"

                            # Чтобы UI не обновлялся слишком часто
                            if now - last_ui_update >= 0.2 or (total > 0 and downloaded >= total):
                                last_ui_update = now
                                self.root.after(
                                    0,
                                    self.update_progress_ui,
                                    percent,
                                    size_text,
                                    speed_text,
                                    eta_text
                                )

                self.root.after(0, self.log, f"✅ Download completed successfully: {final_name}")
                self.root.after(0, lambda: self.status_var.set("The download is complete"))
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self.percent_var.set("100%"))
                self.root.after(0, lambda: self.eta_var.set("Remains: 0 sec"))
                self.root.after(0, lambda: self.continue_button.config(state="disabled"))
                self.root.after(0, lambda: self.root.title("Aria2 Downloader — Done"))

        except Exception as e:
            self.root.after(0, self.log, f"❌ Civitai download error: {e}")
            self.root.after(0, lambda: self.status_var.set("Loading aborted"))
            self.root.after(0, lambda: self.continue_button.config(state="disabled"))
            self.root.after(0, lambda: self.root.title("Aria2 Downloader — Error"))

        finally:
            self.is_running = False
            self.process = None
            self.root.after(0, lambda: self.start_button.config(state="normal"))
            self.root.after(0, lambda: self.stop_button.config(state="disabled"))

    def _format_bytes(self, num):
        step_unit = 1024.0
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num < step_unit:
                if unit == "B":
                    return f"{int(num)}{unit}"
                return f"{num:.2f}{unit}"
            num /= step_unit
        return f"{num:.2f}PB"
    
    def _format_eta(self, seconds):
        seconds = int(max(0, seconds))

        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        if h > 0:
            return f"{h}h {m}m {s}s"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"
        #-----------------

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

        url = self.url_var.get().strip()

        if self.civitai_mode_var.get() and self.is_civitai_url(url):
            self.start_civitai_download()
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
        if not self.is_running:
            return

        if self.process:
            try:
                self.process.terminate()
                self.log("⏹ Download stopped by user.")
            except Exception as e:
                self.log(f"Stop error: {e}")
        else:
            self.is_running = False
            self.log("⏹ Download stopped by user.")

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
        try:
            data = {
                "last_url": self.url_var.get().strip(),
                "last_dir": self.dir_var.get().strip(),
                "last_filename": self.filename_var.get().strip(),
                "civitai_mode": self.civitai_mode_var.get(),
                "civitai_api_key": self.civitai_api_var.get().strip(),
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Config save error: {e}")

    def load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.url_var.set(data.get("last_url", ""))
            self.dir_var.set(data.get("last_dir", ""))
            self.filename_var.set(data.get("last_filename", ""))
            self.civitai_mode_var.set(data.get("civitai_mode", False))
            self.civitai_api_var.set(data.get("civitai_api_key", ""))
        except Exception as e:
            self.log(f"Config load error: {e}")


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