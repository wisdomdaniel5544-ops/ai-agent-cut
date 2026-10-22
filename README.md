# AI Agent Cut

> **Founded by Wisdom Daniel — Founder & CEO, AI Agent Cut**
> [X / @WisdomD64553](https://x.com/WisdomD64553) · [LinkedIn](https://www.linkedin.com/in/wisdom-daniel-a2002a2b4/) · Contact: [aiagentcutapp@gmail.com](mailto:aiagentcutapp@gmail.com)

Long video (file or URL) → 3–5 vertical 720x1280 MP4 clips with word-by-word burned captions. Everything runs locally.

## Pipeline (`aiagentcut/engine.py`)
1. **Fetch**: local file, or URL via yt-dlp (≤720p).
2. **Silence cut**: ffmpeg `silencedetect` (−32 dB, ≥0.6 s, 0.15 s margin), then select/aselect re-encode. (auto-editor can replace this later.)
3. **Transcribe**: faster-whisper (`small`, int8, CPU), word timestamps, VAD. Audio decoded by ffmpeg.
4. **Pick clips**: every 30–60 s window on segment boundaries is scored by `heuristic_scorer` (hook words, questions, strong opener, speech rate, audio RMS energy, clean sentence end); greedy non-overlap top N.
   **LLM slot**: pass `scorer=fn(text, segments, energy) -> float` to `process()`/`pick_clips()`.
5. **Reframe 9:16**: OpenCV YuNet face detector sampled at 3 fps → interpolated, smoothed, dead-zoned crop path; falls back to center crop if no faces.
6. **Captions**: ASS subtitles, 2–4 word groups, current word highlighted + pop. Presets: `bold_yellow`, `clean_white` (boxed), `neon_pop`.
7. **Export**: H.264/AAC 720x1280, bitrate budgeted to keep each clip < 4.9 MB, faststart.

## Install (Linux / macOS / Windows)
```
# ffmpeg must be on PATH
pip install -r requirements.txt
```
The whisper model downloads on first run (~500 MB for `small`; use `-m tiny` for speed).

## Run
CLI:
```
python -m aiagentcut input/talk.mp4 -o output -n 4 -p bold_yellow
python -m aiagentcut "https://www.youtube.com/watch?v=..." -p neon_pop -m base
```
Outputs `output/clip_NN_<preset>.mp4` + `output/report.json` (+ `output/work/` with transcript.json, cut.mp4, .ass files).

Web UI:
```
python -m aiagentcut.server     # http://127.0.0.1:8765
```
Upload a file or paste a URL, choose clip count/style/model, preview and download clips. Jobs saved in `jobs/`.

## Licenses
Own code. Uses ffmpeg (LGPL/GPL binary, called as a separate process), faster-whisper (MIT), OpenCV + YuNet model (Apache-2.0 / MIT), yt-dlp (Unlicense), FastAPI/uvicorn (MIT/BSD). No code from any commercial app.

## v1 additions
- Clip windows from **word-level** sentence units (punctuation/pauses), min length relaxes until N clips found.
- **Virality 0–100 + reason** per clip (hook, flow, value, pace, energy, filler penalty); clips sorted by score.
- **Hook title** overlay (top, first 3 s). **Keyword colours** + optional **emoji** (Noto Color Emoji, OFL).
- **Blurred-background fit** (`--fit blur`, auto when no face). **Aspects** `-a 9:16|1:1|16:9`.
- **Filler removal** (um/uh… cut from video, audio, captions; `--keep-fillers` to disable).
- **Caption edit**: `GET/POST /api/jobs/{id}/clips/{n}/words` `{"words":[...], "title":"..."}` → re-render; UI ✏️ Edit.
- **Optional LLM scorer** (off by default): `AIAC_LLM=ollama` (`AIAC_OLLAMA_MODEL`, `AIAC_OLLAMA_URL`) or `AIAC_LLM=gemini` (`GEMINI_API_KEY`).
- Mobile-first 3-step PWA UI (`web/`), MCP server (PRO): `python -m aiagentcut.mcp_server [--http 8766]`
  (needs `pip install mcp`; a venv with it is at `.venv/`). Tools: list_projects, find_clips, render_clip, make_clips,
  get_captions, edit_captions, get_project.
- Docs: `parity.md`, `brand.md`, `android.md`.

## v2 additions
- **Any link**: YouTube, X, TikTok, Instagram, Facebook, Bilibili, Vimeo, Twitch VODs, Rumble (anything yt-dlp supports), Google Drive /
  Dropbox share links, direct MP4. Several YouTube player clients are tried; `--cookies cookies.txt` or `AIAC_COOKIES` for login-only
  videos. **YouTube often rate-limits (HTTP 429 / "sign in to confirm") data-centre/server IPs** — then upload the file or use cookies.
- **Long uploads**: resumable 8 MB chunked upload (`POST /api/uploads`, `PUT /api/uploads/{id}?offset=`, `GET` to resume); job takes `upload_id`.
  Transcription streams with % progress.
- Pre-trim (`--trim S E`), Find-a-moment prompt (`--prompt`), genre (`--genre`), clip length, language (`--lang`), SRT (`--srt`).
- Score detail (hook/flow/value/trend), safe-zone overlay, 4:5, `--pauses`.
- Brand Template (`templates/brand.json`, UI 🎨 Brand): font, colours, stroke, position, layout, logo, intro/outro, music, vocabulary, censor list.
  Example: `templates/test_brand.json`.
- Transcript editing API: `GET /api/jobs/{id}/transcript`, `POST /api/jobs/{id}/clips/{n}/sections {"remove":[[s,e]],"add":[[s,e]]}`.
- B-roll: `--broll auto|"prompt"` (needs `PEXELS_API_KEY`, else skipped) or `--broll-file clip.mp4`.
- Export: `--xml` / `GET /api/jobs/{id}/clips/{n}/xml?kind=fcpxml|xmeml`; platform presets (`presets.md`) → zip via `--platforms` or UI 📤.
- MCP adds: edit_sections, export_platforms, export_xml; find_clips takes prompt/genre.

## v3 UI (web/index.html)
New dark UI and logo (see `brand.md`). Mobile: intro → onboarding → sign-in → Projects / Learn / + sheet / Profile;
desktop: sidebar + top bar + tool tiles. The previous full editor is at `/classic` (word editing, platform packs, brand templates).
Screenshots and the logo intro video: `samples/v3/`.

New endpoints in `aiagentcut/server.py`:
- `GET /api/projects` — past jobs for the home grid.
- `POST /api/auth/local` — **stub sign-in**. No OAuth is configured: "Continue with Google" and "Continue with email"
  only create a local profile in the browser (no password, no verification).
- `POST /api/leads` `{email, source}` — "Get free clipping tips" sign-ups (after sign-in and on Learn).
  **Leads are stored in `<data dir>/leads/leads.json` and `<data dir>/leads/leads.csv`** (data dir = `AIAC_DATA`, else the repo root;
  `%LOCALAPPDATA%` on the Windows installer). De-duplicated by email. Nothing is emailed yet; Gmail delivery comes later.
- `GET/POST /api/ai-keys` — Connect AI. The Gemini key is saved in `<data dir>/ai_keys.json` (chmod 600, accepted from localhost only)
  and turns on `AIAC_LLM=gemini` scoring/hooks. ElevenLabs, Grok and Manus keys are kept only in the browser's localStorage
  and marked "coming soon" — not used by the backend yet.
- Pricing / Ultra Pro checkout, credits counting and Google Drive import are UI-only for now.
