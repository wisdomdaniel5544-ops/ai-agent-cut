# Brand — AI Agent Cut (v3)

What we learned from how the market leader markets itself (public tutorial video + site, studied, not copied):
one-promise headline ("long video → viral shorts in 1 click"), a number on every clip (virality score) that makes
results feel *measurable*, a free tier to get people in, product demos that show the result in the first seconds,
and a creator-to-creator tone ("you want this on, because people watch without sound"). We keep those *principles*
and build our own identity around **agents** and **ownership** (runs locally, no watermark, agent-drivable).

## Name & wordmark
**AI Agent Cut** — set in a bold Inter-style sans: `AI Agent` (white) + `Cut` (lime #C6FF3D). Short name / app icon label: **AgentCut**.
Older materials used `AI AGENT ✚ CUT` with a coral ✚; that wordmark is retired. Never use other brands' marks, names or colours.

## Tagline
- Primary: **Long video in. Viral clips out.**
- Alt: *Your clipping agent. Free, no watermark.* · *Clip like a pro. Let the agent do the boring part.*

## Colours (v3: strict dark mode, one accent)
| Role | Hex |
|---|---|
| Background | `#000000` |
| Card / raised card | `#121212` / `#1C1C1E` (borders `#2A2A2D`) |
| Primary text | `#FFFFFF` |
| Secondary text | `#A0A0A0` |
| Primary button | white `#FFFFFF` with black text |
| Accent (only one: credits dot, Ultra Pro, scores, logo cut) | lime `#C6FF3D` |

Violet and coral from v1/v2 are retired. Type: Inter / SF / system sans, 800 weight for headers; Anton / Montserrat
ExtraBold stay for burned-in captions.

## Logo (v3)
A white rounded **play triangle sliced by a lime diagonal cut line** ending in a lime dot (the "agent" handle),
on a black/#121212 rounded square. It says "video" + "cut" + "automated" in one shape and reads at 16 px.
Files: `web/static/icon.svg` (master), `icon-192.png`, `icon-512.png`, Android `mipmap-*/ic_launcher*.png`,
Windows `packaging/windows/app.ico` (all regenerated from the SVG). Old robot mark kept as `web/static/icon-v2-old.svg`.
**Launch intro:** triangle pops in, the cut line draws across, the dot snaps on, the wordmark rises (≈2.3 s, CSS/SVG
in `web/index.html`; recording at `samples/v3/logo_intro.mp4`).

## Voice
Short, warm, emoji-light, zero jargon. Verbs first: *Add. Clip. Export.* Celebrate results ("🔥 86 — strong hook").
Never shame the user; errors say what to do next.

## UX (v3, `web/index.html`)
- **Mobile:** launch intro → 3 onboarding slides (long video → shorts / captions people read / start free) → sign-in
  (Continue with Google / Continue with email) → optional "Get free clipping tips" email → **Projects** home with credits
  pill + Ultra Pro button, floating bar (Home · Learn · **+** · Profile). **+** opens a bottom sheet: paste a link, or Gallery / Files.
- **Desktop:** left sidebar (Home, Projects, Brand templates, Learn, Connect AI, Settings), top bar (link input, credits,
  Upgrade, avatar), Upload / Google Drive / Try a sample, 8 tool tiles, projects, Learn rows, what's new.
- **Community:** Free users see "Join the AI AGENT CUT WhatsApp channel" + "Join on Telegram" cards on home, Learn and account.
- **Learn:** intro card to Daniel Bitton (Content Rewards) linking his YouTube channel, then rows of his long videos
  and Shorts (YouTube links + thumbnails only; nothing re-hosted).
- **Connect AI:** bring-your-own keys for Gemini (live), ElevenLabs, Grok, Manus (coming soon).
- Power features (word editing, platform packs, brand templates) live in the advanced editor at `/classic`.

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

## Tiers (v3)
| | FREE | ULTRA PRO — $3.99/mo |
|---|---|---|
| Everything that used to be Pro: clips from upload/link, scores, hook titles, animated captions, reframe, B-roll, filler/silence cut, text editing, platform export | ✅ | ✅ |
| Credits / month | 60 | 600 |
| **MCP agent access** (find_clips, render_clip, make_clips, edit_captions, list_projects…) | — | ✅ |
| Priority rendering, 4K export, no watermark ever | — | ✅ |
| Batch import / auto-posting (roadmap) | — | ✅ |
Checkout is not wired yet.

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
  Ultra Pro ($3.99/mo) adds an agent connector (MCP) so your AI assistants can clip for you.
  Learn the agent clipping workflow: https://whop.com/ai-agents-for-clippers-marketers/
- **Category:** Video Players & Editors · **Tags:** shorts maker, captions, reels, clips, podcast clips.
- Screenshots: `samples/v3/m1_onboarding_1.png`, `m2_signin.png`, `m3_home.png`, `m4_add_video_sheet.png`, `m5_pricing.png`, `m6_learn.png`.

## 3 promo hooks (short-form ads), all ending with the course CTA
1. **"I stopped editing clips. My agent does it now."** — screen: paste link → 3 scored clips appear → tap Save.
   CTA: *"Free app, no watermark. Want the full agent workflow that turns this into income? → whop.com/ai-agents-for-clippers-marketers"*
2. **"This 2-hour podcast had 4 viral moments. Here they are — scored."** — show 🔥 91 / 🔥 86 badges and the reasons.
   CTA: *"Clip it yourself free with AI AGENT ✚ CUT — learn to sell clips with AI agents: whop.com/ai-agents-for-clippers-marketers/"*
3. **"Um… uh… gone."** — before/after of a rambling take vs. the tight clip with pop captions + emoji.
   CTA: *"No watermark, ever. Go pro with agents → whop.com/ai-agents-for-clippers-marketers/"*
