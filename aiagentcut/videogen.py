"""Video models: free open-source models run through public Hugging Face Spaces (gradio_client), plus bring-your-own-key slots."""
import os, shutil, threading, uuid
from pathlib import Path

MODELS = [
    # id, label, kind, space, license, status
    {"id": "wan22_i2v", "label": "Wan 2.2 Image to Video", "kind": "image", "space": "zerogpu-aoti/wan2-2-fp8da-aoti-faster", "license": "Apache-2.0", "commercial": True},
    {"id": "cogvideox5b", "label": "CogVideoX-5B Text to Video", "kind": "text", "space": "THUDM/CogVideoX-5B-Space", "license": "CogVideoX License (commercial use with registration)", "commercial": True},
    {"id": "ltx", "label": "LTX-Video Text/Image to Video", "kind": "text", "space": "Lightricks/ltx-video-distilled", "license": "LTXV Open Weights (free under $10M revenue)", "commercial": True},
    {"id": "hunyuan", "label": "HunyuanVideo", "kind": "text", "space": None, "license": "Tencent Hunyuan Community (excludes EU/UK/KR)", "commercial": False},
    {"id": "byok", "label": "Your own paid video key", "kind": "text", "space": None, "license": "your provider's terms", "commercial": True},
]
WORKING = {m.strip() for m in os.environ.get("AIAC_VIDEO_WORKING", "wan22_i2v").split(",") if m.strip()}
JOBS = {}

def list_models():
    return [dict(m, status="live" if m["id"] in WORKING and m["space"] else "coming_soon") for m in MODELS]

def _find_video(r):
    if isinstance(r, (list, tuple)):
        for x in r:
            v = _find_video(x)
            if v: return v
    if isinstance(r, dict): return _find_video(r.get("video") or r.get("path"))
    if isinstance(r, str) and r.lower().endswith((".mp4", ".webm", ".mov")) and os.path.exists(r): return r
    return None

def _run(jid, m, prompt, image, outdir):
    from gradio_client import Client, handle_file
    j = JOBS[jid]
    try:
        c = Client(m["space"], token=os.environ.get("HF_TOKEN") or None, verbose=False)
        j["status"] = "generating"
        if m["id"] == "wan22_i2v":
            if not image: raise RuntimeError("This model needs a starting image.")
            r = c.predict(handle_file(image), prompt or "cinematic motion", api_name="/generate_video")
        elif m["id"] == "cogvideox5b":
            r = c.predict(prompt, handle_file(image) if image else None, None, api_name="/generate")
        else:
            r = c.predict(prompt, api_name="/text_to_video")
        v = _find_video(r)
        if not v: raise RuntimeError("The model returned no video.")
        out = Path(outdir) / f"{jid}.mp4"; shutil.copy(v, out)
        j.update(status="done", file=f"/genfiles/{out.name}")
    except Exception as e:
        msg = str(e)
        if not msg.strip() or "quota" in msg.lower() or "gpu" in msg.lower() or "Cancelled" in type(e).__name__: msg = "The free GPU queue is busy or today's free quota is used up. Try again later."
        j.update(status="error", error=msg[:300])

def start(model_id, prompt, image, outdir):
    m = next((x for x in MODELS if x["id"] == model_id), None)
    if not m or m["id"] not in WORKING or not m["space"]: raise ValueError("This model is coming soon.")
    jid = uuid.uuid4().hex[:8]; JOBS[jid] = {"status": "queued", "model": model_id}
    threading.Thread(target=_run, args=(jid, m, prompt, image, outdir), daemon=True).start()
    return jid
