Changelog

All notable changes to this project are documented here.

[1.2.0] — 2026-08-07
Added
Queue / batch download: paste multiple links (one per line) and download them either sequentially or all at once ("Download all simultaneously"). Completed items are tracked in aria_gui_queue_state.json and automatically skipped on the next run.
Auto-Continue: an optional toggle that automatically restarts a download a few seconds after a connection drop, instead of requiring a manual click on "Continue". Auto-Continue never triggers after a manual Stop.
Civitai civitai.red fallback: the app now tries civitai.com first and automatically falls back to civitai.red (and vice versa) for both the model-version API lookup and the final CDN download link.
Sensitive values (API keys, Authorization: Bearer headers, token=/api_key= query parameters) are now masked before being written to the on-screen log.
Changed
Civitai downloads now go through aria2c instead of a separate Python requests-based downloader. This gives Civitai downloads the same resume, retry, and stability behavior as regular downloads, and lets them participate in the queue system.
Every Civitai download/continue now resolves a fresh temporary CDN/B2 URL first, since Civitai's signed links expire; the Authorization: Bearer token is only ever sent to Civitai's own API, never to the CDN (the CDN gets a short-lived token= query parameter instead).
Portable (.exe) builds now store their config and queue-state files next to the executable itself, instead of inside the temporary PyInstaller extraction folder — settings and queue progress now persist correctly between runs.
The live aria2 progress line is parsed for the progress bar but no longer duplicated into the text log, keeping the log readable.
Stop now distinguishes a manual stop from a connection drop, and also terminates any in-flight parallel-queue downloads.
Fixed
Empty/blank lines are no longer written to the log.
civitai.com detection now also matches civitai.red links when checking whether a URL should use Civitai mode.
[1.1.0] — previous release
Added Civitai support (Python-based downloader)
UI improvements, DPI/scaling fixes, auto-fit preview
[1.0.0] — initial release
Direct HTTP/HTTPS downloads via aria2c with resume support
Progress tracking, speed, ETA
Custom folder/filename selection