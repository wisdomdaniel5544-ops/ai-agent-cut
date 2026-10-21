"""AI AGENT CUT desktop launcher (Windows). Starts the local server and opens it in its own app window
(Microsoft Edge/Chrome --app mode; falls back to the default browser). Closing the window quits."""
import os, sys, time, threading, socket, subprocess, webbrowser, shutil
from pathlib import Path
BASE = Path(sys.executable).resolve().parent.parent          # install dir: python\pythonw.exe -> ..
os.environ["PATH"] = str(BASE / "ffmpeg") + os.pathsep + os.environ.get("PATH", "")
os.environ.setdefault("AIAC_MODEL_DIR", str(BASE / "models"))
data = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AIAgentCut"; data.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("AIAC_DATA", str(data))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, str(BASE / "app"))
log = open(data / "app.log", "a", buffering=1); sys.stdout = sys.stderr = log

def free_port(p=8765):
    for port in range(p, p + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0: return port
    return p

PORT = free_port(); os.environ["AIAC_PORT"] = str(PORT)
from aiagentcut import server
threading.Thread(target=server.main, daemon=True).start()
url = f"http://127.0.0.1:{PORT}/"
for _ in range(100):
    try:
        socket.create_connection(("127.0.0.1", PORT), 0.2).close(); break
    except OSError: time.sleep(0.2)

def find_browser():
    pf = [os.environ.get(k, "") for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
    for root in pf:
        for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
            p = Path(root) / rel
            if root and p.exists(): return str(p)
    return shutil.which("msedge") or shutil.which("chrome")

b = find_browser()
if b:
    prof = data / "window-profile"
    proc = subprocess.Popen([b, f"--app={url}", f"--user-data-dir={prof}", "--window-size=480,920", "--no-first-run"])
    proc.wait()
    # Edge may hand off to an existing process; keep serving while the app window profile is in use
    lock = prof / "lockfile"
    while lock.exists():
        try: lock.unlink(); break      # unlink succeeds only once the window is closed
        except OSError: time.sleep(2)
else:
    webbrowser.open(url)
    while True: time.sleep(3600)
