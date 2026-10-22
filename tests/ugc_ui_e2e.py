"""Playwright: UGC mode end to end (mobile + desktop screenshots in samples/v4)."""
import asyncio, time, json, shutil
from playwright.async_api import async_playwright
B = "http://127.0.0.1:8765/"; O = "samples/v4/"
U = '{"email":"wisdom@example.com","provider":"google","plan":"free","credits":60,"stub":true}'
BRIEF = """Content Rewards UGC campaign: FocusFlow app
Brand: FocusFlow
FocusFlow helps you block distractions and finish deep work in half the time.
Requirements:
- Videos must be 20-40 seconds, vertical
- Mention FocusFlow in the first 5 seconds
- Show the app on screen or describe it clearly
- Must include #FocusFlowPartner and #ad
- Don't mention competitors or make medical claims
- End with a CTA to download from the link in bio
Payout: $1.50 per 1,000 views, max $300"""
async def main():
    R = {"errors": []}; t0 = time.time()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        m = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await m.new_page(); pg.on("pageerror", lambda e: R["errors"].append("js: " + str(e)))
        await pg.goto(B + "?nointro"); await pg.evaluate(f"localStorage.setItem('aac_onb','1');localStorage.setItem('aac_user',JSON.stringify({U}));localStorage.setItem('aac_lead_asked','1');localStorage.setItem('aac_mode','clip')")
        await pg.reload(); await pg.wait_for_timeout(1500); await pg.screenshot(path=O + "m1_mode_switch_clip.png")
        await pg.click(".mswrap >> text=UGC"); await pg.wait_for_timeout(600); await pg.screenshot(path=O + "m2_ugc_home.png")
        await pg.fill("#ubrief", BRIEF); await pg.click("#ubtn"); await pg.wait_for_selector("#uplan:not(.hide)", timeout=60000); await pg.wait_for_timeout(800)
        await pg.locator("#uck").scroll_into_view_if_needed(); await pg.evaluate("document.querySelectorAll('#uck input').forEach((c,i)=>{if(i<3)c.checked=true})")
        await pg.screenshot(path=O + "m3_brief_checklist.png")
        await pg.locator("#ucreate").scroll_into_view_if_needed(); await pg.wait_for_timeout(400); await pg.screenshot(path=O + "m4_create_options.png")
        await pg.click("[data-o=styles]"); await pg.wait_for_timeout(300); await pg.locator("#ugallery").scroll_into_view_if_needed(); await pg.screenshot(path=O + "m5_styles.png")
        await pg.click("#ugallery .st:nth-child(3) button"); await pg.wait_for_timeout(1200)
        R["script_review"] = await pg.input_value("#uscript")
        await pg.click("[data-o=avatar]"); await pg.wait_for_timeout(300); await pg.locator("#o-avatar").scroll_into_view_if_needed(); await pg.screenshot(path=O + "m6_avatar_consent.png")
        await pg.click("[data-o=faceless]")
        async with pg.expect_file_chooser() as fc: await pg.click("text=+ Add my clips")
        await (await fc.value).set_files("templates/assets/broll_ours.mp4"); await pg.wait_for_function("document.getElementById('ubroll').textContent.includes('clip(s)')", timeout=60000)
        t = time.time(); await pg.click("button[onclick^=renderUgc]")
        await pg.wait_for_selector("#uexport:not(.hide)", timeout=600000); R["render_secs"] = round(time.time() - t, 1)
        await pg.wait_for_timeout(1500); await pg.evaluate("document.querySelectorAll('#uck2 input').forEach((c,i)=>{if(i<5)c.checked=true})")
        await pg.locator("#uexport").scroll_into_view_if_needed(); await pg.screenshot(path=O + "m7_export.png")
        R["video"] = await pg.get_attribute("#udl", "href")
        d = await b.new_context(viewport={"width": 1440, "height": 900}); pg2 = await d.new_page()
        await pg2.goto(B + "?nointro"); await pg2.evaluate(f"localStorage.setItem('aac_onb','1');localStorage.setItem('aac_user',JSON.stringify({U}));localStorage.setItem('aac_mode','ugc')")
        await pg2.reload(); await pg2.wait_for_timeout(1500); await pg2.screenshot(path=O + "d1_ugc_home_desktop.png")
        await pg2.click(".dtop >> text=Clip"); await pg2.wait_for_timeout(800); await pg2.screenshot(path=O + "d2_clip_home_desktop.png")
        await pg2.evaluate("go('learn')"); await pg2.wait_for_timeout(2500); await pg2.screenshot(path=O + "d3_learn_ugc_row.png", full_page=True)
        await pg2.evaluate("go('ai')"); await pg2.wait_for_timeout(800); await pg2.screenshot(path=O + "d4_connect_ai.png")
        await b.close()
    R["secs"] = round(time.time() - t0, 1); json.dump(R, open("tests/results/ugc_ui_e2e.json", "w"), indent=1); print(json.dumps(R, indent=1)[:1500])
asyncio.run(main())
