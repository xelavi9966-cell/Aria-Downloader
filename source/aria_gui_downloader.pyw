import os
import sys
import re
import json
import time
import threading
import subprocess
import tkinter as tk
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
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
            self.base_dir = os.path.dirname(sys.executable)   # папка самой программы
            self.user_dir = self.base_dir
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.user_dir = self.base_dir
 
        self.aria_path = os.path.join(self.base_dir, "aria2c.exe")
        self.config_path = os.path.join(self.user_dir, "aria_gui_config.json")
 
        self.process = None
        self.is_running = False
 
        self.manual_stop_requested = False
        self.auto_continue_job = None
        self.auto_continue_var = tk.BooleanVar(value=False)
 
        # Queue download mode
        self.queue_enabled_var = tk.BooleanVar(value=False)
        self.queue_parallel_var = tk.BooleanVar(value=False)
        self.queue_state_path = os.path.join(self.user_dir, "aria_gui_queue_state.json") if hasattr(self, "user_dir") else "aria_gui_queue_state.json"
        self.queue_items = []
        self.queue_index = 0
        self.queue_active = False
        self.queue_parallel_active = False
        self.queue_processes = []
        self.current_queue_item = None
 
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
 
        queue_frame = tk.LabelFrame(self.root, text="Queue / batch download")
        queue_frame.pack(fill="x", padx=10, pady=(0, 10))
 
        queue_options = tk.Frame(queue_frame)
        queue_options.pack(fill="x", padx=8, pady=(6, 4))
 
        self.queue_enabled_check = tk.Checkbutton(
            queue_options,
            text="Enable queue",
            variable=self.queue_enabled_var,
            command=self.save_config
        )
        self.queue_enabled_check.pack(side="left", padx=(0, 12))
 
        self.queue_parallel_check = tk.Checkbutton(
            queue_options,
            text="Download all simultaneously",
            variable=self.queue_parallel_var,
            command=self.save_config
        )
        self.queue_parallel_check.pack(side="left")
 
        tk.Label(queue_frame, text="Links, one per line. Empty lines are ignored:").pack(anchor="w", padx=8)
        self.queue_text = scrolledtext.ScrolledText(queue_frame, height=5, wrap="word", font=("Consolas", 9))
        self.queue_text.pack(fill="x", padx=8, pady=(2, 8))
        self.queue_text.bind("<FocusOut>", lambda e: self.save_config())
 
        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10, pady=(0, 10))
 
        self.start_button = tk.Button(btns, text="Start", command=self.start_download, width=14)
        self.start_button.pack(side="left", padx=5)
 
        self.continue_button = tk.Button(btns, text="Continue", command=self.continue_download, width=14, state="disabled")
        self.continue_button.pack(side="left", padx=5)
 
        self.auto_continue_check = tk.Checkbutton(
            btns,
            text="Auto-Continue",
            variable=self.auto_continue_var,
            command=self.save_config
        )
        self.auto_continue_check.pack(side="left", padx=(0, 10))
 
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
        text = str(text).rstrip()
        if not text.strip():
            return
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
        return ("civitai.com" in host) or ("civitai.red" in host)
 
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
 
    def _mask_sensitive(self, text):
        """Hide tokens/signatures before writing commands and URLs to the log."""
        if not text:
            return text
        text = re.sub(r'(?i)(token=)[^&\s"]+', r'\1***', text)
        text = re.sub(r'(?i)(api_key=)[^&\s"]+', r'\1***', text)
        text = re.sub(r'(?i)(Authorization=)[^&\s"]+', r'\1***', text)
        text = re.sub(r'(?i)(--header=Authorization:\s*Bearer\s+)[^"\s]+', r'\1***', text)
        text = re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9_\-\.]+', r'\1***', text)
        return text
 
    def _preferred_civitai_hosts(self, source_url):
        """Try the same Civitai domain first, then the other one as fallback."""
        host = urlparse(source_url).netloc.lower()
        if "civitai.red" in host:
            return ["https://civitai.red", "https://civitai.com"]
        return ["https://civitai.com", "https://civitai.red"]
 
    def _replace_civitai_host(self, url, base):
        parsed = urlparse(url)
        if "civitai.com" not in parsed.netloc.lower() and "civitai.red" not in parsed.netloc.lower():
            return url
        base_parsed = urlparse(base)
        return urlunparse((
            base_parsed.scheme,
            base_parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
 
    def get_civitai_download_info(self, url, api_key):
        version_id = self.extract_civitai_version_id(url)
        if not version_id:
            raise Exception(
                "Could not determine modelVersionId from the Civitai link.\n"
                "Use a link containing ?modelVersionId=... or a direct /api/download/models/... link."
            )
 
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 Aria2-Downloader/1.2",
            "Accept": "application/json",
        }
 
        last_error = None
        for base in self._preferred_civitai_hosts(url):
            api_url = f"{base}/api/v1/model-versions/{version_id}"
            try:
                resp = requests.get(api_url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    last_error = f"{base} API returned status {resp.status_code}"
                    continue
 
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
                download_url = self._replace_civitai_host(download_url, base)
 
                return {
                    "download_url": download_url,
                    "filename": selected_file.get("name") or "",
                    "version_id": version_id,
                    "api_base": base,
                }
            except Exception as e:
                last_error = str(e)
                continue
 
        raise Exception(f"Civitai API request failed. Last error: {last_error}")
 
    def add_civitai_token_to_url(self, url, api_key):
        """Use token in the query string for Civitai. Do not send Bearer to the final CDN."""
        parsed = urlparse(url)
        query = parse_qs(parsed.query, keep_blank_values=True)
 
        if api_key and "token" not in query:
            query["token"] = [api_key]
 
        new_query = urlencode(query, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))
 
    def resolve_civitai_final_url(self, download_url, api_key, source_url):
        """Get a fresh temporary CDN/B2 URL.
        Important: aria2 receives the final CDN URL only, without Authorization header.
        """
        last_error = None
 
        for base in self._preferred_civitai_hosts(source_url):
            candidate = self._replace_civitai_host(download_url, base)
            candidate = self.add_civitai_token_to_url(candidate, api_key)
 
            headers = {
                "User-Agent": "Mozilla/5.0 Aria2-Downloader/1.2",
                "Accept-Encoding": "identity",
            }
 
            try:
                resp = requests.get(
                    candidate,
                    headers=headers,
                    allow_redirects=False,
                    timeout=30,
                    stream=True,
                )
                resp.close()
 
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        last_error = f"{base} returned redirect without Location header"
                        continue
                    return location, base
 
                if resp.status_code == 200:
                    return candidate, base
 
                last_error = f"{base} download resolver returned status {resp.status_code}"
            except Exception as e:
                last_error = str(e)
 
        raise Exception(f"Could not resolve fresh Civitai download URL. Last error: {last_error}")
 
    def build_civitai_aria2_command(self, final_url, out_dir, filename):
        cmd = [
            self.aria_path,
            "--console-log-level=warn",
            "--summary-interval=0",
            "--show-console-readout=true",
            "--max-tries=0",
            "--retry-wait=10",
            "--connect-timeout=30",
            "--timeout=30",
            #"--lowest-speed-limit=10K",
            "--continue=true",
            "--allow-overwrite=false",
            "--auto-file-renaming=false",
            "--file-allocation=none",
            "--check-certificate=true",
            "--header=User-Agent: Mozilla/5.0 Aria2-Downloader/1.2",
            "--header=Accept-Encoding: identity",
            # Civitai/B2 is usually more stable with one connection.
            "-x", "1",
            "-s", "1",
            "-k", "1M",
            "-d", out_dir,
        ]
 
        if filename:
            cmd.extend(["-o", filename])
 
        cmd.append(final_url)
        return cmd
 
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
 
        if not os.path.exists(self.aria_path):
            messagebox.showerror("Error", f"Not found aria2c.exe:\n{self.aria_path}")
            return
 
        try:
            info = self.get_civitai_download_info(url, api_key)
 
            if not filename:
                filename = info["filename"]
                if filename:
                    self.filename_var.set(filename)
 
            final_url, resolved_base = self.resolve_civitai_final_url(info["download_url"], api_key, url)
 
            self.save_config()
 
            self.continue_button.config(state="disabled")
            self.progress_var.set(0)
            self.status_var.set("Start Civitai download...")
            self.speed_var.set("Speed: —")
            self.percent_var.set("0%")
            self.size_var.set("Size: —")
            self.eta_var.set("Remains: —")
            self.manual_stop_requested = False
 
            cmd = self.build_civitai_aria2_command(
                final_url,
                out_dir,
                filename or info["filename"],
            )
 
            self.log("=" * 100)
            self.log("Launching Civitai aria2 download mode")
            self.log(f"Civitai version ID: {info['version_id']}")
            self.log(f"Resolved via: {resolved_base}")
            self.log(f"Resolved file: {filename or info['filename']}")
            self.log("Fresh CDN/B2 URL is generated for every Start/Continue. No Bearer header is sent to CDN.")
            self.log("=" * 100)
 
            self.run_process(cmd)
 
        except Exception as e:
            messagebox.showerror("Civitai error", str(e))
            self.log(f"❌ Civitai preparation error: {self._mask_sensitive(str(e))}")
 
    def _civitai_worker(self, download_url, out_dir, filename, api_key):
        try:
            final_name = filename.strip() if filename else ""
            if not final_name:
                final_name = "civitai_download.bin"
 
            save_path = os.path.join(out_dir, final_name)
 
            existing_size = 0
            if os.path.exists(save_path):
                existing_size = os.path.getsize(save_path)
 
            headers = {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Aria2-Downloader/1.0"
            }
 
            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"
                self.root.after(0, self.log, f"Found partial file: {self._format_bytes(existing_size)}")
                self.root.after(0, self.log, "Trying to continue download...")
 
            with requests.get(download_url, headers=headers, stream=True, allow_redirects=True, timeout=60) as resp:
 
                if existing_size > 0:
                    if resp.status_code == 206:
                        mode = "ab"
                        downloaded = existing_size
                        content_length = int(resp.headers.get("Content-Length", 0))
                        total = existing_size + content_length
                    elif resp.status_code == 200:
                        mode = "wb"
                        downloaded = 0
                        total = int(resp.headers.get("Content-Length", 0))
                        self.root.after(0, self.log, "Server did not accept resume. Restarting from zero.")
                    else:
                        raise Exception(f"Download request failed with status {resp.status_code}")
                else:
                    if resp.status_code != 200:
                        raise Exception(f"Download request failed with status {resp.status_code}")
                    mode = "wb"
                    downloaded = 0
                    total = int(resp.headers.get("Content-Length", 0))
 
                if not filename:
                    cd = resp.headers.get("Content-Disposition", "")
                    m = re.search(r'filename="?([^"]+)"?', cd)
                    if m:
                        final_name = m.group(1)
                        save_path = os.path.join(out_dir, final_name)
 
                chunk_size = 1024 * 256
                start_time = time.time()
                last_ui_update = 0
                session_downloaded = 0
 
                self.root.after(0, lambda: self.status_var.set("Loading is underway..."))
                self.root.after(0, lambda: self.root.title("Aria2 Downloader — Civitai mode"))
 
                with open(save_path, mode) as f:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not self.is_running:
                            raise Exception("Download stopped by user.")
 
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            session_downloaded += len(chunk)
 
                            now = time.time()
                            elapsed = max(now - start_time, 0.001)
                            speed_bps = session_downloaded / elapsed
                            speed_text = f"{self._format_bytes(speed_bps)}/s"
 
                            if total > 0:
                                percent = int(downloaded * 100 / total)
                                size_text = f"{self._format_bytes(downloaded)} / {self._format_bytes(total)}"
 
                                remaining_bytes = max(total - downloaded, 0)
                                eta_text = self._format_eta(remaining_bytes / speed_bps) if speed_bps > 0 else "—"
                            else:
                                percent = 0
                                size_text = self._format_bytes(downloaded)
                                eta_text = "—"
 
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
            self.root.after(0, lambda: self.start_button.config(state="disabled" if self.queue_active or self.queue_parallel_active else "normal"))
            self.root.after(0, lambda: self.stop_button.config(state="normal" if self.queue_active or self.queue_parallel_active else "disabled"))
 
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
 
    def get_queue_urls(self):
        if not hasattr(self, "queue_text"):
            return []
        raw = self.queue_text.get("1.0", "end")
        urls = []
        seen = set()
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line not in seen:
                urls.append(line)
                seen.add(line)
        return urls
 
    def load_queue_state(self):
        try:
            if os.path.exists(self.queue_state_path):
                with open(self.queue_state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"Queue state load error: {e}")
        return {"items": {}, "last_completed_url": "", "last_completed_index": -1}
 
    def save_queue_state(self, state):
        try:
            with open(self.queue_state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Queue state save error: {e}")
 
    def mark_queue_item_done(self, url, index, filename=""):
        state = self.load_queue_state()
        items = state.setdefault("items", {})
        items[url] = {
            "status": "done",
            "index": index,
            "filename": filename,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        state["last_completed_url"] = url
        state["last_completed_index"] = index
        self.save_queue_state(state)
 
    def is_queue_item_done(self, url):
        state = self.load_queue_state()
        item = state.get("items", {}).get(url, {})
        return item.get("status") == "done"
 
    def build_command_for_url(self, url, resume=True):
        out_dir = self.dir_var.get().strip()
        api_key = self.civitai_api_var.get().strip()
 
        if not out_dir:
            raise Exception("Select a folder to download.")
        if not os.path.isdir(out_dir):
            raise Exception(f"The folder does not exist: {out_dir}")
 
        # Civitai URL: resolve a fresh temporary CDN/B2 URL every time.
        if self.civitai_mode_var.get() and self.is_civitai_url(url):
            if not api_key:
                raise Exception("Enter the Civitai API key for Civitai queue links.")
            info = self.get_civitai_download_info(url, api_key)
            filename = info.get("filename") or "civitai_download.bin"
            final_url, resolved_base = self.resolve_civitai_final_url(info["download_url"], api_key, url)
            cmd = self.build_civitai_aria2_command(final_url, out_dir, filename)
            return cmd, filename, f"Civitai {info['version_id']} via {resolved_base}"
 
        # Regular URL.
        filename = url.split("?")[0].rstrip("/").split("/")[-1]
        if not filename or "." not in filename or len(filename) > 200:
            filename = ""
        old_url = self.url_var.get()
        old_filename = self.filename_var.get()
        try:
            self.url_var.set(url)
            self.filename_var.set(filename)
            cmd = self.build_command(resume=resume)
        finally:
            self.url_var.set(old_url)
            self.filename_var.set(old_filename)
        if not cmd:
            raise Exception(f"Could not build command for URL: {url}")
        return cmd, filename, "Regular URL"
 
    def start_queue_download(self):
        if self.is_running or self.queue_active or self.queue_parallel_active:
            return
 
        urls = self.get_queue_urls()
        if not urls:
            messagebox.showwarning("Attention", "Queue is enabled, but the queue list is empty.")
            return
 
        if not os.path.exists(self.aria_path):
            messagebox.showerror("Error", f"Not found aria2c.exe:\n{self.aria_path}")
            return
 
        self.save_config()
        self.manual_stop_requested = False
        self.queue_items = urls
 
        if self.queue_parallel_var.get():
            self.start_parallel_queue_download(urls)
            return
 
        self.queue_active = True
        self.queue_index = 0
        self.log("=" * 100)
        self.log(f"Queue started: {len(urls)} link(s), sequential mode.")
        self.log("Already completed links from aria_gui_queue_state.json will be skipped.")
        self.log("=" * 100)
        self.start_next_queue_item()
 
    def start_next_queue_item(self):
        if self.manual_stop_requested:
            self.queue_active = False
            self.current_queue_item = None
            self.status_var.set("Queue stopped")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            return
 
        while self.queue_index < len(self.queue_items) and self.is_queue_item_done(self.queue_items[self.queue_index]):
            self.log(f"Queue: skipped already completed [{self.queue_index + 1}/{len(self.queue_items)}]")
            self.queue_index += 1
 
        if self.queue_index >= len(self.queue_items):
            self.queue_active = False
            self.current_queue_item = None
            self.log("✅ Queue completed successfully.")
            self.status_var.set("Queue complete")
            self.root.title("Aria2 Downloader — Queue done")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.continue_button.config(state="disabled")
            return
 
        url = self.queue_items[self.queue_index]
        try:
            cmd, filename, note = self.build_command_for_url(url, resume=True)
        except Exception as e:
            self.queue_active = False
            self.current_queue_item = None
            self.log(f"❌ Queue preparation error [{self.queue_index + 1}/{len(self.queue_items)}]: {self._mask_sensitive(str(e))}")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            messagebox.showerror("Queue error", str(e))
            return
 
        self.current_queue_item = {"url": url, "index": self.queue_index, "filename": filename}
        self.progress_var.set(0)
        self.percent_var.set("0%")
        self.speed_var.set("Speed: —")
        self.size_var.set("Size: —")
        self.eta_var.set("Remains: —")
        self.status_var.set(f"Queue: {self.queue_index + 1}/{len(self.queue_items)}")
        self.log("=" * 100)
        self.log(f"Queue item [{self.queue_index + 1}/{len(self.queue_items)}]: {note}")
        self.log(self._mask_sensitive(url))
        if filename:
            self.log(f"Output file: {filename}")
        self.log("=" * 100)
        self.run_process(cmd, on_finish=self.on_queue_item_finished)
 
    def on_queue_item_finished(self, success, return_code):
        item = self.current_queue_item
        if not item:
            self.queue_active = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            return
 
        if success:
            self.mark_queue_item_done(item["url"], item["index"], item.get("filename", ""))
            self.log(f"Queue: completed [{item['index'] + 1}/{len(self.queue_items)}]")
            self.queue_index = item["index"] + 1
            self.current_queue_item = None
            self.root.after(300, self.start_next_queue_item)
        else:
            self.log(f"Queue: stopped on item [{item['index'] + 1}/{len(self.queue_items)}], return code {return_code}.")
            self.log("Press Start again to retry this item. Completed previous items will be skipped.")
            self.queue_active = False
            self.current_queue_item = None
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
 
    def start_parallel_queue_download(self, urls):
        self.queue_parallel_active = True
        self.queue_processes = []
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.continue_button.config(state="disabled")
        self.status_var.set(f"Parallel queue: 0/{len(urls)} complete")
        self.root.title("Aria2 Downloader — Parallel queue")
 
        self.log("=" * 100)
        self.log(f"Queue started: {len(urls)} link(s), simultaneous mode.")
        self.log("Warning: Civitai can be unstable with many simultaneous large downloads.")
        self.log("=" * 100)
 
        thread = threading.Thread(target=self._parallel_queue_worker, args=(urls,), daemon=True)
        thread.start()
 
    def _parallel_queue_worker(self, urls):
        completed = 0
        failed = 0
        lock = threading.Lock()
        threads = []
 
        def one_job(index, url):
            nonlocal completed, failed
            if self.is_queue_item_done(url):
                with lock:
                    completed += 1
                self.root.after(0, self.log, f"Parallel queue: skipped already completed [{index + 1}/{len(urls)}]")
                self.root.after(0, lambda: self.status_var.set(f"Parallel queue: {completed}/{len(urls)} complete"))
                return
            try:
                cmd, filename, note = self.build_command_for_url(url, resume=True)
                self.root.after(0, self.log, f"Parallel queue item [{index + 1}/{len(urls)}]: {note}")
                rc = self._run_subprocess_for_parallel(cmd, index, len(urls))
                if rc == 0:
                    self.mark_queue_item_done(url, index, filename)
                    with lock:
                        completed += 1
                    self.root.after(0, self.log, f"✅ Parallel item completed [{index + 1}/{len(urls)}]")
                else:
                    with lock:
                        failed += 1
                    self.root.after(0, self.log, f"⚠ Parallel item failed [{index + 1}/{len(urls)}], code {rc}")
            except Exception as e:
                with lock:
                    failed += 1
                self.root.after(0, self.log, f"❌ Parallel item error [{index + 1}/{len(urls)}]: {self._mask_sensitive(str(e))}")
            finally:
                with lock:
                    done_count = completed
                self.root.after(0, lambda: self.status_var.set(f"Parallel queue: {done_count}/{len(urls)} complete"))
 
        for i, url in enumerate(urls):
            if self.manual_stop_requested:
                break
            t = threading.Thread(target=one_job, args=(i, url), daemon=True)
            threads.append(t)
            t.start()
 
        for t in threads:
            t.join()
 
        def finish_ui():
            self.queue_parallel_active = False
            self.is_running = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            if failed:
                self.status_var.set(f"Parallel queue finished with {failed} error(s)")
                self.root.title("Aria2 Downloader — Parallel queue errors")
            else:
                self.status_var.set("Parallel queue complete")
                self.root.title("Aria2 Downloader — Parallel queue done")
            self.log(f"Parallel queue finished. Completed: {completed}, failed: {failed}.")
        self.root.after(0, finish_ui)
 
    def _run_subprocess_for_parallel(self, cmd, index, total):
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
 
        self.root.after(0, self.log, "Launching parallel command:")
        self.root.after(0, self.log, self._mask_sensitive(" ".join(f'\"{c}\"' if " " in c else c for c in cmd)))
 
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )
        self.queue_processes.append(proc)
        for line in proc.stdout:
            clean_line = line.strip()
            if not clean_line:
                continue
            if self.parse_progress_line(clean_line):
                continue
            self.root.after(0, self.log, f"[{index + 1}/{total}] {self._mask_sensitive(clean_line)}")
        return proc.wait()
 
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
            "--console-log-level=warn",
            "--summary-interval=0",
            "--show-console-readout=true",
            "--max-tries=0",
            "--retry-wait=10",
            "--connect-timeout=30",
            "--timeout=30",
            "--lowest-speed-limit=10K",
            "--allow-overwrite=false",
            "--auto-file-renaming=false",
            "--file-allocation=none",
            "--header=Accept-Encoding: identity",
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
        if self.is_running or self.queue_active or self.queue_parallel_active:
            return
 
        if self.queue_enabled_var.get():
            self.start_queue_download()
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
        self.manual_stop_requested = False
        self.run_process(cmd)
 
    def continue_download(self):
        if self.is_running:
            return
 
        url = self.url_var.get().strip()
        if self.civitai_mode_var.get() and self.is_civitai_url(url):
            self.start_civitai_download()
            return
 
        self.auto_fill_filename_from_url()
        cmd = self.build_command(resume=True)
        if not cmd:
            return
 
        self.save_config()
 
        self.continue_button.config(state="disabled")
        self.status_var.set("Continue downloading...")
        self.manual_stop_requested = False
        self.run_process(cmd)
 
    def stop_download(self):
        if not self.is_running and not self.queue_active and not self.queue_parallel_active:
            return
        
        self.manual_stop_requested = True
 
        if self.queue_processes:
            for proc in list(self.queue_processes):
                try:
                    if proc and proc.poll() is None:
                        proc.terminate()
                except Exception:
                    pass
            self.log("⏹ Parallel queue stopped by user.")
 
        if self.process:
            try:
                self.process.terminate()
                self.log("⏹ Download stopped by user.")
            except Exception as e:
                self.log(f"Stop error: {e}")
        else:
            self.is_running = False
            self.queue_active = False
            self.queue_parallel_active = False
            self.current_queue_item = None
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.log("⏹ Download stopped by user.")
 
    def schedule_auto_continue(self, delay_ms=3000):
        if self.auto_continue_job is not None:
            try:
                self.root.after_cancel(self.auto_continue_job)
            except Exception:
                pass
            self.auto_continue_job = None
 
        if not self.auto_continue_var.get() or self.manual_stop_requested:
            return
 
        self.log(f"Auto-Continue: retry in {delay_ms // 1000} sec...")
        self.status_var.set("Connection lost. Auto-Continue is waiting...")
        self.root.title("Aria2 Downloader — Auto-Continue")
        self.auto_continue_job = self.root.after(delay_ms, self._auto_continue_action)
 
    def _auto_continue_action(self):
        self.auto_continue_job = None
 
        if self.is_running or self.manual_stop_requested or not self.auto_continue_var.get():
            return
 
        self.log("Auto-Continue: restarting download...")
        self.continue_download()
 
    def run_process(self, cmd, on_finish=None):
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.continue_button.config(state="disabled")
 
        self.log("=" * 100)
        self.log("Launching the command:")
        command_text = " ".join(f'"{c}"' if " " in c else c for c in cmd)
        self.log(self._mask_sensitive(command_text))
        self.log("=" * 100)
 
        thread = threading.Thread(target=self._worker, args=(cmd, on_finish), daemon=True)
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
 
    def _worker(self, cmd, on_finish=None):
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
                clean_line = line.strip()
 
                if not clean_line:
                    continue
 
                if self.parse_progress_line(clean_line):
                    continue
 
                self.root.after(0, self.log, self._mask_sensitive(clean_line))
 
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
 
                if self.manual_stop_requested:
                    self.root.after(0, self.log, "Download stopped manually. Auto-Continue will not start.")
                    self.root.after(0, lambda: self.status_var.set("Stopped by user"))
                    self.root.after(0, lambda: self.continue_button.config(state="normal"))
                    self.root.after(0, lambda: self.root.title("Aria2 Downloader — Stopped"))
                else:
                    self.root.after(0, self.log, "You can press Continue to dock.")
                    self.root.after(0, lambda: self.status_var.set("Loading aborted"))
                    self.root.after(0, lambda: self.continue_button.config(state="normal"))
                    self.root.after(0, lambda: self.root.title("Aria2 Downloader — Loading aborted"))
 
                    if self.auto_continue_var.get() and not self.queue_active:
                        self.root.after(0, self.schedule_auto_continue)
 
            if on_finish is not None:
                self.root.after(0, on_finish, return_code == 0, return_code)
 
        except Exception as e:
            self.root.after(0, self.log, f"❌ Startup error: {e}")
            self.root.after(0, lambda: self.status_var.set("Startup error"))
            self.root.after(0, lambda: self.continue_button.config(state="normal"))
            self.root.after(0, lambda: self.root.title("Aria2 Downloader — Error"))
 
            if not self.manual_stop_requested and not self.queue_active:
                self.root.after(0, self.schedule_auto_continue)
 
            if on_finish is not None:
                self.root.after(0, on_finish, False, -1)
 
        finally:
            self.is_running = False
            self.process = None
            self.root.after(0, lambda: self.start_button.config(state="disabled" if self.queue_active or self.queue_parallel_active else "normal"))
            self.root.after(0, lambda: self.stop_button.config(state="normal" if self.queue_active or self.queue_parallel_active else "disabled"))
 
    def save_config(self):
        try:
            data = {
                "last_url": self.url_var.get().strip(),
                "last_dir": self.dir_var.get().strip(),
                "last_filename": self.filename_var.get().strip(),
                "civitai_mode": self.civitai_mode_var.get(),
                "civitai_api_key": self.civitai_api_var.get().strip(),
                "auto_continue": self.auto_continue_var.get(),
                "queue_enabled": self.queue_enabled_var.get(),
                "queue_parallel": self.queue_parallel_var.get(),
                "queue_urls": self.queue_text.get("1.0", "end").strip() if hasattr(self, "queue_text") else "",
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
            self.auto_continue_var.set(data.get("auto_continue", False))
            self.queue_enabled_var.set(data.get("queue_enabled", False))
            self.queue_parallel_var.set(data.get("queue_parallel", False))
            if hasattr(self, "queue_text"):
                self.queue_text.delete("1.0", "end")
                self.queue_text.insert("1.0", data.get("queue_urls", ""))
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