"""UGC mode: campaign brief -> requirements checklist, 3 hooks, 20-45 s script -> faceless 9:16 video.
Original implementation for AI Agent Cut. LLM: Gemini if GEMINI_API_KEY is set, else a local rule-based writer.
URL briefs: Firecrawl API if FIRECRAWL_API_KEY is set, else a plain HTTP fetch. TTS: Kokoro-82M (Apache-2.0 weights,
kokoro-onnx MIT) offline; falls back to Piper or edge-tts if installed. Render: the existing clip engine."""
import json, os, re, subprocess, shutil, html, urllib.request
from pathlib import Path
from . import engine

ROOT = Path(__file__).resolve().parent.parent
WPS = 2.9  # spoken words per second for the voiceover pace we use

# ---------- styles gallery (structures are our own) ----------
STYLES = {
    "ai_ad":     {"label": "AI ad", "desc": "Fast, punchy product ad with a bold claim",
                  "beats": ["hook", "pain", "product", "proof", "cta"]},
    "explainer": {"label": "Explainer", "desc": "How it works in three simple steps",
                  "beats": ["hook", "question", "step1", "step2", "step3", "cta"]},
    "review":    {"label": "Review", "desc": "Honest first-person review with a verdict",
                  "beats": ["hook", "context", "liked", "caveat", "verdict", "cta"]},
    "unboxing":  {"label": "Unboxing", "desc": "First impressions, what's inside, first use",
                  "beats": ["hook", "inside", "first_use", "surprise", "cta"]},
    "story":     {"label": "Story", "desc": "Mini story: before, turning point, after",
                  "beats": ["hook", "before", "turn", "after", "cta"]},
}

# ---------- reading a brief ----------
def _strip_html(t):
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</(p|li|h\d|div)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t); t = html.unescape(t)
    return "\n".join(l.strip() for l in t.splitlines() if l.strip())

def read_url(url, log=print):
    """Firecrawl (if key) gives clean markdown even for JS pages; otherwise fetch + strip tags (may miss JS content)."""
    key = os.environ.get("FIRECRAWL_API_KEY")
    if key:
        try:
            req = urllib.request.Request("https://api.firecrawl.dev/v1/scrape", json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True}).encode(),
                                         {"Content-Type": "application/json", "Authorization": "Bearer " + key})
            d = json.loads(urllib.request.urlopen(req, timeout=90).read())
            md = (d.get("data") or {}).get("markdown")
            if md: return md[:20000], "firecrawl"
        except Exception as e: log(f"Firecrawl failed ({str(e)[:80]}), trying a plain fetch")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AI Agent Cut)"})
    raw = urllib.request.urlopen(req, timeout=30).read(2_000_000).decode("utf-8", "ignore")
    meta = " ".join(html.unescape(m) for m in re.findall(r'<meta[^>]+(?:name|property)="(?:description|og:description|og:title)"[^>]+content="([^"]*)"', raw))
    return (meta + "\n" + _strip_html(raw))[:20000], "http"

RULE_WORDS = r"\b(must|should|need|required|require|include|mention|show|use|avoid|don'?t|do not|never|only|tag|hashtag|link|cta|call to action|disclose|#ad|caption|seconds?|sec|length|vertical|9:16|face|voiceover|music|logo|brand|product|post|upload|submit|views?|payout|per 1,?000|cpm)\b"

def _product(text):
    for pat in (r"(?im)^\s*(?:brand|product|app|company|client)\s*[:\-]\s*(.+)$", r"(?i)\bpromot(?:e|ing)\s+([A-Z][\w.&' -]{1,40})", r"(?i)\babout\s+([A-Z][\w.&'-]{1,30})"):
        m = re.search(pat, text)
        if m: return m.group(1).strip().strip(".").split("  ")[0][:40]
    caps = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s[A-Z][a-zA-Z0-9]+)?)\b", text)
    stop = {"The", "This", "You", "Your", "We", "Our", "Must", "Do", "Don", "Make", "Post", "Videos", "Video", "UGC", "Content", "Rewards", "Brief", "Campaign", "TikTok", "Instagram", "YouTube", "Reels", "Shorts", "CTA", "No", "Use", "Show"}
    caps = [c for c in caps if c.split()[0] not in stop]
    return max(set(caps), key=caps.count) if caps else "this product"

