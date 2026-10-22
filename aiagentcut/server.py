"""Local web UI: FastAPI + plain HTML. Run: python -m aiagentcut.server  (http://127.0.0.1:8765)"""
import threading, uuid, shutil, json, subprocess, re
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Body, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from . import engine
from .engine import process, PRESETS, ASPECTS, GENRES, PLATFORMS

import os
ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("AIAC_DATA") or ROOT)  # writable data dir (installer: %LOCALAPPDATA%)
JOBS_DIR = DATA / "jobs"; JOBS_DIR.mkdir(exist_ok=True)
UP_DIR = DATA / "uploads"; UP_DIR.mkdir(exist_ok=True)
TPL_DIR = DATA / "templates"; (TPL_DIR / "assets").mkdir(parents=True, exist_ok=True)
BRAND = TPL_DIR / "brand.json"
app = FastAPI(title="AI AGENT CUT")
app.mount("/static", StaticFiles(directory=ROOT / "web" / "static"), name="static")
JOBS = {}

@app.get("/manifest.webmanifest")
def manifest(): return FileResponse(ROOT / "web" / "manifest.webmanifest", media_type="application/manifest+json")
@app.get("/sw.js")
def sw(): return FileResponse(ROOT / "web" / "sw.js", media_type="text/javascript")
@app.get("/", response_class=HTMLResponse)
def index(): return (ROOT / "web" / "index.html").read_text()

@app.get("/classic", response_class=HTMLResponse)
def classic(): return (ROOT / "web" / "classic.html").read_text()

