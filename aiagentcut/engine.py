"""AI Agent Cut - core clipping engine (v2).
Pipeline: fetch -> silence cut -> transcribe -> pick clips -> 9:16 reframe -> burned captions -> MP4 720x1280.
Built on ffmpeg, faster-whisper (MIT), OpenCV, yt-dlp. No third-party app code."""
import json, os, re, subprocess, shutil, math
from pathlib import Path
import numpy as np

W, H = 720, 1280  # default 9:16
import sys
def YTDLP():
    """yt-dlp CLI if on PATH, else the bundled Python module (Windows installer)."""
    return ["yt-dlp"] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(map(str,cmd))[:300]}\n{r.stderr[-1500:]}")
    return r

def duration(path):
    return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)]).stdout.strip())

# ---------- 0. fetch ----------
class FetchError(RuntimeError): pass

def normalize_url(u):
    """Share links -> direct download links (Google Drive, Dropbox)."""
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([\w-]+)", u)
    if m: return f"https://drive.google.com/uc?export=download&confirm=t&id={m.group(1)}"
    if "dropbox.com" in u: return re.sub(r"([?&])dl=0", r"\1dl=1", u) if "dl=0" in u else u + ("&" if "?" in u else "?") + "dl=1"
    return u

def fetch(src, workdir, cookies=None, log=print):
    """Local file, or any URL yt-dlp supports (YouTube, X, TikTok, Instagram, Facebook, Bilibili, Vimeo, Twitch VODs,
    Rumble, ...), Google Drive / Dropbox share links and direct MP4s. Tries several YouTube player clients; optional
    cookies file (AIAC_COOKIES env or `cookies` arg, Netscape cookies.txt) for login-only / rate-limited content."""
    workdir = Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    if not re.match(r"https?://", src): return Path(src)
    out = workdir / "source.mp4"
    if out.exists() and out.stat().st_size > 0: return out
    url = normalize_url(src.strip()); cookies = cookies or os.environ.get("AIAC_COOKIES")
    base = YTDLP() + ["--no-playlist","-f","bv*[height<=720]+ba/b[height<=720]/bv*+ba/b","--merge-output-format","mp4",
            "--retries","5","--fragment-retries","10","-o",str(workdir / "source.%(ext)s")] + (["--cookies", cookies] if cookies else [])
    yt = re.search(r"youtu\.?be", url)
    tries = [[]] + ([["--extractor-args", f"youtube:player_client={c}"] for c in ("tv,web_safari", "android,ios", "mweb")] if yt else [])
    last = ""
    for extra in tries:
        r = subprocess.run(base + extra + [url], capture_output=True, text=True); last = r.stderr
        cand = [p for p in workdir.glob("source.*") if p.suffix in (".mp4", ".mkv", ".webm", ".mov")]
        if r.returncode == 0 and cand:
            p = cand[0]
            if p.suffix != ".mp4": run(["ffmpeg","-y","-v","error","-i",str(p),"-c","copy",str(out)]); p.unlink()
            return out
        log("download attempt failed, trying another method")
    # direct file fallback (plain http download)
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(out, "wb") as f: shutil.copyfileobj(r, f)
        if duration(out) > 0: return out
    except Exception: pass
    if out.exists(): out.unlink()
    low = last.lower()
    if "429" in low or "too many requests" in low or "sign in to confirm" in low:
        msg = "The site is rate-limiting this server. Try again later, upload the file instead, or add a cookies file."
    elif "private" in low or "login" in low or "log in" in low:
        msg = "That video needs a login. Upload the file instead, or add a cookies file."
    elif "unsupported url" in low:
        msg = "We can't read that link. Paste a direct video page link or upload the file."
    else: msg = "Couldn't download that link. Check it opens in a browser, or upload the file."
    raise FetchError(msg + " (" + last.strip().splitlines()[-1][:160] + ")" if last.strip() else msg)

# ---------- 1. silence cut ----------
def trim_args(trim):
    a, b = (trim or (None, None))
    return (["-ss", f"{a:.3f}"] if a else []) + (["-to", f"{b:.3f}"] if b else [])

def pretrim(src, out, trim):
    """Pre-trim (processing timeframe) without re-encoding."""
    run(["ffmpeg","-y","-v","error",*trim_args(trim),"-i",str(src),"-c","copy","-avoid_negative_ts","make_zero",str(out)]); return out

def silence_cut(src, out, noise_db=-32, min_silence=0.6, margin=0.15, trim=None):
    """Detect silences with ffmpeg silencedetect, keep speech (+margin). Returns kept segments.
    trim=(start,end) seconds of the source to process (pre-trim; saves time)."""
    if trim and any(trim):
        src = pretrim(src, Path(out).with_name("trimmed.mp4"), trim)
    total = duration(src)
    r = subprocess.run(["ffmpeg","-hide_banner","-i",str(src),"-af",f"silencedetect=noise={noise_db}dB:d={min_silence}","-f","null","-"],capture_output=True,text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    keep, cur = [], 0.0
    for s, e in zip(starts, ends + [total]*(len(starts)-len(ends))):
        a, b = cur, min(total, s + margin)
        if b - a > 0.2: keep.append((a, b))
        cur = max(cur, e - margin)
    if total - cur > 0.2: keep.append((cur, total))
    if not keep: keep = [(0, total)]
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in keep)
    run(["ffmpeg","-y","-hide_banner","-i",str(src),
         "-vf",f"select='{expr}',setpts=N/FRAME_RATE/TB","-af",f"aselect='{expr}',asetpts=N/SR/TB",
         "-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","128k",str(out)])
    removed = total - sum(b - a for a, b in keep)
    return {"segments": keep, "original": total, "removed_seconds": round(removed, 2)}

# ---------- 2. transcription ----------
def _srt_t(x):
    h, m, rest = x.strip().replace(",", ".").split(":"); return int(h)*3600 + int(m)*60 + float(rest)

def parse_srt(text, offset=0.0):
    """User-supplied SRT -> transcript (word times spread evenly inside each cue)."""
    segs = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "").strip()):
        lines = [l for l in block.split("\n") if l.strip()]
        tl = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if tl is None: continue
        a, b = [_srt_t(x) - offset for x in lines[tl].split("-->")]
        if b <= 0: continue
        a = max(a, 0); txt = re.sub(r"<[^>]+>", "", " ".join(lines[tl+1:])).strip(); ws = txt.split()
        if not ws: continue
        d = (b - a) / len(ws)
        segs.append({"start": a, "end": b, "text": txt, "words": [{"start": a+i*d, "end": a+(i+1)*d, "word": w} for i, w in enumerate(ws)]})
    return {"language": "srt", "segments": segs}

def apply_vocab(tr, vocab):
    """Brand vocabulary: {"wrong spelling": "Right Spelling"} applied word-by-word (case-insensitive, keeps punctuation)."""
    if not vocab: return tr
    v = {k.lower().strip(): val for k, val in vocab.items() if k.strip()}
    for s in tr["segments"]:
        for w in s["words"]:
            c = _clean(w["word"])
            if c in v: w["word"] = re.sub(re.escape(c), v[c], w["word"], flags=re.I) if c in w["word"].lower() else v[c]
        s["text"] = " ".join(w["word"] for w in s["words"]) or s["text"]
    return tr

