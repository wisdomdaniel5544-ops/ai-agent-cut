# IMPROVEMENTS — v3 robustness & speed pass (2026-10-22)

Test machine: the build box (8 vCPU, 15 GB RAM, no GPU). Test inputs: a 56-min public YouTube podcast
(`oopwD8yoYqQ`, "Open Commons Ep. 3"), the same file uploaded locally (217 MB), a 4-min AV1 file, a corrupt file, a dead link,
and the 4.5-min `input/talk.mp4` through the v3 UI with Playwright. Harnesses: `tests/e2e.py` (HTTP API: upload or link → clips →
caption edit → 3-platform export) and `tests/ui_e2e.py` (Playwright: onboarding → sign-in → + sheet → Gallery upload → clips).
Raw results: `tests/results/*.json`.

## Bugs found and fixed
| # | Severity | Bug | Fix |
|---|---|---|---|
| 1 | Crash | YouTube now serves **AV1**; OpenCV's FFmpeg can't decode AV1 on CPU → every clip render died with `Could not open encoder before EOF` (0 clips). Same for AV1 uploads. | yt-dlp format sort prefers H.264 (`-S vcodec:h264`), plus `ensure_decodable()` transcodes once to H.264 when the first frame can't be read (uploads and links, MCP too). |
| 2 | Crash | Silence cut built one giant `select=between(...)+...` expression and re-encoded the whole video: `Cannot allocate memory` on the 56-min input, and ~3 s per minute of video even when it worked. | New `detect_silences()` runs audio-only `silencedetect`; silences are skipped per clip at render time (`timeline(..., silences=)`). No full re-encode. |
| 3 | Silent wrong output | FastAPI ≥0.150 turns a **missing** bool form field into `False`, so jobs from the v3 UI/API/MCP clients ran with hook titles, keyword colours, filler cut, silence cut and brand **all off**. | Bools are parsed explicitly with their real defaults in `POST /api/jobs`. |
| 4 | API error | `POST /clips/{i}/words` with a string gave "expected 186 words, got 1004". | Accepts a list or a space-separated string. |
| 5 | Stale tool | Box had yt-dlp 2026.08.19 (YouTube extraction breaks often). | Upgraded to 2026.10.21; keep it updated in releases. |
| 6 | UX | Progress sat at 2% during download, jumped around, errors showed raw ffmpeg stderr. | Monotonic server-side progress for every stage; `friendly_error()` gives a plain message + next step (UI shows it); UI poll retries on network drops. |
| 7 | Reliability | One failed render killed the job. | Each clip render retries once, then fails with "clip N failed to render". |
| 8 | Phone app | APK only showed a "connect" page; v3 UI not in the app. | v3 UI bundled in the APK; `API_BASE` shim sends API calls to the saved PC server (Profile → Clipping server). |

## Speed (56-min YouTube podcast, 3 clips, full flow)
| Stage | Before (crash-fixed only) | After | Change |
|---|---|---|---|
| Download | 17–42 s (network) | 20–42 s | +4 concurrent fragments; network-bound |
| Silence handling | crashed (old re-encode: 12.9 s for 4.5 min → ~2.7 min/hour) | 2.6 s detect for 56 min | ~60x |
| Transcription (small, int8) | 277 s | 137–150 s | **~2x** (BatchedInferencePipeline for inputs >10 min, all cores, model cached across jobs) |
| Render 3 clips | 48 s (sequential, x264 medium) | 33–40 s | parallel renders (cores/3) + x264 veryfast |
| Export to 3 platforms | 52 s | 39–43 s | parallel |
| **Whole job** | 365 s (after crash fixes; before them it crashed) | **229–236 s** | **~35% faster** |

## Repos evaluated (GitHub API, 2026-10-22)
| Repo | Stars | License | Last push / release | Decision |
|---|---|---|---|---|
| SYSTRAN/faster-whisper | 26.0k | MIT | 2026-10-16 / v1.2.1 | **Adopted** (already used) + BatchedInferencePipeline |
| yt-dlp/yt-dlp | 200k | Unlicense | 2026-10-21 / 2026.10.21 | **Adopted** (upgraded) |
| opencv (YuNet via opencv_zoo) | 1.1k zoo | Apache-2.0 / MIT model | 2026-10-20 | **Kept** for face tracking |
| m-bain/whisperX | 24.8k | BSD-2 | 2026-10-18 / v3.8.6 | Not adopted: PyTorch + pyannote (~2 GB), GPU-oriented |
| ggml-org/whisper.cpp | 54.5k | MIT | 2026-10-19 | Later: on-device Android mode |
| Breakthrough/PySceneDetect | 5.3k | BSD-3 | 2026-10-22 / v0.7.2 | Candidate for scene-aware cuts/B-roll |
| google-ai-edge/mediapipe | 37.4k | Apache-2.0 | 2026-10-22 | Not needed yet (YuNet is good on CPU) |
| WyattBlue/auto-editor | 5.6k | Unlicense | 2026-10-22 / 31.7.2 | Idea used (audio-only silence detection) via ffmpeg directly |
| snakers4/silero-vad | 10.5k | MIT | 2026-10-22 / v6.2.3 | Used indirectly by faster-whisper |
| rq/rq, celery/celery | 10.7k / 29k | BSD-2 / BSD-3 | active | Not needed for single-user local app; revisit for hosted mode |
| mutonby/openshorts | 7.0k | MIT | 2026-10-20 | Reviewed only; no code copied |
| Zulko/moviepy | 15k | MIT | 2026-08-26 | Not needed (ffmpeg pipeline is faster) |
| mifi/lossless-cut | 44.9k | **GPL-2.0** | active | Avoid bundling |
| linto-ai/whisper-timestamped | 2.9k | **AGPL-3.0** | active | Avoid |

X search for repo recommendations only returned generic "10 free AI tools" listicles with no specific, verifiable repos,
so nothing was taken from X. No crypto/"cracked" repos used; no proprietary code copied.

## Still left
- **FFmpeg licence in the Windows installer:** it bundles the BtbN *GPL* build (libx264). OK as a separate executable, but the
  release must link the FFmpeg source; or switch to an LGPL build + OpenH264/hardware encoder.
- Caption fonts (Anton, Bebas Neue, Montserrat Alternates, OFL) are not bundled; installs without them fall back to a default font.
- Transcription is still the slowest stage (~2.5 min per hour of video on 8 CPU cores). Options: `base`/`distil` model toggle, GPU (CUDA) path.
- Face tracking seeks per sample (`cap.set`) which is slow on long-GOP files; switch to sequential grab.
- Upload is resumable on the server, but the UI doesn't resume after a page reload yet.
- Jobs live in memory + `jobs/`; a server restart mid-job loses that job (needs a small persistent queue).
- The box rebooted once during a long run (cause unknown, peak use stayed under 13 GB); watch memory with 2 parallel renders on 8 GB PCs (`AIAC_RENDER_WORKERS=1`).
- Google sign-in, checkout, credits, Google Drive import are still stubs.
