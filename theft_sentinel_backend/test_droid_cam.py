"""
Quick diagnostic: probe DroidCam at the new IP with various User-Agent and path combos.
"""
import requests, sys

BASE = "http://10.135.228.62:4747"
PATHS = ["/video", "/mjpegfeed", "/", "/cam"]
USER_AGENTS = [
    ("DroidCam/1.0",        "DroidCam/1.0"),
    ("None (no UA header)", None),
    ("curl/7.0",            "curl/7.0"),
    ("Mozilla/5.0",         "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
]

print(f"Probing {BASE}")
print("="*60)
for path in PATHS:
    url = BASE + path
    for ua_label, ua_value in USER_AGENTS:
        headers = {"Connection": "keep-alive"}
        if ua_value:
            headers["User-Agent"] = ua_value
        try:
            r = requests.get(url, stream=True, timeout=4, headers=headers)
            ct = r.headers.get("Content-Type", "?")
            ok = "MJPEG OK" if "multipart" in ct or "image" in ct else "HTML/other"
            print(f"  [{ok}] [{r.status_code}] {path}  UA={ua_label}  ct={ct}")
            r.close()
        except Exception as e:
            print(f"  [ERROR]   {path}  UA={ua_label}  -> {e}")