def _benefit(text):
    m = re.search(r"(?i)\b(?:helps?|lets?|makes?|so you can|to)\s+(?:you\s+)?([a-z][^.\n]{8,70})", text)
    return m.group(1).strip().rstrip(",;") if m else "save time every day"

def local_brief(text, style="ai_ad"):
    lines = [re.sub(r"^\s*[-*•\d.)\]]+\s*", "", l).strip() for l in re.split(r"[\n\r]+|(?<=[.!?])\s+(?=[A-Z])", text)]
    lines = [l for l in lines if 6 <= len(l) <= 220]
    rules, seen = [], set()
    for l in lines:
        if re.match(r"(?i)(brand|product|app|company|client|payout|budget|campaign|requirements?)\s*[:\-]?\s*$|(brand|product|app|company|client|payout|budget)\s*:", l): continue
        if re.search(RULE_WORDS, l, re.I):
            k = re.sub(r"\W+", " ", l.lower())[:60]
            if k not in seen: seen.add(k); rules.append(l.rstrip("."))
    tags = sorted(set(re.findall(r"(?<!\w)[#@][\w.]{2,30}", text)))
    m = re.search(r"(\d{1,3})\s*(?:-|–|to)\s*(\d{1,3})\s*(?:s\b|sec|seconds)", text, re.I)
    lo, hi = (int(m.group(1)), int(m.group(2))) if m else (20, 45)
    lo, hi = max(15, min(lo, 60)), max(20, min(hi, 60))
    product, benefit = _product(text), _benefit(text)
    checklist = rules[:10]
    std = [f"Length {lo}-{hi} seconds, vertical 9:16", "Hook in the first 2 seconds", f"Name {product} clearly and show it on screen",
           "Original footage only: no reused clips or other people's likeness", "Clear call to action at the end"]
    if tags: std.insert(2, "Include " + " ".join(tags))
    if re.search(r"#ad|disclos|sponsor|paid partnership", text, re.I): std.append("Disclose the partnership (#ad / paid partnership)")
    if any(re.search(r"\bseconds?|\bsec\b", r, re.I) for r in checklist): std = std[1:]
    for s in std:
        if not any(s.split()[0].lower() in r.lower() and s.split()[1].lower() in r.lower() for r in checklist): checklist.append(s)
    hooks = [f"I didn't expect {product} to {benefit.split(' and ')[0]}.",
             f"Stop scrolling if you still don't {benefit.split(' and ')[0]}.",
             f"Three seconds to show you why everyone's switching to {product}."]
    return {"product": product, "benefit": benefit, "checklist": checklist[:14], "hooks": hooks, "tags": tags,
            "length": [lo, hi], "script": write_script(product, benefit, hooks[0], style, lo, hi, tags), "engine": "local"}

