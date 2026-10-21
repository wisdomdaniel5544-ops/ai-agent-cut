# Feature parity: AI AGENT CUT vs. the market-leading AI clipper

Source of the feature list: full auto-caption transcript of the public tutorial https://youtu.be/dvO5NsYovM4
(saved: `/workspace/app-research/opus_transcript.txt`, raw VTT `research/opus.en.vtt`) plus the vendor's public
pricing / help pages (virality score, captions & emojis, AI reframe). Only public behaviour was studied — no code,
assets, models or UI were copied. Status: ✅ done · 🟡 partial · ❌ missing.

| # | Feature (as publicly described) | Our status | Where / notes |
|---|---|---|---|
| 1 | Import by link or upload | ✅ | v2: any yt-dlp site + Drive/Dropbox/direct MP4, client fallbacks, cookies, friendly errors; resumable 8 MB chunked upload |
| 2 | Language select / multi-language transcription | ✅ | v2: language picker (auto + 17 shown; any whisper code via API/CLI `--lang`) |
| 3 | Upload own SRT | ✅ | v2: SRT upload (UI/`--srt`), skips transcription; word times spread inside each cue |
| 4 | Clip model "auto / basic / anything" (non-talking footage, visual cues) | 🟡 | speech-based only; no visual/scene understanding |
| 5 | Genre hint (Q&A, podcast…) | ✅ | v2: 8 genres re-weight hook/flow/value/trend/pace |
| 6 | Clip length presets | ✅ | v2 UI chips: Auto, <30s, 30–60s, 60–90s, 1.5–3m (any via API); 15-min not offered in UI |
| 7 | Prompt "find a moment" | 🟡 | v2: keyword-match relevance filters + 50% of score; semantic match needs LLM/embeddings |
| 8 | Processing timeframe (pre-trim) | ✅ | v2: dual slider with "Saves m:ss", stream-copy trim |
| 9 | Clip windows on clean sentence boundaries | ✅ | v1 uses **word-level** sentence units + relaxing min length (fixes "fewer clips") |
| 10 | Virality score + why (hook/flow/value/trend) | ✅ | v2: tap score → bars for hook/flow/value/trend (+prompt) and reason. Trend = static topic list, not live trends |
| 11 | Optional LLM scoring | ✅ | `AIAC_LLM=ollama` or `gemini` env (off by default), returns score/reason/title |
| 12 | Auto hook (headline text on screen at start) | ✅ | white box title, top, first 3 s, fade; editable |
| 13 | AI rewrite title / description / hashtags | 🟡 | title via LLM slot; no description/hashtag generator |
| 14 | Animated caption templates (karaoke etc.) | ✅ | 3 presets: bold_yellow, clean_white, neon_pop (word highlight + pop) |
| 15 | Font / size / stroke / colours / position controls | ✅ | v2 Brand Template sheet (font, size, 4 colours, stroke, position); weight/italic/shadow only via JSON |
| 16 | Keyword highlight colour | ✅ | keyword detector + per-preset colour |
| 17 | Auto emoji | ✅ | Noto Color Emoji (OFL) rendered via Pillow, popped above captions |
| 18 | Speaker-based caption colours | ❌ | needs diarization (pyannote, MIT) |
| 19 | Censor words / brand vocabulary | ✅ | v2: vocab `wrong=Right` fixes transcript; censor list → bleep tone + masked caption (p*****) |
| 20 | Transcript-based editing | ✅/🟡 | v2: edit words + title; 🗑 delete sentences; ➕ add sections from full transcript. No per-word timing handles |
| 21 | Remove filler words | ✅ | um/uh/erm… cut from video+audio and captions |
| 22 | Remove pauses | ✅ | silence cut toggle + v2 "cut every pause" (>0.5 s gaps inside clips) |
| 23 | Aspect ratios 9:16 / 4:5 / 1:1 / 16:9 | ✅ | v2 adds 4:5 + 19 platform presets (presets.md), multi-export zip |
| 24 | Face-tracking reframe | ✅ | YuNet face track, smoothed + dead-zone |
| 25 | Fit layout with blurred top/bottom | ✅ | `fit=blur`, auto when no face (slides/screens) |
| 26 | Split-screen / 3-4 speaker / gameplay / screenshare layouts | ❌ | next: two-face split when 2 faces detected |
| 27 | Moving-object tracking (non-face) | ❌ | could use OpenCV trackers / saliency |
| 28 | Manual reframe / zoom per segment, split clip at playhead | ❌ | needs timeline editor |
| 29 | Timeline editor, extend clip with other sections | ❌ | |
| 30 | Stock / AI B-roll | 🟡 | v2: Pexels stock by prompt or auto-keywords (needs PEXELS_API_KEY; untested live — no key) or user clip; AI-generated B-roll ❌ |
| 31 | Transitions | ❌ | ffmpeg xfade |
| 32 | Logo, intro/outro, music | ✅ | v2: from Brand Template; music is user-provided (looped, ducked to 10–12%) |
| 33 | Brand templates (saved) | 🟡 | v2: one saved brand applied to every job (toggle); multiple named templates ❌ |
| 34 | AI voice-over hook | ❌ | Piper TTS (MIT) possible |
| 35 | Export MP4 (watermark-free) | ✅ | ≤4.9 MB H.264, no watermark on free tier |
| 36 | Export XML for Premiere / Resolve / FCP | ✅ | v2: FCPXML 1.9 + xmeml v4 (cuts only; captions/overlays not in XML) |
| 37 | Social scheduler / auto-post / analytics | ❌ | out of scope (APIs + review) |
| 38 | Auto-import new YouTube uploads | ❌ | RSS poll + yt-dlp |
| 39 | Teams / workspaces | ❌ | |
| 40 | API / MCP connector | ✅ | `aiagentcut/mcp_server.py` (stdio + streamable HTTP) — PRO |
| 42 | Safe-zone guide in preview | ✅ | v2: per-platform hatched overlay toggle |
| 41 | Mobile app | 🟡 | mobile-first PWA web UI; Android plan in `android.md` |

**v2 count (42 rows):** 25 ✅ · 7 🟡 (incl. one ✅/🟡) · 10 ❌. Remaining gaps: visual (non-speech) clip finding, split/multi-speaker layouts, object tracking, timeline editor & manual
reframe, AI B-roll, transitions, speaker colours, AI voice-over, scheduler/auto-post/analytics, auto-import, teams.
