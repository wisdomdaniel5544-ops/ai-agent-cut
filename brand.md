# Brand — AI AGENT ✚ CUT

What we learned from how the market leader markets itself (public tutorial video + site, studied, not copied):
one-promise headline ("long video → viral shorts in 1 click"), a number on every clip (virality score) that makes
results feel *measurable*, a free tier to get people in, product demos that show the result in the first seconds,
and a creator-to-creator tone ("you want this on, because people watch without sound"). We keep those *principles*
and build our own identity around **agents** and **ownership** (runs locally, no watermark, agent-drivable).

## Name & wordmark
**AI AGENT ✚ CUT** — written `AI AGENT` (white) + `✚` (coral) + `CUT` (lime). Short name / app icon label: **AgentCut**.
The ✚ reads as "agent *plus* cut" and doubles as a cut mark. Never use other brands' marks, names or colours.

## Tagline
- Primary: **Long video in. Viral clips out.**
- Alt: *Your clipping agent. Free, no watermark.* · *Clip like a pro. Let the agent do the boring part.*

## Colours (playful but clean, high-contrast for small screens)
| Role | Hex |
|---|---|
| Ink (background) | `#0E0F13` |
| Card | `#181A21` |
| Lime (primary action, scores) | `#C6FF3D` |
| Violet (selected / gradients) | `#7B61FF` |
| Coral (✚, alerts, accents) | `#FF5A5F` |
| Soft grey text | `#9AA0AE` |

Type: system UI for the app (fast, native feel); Anton / Montserrat ExtraBold for captions & promo titles (OFL fonts).

## Logo idea
A friendly rounded robot head (violet) with two lime "eye" dots and a coral antenna, sitting above a pair of lime
scissor blades crossing into an ✚. Works at 48 px. File: `web/static/icon.svg` (+ `icon-512.png`).

## Voice
Short, warm, emoji-light, zero jargon. Verbs first: *Add. Clip. Export.* Celebrate results ("🔥 86 — strong hook").
Never shame the user; errors say what to do next.

## UX principles (applied in `web/index.html`)
1. **3 steps only**: ① Add (tap to pick / paste link) → ② Clip (one progress bar with plain words) → ③ Export (Save / Edit).
2. **One giant button** at thumb height. Everything else optional, hidden under "⚙️ More".
3. **Sensible defaults**: 9:16, 3 clips, Bold style, hook title + keyword colours + um/uh removal ON. Zero settings needed.
4. **Icons + 1–2 words** on every control; big chips (≥44 px) instead of dropdowns.
5. **Instant preview**: clips play inline, sorted by score, with a one-line "why".
6. Edit = type over the words, tap 🔁 Update.

## Landing page copy
> **Long video in. Viral clips out.** ✂️🤖
> Drop a podcast, stream or talk. AI AGENT ✚ CUT finds the moments people will stop scrolling for, frames the
> speaker, adds bold animated captions and a hook title — in minutes.
> **[ ✂️ Make my first clips — free ]**
>
> 🔥 **Every clip gets a score** — know which one to post first, and why.
> 🪝 **Hook titles** that work with the sound off.
> 🌈 **Captions that pop** — word-by-word, keyword colours, emoji.
> 🙂 **Always in frame** — face tracking, or a clean blurred fit for slides & screens.
> 🤐 **No "um", no dead air** — fillers and silences cut automatically.
> 📱 **9:16 · 1:1 · 16:9** in one tap.
> 🆓 **Free forever: no watermark.** Clip, caption, reframe, export.
> 🤖 **PRO: plug it into your AI agents** — our MCP server lets Claude-style agents find, render and edit clips for you, on autopilot.
>
> *Want to turn clipping into income?* Learn the full agent workflow → https://whop.com/ai-agents-for-clippers-marketers/

## Tiers
| | FREE (giveaway) | PRO |
|---|---|---|
| Clips from upload or link | ✅ | ✅ |
| Virality score + reason, hook title | ✅ | ✅ + LLM scoring (Ollama/Gemini) |
| Animated captions, keyword colours, emoji, edit words | ✅ | ✅ |
| Face reframe / blur-fit, 9:16 · 1:1 · 16:9 | ✅ | ✅ |
| Filler + silence removal | ✅ | ✅ |
| Export MP4, **no watermark** | ✅ | ✅ |
| **MCP server** (agents drive the app: find_clips, render_clip, make_clips, edit_captions, list_projects…) | — | ✅ |
| Batch / auto-import, priority rendering (roadmap) | — | ✅ |

## Google Play listing
- **Title (≤30):** AI AGENT CUT: Viral Clip Maker
- **Short description (≤80):** Turn long videos into viral shorts with captions & hooks. Free, no watermark.
- **Full description:**
  Turn one long video into scroll-stopping shorts in 3 taps. ✂️
  ① Add a video or paste a link ② Tap Make clips ③ Save or share.
  • 🔥 Virality score on every clip, with the reason
  • 🪝 Auto hook title for the first seconds
  • 🌈 Animated word-by-word captions with keyword colours and emoji
  • 🙂 Smart framing that follows the speaker, or blurred fit for slides
  • 🤐 Removes "um", "uh" and silences
  • 📱 9:16, 1:1 and 16:9
  • ✏️ Fix any caption word and re-render
  • 🆓 No watermark on the free plan
  PRO adds an agent connector (MCP) so your AI assistants can clip for you.
  Learn the agent clipping workflow: https://whop.com/ai-agents-for-clippers-marketers/
- **Category:** Video Players & Editors · **Tags:** shorts maker, captions, reels, clips, podcast clips.
- Screenshots: `samples/v1/ui_step1_mobile.png`, `samples/v1/ui_step3_mobile.png` + 3 clip stills.

## 3 promo hooks (short-form ads), all ending with the course CTA
1. **"I stopped editing clips. My agent does it now."** — screen: paste link → 3 scored clips appear → tap Save.
   CTA: *"Free app, no watermark. Want the full agent workflow that turns this into income? → whop.com/ai-agents-for-clippers-marketers"*
2. **"This 2-hour podcast had 4 viral moments. Here they are — scored."** — show 🔥 91 / 🔥 86 badges and the reasons.
   CTA: *"Clip it yourself free with AI AGENT ✚ CUT — learn to sell clips with AI agents: whop.com/ai-agents-for-clippers-marketers/"*
3. **"Um… uh… gone."** — before/after of a rambling take vs. the tight clip with pop captions + emoji.
   CTA: *"No watermark, ever. Go pro with agents → whop.com/ai-agents-for-clippers-marketers/"*
