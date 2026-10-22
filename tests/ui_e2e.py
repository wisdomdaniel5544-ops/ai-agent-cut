"""Playwright user test of the v3 UI: sign in, upload a file from the + sheet, watch progress, land on the clips."""
import asyncio, time, json, sys
from playwright.async_api import async_playwright
B = "http://127.0.0.1:8765/"; F = sys.argv[1] if len(sys.argv) > 1 else "input/talk.mp4"
async def main():
    R = {"errors": [], "progress": []}; t0 = time.time()
    async with async_playwright() as p:
        b = await p.chromium.launch(); c = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        pg = await c.new_page(); pg.on("pageerror", lambda e: R["errors"].append("js: " + str(e)))
        await pg.goto(B + "?nointro"); await pg.click("#nextBtn"); await pg.click("#nextBtn"); await pg.click("#nextBtn")
        await pg.click("text=Continue with email"); await pg.fill("#email", "tester@example.com"); await pg.click("#ebox >> text=Continue")
        await pg.wait_for_timeout(800); await pg.click("text=Skip for now"); await pg.click(".fab")
        async with pg.expect_file_chooser() as fc: await pg.click("#sheet >> text=Gallery")
        await (await fc.value).set_files(F)
        last = None
        while time.time() - t0 < 900:
            if "/classic" in pg.url: break
            try: m = await pg.text_content("#jmsg", timeout=1000)
            except Exception: m = None
            if m and m != last: R["progress"].append([round(time.time() - t0, 1), m]); last = m
            if m and m.startswith("Failed"): R["errors"].append(m); break
            await pg.wait_for_timeout(1000)
        if "/classic" in pg.url:
            await pg.wait_for_selector(".clip video", timeout=60000); R["clips_shown"] = await pg.locator(".clip").count()
            await pg.screenshot(path="tests/results/ui_e2e_clips.png")
        await b.close()
    R["secs"] = round(time.time() - t0, 1); json.dump(R, open("tests/results/ui_e2e.json", "w"), indent=1)
    print(json.dumps({k: R[k] for k in ("secs", "errors")} | {"clips_shown": R.get("clips_shown"), "steps": len(R["progress"])}))
asyncio.run(main())
