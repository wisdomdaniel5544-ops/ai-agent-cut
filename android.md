# Android plan — AI AGENT ✚ CUT

UX is identical to the mobile web app (`web/index.html`): 3 steps (Add → Clip → Export), one big thumb button,
chips not dropdowns, defaults that need no settings, inline previews, share-sheet export.

## Phase 1 (fastest, recommended): PWA + Trusted Web Activity
- The web UI is already mobile-first and installable: `web/manifest.webmanifest`, `web/sw.js`, `web/static/icon*.{svg,png}`.
- Host the FastAPI backend (GPU or 8-core CPU box) behind HTTPS + auth (`python -m aiagentcut.server` behind a proxy;
  job storage in object storage with 3-day expiry for free tier).
- Wrap with **Bubblewrap** (Apache-2.0) → TWA `.aab`; add `assetlinks.json` at `/.well-known/` for verified full-screen.
- Android extras via Web APIs: `<input type=file accept=video/*>` opens the gallery; **Web Share Target** in the
  manifest so users can "Share → AgentCut" a YouTube link; `navigator.share()` for exporting a finished clip.
- Pros: one codebase, ships in days. Cons: needs network + server cost.

## Phase 2: Capacitor app (native polish)
- **Capacitor** (MIT) loading the same web UI; plugins: Filesystem, Share, Camera/Media picker, Local/Push Notifications
  ("Your clips are ready 🔥"), background upload with resumable chunks (tus protocol).
- Still calls the hosted backend for transcription + rendering. Store listing copy in `brand.md`.

## Phase 3: on-device (offline / privacy mode)
- Transcription: **whisper.cpp** (MIT) Android build with `tiny`/`base` int8 models (~75–150 MB) or Vosk (Apache-2.0).
- Face detection: YuNet via OpenCV Android (Apache-2.0) or ML Kit face detection.
- Render: **FFmpegKit** is retired upstream (2025) — use a maintained fork or build ffmpeg with `libass` + `libx264`
  ourselves (mind GPL/LGPL: libx264 is GPL → prefer MediaCodec H.264 encoder via Media3 Transformer, keeping ffmpeg LGPL).
- Captions: render ASS with libass, or draw on Media3 `OverlayEffect` (Kotlin port of `build_ass` logic).
- Port the scoring heuristics (`virality`, `sentences`, `hook_title`) to Kotlin — they are pure functions.
- Expect 1–3 min per clip on a mid-range phone; offer "cloud boost" as fallback.

## Release checklist
Privacy policy (video stays on device / auto-deleted on server), Data-safety form, content rating, 512 px icon,
feature graphic 1024×500 in brand colours, 4+ phone screenshots, internal → closed → production tracks.
