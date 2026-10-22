# Third-party licenses — AI Agent Cut

AI Agent Cut's own code is **MIT** (see `LICENSE`).

> **License choice note:** MIT is the right default for an open-source app that wants adoption. If you'd rather
> stop others from taking the code into a closed hosted service, relicense future versions under **AGPL-3.0**
> (anyone who runs a modified version as a service must publish their changes). That decision is reversible only
> for future releases; versions already published as MIT stay MIT.

No code from proprietary products (e.g. Opus Clip) is included. All third-party code below is used as a library
or a separate executable, unmodified.

## Python runtime dependencies (installed via pip / bundled in the Windows installer)
| Package | Version tested | License | Used for |
|---|---|---|---|
| faster-whisper (SYSTRAN) | 1.2.1 | MIT | Speech-to-text with word timestamps; BatchedInferencePipeline for long videos |
| CTranslate2 | 4.8.3 | MIT | Inference engine behind faster-whisper |
| PyAV (av) | 19.0.1 | BSD-3-Clause | Pulled in by faster-whisper (we decode audio with the ffmpeg CLI instead) |
| onnxruntime | 1.31.0 | MIT | Silero VAD inside faster-whisper |
| tokenizers (Hugging Face) | 0.23.3 | Apache-2.0 | Whisper tokenizer |
| huggingface_hub | 2.2.0 | Apache-2.0 | First-run model download |
| numpy | 2.5.4 | BSD-3-Clause | Audio / frame arrays |
| opencv-python-headless | 5.0.0 | Apache-2.0 (wheel bundles an LGPL FFmpeg build, dynamically loaded) | Frame reading, YuNet face detection, resizing |
| Pillow | system | MIT-CMU (HPND) | Emoji rendering |
| FastAPI | 0.156 | MIT | HTTP API |
| Starlette | 1.9 | BSD-3-Clause | ASGI toolkit under FastAPI |
| Pydantic | 2.14 | MIT | Request validation |
| Uvicorn | 0.54 | BSD-3-Clause | Web server |
| python-multipart | 0.0.32 | Apache-2.0 | Form / file uploads |
| yt-dlp | 2026.10.21 | Unlicense (public domain) | Downloading links (YouTube, X, TikTok, Drive...) |
| mcp (Model Context Protocol SDK) | latest | MIT | MCP server for AI agents (Ultra Pro) |

## Models and data
| Item | License | Notes |
|---|---|---|
| Whisper weights (OpenAI), CTranslate2 conversions by Systran (`Systran/faster-whisper-*`) | MIT | Downloaded on first run or bundled in the installer |
| Silero VAD (via faster-whisper) | MIT | |
| YuNet face detector `face_detection_yunet_2023mar.onnx` (OpenCV Zoo) | MIT | In `models/` |
| Noto Color Emoji (system font) | OFL-1.1 | Emoji overlays, not bundled |
| Caption fonts Anton, Bebas Neue, Montserrat Alternates | OFL-1.1 | Used if installed on the system; not bundled yet |

## Executables (separate processes)
| Tool | License | Notes |
|---|---|---|
| FFmpeg / ffprobe | LGPL-2.1+, **GPL-2.0+ when built with libx264** | Called as a separate program. The Windows installer currently ships the BtbN **GPL** build (needed for libx264). Shipping it is allowed if you also offer the corresponding FFmpeg source (link to the exact BtbN release + FFmpeg source) — see `LICENSE-NOTICES.txt`. Our MIT code is not affected because FFmpeg runs as a separate executable. |
| libass (inside FFmpeg) | ISC | Burned-in animated captions |
| x264 (inside the GPL FFmpeg build) | GPL-2.0+ | H.264 encoding. LGPL alternative: hardware encoders or OpenH264 (BSD) |

## Android app (Capacitor wrapper)
| Package | License |
|---|---|
| @capacitor/core, @capacitor/android, @capacitor/cli 7.x | MIT |
| AndroidX / Gradle Android plugin | Apache-2.0 |

## Windows installer
| Item | License |
|---|---|
| CPython 3.12 embeddable | PSF-2.0 |
| NSIS (build tool only, its stub is in the .exe) | zlib/libpng + bzip2 + CPL (installer stub permits redistribution) |

## Evaluated but NOT bundled
| Project | License | Why not |
|---|---|---|
| whisperX | BSD-2-Clause | Needs PyTorch + pyannote (~2 GB, GPU-oriented); faster-whisper's batched pipeline gives most of the CPU speed-up |
| whisper.cpp | MIT | Good for the future on-device Android mode; not needed on desktop |
| PySceneDetect | BSD-3-Clause | Candidate for B-roll/scene boundaries; not adopted yet (clip windows follow sentences) |
| MediaPipe | Apache-2.0 | YuNet already tracks faces well enough on CPU; MediaPipe adds ~30 MB |
| auto-editor | Unlicense | We do the same silence detection with ffmpeg's silencedetect directly |
| RQ / Celery / Huey | BSD-2 / BSD-3 / MIT | Not needed for a single-user local app; thread pool is enough |
| LosslessCut | GPL-2.0 | GPL desktop app; ideas only, no code |
| whisper-timestamped | **AGPL-3.0** | Avoided (copyleft over network use) |

## UGC mode (v4, unreleased)
- **Kokoro-82M** weights (hexgrad): Apache-2.0. Used offline for UGC voiceovers. These are model files, downloaded to `models/kokoro/` and not committed.
- **kokoro-onnx**: MIT. It runs in a separate venv subprocess.
- **espeak-ng / espeakng-loader** (pulled in by kokoro-onnx for phonemes): GPL-3.0. It runs as an isolated subprocess and is not linked into the app's code.
- **edge-tts** (fallback): LGPL-3.0 library. It calls Microsoft's online TTS service, so that service's terms apply.
- **Piper** is optional and supported only through the user's own install (AIAC_PIPER_VOICE). piper1-gpl is GPL-3.0 and is not bundled.
- **Firecrawl** and **Pexels** are external APIs. They are used only with the user's own keys.