def transcribe(path, model_size="small", language=None, log=print):
    from faster_whisper import WhisperModel
    md = os.environ.get("AIAC_MODEL_DIR")  # bundled models (installer): <dir>/faster-whisper-<size>
    local = Path(md) / f"faster-whisper-{model_size}" if md else None
    model = WhisperModel(str(local) if local and local.exists() else model_size, device="cpu", compute_type="int8")
    raw = subprocess.run(["ffmpeg","-v","error","-i",str(path),"-ac","1","-ar","16000","-f","s16le","-"],capture_output=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32)/32768  # decode via ffmpeg (avoids PyAV version issues)
    segs, info = model.transcribe(audio, word_timestamps=True, language=language or None, vad_filter=True)
    out = []; total = max(info.duration, 1); last = -1
    for s in segs:  # generator: streamed, so we can report progress on long videos
        pct = int(100 * s.end / total)
        if pct // 5 != last // 5: log(f"transcribing {pct}%"); last = pct
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "words": [{"start": w.start, "end": w.end, "word": w.word.strip()} for w in (s.words or [])]})
    return {"language": info.language, "segments": out}

# ---------- 3. clip picking (v1: word-level windows) ----------
HOOKS = ["secret","mistake","truth","never","always","why","how","what if","imagine","problem","biggest",
         "nobody","everyone","stop","best","worst","free","money","important","actually","crazy","story",
         "you need","you should","here's","the key","the reason","most people","think about","listen"]
FILLERS = {"um","uh","umm","uhh","erm","er","ah","hmm","mm","mhm"}
VALUE = ["because","so that","the reason","means","learn","step","tip","result","example","lesson","how to","here's how"]

def _clean(w): return re.sub(r"[^\w']", "", w.lower())

