# 🚀 Aria Downloader GUI

A simple and reliable Windows GUI for downloading large files using **aria2c** with resume support.

Designed especially for downloading models and assets from platforms like **HuggingFace**, **GitHub Releases**, and other direct links — without dealing with broken browser downloads.

---

## ✨ Features

* ✅ Download via direct HTTP/HTTPS links
* 🔄 Resume downloads after connection loss
* 📊 Real-time progress display
* ⚡ Download speed indicator
* ⏱ ETA (estimated time remaining)
* 📁 Custom download folder selection
* 📝 Custom file name support
* 🖱 Drag & Drop URL support *(optional / if implemented)*
* 🧠 Auto-detect file name from URL
* 🪟 Clean GUI (no console window)
* 📦 Portable `.exe` version — no Python required

---

## 📥 Download

👉 Go to the **Releases** section:
https://github.com/xelavi9966-cell/Aria-Downloader/releases

Download the latest `.zip` archive:

* Extract it
* Run `Aria Downloader.exe`

---

## 🧑‍💻 How to Use

1. Paste or drag a direct download link
2. Select a destination folder
3. (Optional) Set a custom file name
4. Click **Start**
5. If download fails — click **Continue**

---

## ⚠️ Important Notes

* Use **direct links only**

  * ✔ Works: HuggingFace (`resolve/...`), GitHub Releases
  * ❌ Doesn't work: Google Drive, Mega, Yandex Disk

* If `Ctrl+V` doesn't work:

  * Switch to **English keyboard layout**
  * Or use **Shift+Insert**

---

## 🛠️ Build from Source

### Requirements

* Python 3.10+
* `aria2c.exe`

---

### Install dependencies

```bash
pip install pyinstaller
```

---

### Build executable

```bash
pyinstaller --noconfirm --onefile --windowed --name "Aria Downloader" --icon "app_icon.ico" --add-binary "aria2c.exe;." aria_gui_downloader.pyw
```

Output will be in:

```
dist/Aria Downloader.exe
```

---

## 📁 Project Structure

```
Aria-Downloader/
├─ source/
│  └─ aria_gui_downloader.pyw
├─ assets/
│  ├─ app_icon.ico
│  └─ screenshots/
├─ README.md
├─ LICENSE
```

---

## 🧠 How It Works

This application is a graphical interface for:

👉 **aria2c**

It provides:

* stable multi-part downloads
* automatic resume
* better performance than browsers

---

## 📌 Future Improvements

* ⏳ Download queue
* 🌐 Cookie support for restricted downloads
* 🧲 Torrent / magnet support
* 📄 Batch download from `.txt`
* 🎨 UI improvements

---

## 📜 License

This project is licensed under the MIT License.

---

## ❤️ Credits

* aria2 — https://aria2.github.io
* Built with Python + tkinter

---

## 👤 Author

Created by **Xelavi**

---

If you find this project useful — ⭐ star the repo!