def write_script(product, benefit, hook, style="ai_ad", lo=20, hi=45, tags=()):
    p = product; b = re.split(r"\s+(?:and|,|while|so)\s+", benefit)[0]; bf = benefit
    lines = {
        "ai_ad": [hook, f"Most of us waste hours trying to {b} the hard way.", f"{p} does it for you in a few taps, no learning curve.",
                  f"I tried it this week and it actually worked the first time.", f"Try {p} today. The link is in my bio."],
        "explainer": [hook, f"So how does {p} help you {b}?", f"Step one: open {p} and pick what you need.",
                      "Step two: let it do the heavy lifting while you keep going.", "Step three: check the result and share it.",
                      f"That's it. Try {p} with the link in my bio."],
        "review": [hook, f"I've been using {p} for a week to {bf}.", "What I liked: it's fast, simple and it just works.",
                   "One thing to know: it takes a minute to set up the first time.", f"My verdict? I'm keeping {p}.", "Link's in my bio if you want to try it."],
        "unboxing": [hook, f"Okay, let's open {p} and see what's inside.", f"First use: it helps me {b} right away.",
                     "Honestly, the surprise was how quick it is.", f"If you want one, {p} is linked in my bio."],
        "story": [hook, f"A month ago I couldn't {b}, and it was stressing me out.", f"Then a friend showed me {p}.",
                  f"Now I {b} without even thinking about it.", f"If that sounds like you, try {p}. Link in bio."],
    }[style if style in STYLES else "ai_ad"]
    s = " ".join(lines)
    words = s.split()
    if len(words) > hi * WPS: s = " ".join(words[: int(hi * WPS)]).rstrip(",") + "."
    pads = ["It took me less than a minute to get started.", "Honestly, I wish I'd found it sooner.", f"Seriously, {p} is worth a look.",
            "And it fits right into my day.", "No complicated setup, no fuss.", "I use it every single morning now.",
            "My friends keep asking me what changed.", f"If you've been on the fence, {p} is the push you need.",
            "It does exactly what it says it does.", "And the best part? It saves me real time every day."]
    lo = max(lo, 25); hi = max(hi, lo + 5)
    k = 0
    while len(s.split()) < (lo + 6) * WPS and k < len(pads):
        last = s.rfind(". ", 0, len(s) - 2)  # keep the CTA as the last sentence
        s = (s[:last + 1] + " " + pads[k] + s[last + 1:]) if last > 0 else s + " " + pads[k]; k += 1
    if tags: s += " " + " ".join(t for t in tags if t.startswith("#"))[:0]  # hashtags go in the post caption, not the voiceover
    return s

def gemini_brief(text, style, log=print):
    key = os.environ.get("GEMINI_API_KEY")
    if not key: return None
    model = os.environ.get("AIAC_GEMINI_MODEL", "gemini-flash-latest"); st = STYLES.get(style, STYLES["ai_ad"])
    prompt = ("You help a UGC creator follow a paid campaign brief exactly. From the brief below, reply ONLY JSON: "
              '{"product":str,"benefit":str,"checklist":[short requirement strings, include every must/don\'t rule, hashtags, length, CTA, disclosure],'
              '"hooks":[3 different scroll-stopping first lines, max 12 words each],'
              f'"script":"a {st["label"].lower()} voiceover script, beats: {", ".join(st["beats"])}, 20-45 seconds when spoken (55-110 words), first person, starts with hook 1, follows every rule, no hashtags, no emojis",'
              '"length":[min_seconds,max_seconds]}. Never invent claims the brief does not support.\nBRIEF:\n') + text[:12000]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}}
    try:
        out = json.loads(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=90).read())
        d = json.loads(out["candidates"][0]["content"]["parts"][0]["text"])
        assert d.get("script") and d.get("checklist") and len(d.get("hooks", [])) >= 3
        d["engine"] = "gemini"; d.setdefault("length", [20, 45]); d["tags"] = sorted(set(re.findall(r"(?<!\w)[#@][\w.]{2,30}", text))); return d
    except Exception as e:
        log(f"Gemini failed ({str(e)[:100]}), using the local writer"); return None

def brief(text="", url="", style="ai_ad", log=print):
    src = "text"
    if url:
        page, src = read_url(url, log); text = (text + "\n" + page).strip()
    if len(text.strip()) < 20: raise ValueError("Paste the campaign brief text (or a link) first.")
    d = gemini_brief(text, style, log) or local_brief(text, style)
    d.update(style=style, source=src, words=len(d["script"].split()), est_seconds=round(len(d["script"].split()) / WPS, 1))
    return d