def sentences(words, gap=0.6):
    """Split the word stream into sentence-like units using punctuation and pauses (word-level timings)."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i+1] if i+1 < len(words) else None
        if w["word"].rstrip()[-1:] in ".?!" or nxt is None or nxt["start"] - w["end"] > gap or len(cur) >= 40:
            out.append({"start": cur[0]["start"], "end": cur[-1]["end"], "words": cur,
                        "text": " ".join(x["word"] for x in cur)})
            cur = []
    return out

TREND = ["ai","agent","chatgpt","money","side hustle","viral","2026","crypto","bitcoin","startup","productivity","health",
         "tiktok","youtube","creator","automation","code","job","salary","free","hack","secret","new"]
GENRES = {  # weights for hook, flow, value, trend, pace+energy
    "auto": (0.30, 0.20, 0.25, 0.10, 0.15), "podcast": (0.25, 0.25, 0.30, 0.10, 0.10),
    "qa": (0.40, 0.20, 0.25, 0.05, 0.10), "tutorial": (0.20, 0.20, 0.45, 0.05, 0.10),
    "vlog": (0.30, 0.25, 0.15, 0.10, 0.20), "talk": (0.30, 0.25, 0.25, 0.05, 0.15),
    "gaming": (0.25, 0.10, 0.10, 0.15, 0.40), "news": (0.30, 0.20, 0.25, 0.20, 0.05),
}
def _prompt_rel(text, prompt):
    if not prompt: return 0.0
    toks = [t for t in re.findall(r"\w+", prompt.lower()) if t not in STOP and len(t) > 2]
    if not toks: return 0.0
    tl = text.lower(); return sum(1 for t in toks if t in tl) / len(toks)

def virality(text, sents, energy, genre="auto", prompt=None, detail=False):
    """Heuristic virality 0-100 + reason. Components (0-1): hook, flow, value, trend (+pace/energy, prompt)."""
    t = text.lower(); first = sents[0]["text"].lower()
    hook = min(1.0, (0.7 if (any(h in first for h in HOOKS) or "?" in first) else 0) + min(t.count("?"), 3) * 0.1)
    hooks_total = sum(t.count(h) for h in HOOKS)
    nw = sum(len(s["words"]) for s in sents); dur = max(sents[-1]["end"] - sents[0]["start"], 1)
    pace = min(nw / dur / 3.0, 1.0)
    flow = (0.6 if sents[-1]["text"].rstrip()[-1:] in ".?!" else 0.2) + (0.4 if sents[0]["text"][:1].isupper() else 0.1)
    value = min(1.0, sum(t.count(v) for v in VALUE) * 0.2 + hooks_total * 0.08)
    trend = min(1.0, sum(1 for k in TREND if re.search(r"\b" + re.escape(k) + r"\b", t)) * 0.25)
    fill = sum(1 for s in sents for w in s["words"] if _clean(w["word"]) in FILLERS) / max(nw, 1)
    wh, wf, wv, wt, wp = GENRES.get(genre, GENRES["auto"])
    raw = wh*hook + wf*flow + wv*value + wt*trend + wp*(0.6*pace + 0.4*energy) - 0.5*fill
    rel = _prompt_rel(text, prompt)
    if prompt: raw = 0.5*raw + 0.5*rel
    score = int(max(1, min(99, round(15 + 85*raw))))
    parts = sorted([("strong hook", hook), ("clean ending", flow), ("useful/insightful", value), ("on-trend topic", trend),
                    ("fast pace", pace), ("high energy", energy)], key=lambda x: -x[1])
    reason = ", ".join(p for p, v in parts[:2] if v > 0.3) or "steady talk segment"
    if prompt and rel > 0: reason = f"matches your prompt ({int(rel*100)}%), " + reason
    if hook < 0.3: reason += "; weak opener"
    if detail:
        return score, reason, {"hook": round(hook*100), "flow": round(flow*100), "value": round(value*100),
                               "trend": round(trend*100), "pace": round(pace*100), "energy": round(energy*100),
                               "prompt": round(rel*100) if prompt else None}
    return score, reason

def hook_title(text, sents, max_words=8):
    """Short on-screen hook headline (local, no LLM): prefer a complete punchy sentence near the start."""
    def strip(t): return [w for w in t.split() if _clean(w) not in FILLERS]
    def rank(s):
        ws = strip(s["text"]); lo = s["text"].lower()
        return (("?" in s["text"]) * 2 + sum(h in lo for h in HOOKS) + (3 <= len(ws) <= max_words) * 2)
    best = max(sents[:6], key=rank); ws = strip(best["text"])
    t = " ".join(ws[:max_words]).strip(" ,;:-")
    return t + ("…" if len(ws) > max_words else "")

def heuristic_scorer(text, seg_list, audio_energy):
    """Back-compat scorer: returns float. New code uses virality()."""
    return virality(text, seg_list, audio_energy)[0] / 10

def llm_scorer_from_env():
    """Optional LLM slot. AIAC_LLM=ollama (AIAC_OLLAMA_MODEL, AIAC_OLLAMA_URL) or AIAC_LLM=gemini (GEMINI_API_KEY).
    Returns fn(text)->dict(score,reason,title) or None. Off by default."""
    kind = os.environ.get("AIAC_LLM", "").lower()
    if kind not in ("ollama", "gemini"): return None
    import urllib.request
    prompt = ("Rate this short-video transcript for social virality. Reply ONLY JSON "
              '{"score":0-100,"reason":"<12 words","title":"<8 word hook headline"}.\nTranscript:\n')
    def call(text):
        if kind == "ollama":
            url = os.environ.get("AIAC_OLLAMA_URL", "http://127.0.0.1:11434") + "/api/generate"
            body = {"model": os.environ.get("AIAC_OLLAMA_MODEL", "llama3.2"), "prompt": prompt + text[:4000], "stream": False, "format": "json"}
            req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
            out = json.loads(urllib.request.urlopen(req, timeout=120).read())["response"]
        else:
            key = os.environ["GEMINI_API_KEY"]; model = os.environ.get("AIAC_GEMINI_MODEL", "gemini-2.0-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            body = {"contents": [{"parts": [{"text": prompt + text[:4000]}]}], "generationConfig": {"responseMimeType": "application/json"}}
            req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
            out = json.loads(urllib.request.urlopen(req, timeout=120).read())["candidates"][0]["content"]["parts"][0]["text"]
        d = json.loads(out); d["score"] = int(max(0, min(100, float(d.get("score", 50))))); return d
    return call

def audio_rms(path, sr=8000):
    raw = subprocess.run(["ffmpeg","-v","error","-i",str(path),"-ac","1","-ar",str(sr),"-f","s16le","-"],capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32)/32768
    n = len(a)//sr
    return np.sqrt((a[:n*sr].reshape(n, sr)**2).mean(1)) if n else np.zeros(1)

def pick_clips(transcript, media, n=4, min_len=30, max_len=60, scorer=None, llm=None, log=print, genre="auto", prompt=None):
    """Windows start/end on sentence boundaries derived from WORD timings (not whisper segments, which can be
    longer than max_len and starve the search). Relaxes min_len until n non-overlapping clips are found."""
    words = [w for s in transcript["segments"] for w in s["words"]]
    if not words: return []
    sents = sentences(words); rms = audio_rms(media)
    norm = (rms - rms.min()) / (np.ptp(rms) + 1e-9)
    def energy(a, b): return float(norm[int(a):max(int(b), int(a)+1)].mean()) if len(norm) else 0.0
    chosen, lo = [], min_len
    total = words[-1]["end"] - words[0]["start"]
    while True:
        cands = []
        for i in range(len(sents)):
            for j in range(i, len(sents)):
                d = sents[j]["end"] - sents[i]["start"]
                if d > max_len: break
                if d < lo: continue
                sl = sents[i:j+1]; text = " ".join(s["text"] for s in sl)
                if scorer:  # legacy custom scorer: float, map to 0-100
                    sc = scorer(text, sl, energy(sl[0]["start"], sl[-1]["end"])); score = int(max(0, min(100, sc*10))); reason = "custom scorer"
                    det = None
                else:
                    score, reason, det = virality(text, sl, energy(sl[0]["start"], sl[-1]["end"]), genre, prompt, True)
                cands.append({"start": sl[0]["start"], "end": sl[-1]["end"], "text": text, "score": score,
                              "reason": reason, "detail": det, "sents": sl})
        if prompt and any((c["detail"] or {}).get("prompt") for c in cands):  # 'find a moment': only matching windows
            cands = [c for c in cands if (c["detail"] or {}).get("prompt")]
        cands.sort(key=lambda c: -c["score"])
        for c in cands:
            if len(chosen) >= n: break
            if all(c["end"] <= k["start"] or c["start"] >= k["end"] for k in chosen): chosen.append(c)
        if len(chosen) >= n or lo <= min(8, min_len) or lo >= total: break
        lo = max(min(8, min_len), lo * 0.66)  # relax and fill remaining gaps
    if not chosen:
        chosen = [{"start": words[0]["start"], "end": min(words[-1]["end"], words[0]["start"] + max_len), "text": " ".join(w["word"] for w in words),
                   "score": 40, "reason": "short input", "detail": None, "sents": sents}]
    for c in chosen:
        c["title"] = hook_title(c["text"], c["sents"])
        if llm:
            try:
                d = llm(c["text"]); c.update(score=d["score"], reason="LLM: " + str(d.get("reason", ""))[:80],
                                             title=str(d.get("title") or c["title"])[:60])
            except Exception as e: log(f"LLM scorer failed, using heuristic ({str(e)[:80]})")
        c.pop("sents", None)
    return sorted(chosen, key=lambda c: -c["score"])

# ---------- 4. reframe ----------
YUNET = Path(os.environ.get("AIAC_MODEL_DIR") or Path(__file__).resolve().parent.parent / "models") / "face_detection_yunet_2023mar.onnx"
ASPECTS = {"9:16": (720, 1280), "4:5": (720, 900), "1:1": (720, 720), "16:9": (1280, 720)}

def face_track(path, start, end, sample_fps=3):
    """Sample frames, detect largest face with OpenCV YuNet (MIT model). Returns [(t, cx)]."""
    import cv2
    cap = cv2.VideoCapture(str(path)); fw = cap.get(cv2.CAP_PROP_FRAME_WIDTH); fh = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    pts = []
    try:
        det = cv2.FaceDetectorYN.create(str(YUNET), "", (int(fw//2), int(fh//2)), 0.7)
    except Exception:
        cap.release(); return pts, fw
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t*1000); ok, fr = cap.read()
        if not ok: break
        _, faces = det.detect(cv2.resize(fr, (int(fw//2), int(fh//2))))
        if faces is not None and 0 < len(faces) <= 2:
            f = max(faces, key=lambda f: f[2]*f[3]); pts.append((t - start, (f[0] + f[2]/2)*2))
        t += 1/sample_fps
    cap.release()
    return pts, fw

def crop_track(pts, fw, fh, clip_dur, fps, ow=720, oh=1280):
    cw = min(fw, int(fh*ow/oh) // 2 * 2)
    n = max(1, int(round(clip_dur*fps))); ts = np.arange(n)/fps
    if len(pts) >= 2:
        pt = np.array(pts); cx = np.interp(ts, pt[:, 0], pt[:, 1])
        k = int(fps*1.5) | 1; cx = np.convolve(np.pad(cx, k//2, mode="edge"), np.ones(k)/k, mode="valid")
        out = [cx[0]]
        for v in cx[1:]: out.append(out[-1] + (v - out[-1])*0.08 if abs(v - out[-1]) > cw*0.05 else out[-1])
        cx = np.array(out); mode = "face"
    else:
        cx = np.full(n, fw/2); mode = "center"
    x = np.clip(cx - cw/2, 0, fw - cw).astype(int)
    return x, cw, mode

def fit_blur(fr, ow, oh):
    """Whole frame fitted in the middle over a blurred, zoomed copy of itself (for slides / no-face)."""
    import cv2
    fh, fw = fr.shape[:2]
    s = max(ow/fw, oh/fh); bg = cv2.resize(fr, (int(fw*s)+1, int(fh*s)+1))
    y0 = (bg.shape[0]-oh)//2; x0 = (bg.shape[1]-ow)//2; bg = bg[y0:y0+oh, x0:x0+ow]
    bg = cv2.GaussianBlur(cv2.resize(bg, (ow//8, oh//8)), (0, 0), 3); bg = cv2.resize(bg, (ow, oh))
    bg = (bg * 0.55).astype(np.uint8)
    s = min(ow/fw, oh/fh); fg = cv2.resize(fr, (int(fw*s)//2*2, int(fh*s)//2*2), interpolation=cv2.INTER_AREA)
    y = (oh-fg.shape[0])//2; x = (ow-fg.shape[1])//2; bg[y:y+fg.shape[0], x:x+fg.shape[1]] = fg
    return bg

# ---------- 5. captions ----------
PRESETS = {
  "bold_yellow": dict(font="Anton", size=78, primary="&H00FFFFFF", hi="&H0000E5FF", kw="&H0000FF7F", outline="&H00000000", ol=5, shadow=2, y=0.69, upper=True, words=3),
  "clean_white": dict(font="Montserrat Alternates ExtraBold", size=60, primary="&H00FFFFFF", hi="&H00FFFFFF", kw="&H0000D7FF", outline="&H00000000", ol=3, shadow=0, y=0.75, upper=False, words=4, box=True),
  "neon_pop":    dict(font="Bebas Neue", size=96, primary="&H00FFFFFF", hi="&H0032FF39", kw="&H00FF60FF", outline="&H00400040", ol=6, shadow=3, y=0.64, upper=True, words=2),
}
STOP = set("the a an and or but to of in on at for with is are was were be been it this that i you we they he she my your our so just like really very".split())
EMOJI = {"money":"💰","cash":"💰","rich":"💰","fire":"🔥","crazy":"🤯","mind":"🤯","love":"❤️","heart":"❤️","idea":"💡","secret":"🤫",
         "time":"⏰","fast":"⚡","quick":"⚡","win":"🏆","best":"🏆","growth":"📈","grow":"📈","money's":"💰","think":"🤔","why":"🤔",
         "laugh":"😂","funny":"😂","stop":"🛑","mistake":"❌","wrong":"❌","right":"✅","yes":"✅","work":"💼","code":"💻",
         "ai":"🤖","video":"🎬","phone":"📱","world":"🌍","rocket":"🚀","launch":"🚀","eat":"🍽️","food":"🍕","music":"🎵","free":"🎁"}

def is_keyword(w):
    c = _clean(w)
    return bool(c) and c not in STOP and (any(c == h or c in h.split() for h in HOOKS) or c.isdigit() or c in EMOJI or len(c) >= 8)

def ass_time(t):
    t = max(t, 0); h = int(t//3600); m = int(t%3600//60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def _esc(s): return s.replace("{", "").replace("}", "").replace("\\", "")

def hex2ass(h, alpha="00"):
    h = h.lstrip("#"); return f"&H{alpha}{h[4:6]}{h[2:4]}{h[0:2]}".upper()

def resolve_style(preset, template=None):
    """Caption style = preset, overridden by a saved Brand Template (hex colours, font, stroke, position...)."""
    p = dict(PRESETS.get(preset, PRESETS["bold_yellow"]))
    t = template or {}
    for k, ak in [("color", "primary"), ("highlight", "hi"), ("keyword", "kw"), ("stroke_color", "outline")]:
        if t.get(k): p[ak] = hex2ass(t[k])
    for k, ak in [("font", "font"), ("size", "size"), ("stroke", "ol"), ("shadow", "shadow"), ("uppercase", "upper"),
                  ("words", "words"), ("caption_y", "y"), ("box", "box")]:
        if t.get(k) not in (None, ""): p[ak] = t[k]
    return p

def build_ass(words, preset, out, ow=720, oh=1280, title=None, title_secs=3.0, keywords=True, template=None):
    p = preset if isinstance(preset, dict) else resolve_style(preset, template)
    sc = min(ow, oh) / 720; size = int(p["size"] * sc * (0.85 if oh < ow else 1)); ypos = int(oh * float(p["y"])) if oh > ow * 1.2 else int(oh * min(0.82, float(p["y"]) + 0.1))
    border = 3 if p.get("box") else 1; back = "&H99000000" if p.get("box") else "&H00000000"
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {ow}
PlayResY: {oh}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{p['font']},{size},{p['primary']},{p['hi']},{p['outline']},{back},-1,0,0,0,100,100,1,0,{border},{int(p['ol']*sc)},{p['shadow']},5,40,40,0,1
Style: Title,Montserrat Alternates ExtraBold,{int(46*sc)},&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,{int(14*sc)},0,8,50,50,{int(oh*0.08)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if title:
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(title_secs)},Title,,0,0,0,,{{\\fad(150,250)}}{_esc(title)}")
    groups = [words[i:i+p["words"]] for i in range(0, len(words), p["words"])]
    for g in groups:
        for k, w in enumerate(g):
            st = w["start"]; en = g[k+1]["start"] if k+1 < len(g) else w["end"]
            if en <= st: continue
            parts = []
            for m, ww in enumerate(g):
                txt = _esc(ww["word"].upper() if p["upper"] else ww["word"])
                if m == k: parts.append(f"{{\\c{p['hi']}\\fscx110\\fscy110}}{txt}{{\\r}}")
                elif keywords and is_keyword(ww["word"]): parts.append(f"{{\\c{p['kw']}}}{txt}{{\\r}}")
                else: parts.append(txt)
            pop = "{\\t(0,80,\\fscx104\\fscy104)\\t(80,160,\\fscx100\\fscy100)}" if k == 0 else ""
            lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Cap,,0,0,0,,{{\\pos({ow//2},{ypos})}}{pop}" + " ".join(parts))
    Path(out).write_text(head + "\n".join(lines) + "\n", encoding="utf-8")

_EMOJI_CACHE = {}
def emoji_rgba(ch, px=96):
    """Render a color emoji with Pillow + Noto Color Emoji (OFL). Returns HxWx4 BGRA uint8 or None."""
    if ch in _EMOJI_CACHE: return _EMOJI_CACHE[ch]
    img = None
    try:
        from PIL import Image, ImageDraw, ImageFont
        f = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
        im = Image.new("RGBA", (136, 128), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox()).resize((px, px)); a = np.array(im)
        img = a[:, :, [2, 1, 0, 3]].copy()
    except Exception: pass
    _EMOJI_CACHE[ch] = img; return img

def emoji_events(words, gap=2.5):
    ev, last = [], -99
    for w in words:
        e = EMOJI.get(_clean(w["word"]))
        if e and w["start"] - last > gap: ev.append((w["start"], w["start"] + 1.4, e)); last = w["start"]
    return ev

# ---------- 6. platform presets ----------
# render size is 720p-class to respect the size cap; "native" is the platform's recommended upload size.
# safe = fraction of frame covered by platform UI (top, bottom, left, right).
PLATFORMS = {
 "tiktok":      dict(label="TikTok", icon="🎵", aspect="9:16", native="1080x1920", max_dur=600, fps=30, max_mb=4.9, safe=(0.10, 0.22, 0.04, 0.16)),
 "reels":       dict(label="IG Reels", icon="📸", aspect="9:16", native="1080x1920", max_dur=180, fps=30, max_mb=4.9, safe=(0.14, 0.24, 0.04, 0.14)),
 "ig_feed":     dict(label="IG Feed", icon="🖼️", aspect="4:5", native="1080x1350", max_dur=60, fps=30, max_mb=4.9, safe=(0.0, 0.0, 0.0, 0.0)),
 "ig_stories":  dict(label="IG Stories", icon="⭕", aspect="9:16", native="1080x1920", max_dur=60, fps=30, max_mb=4.9, safe=(0.14, 0.20, 0.04, 0.04)),
 "shorts":      dict(label="YT Shorts", icon="▶️", aspect="9:16", native="1080x1920", max_dur=180, fps=30, max_mb=4.9, safe=(0.12, 0.20, 0.04, 0.16)),
 "youtube":     dict(label="YouTube", icon="📺", aspect="16:9", native="1920x1080", max_dur=43200, fps=30, max_mb=4.9, safe=(0.0, 0.12, 0.0, 0.0)),
 "x":           dict(label="X", icon="✖️", aspect="16:9", native="1280x720", max_dur=140, fps=30, max_mb=4.9, safe=(0.0, 0.10, 0.0, 0.0)),
 "fb_reels":    dict(label="FB Reels", icon="📘", aspect="9:16", native="1080x1920", max_dur=90, fps=30, max_mb=4.9, safe=(0.14, 0.35, 0.04, 0.14)),
 "linkedin":    dict(label="LinkedIn", icon="💼", aspect="1:1", native="1080x1080", max_dur=600, fps=30, max_mb=4.9, safe=(0.0, 0.08, 0.0, 0.0)),
 "snapchat":    dict(label="Spotlight", icon="👻", aspect="9:16", native="1080x1920", max_dur=60, fps=30, max_mb=4.9, safe=(0.10, 0.20, 0.04, 0.12)),
 "pinterest":   dict(label="Pinterest", icon="📌", aspect="9:16", native="1080x1920", max_dur=60, fps=30, max_mb=4.9, safe=(0.10, 0.20, 0.04, 0.04)),
 "threads":     dict(label="Threads", icon="🧵", aspect="4:5", native="1080x1350", max_dur=300, fps=30, max_mb=4.9, safe=(0.0, 0.0, 0.0, 0.0)),
 "bilibili":    dict(label="Bilibili", icon="📼", aspect="16:9", native="1920x1080", max_dur=600, fps=30, max_mb=4.9, safe=(0.0, 0.10, 0.0, 0.0)),
 "douyin":      dict(label="Douyin", icon="🎶", aspect="9:16", native="1080x1920", max_dur=900, fps=30, max_mb=4.9, safe=(0.10, 0.22, 0.04, 0.16)),
 "kuaishou":    dict(label="Kuaishou", icon="⚡", aspect="9:16", native="1080x1920", max_dur=600, fps=30, max_mb=4.9, safe=(0.10, 0.22, 0.04, 0.16)),
 "kwai":        dict(label="Kwai", icon="🟠", aspect="9:16", native="1080x1920", max_dur=600, fps=30, max_mb=4.9, safe=(0.10, 0.22, 0.04, 0.16)),
 "likee":       dict(label="Likee", icon="💗", aspect="9:16", native="1080x1920", max_dur=300, fps=30, max_mb=4.9, safe=(0.10, 0.22, 0.04, 0.16)),
 "vk_clips":    dict(label="VK Clips", icon="🔵", aspect="9:16", native="1080x1920", max_dur=180, fps=30, max_mb=4.9, safe=(0.10, 0.22, 0.04, 0.16)),
 "triller":     dict(label="Triller", icon="🎤", aspect="9:16", native="1080x1920", max_dur=600, fps=30, max_mb=4.9, safe=(0.10, 0.22, 0.04, 0.16)),
}

# ---------- 7. helpers for render ----------
def has_audio(path):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=index","-of","csv=p=0",str(path)],capture_output=True,text=True)
    return bool(r.stdout.strip())

def subtract(ranges, cuts):
    out = []
    for a, b in ranges:
        segs = [(a, b)]
        for c, d in cuts:
            nxt = []
            for x, y in segs:
                if d <= x or c >= y: nxt.append((x, y)); continue
                if c - x > 0.05: nxt.append((x, c))
                if y - d > 0.05: nxt.append((d, y))
            segs = nxt
        out += segs
    return out

def timeline(clip, words, remove_fillers=True, remove_pauses=False, max_dur=None):
    """Absolute source ranges in playback order: clip parts (transcript edits) minus fillers/pauses, capped to max_dur."""
    parts = clip.get("parts") or [[clip["start"], clip["end"]]]
    cuts = []
    if remove_fillers: cuts += [(w["start"], w["end"]) for w in words if _clean(w["word"]) in FILLERS]
    if remove_pauses:
        ws = [w for w in words if parts[0][0] - 1 <= w["start"] <= max(p[1] for p in parts) + 1]
        cuts += [(x["end"] + 0.12, y["start"] - 0.12) for x, y in zip(ws, ws[1:]) if y["start"] - x["end"] > 0.5]
    keep = subtract([tuple(p) for p in parts], cuts)
    if max_dur:
        out, acc = [], 0.0
        for a, b in keep:
            if acc >= max_dur: break
            b = min(b, a + max_dur - acc); out.append((a, b)); acc += b - a
        keep = out
    return keep

def to_out(t, keep, offset=0.0):
    acc = 0.0
    for a, b in keep:
        if a - 0.02 <= t <= b + 0.02: return offset + acc + min(max(t - a, 0), b - a)
        acc += b - a
    return None

def words_for(keep, words, offset=0.0, censor=(), censor_mode="mask"):
    cens = {c.lower() for c in censor}; out = []
    for w in words:
        if _clean(w["word"]) in FILLERS: continue
        s = to_out(w["start"], keep, offset); e = to_out(w["end"], keep, offset)
        if s is None or e is None or e < s: continue
        txt = w["word"]
        if _clean(txt) in cens:
            txt = txt[0] + "*" * max(1, len(_clean(txt)) - 1) if censor_mode != "remove" else "[bleep]"
        out.append(dict(w, word=txt, start=s, end=e, censored=_clean(w["word"]) in cens))
    return out

def cover(fr, ow, oh):
    import cv2
    fh, fw = fr.shape[:2]; s = max(ow/fw, oh/fh)
    im = cv2.resize(fr, (int(fw*s)+1, int(fh*s)+1)); y = (im.shape[0]-oh)//2; x = (im.shape[1]-ow)//2
    return im[y:y+oh, x:x+ow]

class Reader:
    """Sequential frame reader at an output fps with seeking per range."""
    def __init__(self, path):
        import cv2; self.cap = cv2.VideoCapture(str(path)); self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.w = int(self.cap.get(3)); self.h = int(self.cap.get(4)); self.dur = self.cap.get(7) / self.fps
    def frames(self, a, b, fps):
        import cv2
        self.cap.set(cv2.CAP_PROP_POS_MSEC, a*1000); ok, fr = self.cap.read(); i = 0
        for k in range(int(round((b - a) * fps))):
            t = a + k / fps
            while ok and a + (i + 1) / self.fps <= t:
                ok2, nf = self.cap.read()
                if not ok2: break
                fr = nf; i += 1
            if fr is None: return
            yield t, fr

def overlay_rgba(img, rgba, x0, y0):
    eh, ew = rgba.shape[:2]; H_, W_ = img.shape[:2]
    if x0 < 0 or y0 < 0 or x0 + ew > W_ or y0 + eh > H_: return
    al = rgba[:, :, 3:4] / 255.0; roi = img[y0:y0+eh, x0:x0+ew]
    img[y0:y0+eh, x0:x0+ew] = (roi*(1-al) + rgba[:, :, :3]*al).astype(np.uint8)

def load_logo(path, ow, oh, scale=0.16):
    import cv2
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im is None: return None
    if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
    if im.shape[2] == 3: im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    w = int(min(ow, oh) * scale); h = int(im.shape[0] * w / im.shape[1])
    return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)

# ---------- 8. B-roll ----------
def pexels_broll(query, workdir, portrait=True):
    """Free stock B-roll from Pexels (needs PEXELS_API_KEY; Pexels license, attribution appreciated). Returns path or None."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key or not query: return None
    import urllib.request, urllib.parse
    out = Path(workdir) / f"broll_{re.sub(r'[^a-z0-9]+', '_', query.lower())[:40]}.mp4"
    if out.exists(): return out
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": query, "per_page": 3, "orientation": "portrait" if portrait else "landscape"})
    d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": key}), timeout=30).read())
    for v in d.get("videos", []):
        files = sorted([f for f in v["video_files"] if f.get("width") and 540 <= min(f["width"], f["height"]) <= 1080], key=lambda f: f["width"])
        if files:
            urllib.request.urlretrieve(files[0]["link"], out); return out
    return None

