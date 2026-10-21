# Platform export presets

Rendered at 720p-class (to keep every file under the size cap); `native` is the platform's recommended upload size —
set `size` in render opts for full-res. Max duration trims the clip end. Safe zones = share of the frame covered by the app's UI
(top, bottom, left, right), drawn as red hatched areas by the 📐 Safe zones toggle. Values are our own estimates from public
platform specs/creator guides as of 2026 — platforms change these often, verify before relying on them.

| Key | Platform | Aspect | Render | Native | Max dur (s) | FPS | Size cap | Safe top/bottom/left/right |
|---|---|---|---|---|---|---|---|---|
| `tiktok` | 🎵 TikTok | 9:16 | 720x1280 | 1080x1920 | 600 | 30 | 4.9 MB | 10% / 22% / 4% / 16% |
| `reels` | 📸 IG Reels | 9:16 | 720x1280 | 1080x1920 | 180 | 30 | 4.9 MB | 14% / 24% / 4% / 14% |
| `ig_feed` | 🖼️ IG Feed | 4:5 | 720x900 | 1080x1350 | 60 | 30 | 4.9 MB | 0% / 0% / 0% / 0% |
| `ig_stories` | ⭕ IG Stories | 9:16 | 720x1280 | 1080x1920 | 60 | 30 | 4.9 MB | 14% / 20% / 4% / 4% |
| `shorts` | ▶️ YT Shorts | 9:16 | 720x1280 | 1080x1920 | 180 | 30 | 4.9 MB | 12% / 20% / 4% / 16% |
| `youtube` | 📺 YouTube | 16:9 | 1280x720 | 1920x1080 | 43200 | 30 | 4.9 MB | 0% / 12% / 0% / 0% |
| `x` | ✖️ X | 16:9 | 1280x720 | 1280x720 | 140 | 30 | 4.9 MB | 0% / 10% / 0% / 0% |
| `fb_reels` | 📘 FB Reels | 9:16 | 720x1280 | 1080x1920 | 90 | 30 | 4.9 MB | 14% / 35% / 4% / 14% |
| `linkedin` | 💼 LinkedIn | 1:1 | 720x720 | 1080x1080 | 600 | 30 | 4.9 MB | 0% / 8% / 0% / 0% |
| `snapchat` | 👻 Spotlight | 9:16 | 720x1280 | 1080x1920 | 60 | 30 | 4.9 MB | 10% / 20% / 4% / 12% |
| `pinterest` | 📌 Pinterest | 9:16 | 720x1280 | 1080x1920 | 60 | 30 | 4.9 MB | 10% / 20% / 4% / 4% |
| `threads` | 🧵 Threads | 4:5 | 720x900 | 1080x1350 | 300 | 30 | 4.9 MB | 0% / 0% / 0% / 0% |
| `bilibili` | 📼 Bilibili | 16:9 | 1280x720 | 1920x1080 | 600 | 30 | 4.9 MB | 0% / 10% / 0% / 0% |
| `douyin` | 🎶 Douyin | 9:16 | 720x1280 | 1080x1920 | 900 | 30 | 4.9 MB | 10% / 22% / 4% / 16% |
| `kuaishou` | ⚡ Kuaishou | 9:16 | 720x1280 | 1080x1920 | 600 | 30 | 4.9 MB | 10% / 22% / 4% / 16% |
| `kwai` | 🟠 Kwai | 9:16 | 720x1280 | 1080x1920 | 600 | 30 | 4.9 MB | 10% / 22% / 4% / 16% |
| `likee` | 💗 Likee | 9:16 | 720x1280 | 1080x1920 | 300 | 30 | 4.9 MB | 10% / 22% / 4% / 16% |
| `vk_clips` | 🔵 VK Clips | 9:16 | 720x1280 | 1080x1920 | 180 | 30 | 4.9 MB | 10% / 22% / 4% / 16% |
| `triller` | 🎤 Triller | 9:16 | 720x1280 | 1080x1920 | 600 | 30 | 4.9 MB | 10% / 22% / 4% / 16% |

Bitrate: video = (size cap × 8 000 × 0.88 / duration) − 96 kbit/s (AAC 96k audio), maxrate 1.3×, H.264 High, yuv420p, faststart.
Multi-export: UI 📤 Platforms (multi-select chips) → one zip; API `POST /api/jobs/{id}/clips/{n}/export {"platforms":[...]}`;
CLI `--platforms tiktok reels shorts`; MCP tool `export_platforms`. Note: Instagram Feed and Threads use 4:5; LinkedIn 1:1; YouTube/X/Bilibili 16:9.