# ---------- TTS ----------
KOKORO_DIR = Path(os.environ.get("AIAC_MODEL_DIR") or ROOT / "models") / "kokoro"
VOICES = {"warm_female": "af_heart", "bright_female": "af_bella", "calm_male": "am_michael", "deep_male": "am_onyx", "british_female": "bf_emma"}

KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"

def _kokoro_dir():
    """Bundled/dev model dir, else a writable per-user dir (installer: %LOCALAPPDATA%) where we download on first use."""
    if (KOKORO_DIR / "kokoro-v1.0.int8.onnx").exists(): return KOKORO_DIR
    return Path(os.environ.get("AIAC_DATA") or ROOT) / "models" / "kokoro"

def ensure_kokoro(log=print):
    d = _kokoro_dir(); d.mkdir(parents=True, exist_ok=True)
    for f in ("kokoro-v1.0.int8.onnx", "voices-v1.0.bin"):
        t = d / f
        if t.exists() and t.stat().st_size > 1_000_000: continue
        log(f"Downloading voice model {f} (first run only, ~{'89' if f.endswith('onnx') else '27'} MB)...")
        try:
            tmp = t.with_suffix(".part"); urllib.request.urlretrieve(KOKORO_URL + f, tmp); tmp.replace(t)
        except Exception as e:
            log(f"Voice model download failed: {e}"); return None
    return d

def _kokoro_python():
    import sys
    for c in (os.environ.get("AIAC_KOKORO_PY"), "/workspace/venv-kokoro/bin/python", sys.executable, shutil.which("python3")):
        if c and Path(c).exists():
            if subprocess.run([c, "-c", "import kokoro_onnx, soundfile"], capture_output=True).returncode == 0: return c
    return None

def tts(text, out_wav, voice="warm_female", speed=1.05, log=print):
    out_wav = Path(out_wav)
    py = _kokoro_python(); kd = ensure_kokoro(log) if py else None
    model = (kd or KOKORO_DIR) / "kokoro-v1.0.int8.onnx"
    if py and model.exists():
        code = ("import sys,json,soundfile as sf;from kokoro_onnx import Kokoro;a=json.loads(sys.argv[1]);"
                "k=Kokoro(a['m'],a['v']);s,sr=k.create(a['t'],voice=a['voice'],speed=a['sp'],lang='en-us');sf.write(a['o'],s,sr)")
        arg = json.dumps({"m": str(model), "v": str(model.parent / "voices-v1.0.bin"), "t": text, "voice": VOICES.get(voice, voice), "sp": speed, "o": str(out_wav)})
        r = subprocess.run([py, "-c", code, arg], capture_output=True, text=True)
        if r.returncode == 0 and out_wav.exists(): return "kokoro"
        log("Kokoro TTS failed: " + r.stderr[-200:])
    pv = next((p for p in [os.environ.get("AIAC_PIPER_VOICE")] if p and Path(p).exists()), None)
    if shutil.which("piper") and pv:
        subprocess.run(["piper", "-m", pv, "-f", str(out_wav)], input=text, text=True, capture_output=True)
        if out_wav.exists(): return "piper"
    if shutil.which("edge-tts"):
        mp3 = out_wav.with_suffix(".mp3")
        subprocess.run(["edge-tts", "--voice", "en-US-AriaNeural", "--text", text, "--write-media", str(mp3)], capture_output=True)
        if mp3.exists(): engine.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), str(out_wav)]); return "edge-tts"
    raise RuntimeError("No text-to-speech engine available. Install the Kokoro voice pack (see README).")

# ---------- faceless render ----------
_FONT = next((f for f in ("/home/box/.fonts/Anton-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf") if Path(f).exists()), None)
def _dt(t): return re.sub(r"[^\w &.!?-]", "", t)[:24].replace(":", " ")
PALETTES = [("0x121212", "0x2A2A2D"), ("0x0d1a0a", "0x3d5c10"), ("0x101820", "0x223a52"), ("0x1a1010", "0x4a2020")]

