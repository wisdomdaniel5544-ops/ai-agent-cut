import argparse, json
from pathlib import Path
from .engine import process, PRESETS, ASPECTS, GENRES, PLATFORMS, export_xml, export_platforms
def main():
    ap = argparse.ArgumentParser(prog="aiagentcut", description="AI AGENT CUT - long video to captioned short clips")
    ap.add_argument("input", help="video file path or URL (YouTube, X, TikTok, Drive, Dropbox, direct mp4 ...)")
    ap.add_argument("-o", "--out", default="output")
    ap.add_argument("-n", "--clips", type=int, default=4)
    ap.add_argument("-p", "--preset", default="bold_yellow", choices=list(PRESETS))
    ap.add_argument("-m", "--model", default="small", help="whisper model: tiny/base/small/medium")
    ap.add_argument("-a", "--aspect", default="9:16", choices=list(ASPECTS))
    ap.add_argument("--fit", default="auto", choices=["auto", "crop", "blur"])
    ap.add_argument("--min", type=float, default=30); ap.add_argument("--max", type=float, default=60)
    ap.add_argument("--trim", nargs=2, type=float, metavar=("START", "END"), help="only process this part of the source (seconds)")
    ap.add_argument("--prompt", help="find a moment, e.g. 'pricing advice'")
    ap.add_argument("--genre", default="auto", choices=list(GENRES))
    ap.add_argument("--lang", help="language code, e.g. en, es, fr (default: auto-detect)")
    ap.add_argument("--srt", help="use this SRT instead of transcribing")
    ap.add_argument("--vocab", nargs="*", default=[], help="fix spellings: wrong=Right")
    ap.add_argument("--censor", nargs="*", default=[], help="words to bleep/mask")
    ap.add_argument("--censor-mode", default="bleep", choices=["bleep", "mask"])
    ap.add_argument("--template", help="brand template JSON (font, colors, logo, intro, outro, music ...)")
    ap.add_argument("--broll", help="'auto' or a prompt (needs PEXELS_API_KEY)"); ap.add_argument("--broll-file")
    ap.add_argument("--no-silence-cut", action="store_true"); ap.add_argument("--pauses", action="store_true", help="also remove dead pauses inside clips")
    ap.add_argument("--no-hook", action="store_true"); ap.add_argument("--no-keywords", action="store_true")
    ap.add_argument("--emoji", action="store_true"); ap.add_argument("--keep-fillers", action="store_true")
    ap.add_argument("--xml", action="store_true", help="also write FCPXML + Premiere XML per clip")
    ap.add_argument("--platforms", nargs="*", default=[], choices=list(PLATFORMS), help="export clip 1 for these platforms (zip)")
    ap.add_argument("--cookies", help="cookies.txt for login-only links")
    a = ap.parse_args()
    tpl = json.loads(Path(a.template).read_text()) if a.template else None
    r = process(a.input, a.out, a.clips, a.preset, a.model, a.min, a.max, not a.no_silence_cut, aspect=a.aspect,
                fit=a.fit, hook=not a.no_hook, keywords=not a.no_keywords, emoji=a.emoji, remove_fillers=not a.keep_fillers,
                trim=tuple(a.trim) if a.trim else None, prompt=a.prompt, genre=a.genre, language=a.lang, srt=a.srt,
                vocab=dict(v.split("=", 1) for v in a.vocab), censor=a.censor, censor_mode=a.censor_mode, template=tpl,
                broll=a.broll, broll_file=a.broll_file, remove_pauses=a.pauses, cookies=a.cookies)
    if a.xml:
        for i in range(1, len(r["clips"]) + 1): export_xml(a.out, i, "fcpxml"); export_xml(a.out, i, "xmeml")
    if a.platforms: print("platform zip:", export_platforms(a.out, 1, a.platforms))
    print(json.dumps({k: v for k, v in r.items() if k != "options"}, indent=1)[:3000])
if __name__ == "__main__": main()
