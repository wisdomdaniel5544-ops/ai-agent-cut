"""End-to-end user test through the HTTP API. Usage: python tests/e2e.py LABEL (--url URL | --file PATH) [--clips 3]
Logs every step with timings to tests/results/LABEL.json."""
import argparse, json, time, os, sys, urllib.request, urllib.error
B = os.environ.get("AIAC_URL", "http://127.0.0.1:8765")
def req(method, path, data=None, headers=None, raw=None):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    h = headers or ({"Content-Type": "application/json"} if data is not None else {})
    r = urllib.request.Request(B + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=600) as f: return f.status, json.loads(f.read() or b"null")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"null")
def form(fields):
    bnd = "----aac" + str(time.time()).replace(".", "")
    out = b"".join(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()) + f"--{bnd}--\r\n".encode()
    return out, {"Content-Type": f"multipart/form-data; boundary={bnd}"}
ap = argparse.ArgumentParser(); ap.add_argument("label"); ap.add_argument("--url"); ap.add_argument("--file"); ap.add_argument("--clips", default="3")
ap.add_argument("--model", default=""); a = ap.parse_args()
R = {"label": a.label, "src": a.url or a.file, "steps": [], "errors": []}; T0 = time.time()
def step(name, t0, **kw): R["steps"].append(dict(step=name, secs=round(time.time() - t0, 1), **kw)); print(name, round(time.time() - t0, 1), kw, flush=True)
fields = {"clips": a.clips}
if a.model: fields["model"] = a.model
if a.file:  # resumable chunked upload, like the UI
    t = time.time(); st, j = req("POST", "/api/uploads", {"name": os.path.basename(a.file)}); uid = j["id"]; size = os.path.getsize(a.file); CH = 8 << 20
    with open(a.file, "rb") as f:
        off = 0
        while off < size:
            st, j = req("PUT", f"/api/uploads/{uid}?offset={off}", raw=f.read(CH), headers={"Content-Type": "application/octet-stream"})
            if st != 200: R["errors"].append(f"upload chunk {st} {j}"); break
            off = j["offset"]
    step("upload", t, mb=round(size / 1e6, 1)); fields["upload_id"] = uid
else: fields["url"] = a.url
t = time.time(); body, h = form(fields); st, j = req("POST", "/api/jobs", raw=body, headers=h)
if st != 200: R["errors"].append(f"create job {st} {j}"); print(R); sys.exit(1)
jid = j["id"]; R["job"] = jid; last, lt, phase = None, time.time(), None
def phase_of(m):
    for k in ("fetching", "download", "cutting silences", "transcribing", "picking", "rendering clip", "done"):
        if m.startswith(k): return k
    return None
while True:
    st, j = req("GET", f"/api/jobs/{jid}")
    log = j.get("log") or []
    for m in log[len(R.get("_seen", [])):]:
        p = phase_of(m)
        if m.startswith("rendering clip"): p = m.split(" (")[0]
        if p and p != phase:
            if phase: step(phase, lt)
            phase, lt = p, time.time()
    R["_seen"] = log
    if j["status"] != "running": break
    time.sleep(1)
if phase and phase != "done": step(phase, lt)
R["total_job_secs"] = round(time.time() - t, 1)
if j["status"] == "error": R["errors"].append("job error: " + (log[-1] if log else "")[-500:])
R.pop("_seen", None)
clips = (j.get("report") or {}).get("clips") or []; R["clips"] = [{k: c.get(k) for k in ("score", "duration", "reframe", "title", "size_mb")} for c in clips]
if clips:
    t = time.time(); st, w = req("GET", f"/api/jobs/{jid}/clips/1/words")
    if st != 200: R["errors"].append(f"get words {st} {w}")
    else:
        words = w["words"]; words[0] = words[0].upper()
        st, e = req("POST", f"/api/jobs/{jid}/clips/1/words", {"words": words, "title": "Edited by e2e"})
        if st != 200: R["errors"].append(f"edit words {st} {str(e)[:300]}")
    step("edit captions + rerender", t)
    t = time.time(); st, e = req("POST", f"/api/jobs/{jid}/clips/1/export", {"platforms": ["tiktok", "reels", "shorts"]})
    if st != 200: R["errors"].append(f"export {st} {e}")
    else:
        while True:
            st, x = req("GET", f"/api/exports/{e['key']}")
            if x["status"] != "running": break
            time.sleep(1)
        if x["status"] != "done": R["errors"].append("export error: " + str(x.get("error"))[:300])
    step("platform export x3", t)
R["wall_secs"] = round(time.time() - T0, 1)
os.makedirs("tests/results", exist_ok=True); json.dump(R, open(f"tests/results/{a.label}.json", "w"), indent=1)
print(json.dumps({k: R[k] for k in ("total_job_secs", "wall_secs", "errors", "clips")}, indent=1))