def _gen_bg(out, dur, k=0, product=""):
    """Original animated backdrop when there's no B-roll: slow moving gradient + soft noise."""
    a, b = PALETTES[k % len(PALETTES)]
    engine.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"gradients=s=720x1280:c0={a}:c1={b}:x0=0:y0=0:x1=720:y1=1280:speed=0.02:d={dur:.2f}:r=30",
                "-vf", "noise=alls=6:allf=t" + (f",drawtext=fontfile={_FONT}:text='{_dt(product)}':fontcolor=white@0.92:fontsize=88:x=(w-tw)/2:y=h*0.30" if product and _FONT else "") + ",format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", str(out)])
    return out

def build_source(broll, audio, out, work, log=print, product=""):
    """Concatenate B-roll (each cover-cropped to 720x1280, looped if short) to the voiceover length; mux audio."""
    dur = engine.duration(audio) + 0.35
    if not broll: broll = [_gen_bg(Path(work) / f"bg{k}.mp4", dur / 3 + 0.5, k, product) for k in range(3)]
    n = len(broll); seg = dur / n; ins, fc = [], []
    for k, p in enumerate(broll):
        ins += ["-stream_loop", "-1", "-i", str(p)]
        fc.append(f"[{k}:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30,trim=0:{seg:.3f},setpts=PTS-STARTPTS[v{k}]")
    fc.append("".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[v]")
    engine.run(["ffmpeg", "-y", "-v", "error", *ins, "-i", str(audio), "-filter_complex", ";".join(fc), "-map", "[v]", "-map", f"{n}:a",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", f"{dur:.3f}", str(out)])
    return Path(out), dur

def render_faceless(outdir, script, hook=None, voice="warm_female", broll=(), stock_query=None, preset="bold_yellow", log=print, product=""):
    outdir = Path(outdir); work = outdir / "work"; work.mkdir(parents=True, exist_ok=True)
    script = re.sub(r"\s+", " ", script).strip()
    if len(script.split()) < 8: raise ValueError("The script is too short. Write at least a couple of sentences.")
    log("writing voiceover"); wav = work / "voice.wav"; eng = tts(script, wav, voice, log=log)
    broll = [Path(b) for b in broll if b and Path(b).exists()]
    if not broll and stock_query and os.environ.get("PEXELS_API_KEY"):
        log("finding stock B-roll")
        for q in [stock_query] + stock_query.split()[:2]:
            try:
                p = engine.pexels_broll(q, work)
                if p and p not in broll: broll.append(p)
            except Exception as e: log(f"stock B-roll failed ({str(e)[:60]})")
            if len(broll) >= 3: break
    dec = []
    for k, b in enumerate(broll):
        (work / f"dec{k}").mkdir(exist_ok=True); dec.append(engine.ensure_decodable(b, work / f"dec{k}", log))
    broll = dec
    log("assembling B-roll"); src, dur = build_source(broll, wav, work / "ugc_source.mp4", work, log, product)
    log("timing captions"); tr = engine.transcribe(src, os.environ.get("AIAC_UGC_MODEL", "base"), "en", log=lambda m: None)
    words = [w for s in tr["segments"] for w in s["words"]]
    clip = {"start": 0.0, "end": dur, "title": (hook or script.split(".")[0])[:70]}
    opts = dict(aspect="9:16", fit="blur", hook=True, keywords=True, emoji=False, remove_fillers=False, remove_pauses=False, preset=preset)
    log("rendering video"); out = outdir / "ugc_9x16.mp4"
    r = engine.render_clip(src, clip, words, out, work, opts)
    r.update(tts=eng, broll=[str(b) for b in broll] or "generated backdrop", title=clip["title"]); return r

# ---------- avatar (pluggable, consent-gated) ----------
AVATAR_PROVIDER = os.environ.get("AIAC_AVATAR_PROVIDER")  # e.g. a future local lip-sync server URL; None = coming soon