def broll_events(cw_words, opts, workdir, main_off, main_dur, log=print):
    """Return [(t0, t1, path)] in output time. opts['broll']: 'auto' (keywords) or a prompt; opts['broll_file']: user clip."""
    ev = []
    if opts.get("broll_file") and Path(opts["broll_file"]).exists():
        t0 = main_off + main_dur * 0.35; ev.append((t0, t0 + 2.5, opts["broll_file"]))
    elif opts.get("broll"):
        if not os.environ.get("PEXELS_API_KEY"): log("B-roll skipped (set PEXELS_API_KEY for free stock footage)"); return []
        qs = []
        if opts["broll"] == "auto":
            seen = set()
            for w in cw_words:
                c = _clean(w["word"])
                if len(c) >= 6 and c not in STOP and c not in seen and w["start"] > main_off + 3: qs.append((w["start"], c)); seen.add(c)
            qs = qs[::max(1, len(qs)//2)][:2]
        else: qs = [(main_off + main_dur * 0.35, opts["broll"])]
        for t, q in qs:
            try:
                p = pexels_broll(q, workdir)
                if p: ev.append((t, t + 2.5, str(p)))
            except Exception as e: log(f"B-roll '{q}' failed: {str(e)[:80]}")
    return ev

# ---------- 9. render ----------
DEFAULT_OPTS = dict(preset="bold_yellow", aspect="9:16", fit="auto", hook=True, keywords=True, emoji=False,
                    remove_fillers=True, remove_pauses=False, censor=[], censor_mode="bleep", template=None,
                    broll=None, broll_file=None, max_mb=4.9, fps=None, max_dur=None, size=None)

def render_clip(media, clip, words, out, workdir=".", opts=None, cw_words=None, log=print, **kw):
    """Render one clip. opts: see DEFAULT_OPTS (+ template: logo, logo_pos, logo_scale, intro, outro, music, music_volume, layout).
    cw_words: edited output-timeline caption words (skip regeneration)."""
    import cv2
    o = dict(DEFAULT_OPTS); o.update(opts or {}); o.update(kw); t = o.get("template") or {}
    if t.get("layout") and o["fit"] == "auto": o["fit"] = t["layout"]
    ow, oh = o["size"] or ASPECTS[o["aspect"]]
    rd = Reader(media); fps = o["fps"] or min(30, round(rd.fps) or 30)
    keep = timeline(clip, words, o["remove_fillers"], o["remove_pauses"], o["max_dur"])
    intro = t.get("intro") if t.get("intro") and Path(t["intro"]).exists() else None
    outro = t.get("outro") if t.get("outro") and Path(t["outro"]).exists() else None
    idur = min(duration(intro), 5) if intro else 0.0; odur = min(duration(outro), 5) if outro else 0.0
    mdur = sum(b - a for a, b in keep); total = idur + mdur + odur
    # framing: face crop per range, or blurred fit
    tracks, nface, nsamp = [], 0, 0
    for a, b in keep:
        pts, _ = face_track(media, a, b, sample_fps=3 if b - a > 2 else 6); nface += len(pts); nsamp += max(1, (b - a) * 3)
        tracks.append(crop_track(pts, rd.w, rd.h, b - a, fps, ow, oh))
    cwid = tracks[0][1] if tracks else rd.w
    mode = "face" if any(tr[2] == "face" for tr in tracks) else "center"
    if o["fit"] == "blur" or (o["fit"] == "auto" and (nface / max(nsamp, 1) < 0.3 or cwid >= rd.w)): mode = "blur_fit"
    if cw_words is None: cw_words = words_for(keep, words, idur, o["censor"], o["censor_mode"])
    style = resolve_style(o["preset"], t)
    ass = Path(workdir) / (Path(out).stem + ".ass")
    title = clip.get("title") if o["hook"] else None
    build_ass(cw_words, style, ass, ow, oh, title, keywords=o["keywords"])
    if idur and title:  # retime title after intro
        txt = ass.read_text().replace(f"Dialogue: 1,{ass_time(0)},{ass_time(3.0)},", f"Dialogue: 1,{ass_time(idur)},{ass_time(idur+3)},")
        ass.write_text(txt)
    evs = [(a, b, emoji_rgba(e, int(min(ow, oh)*0.15))) for a, b, e in (emoji_events(cw_words) if o["emoji"] else [])]
    evs = [e for e in evs if e[2] is not None]
    brs = broll_events(cw_words, o, workdir, idur, mdur, log)
    breaders = {p: Reader(p) for _, _, p in brs}
    logo = load_logo(t["logo"], ow, oh, float(t.get("logo_scale", 0.16))) if t.get("logo") and Path(t["logo"]).exists() else None
    # audio graph
    inputs, idx = [], {}
    def inp(p):
        if p not in idx: idx[p] = len(inputs) + 1; inputs.append(p)
        return idx[p]
    segs = ([(intro, 0, idur)] if intro else []) + [(str(media), a, b) for a, b in keep] + ([(outro, 0, odur)] if outro else [])
    uses = {}
    for p, a, b in segs:
        if has_audio(p): inp(p); uses[p] = uses.get(p, 0) + 1
    fc, labels, split_ct = [], [], {}
    for p, n in uses.items():
        fc.append(f"[{idx[p]}:a]asplit={n}" + "".join(f"[s{idx[p]}_{k}]" for k in range(n)) if n > 1 else f"[{idx[p]}:a]anull[s{idx[p]}_0]")
    for k, (p, a, b) in enumerate(segs):
        if p in uses:
            j = split_ct.get(p, 0); split_ct[p] = j + 1
            fc.append(f"[s{idx[p]}_{j}]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[g{k}]")
        else:
            fc.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{b-a:.3f}[g{k}]")
        labels.append(f"[g{k}]")
    fc.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[cat]"); last = "cat"
    bleeps = [(w["start"], w["end"]) for w in cw_words if w.get("censored") or re.search(r"\w\*+", w["word"])]
    if bleeps:
        ex = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in bleeps)
        fc.append(f"[{last}]volume=0:enable='{ex}'[mut]"); last = "mut"
        if o["censor_mode"] == "bleep":
            fc.append(f"aevalsrc='0.25*sin(2*PI*1000*t)*({ex})':s=48000:c=stereo:d={total:.3f}[bp]")
            fc.append(f"[{last}][bp]amix=inputs=2:duration=first:normalize=0[bl]"); last = "bl"
    music = t.get("music") if t.get("music") and Path(t["music"]).exists() else None
    margs = []
    if music:
        mi = len(inputs) + 1; inputs.append(music); margs = [mi]
        fc.append(f"[{mi}:a]volume={float(t.get('music_volume', 0.12))},atrim=0:{total:.3f},aresample=48000,aformat=channel_layouts=stereo[mu]")
        fc.append(f"[{last}][mu]amix=inputs=2:duration=first:normalize=0[mx]"); last = "mx"
    fc.append(f"[0:v]ass={ass}[vout]")
    vbr = int(max(300, (o["max_mb"]*8*1000*0.88/max(total, 1)) - 96))
    cmd = ["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","bgr24","-s",f"{ow}x{oh}","-r",f"{fps}","-i","-"]
    for k, p in enumerate(inputs):
        if margs and k + 1 == margs[0]: cmd += ["-stream_loop","-1"]
        cmd += ["-vn","-i",str(p)]
    cmd += ["-filter_complex",";".join(fc),"-map","[vout]","-map",f"[{last}]","-c:v","libx264","-preset","medium",
            "-b:v",f"{vbr}k","-maxrate",f"{int(vbr*1.3)}k","-bufsize",f"{vbr*2}k","-pix_fmt","yuv420p","-r",str(fps),
            "-c:a","aac","-b:a","96k","-t",f"{total:.3f}","-movflags","+faststart",str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    ey = int(oh * float(style["y"])) - int(min(ow, oh)*0.27) if oh > ow * 1.2 else int(oh*0.55)
    lp = t.get("logo_pos", "tr"); m = int(min(ow, oh) * 0.04)
    def emit(img, to, main=True):
        if main:
            for a, b, p in brs:
                if a <= to < b:
                    br = breaders[p]; fr2 = next(br.frames((to - a) % max(br.dur - 0.1, 0.5), (to - a) % max(br.dur - 0.1, 0.5) + 1/fps, fps), None)
                    if fr2 is not None: img = cover(fr2[1], ow, oh)
            for a, b, em in evs:
                if a <= to < b: overlay_rgba(img, em, (ow - em.shape[1])//2, max(0, ey))
            if logo is not None:
                lh, lw = logo.shape[:2]
                overlay_rgba(img, logo, m if "l" in lp else ow - lw - m, m if "t" in lp else oh - lh - m)
        proc.stdin.write(np.ascontiguousarray(img).tobytes())
    try:
        k_out = 0
        if intro:
            for _, fr in Reader(intro).frames(0, idur, fps): emit(fit_blur(fr, ow, oh), k_out/fps, False); k_out += 1
        for (a, b), (xs, cw, _) in zip(keep, tracks):
            for i, (tt, fr) in enumerate(rd.frames(a, b, fps)):
                if mode == "blur_fit": img = fit_blur(fr, ow, oh)
                else:
                    x = xs[min(i, len(xs)-1)]; img = cv2.resize(fr[:, x:x+cw], (ow, oh), interpolation=cv2.INTER_LANCZOS4)
                emit(img, k_out/fps); k_out += 1
        if outro:
            for _, fr in Reader(outro).frames(0, odur, fps): emit(fit_blur(fr, ow, oh), k_out/fps, False); k_out += 1
        proc.stdin.close()
    except BrokenPipeError: pass
    err = proc.stderr.read().decode(); proc.wait()
    if proc.returncode: raise RuntimeError(err[-1500:])
    (Path(workdir) / (Path(out).stem + ".words.json")).write_text(json.dumps(cw_words))
    nfill = sum(1 for w in words if _clean(w["word"]) in FILLERS and any(a - 0.3 <= w["start"] <= b + 0.3 for a, b in (clip.get("parts") or [[clip["start"], clip["end"]]])))
    return {"file": str(out), "reframe": mode, "aspect": o["aspect"], "size": f"{ow}x{oh}", "fps": fps, "fillers_removed": nfill,
            "duration": round(total, 2), "keep": [[round(a, 3), round(b, 3)] for a, b in keep], "broll": len(brs),
            "size_mb": round(os.path.getsize(out)/1e6, 2)}

# ---------- 10. editing ----------
def _load(outdir):
    outdir = Path(outdir); rep = json.loads((outdir / "report.json").read_text()); work = outdir / "work"
    words = [w for s in json.loads((work / "transcript.json").read_text())["segments"] for w in s["words"]]
    return outdir, rep, work, words

def _save_clip(outdir, rep, idx, c, r):
    c.update({k: v for k, v in r.items() if k != "file"}); c["edited"] = c.get("edited", 0) + 1
    (Path(outdir) / "report.json").write_text(json.dumps(rep, indent=1)); return c

def rerender_with_text(outdir, idx, new_words_text, title=None):
    """Caption edit: replace word texts (same length; '' deletes a word) for clip idx (1-based), re-render."""
    outdir, rep, work, words = _load(outdir); c = rep["clips"][idx-1]
    ws = json.loads((work / (Path(c["file"]).stem + ".words.json")).read_text())
    if len(new_words_text) != len(ws): raise ValueError(f"expected {len(ws)} words, got {len(new_words_text)}")
    ws = [dict(w, word=t.strip()) for w, t in zip(ws, new_words_text) if t.strip()]
    if title is not None: c["title"] = title
    r = render_clip(c["media"], c, words, c["file"], work, rep["options"], cw_words=ws)
    return _save_clip(outdir, rep, idx, c, r)

def transcript_sentences(outdir):
    outdir, rep, work, words = _load(outdir)
    return [{"i": i, "start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"]} for i, s in enumerate(sentences(words))]

def edit_sections(outdir, idx, remove=(), add=(), add_at="end"):
    """Transcript-based editing. remove: [[start,end],...] ranges (e.g. a sentence's times) cut from the clip;
    add: ranges from anywhere in the transcript appended at 'start' or 'end'. Re-renders (caption text edits reset)."""
    outdir, rep, work, words = _load(outdir); c = rep["clips"][idx-1]
    parts = [tuple(p) for p in (c.get("parts") or [[c["start"], c["end"]]])]
    parts = subtract(parts, [tuple(r) for r in remove])
    adds = [tuple(r) for r in add]
    parts = (adds + parts) if add_at == "start" else (parts + adds)
    if not parts: raise ValueError("nothing left in clip")
    c["parts"] = [[round(a, 3), round(b, 3)] for a, b in parts]
    r = render_clip(c["media"], c, words, c["file"], work, rep["options"])
    return _save_clip(outdir, rep, idx, c, r)

def export_platforms(outdir, idx, platforms, log=print):
    """Render clip idx for several platform presets and zip them. Returns zip path."""
    import zipfile
    outdir, rep, work, words = _load(outdir); c = rep["clips"][idx-1]; files = []
    for p in platforms:
        P = PLATFORMS[p]; o = dict(rep["options"]); o.update(aspect=P["aspect"], fps=P["fps"], max_mb=P["max_mb"], max_dur=P["max_dur"])
        out = outdir / f"clip_{idx:02d}_{p}.mp4"; log(f"exporting {P['label']}")
        render_clip(c["media"], c, words, out, work, o); files.append(out)
    z = outdir / f"clip_{idx:02d}_platforms.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        for f in files: zf.write(f, f.name)
    return z

# ---------- 11. NLE export ----------
def export_xml(outdir, idx, kind="fcpxml"):
    """Export clip idx as FCPXML 1.9 (Final Cut / DaVinci Resolve) or xmeml v4 (Premiere Pro / Resolve).
    References the processed source media with the clip's kept ranges as cuts, plus the hook title as a marker."""
    from xml.sax.saxutils import escape
    outdir, rep, work, words = _load(outdir); c = rep["clips"][idx-1]
    media = Path(c["media"]).resolve(); rd = Reader(media); tb = int(round(rd.fps)) or 30
    keep = [tuple(k) for k in c.get("keep") or timeline(c, words, rep["options"].get("remove_fillers", True))]
    f = lambda t: int(round(t * tb)); total = sum(f(b) - f(a) for a, b in keep); name = escape(c.get("title") or f"clip {idx}")
    srcdur = f(duration(media))
    if kind == "fcpxml":
        items, off = [], 0
        for a, b in keep:
            items.append(f'<asset-clip ref="r2" offset="{off}/{tb}s" start="{f(a)}/{tb}s" duration="{f(b)-f(a)}/{tb}s" name="{escape(media.name)}"/>'); off += f(b) - f(a)
        x = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9"><resources>
<format id="r1" frameDuration="1/{tb}s" width="{rd.w}" height="{rd.h}"/>
<asset id="r2" name="{escape(media.name)}" start="0s" duration="{srcdur}/{tb}s" hasVideo="1" hasAudio="1" format="r1"><media-rep kind="original-media" src="file://{escape(str(media))}"/></asset>
</resources><library><event name="AI AGENT CUT"><project name="{name}"><sequence format="r1" duration="{total}/{tb}s" tcStart="0s"><spine>
{chr(10).join(items)}
</spine></sequence></project></event></library></fcpxml>'''
        out = outdir / f"clip_{idx:02d}.fcpxml"
    else:
        items, off = [], 0
        for k, (a, b) in enumerate(keep):
            d = f(b) - f(a); fileel = f'<file id="file-1"><name>{escape(media.name)}</name><pathurl>file://{escape(str(media))}</pathurl><rate><timebase>{tb}</timebase></rate><duration>{srcdur}</duration></file>' if k == 0 else '<file id="file-1"/>'
            items.append(f'<clipitem id="ci{k}"><name>{escape(media.name)}</name><rate><timebase>{tb}</timebase></rate><start>{off}</start><end>{off+d}</end><in>{f(a)}</in><out>{f(b)}</out>{fileel}</clipitem>'); off += d
        aitems = [re.sub(r'<file id="file-1">.*?</file>', '<file id="file-1"/>', i).replace('<clipitem id="ci', '<clipitem id="ai') for i in items]
        x = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4"><sequence id="seq1"><name>{name}</name><duration>{total}</duration><rate><timebase>{tb}</timebase></rate>
<media><video><format><samplecharacteristics><width>{rd.w}</width><height>{rd.h}</height></samplecharacteristics></format><track>{"".join(items)}</track></video>
<audio><track>{"".join(aitems)}</track></audio></media></sequence></xmeml>'''
        out = outdir / f"clip_{idx:02d}_premiere.xml"
    out.write_text(x); return out

# ---------- orchestrator ----------
def process(src, outdir, n_clips=4, preset="bold_yellow", model="small", min_len=30, max_len=60,
            silence=True, log=print, scorer=None, aspect="9:16", fit="auto", hook=True, keywords=True,
            emoji=False, remove_fillers=True, reuse=True, trim=None, prompt=None, genre="auto", language=None,
            srt=None, vocab=None, censor=None, censor_mode="bleep", template=None, broll=None, broll_file=None,
            remove_pauses=False, cookies=None):
    """trim=(start,end) pre-trim seconds; prompt='find a moment'; genre in GENRES; srt=path to user captions
    (skips transcription and silence cut); vocab={wrong: right}; censor=[words]; template=Brand Template dict."""
    outdir = Path(outdir); work = outdir / "work"; work.mkdir(parents=True, exist_ok=True)
    log("fetching input"); media = fetch(src, work, cookies=cookies, log=log)
    template = template or {}
    opts = dict(preset=preset, aspect=aspect, fit=fit, hook=hook, keywords=keywords, emoji=emoji,
                remove_fillers=remove_fillers, remove_pauses=remove_pauses, censor=list(censor or template.get("censor") or []),
                censor_mode=censor_mode, template=template, broll=broll, broll_file=broll_file, model=model)
    report = {"input": str(src), "options": opts,
              "find": dict(prompt=prompt, genre=genre, min_len=min_len, max_len=max_len, trim=trim, language=language, srt=bool(srt))}
    vocab = dict(template.get("vocab") or {}, **(vocab or {}))
    key = json.dumps({"trim": trim, "silence": silence and not srt, "lang": language, "model": model, "srt": str(srt)})
    kf = work / "cache_key.json"; cached = reuse and kf.exists() and kf.read_text() == key and (work / "transcript.json").exists()
    if srt:
        if trim and any(trim): media = pretrim(media, work / "trimmed.mp4", trim)
        tr = parse_srt(Path(srt).read_text(errors="ignore"), offset=(trim or (0,))[0] or 0); log(f"using uploaded SRT ({len(tr['segments'])} cues)")
    else:
        if silence:
            cut = work / "cut.mp4"
            if cached and cut.exists(): log("reusing silence-cut media")
            else: log("cutting silences"); report["silence"] = {k: v for k, v in silence_cut(media, cut, trim=trim).items() if k != "segments"}
            media = cut
        elif trim and any(trim): media = pretrim(media, work / "trimmed.mp4", trim)
        tj = work / "transcript.json"
        if cached: log("reusing transcript"); tr = json.loads(tj.read_text())
        else: tr = transcribe(media, model, language, log=log)
    tr = apply_vocab(tr, vocab)
    (work / "transcript.json").write_text(json.dumps(tr, indent=1)); kf.write_text(key)
    words = [w for s in tr["segments"] for w in s["words"]]
    llm = llm_scorer_from_env()
    log("picking clips" + (" (LLM: %s)" % os.environ.get("AIAC_LLM") if llm else "") + (f" for '{prompt}'" if prompt else ""))
    clips = pick_clips(tr, media, n_clips, min_len, max_len, scorer, llm, log, genre=genre, prompt=prompt)
    results = []
    tag = f"{preset}_{aspect.replace(':','x')}"
    for i, c in enumerate(clips, 1):
        out = outdir / f"clip_{i:02d}_{tag}.mp4"
        log(f"rendering clip {i}/{len(clips)} ({c['start']:.1f}-{c['end']:.1f}s, virality {c['score']})")
        r = render_clip(media, c, words, out, work, opts, log=log)
        r.update(start=round(c["start"], 2), end=round(c["end"], 2), score=c["score"], reason=c["reason"], detail=c.get("detail"),
                 title=c["title"], text=c["text"][:300], media=str(media))
        results.append(r)
    report["clips"] = results
    (outdir / "report.json").write_text(json.dumps(report, indent=1))
    log("done"); return report