@app.get("/api/projects")
def projects():
    out = []
    for d in sorted(JOBS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir(): continue
        j = _load(d.name)
        if not j: continue
        clips = (j.get("report") or {}).get("clips") or []
        out.append({"id": d.name, "status": j.get("status"), "clips": len(clips), "mtime": d.stat().st_mtime,
                    "thumb": ("/files/%s/%s" % (d.name, clips[0]["file"].split("/")[-1])) if clips else None,
                    "title": (clips[0].get("title") if clips else "") or d.name})
    return out[:50]

# Local sign-in stub: no real OAuth configured. Stores a display name/email only; no password, no verification.
@app.post("/api/auth/local")
def auth_local(email: str = Body("", embed=True), provider: str = Body("email", embed=True)):
    return {"user": {"email": email or "guest@local", "provider": provider, "plan": "free", "credits": 60, "stub": True}}

# ---- lead capture ("Get free clipping tips"): appended to DATA/leads/leads.csv + leads.json. No email is sent yet.
LEADS_DIR = DATA / "leads"; LEADS_DIR.mkdir(exist_ok=True)
_lead_lock = threading.Lock()

@app.post("/api/leads")
def add_lead(email: str = Body(..., embed=True), source: str = Body("app", embed=True), name: str = Body("", embed=True)):
    import csv, time
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(email) > 254:
        return JSONResponse({"error": "Enter a valid email"}, 400)
    row = {"email": email, "name": name.strip()[:80], "source": re.sub(r"[^\w-]", "", source)[:32],
           "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    with _lead_lock:
        jf = LEADS_DIR / "leads.json"; leads = json.loads(jf.read_text()) if jf.exists() else []
        if any(l["email"] == email for l in leads): return {"ok": True, "duplicate": True}
        leads.append(row); jf.write_text(json.dumps(leads, indent=1))
        cf = LEADS_DIR / "leads.csv"; new = not cf.exists()
        with open(cf, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row)); new and w.writeheader(); w.writerow(row)
    return {"ok": True}

# ---- Connect AI: user's own keys. Only Gemini is wired (engine reads GEMINI_API_KEY + AIAC_LLM=gemini).
# Stored on THIS machine only in DATA/ai_keys.json (chmod 600); accepted from localhost only. Never returned in full.
AI_KEYS = DATA / "ai_keys.json"
def _apply_keys():
    k = json.loads(AI_KEYS.read_text()) if AI_KEYS.exists() else {}
    if k.get("gemini"): os.environ["GEMINI_API_KEY"] = k["gemini"]; os.environ.setdefault("AIAC_LLM", "gemini")
    return k
_apply_keys()

@app.get("/api/ai-keys")
def ai_keys_status():
    k = json.loads(AI_KEYS.read_text()) if AI_KEYS.exists() else {}
    return {name: ("…" + v[-4:]) if v else "" for name, v in k.items()} | {"wired": ["gemini"]}

@app.post("/api/ai-keys")
def ai_keys_save(request: Request, provider: str = Body(..., embed=True), key: str = Body("", embed=True)):
    if request.client and request.client.host not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse({"error": "keys can only be set from this computer"}, 403)
    if provider != "gemini": return JSONResponse({"error": "not wired yet"}, 400)
    k = json.loads(AI_KEYS.read_text()) if AI_KEYS.exists() else {}
    k[provider] = key.strip()
    if not k[provider]: k.pop(provider); os.environ.pop("GEMINI_API_KEY", None)
    AI_KEYS.write_text(json.dumps(k)); os.chmod(AI_KEYS, 0o600); _apply_keys()
    return {"ok": True}

@app.get("/api/presets")
def presets():
    return {"presets": list(PRESETS), "aspects": list(ASPECTS), "genres": list(GENRES),
            "platforms": {k: {kk: v[kk] for kk in ("label", "icon", "aspect", "max_dur", "fps", "native", "safe")} for k, v in PLATFORMS.items()}}

# ---- resumable chunked upload (hours-long files): POST init -> PUT chunks at offset -> GET size to resume ----
@app.post("/api/uploads")
def up_init(name: str = Body(..., embed=True)):
    uid = uuid.uuid4().hex[:12]; (UP_DIR / uid).mkdir()
    (UP_DIR / uid / "name").write_text(re.sub(r"[^\w.\- ]", "_", Path(name).name)[:120]); (UP_DIR / uid / "data").touch()
    return {"id": uid, "offset": 0}

@app.get("/api/uploads/{uid}")
def up_status(uid: str):
    d = UP_DIR / Path(uid).name
    return {"id": uid, "offset": (d / "data").stat().st_size} if d.exists() else JSONResponse({"error": "unknown upload"}, 404)

@app.put("/api/uploads/{uid}")
async def up_chunk(uid: str, request: Request, offset: int = 0):
    d = UP_DIR / Path(uid).name; f = d / "data"
    if not d.exists(): return JSONResponse({"error": "unknown upload"}, 404)
    size = f.stat().st_size
    if offset != size: return JSONResponse({"error": "offset mismatch", "offset": size}, 409)
    with open(f, "ab") as fh:
        async for chunk in request.stream(): fh.write(chunk)
    return {"offset": f.stat().st_size}

def _upload_path(uid):
    d = UP_DIR / Path(uid).name; p = d / ("file_" + (d / "name").read_text())
    if not p.exists(): (d / "data").rename(p)
    return p

@app.get("/api/probe")
def probe(url: str = "", upload: str = ""):
    """Duration for the pre-trim slider."""
    try:
        if upload: return {"duration": engine.duration(_upload_path(upload))}
        r = subprocess.run(engine.YTDLP() + ["--no-playlist", "--print", "duration", "--print", "title", engine.normalize_url(url)], capture_output=True, text=True, timeout=60)
        lines = r.stdout.strip().splitlines()
        return {"duration": float(lines[0]), "title": lines[1] if len(lines) > 1 else ""}
    except Exception: return {"duration": None}

# ---- brand template ----
@app.get("/api/template")
def get_tpl(): return json.loads(BRAND.read_text()) if BRAND.exists() else {}

@app.post("/api/template")
async def save_tpl(request: Request):
    form = await request.form(); t = json.loads(BRAND.read_text()) if BRAND.exists() else {}
    for k, v in form.items():
        if hasattr(v, "filename"):
            if v.filename:
                p = TPL_DIR / "assets" / (k + Path(v.filename).suffix.lower()); p.write_bytes(await v.read()); t[k] = str(p)
        elif k in ("vocab_text", "censor_text"):
            if k == "vocab_text": t["vocab"] = dict(l.split("=", 1) for l in v.splitlines() if "=" in l)
            else: t["censor"] = [w.strip() for w in re.split(r"[,\n]", v) if w.strip()]
        elif k in ("size", "stroke", "shadow", "words"): t[k] = int(float(v))
        elif k in ("caption_y", "logo_scale", "music_volume"): t[k] = float(v)
        elif k in ("uppercase", "box"): t[k] = v in ("true", "1", "on")
        elif k.startswith("clear_"): t.pop(k[6:], None)
        else: t[k] = v
    BRAND.write_text(json.dumps(t, indent=1)); return t

def _run(jid, src, n, preset, model, opts):
    j = JOBS[jid]
    def log(m):
        j["log"].append(m)
        # coarse but monotonic progress: fetch 2-10, silences 12, transcribe 15-55, pick 58, render 60-98
        mm = re.match(r"transcribing (\d+)%", m); mr = re.match(r"rendering clip (\d+)/(\d+)", m)
        if mm: p = 15 + int(mm.group(1)) * 0.4
        elif mr: p = 60 + 38 * int(mr.group(1)) / max(1, int(mr.group(2)))
        else: p = {"fetching": 3, "download": 6, "converting": 9, "cutting": 12, "reusing": 14, "picking": 58, "done": 100}.get(m.split(" ")[0], None)
        if p is not None: j["progress"] = max(j.get("progress", 0), round(p, 1))
    try:
        j["report"] = process(src, JOBS_DIR / jid, n, preset, model, log=log, **opts); j["status"] = "done"
    except Exception as e:
        j["status"] = "error"; j["log"].append(str(e)[-600:]); j["error"] = friendly_error(e)

def friendly_error(e):
    """Plain-language error + what to do next (raw details stay in the log)."""
    t = str(e).lower()
    if isinstance(e, engine.FetchError): return str(e)[:300]
    if "download" in t or "yt-dlp" in t:
        return "Couldn't download this link. If it's private, age-restricted or region-locked, download it and upload the file instead."
    if "no space" in t: return "The disk is full. Free some space and try again."
    if "cannot allocate memory" in t or isinstance(e, MemoryError): return "Not enough memory for this video. Try a shorter part (trim) or close other apps."
    if "invalid data" in t or "moov atom" in t or "could not open" in t: return "This file looks damaged or isn't a supported video. Try exporting it again as MP4."
    if "failed to render" in t: return "A clip failed to render. Try again; if it keeps failing, pick another style or aspect."
    return "Something went wrong while making clips. Try again; details are in the log."

@app.post("/api/jobs")
async def create(url: str = Form(""), upload_id: str = Form(""), clips: int = Form(3), preset: str = Form("bold_yellow"),
                 model: str = Form("small"), aspect: str = Form("9:16"), fit: str = Form("auto"),
                 hook: str | None = Form(None), keywords: str | None = Form(None), emoji: str | None = Form(None),
                 fillers: str | None = Form(None), pauses: str | None = Form(None), silence: str | None = Form(None),
                 trim_start: float = Form(0), trim_end: float = Form(0), prompt: str = Form(""), genre: str = Form("auto"),
                 min_len: float = Form(30), max_len: float = Form(60), language: str = Form(""),
                 brand: str | None = Form(None), broll: str = Form(""), censor_mode: str = Form("bleep"),
                 file: UploadFile | None = File(None), srt: UploadFile | None = File(None), broll_file: UploadFile | None = File(None)):
    # FastAPI >=0.150 turns a *missing* bool Form field into False, silently disabling defaults; parse explicitly.
    _b = lambda v, d: d if v in (None, "") else str(v).strip().lower() in ("1", "true", "on", "yes")
    hook = _b(hook, True); keywords = _b(keywords, True); emoji = _b(emoji, False); fillers = _b(fillers, True); pauses = _b(pauses, False); silence = _b(silence, True); brand = _b(brand, True)
    jid = uuid.uuid4().hex[:8]; d = JOBS_DIR / jid; d.mkdir()
    if upload_id: src = str(_upload_path(upload_id))
    elif file and file.filename:
        src = d / ("upload_" + Path(file.filename).name)
        with open(src, "wb") as f: shutil.copyfileobj(file.file, f)
        src = str(src)
    elif url: src = url.strip()
    else: return JSONResponse({"error": "Add a video or paste a link"}, 400)
    if aspect not in ASPECTS: return JSONResponse({"error": "bad aspect"}, 400)
    srt_path = bf = None
    if srt and srt.filename: srt_path = d / "captions.srt"; srt_path.write_bytes(await srt.read())
    if broll_file and broll_file.filename: bf = d / ("broll" + Path(broll_file.filename).suffix); bf.write_bytes(await broll_file.read())
    tpl = json.loads(BRAND.read_text()) if brand and BRAND.exists() else None
    opts = dict(aspect=aspect, fit=fit, hook=hook, keywords=keywords, emoji=emoji, remove_fillers=fillers, remove_pauses=pauses,
                silence=silence, trim=(trim_start or None, trim_end or None) if (trim_start or trim_end) else None,
                prompt=prompt.strip() or None, genre=genre, min_len=min_len, max_len=max_len, language=language or None,
                srt=srt_path, template=tpl, broll=broll or None, broll_file=str(bf) if bf else None, censor_mode=censor_mode)
    JOBS[jid] = {"status": "running", "log": [], "report": None, "progress": 2}
    threading.Thread(target=_run, args=(jid, src, clips, preset, model, opts), daemon=True).start()
    return {"id": jid}

def _load(jid):
    if jid in JOBS: return JOBS[jid]
    rp = JOBS_DIR / Path(jid).name / "report.json"
    return {"status": "done", "log": [], "report": json.loads(rp.read_text())} if rp.exists() else None

def _refresh(jid):
    rp = JOBS_DIR / Path(jid).name / "report.json"
    if jid in JOBS: JOBS[jid]["report"] = json.loads(rp.read_text())

@app.get("/api/jobs/{jid}")
def status(jid: str): return _load(jid) or JSONResponse({"error": "unknown"}, 404)

@app.get("/api/jobs/{jid}/transcript")
def transcript(jid: str): return engine.transcript_sentences(JOBS_DIR / Path(jid).name)

@app.get("/api/jobs/{jid}/clips/{idx}/words")
def get_words(jid: str, idx: int):
    rep = (_load(jid) or {}).get("report")
    if not rep or not (1 <= idx <= len(rep["clips"])): return JSONResponse({"error": "unknown clip"}, 404)
    c = rep["clips"][idx-1]
    wj = JOBS_DIR / Path(jid).name / "work" / (Path(c["file"]).stem + ".words.json")
    return {"title": c.get("title", ""), "words": [w["word"] for w in json.loads(wj.read_text())]}

@app.post("/api/jobs/{jid}/clips/{idx}/words")
def edit_words(jid: str, idx: int, body: dict = Body(...)):
    try: c = engine.rerender_with_text(JOBS_DIR / Path(jid).name, idx, body["words"], body.get("title"))
    except Exception as e: return JSONResponse({"error": str(e)[-400:]}, 400)
    _refresh(jid); return c

@app.post("/api/jobs/{jid}/clips/{idx}/sections")
def edit_sections(jid: str, idx: int, body: dict = Body(...)):
    """{"remove": [[s,e],...], "add": [[s,e],...], "at": "end"|"start"} — transcript-based editing."""
    try: c = engine.edit_sections(JOBS_DIR / Path(jid).name, idx, body.get("remove", []), body.get("add", []), body.get("at", "end"))
    except Exception as e: return JSONResponse({"error": str(e)[-400:]}, 400)
    _refresh(jid); return c

@app.get("/api/jobs/{jid}/clips/{idx}/xml")
def xml(jid: str, idx: int, kind: str = "fcpxml"):
    p = engine.export_xml(JOBS_DIR / Path(jid).name, idx, "fcpxml" if kind == "fcpxml" else "xmeml")
    return FileResponse(p, filename=p.name)

EXPORTS = {}
@app.post("/api/jobs/{jid}/clips/{idx}/export")
def export(jid: str, idx: int, body: dict = Body(...)):
    plats = [p for p in body.get("platforms", []) if p in PLATFORMS]
    if not plats: return JSONResponse({"error": "pick at least one platform"}, 400)
    key = f"{jid}-{idx}"; EXPORTS[key] = {"status": "running", "log": []}
    def work():
        try:
            z = engine.export_platforms(JOBS_DIR / Path(jid).name, idx, plats, log=lambda m: EXPORTS[key]["log"].append(m))
            EXPORTS[key].update(status="done", file=z.name)
        except Exception as e: EXPORTS[key].update(status="error", error=str(e)[-300:])
    threading.Thread(target=work, daemon=True).start(); return {"key": key}

@app.get("/api/exports/{key}")
def export_status(key: str): return EXPORTS.get(key) or JSONResponse({"error": "unknown"}, 404)

@app.get("/files/{jid}/{name}")
def files(jid: str, name: str):
    p = (JOBS_DIR / Path(jid).name / Path(name).name)
    return FileResponse(p) if p.exists() else JSONResponse({"error": "missing"}, 404)

@app.get("/tplfiles/{name}")
def tplfiles(name: str):
    p = TPL_DIR / "assets" / Path(name).name
    return FileResponse(p) if p.exists() else JSONResponse({"error": "missing"}, 404)

LAN = {}
@app.post("/api/lan")
def lan(request: Request):
    """'📱 Phone' button: also serve this app on the local Wi-Fi (port+1) so the Android app can connect. Local requests only."""
    if request.client.host not in ("127.0.0.1", "::1"): return JSONResponse({"error": "local only"}, 403)
    import socket, uvicorn
    port = int(os.environ.get("AIAC_PORT", "8765")) + 1
    if not LAN:
        cfg = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
        threading.Thread(target=uvicorn.Server(cfg).run, daemon=True).start(); LAN["on"] = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("10.255.255.255", 1)); ip = s.getsockname()[0]; s.close()
    except Exception: ip = "127.0.0.1"
    return {"url": f"http://{ip}:{port}"}

def main():
    """AIAC_HOST=0.0.0.0 lets phones on the same Wi-Fi use this PC (Android app 'Connect')."""
    import uvicorn; uvicorn.run(app, host=os.environ.get("AIAC_HOST", "127.0.0.1"), port=int(os.environ.get("AIAC_PORT", "8765")))
if __name__ == "__main__": main()
