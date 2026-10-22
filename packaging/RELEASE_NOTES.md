## AI Agent Cut 3.0 — Long video in. Viral clips out.

**New look:** dark UI, new logo and launch intro, onboarding, Google/email sign-in (local profile), Projects home, a + sheet to paste a link or pick a video, Learn tab, Connect AI (bring your own Gemini key), pricing and About.

**Fixes and speed**
- Fixed: YouTube AV1 videos crashed every render. They now download as H.264 or get converted automatically.
- Fixed: silence removal crashed on long videos (out of memory). It is now audio-only and about 60x faster.
- Fixed: jobs started from the new UI/API ran with hook titles, captions colours and filler/silence cutting switched off.
- About 2x faster transcription on long videos, parallel clip renders and exports: a 56-min podcast went from 365 s to ~230 s on 8 CPU cores.
- Clear error messages with what to do next, monotonic progress, auto-retry of a failed render.

**Downloads**
- Windows 10/11 (64-bit): `AIAgentCut-Setup.exe`. Windows may show "Windows protected your PC": More info → Run anyway.
- Android: `AIAgentCut.apk`. It connects to AI Agent Cut on your PC over the same Wi-Fi (Profile → Clipping server).

MIT licensed. Third-party licenses: THIRD_PARTY_LICENSES.md and LICENSE-NOTICES.txt (FFmpeg in the Windows build is GPL; source links included).
