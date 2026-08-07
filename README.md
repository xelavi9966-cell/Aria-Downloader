🚀 Aria Downloader GUI

A fast and reliable Windows GUI for downloading large files using aria2c with full resume support.

Designed for stable downloads from platforms like HuggingFace, GitHub Releases, and other direct sources — without broken browser downloads.

🔽 Download

👉 Get the latest version here:
https://github.com/xelavi9966-cell/Aria-Downloader/releases

Download .zip, extract and run:

Aria Downloader.exe

✨ Features
📥 Download via direct HTTP/HTTPS links
🔄 Resume downloads after connection loss
♻️ Auto-Continue — automatically retries the download after a dropped connection
📋 Queue / batch download — paste a list of links and download them one by one or all at once
📊 Real-time progress tracking
⚡ Speed monitoring
⏱ ETA (estimated time remaining)
📁 Custom download folder selection
📝 Custom file name support
🧠 Auto-detect file name from URL
🔒 Sensitive data (API keys/tokens) masked in the log
🪟 Clean GUI (no console window)
📦 Portable .exe — no Python required
🖥 Interface
URL input field
Folder selection
File name override
Queue / batch download panel (multi-line link list, sequential or simultaneous mode)
Start / Continue / Stop buttons
Auto-Continue toggle
Progress bar + speed + ETA
🧑‍💻 How to Use
Paste or drag a direct download link
Select destination folder
(Optional) Set custom file name
Click Start
If interrupted — click Continue, or enable Auto-Continue to retry automatically
Batch / queue downloads
Tick Enable queue
Paste links into the queue box, one per line
Choose sequential mode (one file at a time) or tick Download all simultaneously for parallel downloads
Click Start — already completed links are remembered and skipped on the next run
⚠️ Important Notes
Supported:
✔ HuggingFace (resolve/...)
✔ GitHub Releases
✔ Direct file URLs
Not supported:
❌ Google Drive
❌ Mega
🎯 Civitai Support

You can download files directly from Civitai without using a browser.

How it works:
Paste a direct download link from Civitai (or enable "Civitai download (API)" with your API key)
The app resolves a fresh, temporary CDN link and downloads it via aria2c — same resume/retry reliability as any other download
Automatically falls back between civitai.com and civitai.red if one is unavailable
Supports large model files without breaking
Recommended:
Use "Download" links from model pages
Ensure the link is a direct file URL

This makes it especially useful for:

LoRA training datasets
Checkpoints
ControlNet / SDXL assets
Keyboard issues (Windows)

If Ctrl+V doesn't work:

Switch to English layout
Or use Shift + Insert
🧠 Why not browser downloads?

Browsers often:

break large downloads
don't resume properly
lose progress

This tool uses aria2c, which provides:

multi-thread downloading
stable resume
higher speed
🛠 Build from Source
Requirements
Python 3.10+
aria2c.exe
Install
bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed \
--name "Aria Downloader" \
--icon "assets/app_icon.ico" \
--add-binary "aria2c.exe;." \
aria_gui_downloader.pyw
📁 Project Structure

Aria-Downloader/ ├─ source/ │ └─ aria_gui_downloader.pyw ├─ assets/ │ ├─ app_icon.ico │ └─ screenshots/ ├─ README.md ├─ LICENSE

📜 License

MIT License

❤️ Credits

aria2 — https://aria2.github.io Built with Python + tkinter