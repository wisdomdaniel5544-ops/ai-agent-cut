"""AI Agent Cut — PRO: MCP server so AI agents can drive the clipper.
Official MCP Python SDK (MIT). Transports: stdio (default) and streamable HTTP.
  python -m aiagentcut.mcp_server                 # stdio (Claude Desktop / any MCP client)
  python -m aiagentcut.mcp_server --http 8766     # http://127.0.0.1:8766/mcp
HTTP binds 127.0.0.1 by default; put it behind a reverse proxy with auth before exposing it."""
import json, sys, uuid, argparse
from pathlib import Path
try:
    from mcp.server.mcpserver import MCPServer as _Server      # mcp >= 2
except ImportError:
    from mcp.server.fastmcp import FastMCP as _Server           # mcp 1.x
from . import engine

ROOT = Path(__file__).resolve().parent.parent
import os
PROJECTS = Path(os.environ.get("AIAC_DATA") or ROOT) / "jobs"; PROJECTS.mkdir(exist_ok=True)
mcp = _Server("ai-agent-cut", instructions="Turn long videos into short captioned clips. Typical flow: "
              "find_clips(source) -> render_clip(project, idx) or make_clips(source) -> edit_captions -> get_project.")

def _proj(pid): 
    d = PROJECTS / Path(pid).name
    if not d.exists(): raise ValueError(f"unknown project {pid}")
    return d

def _summary(c, i):
    return {"idx": i, "start": c["start"], "end": c["end"], "virality": c["score"], "reason": c.get("reason"),
            "hook_title": c.get("title"), "file": c.get("file"), "text": c.get("text", "")[:200]}

@mcp.tool()
def list_projects() -> list[dict]:
    """List clipping projects with clip counts and top virality."""
    out = []
    for d in sorted(PROJECTS.iterdir(), key=lambda p: -p.stat().st_mtime):
        rp = d / "report.json"; fc = d / "candidates.json"
        if rp.exists():
            r = json.loads(rp.read_text()); out.append({"project": d.name, "input": r.get("input"), "clips": len(r["clips"]),
                "top_virality": max([c["score"] for c in r["clips"]] or [0]), "rendered": True})
        elif fc.exists():
            out.append({"project": d.name, "candidates": len(json.loads(fc.read_text())["clips"]), "rendered": False})
    return out

@mcp.tool()
def find_clips(source: str, n: int = 4, min_len: float = 30, max_len: float = 60, model: str = "small",
               prompt: str | None = None, genre: str = "auto") -> dict:
    """Transcribe a video (local path or URL) and return the best clip windows with virality 0-100, reason and hook title.
    Does not render. Returns a project id for render_clip."""
    pid = uuid.uuid4().hex[:8]; d = PROJECTS / pid; work = d / "work"; work.mkdir(parents=True)
    media = engine.fetch(source, work); cut = work / "cut.mp4"; engine.silence_cut(media, cut)
    tr = engine.transcribe(cut, model); (work / "transcript.json").write_text(json.dumps(tr))
    clips = engine.pick_clips(tr, cut, n, min_len, max_len, genre=genre, prompt=prompt)
    (d / "candidates.json").write_text(json.dumps({"input": source, "media": str(cut), "clips": clips}))
    return {"project": pid, "clips": [_summary(c, i) for i, c in enumerate(clips, 1)]}

@mcp.tool()
def render_clip(project: str, idx: int, aspect: str = "9:16", preset: str = "bold_yellow", fit: str = "auto",
                hook: bool = True, emoji: bool = False, remove_fillers: bool = True) -> dict:
    """Render candidate clip `idx` (1-based) of a find_clips project to MP4 (<4.9 MB). aspect: 9:16|1:1|16:9;
    preset: bold_yellow|clean_white|neon_pop; fit: auto|crop|blur."""
    d = _proj(project); cand = json.loads((d / "candidates.json").read_text()); c = cand["clips"][idx-1]
    work = d / "work"; words = [w for s in json.loads((work / "transcript.json").read_text())["segments"] for w in s["words"]]
    out = d / f"clip_{idx:02d}_{preset}_{aspect.replace(':','x')}.mp4"
    opts = dict(preset=preset, aspect=aspect, fit=fit, hook=hook, keywords=True, emoji=emoji, remove_fillers=remove_fillers)
    r = engine.render_clip(cand["media"], c, words, out, work, opts)
    r.update(start=round(c["start"], 2), end=round(c["end"], 2), score=c["score"], reason=c["reason"], title=c["title"], text=c["text"][:300], media=cand["media"])
    rp = d / "report.json"
    rep = json.loads(rp.read_text()) if rp.exists() else {"input": cand["input"], "clips": [],
          "options": opts}
    rep["clips"].append(r); rp.write_text(json.dumps(rep, indent=1))
    return {"clip_number": len(rep["clips"]), **_summary(r, len(rep["clips"])), "size_mb": r["size_mb"], "reframe": r["reframe"]}

@mcp.tool()
def make_clips(source: str, n: int = 3, aspect: str = "9:16", preset: str = "bold_yellow", emoji: bool = False) -> dict:
    """One-shot: find and render the n best clips with captions, hook title and filler removal."""
    pid = uuid.uuid4().hex[:8]
    r = engine.process(source, PROJECTS / pid, n, preset, aspect=aspect, emoji=emoji, log=lambda m: print(m, file=sys.stderr))
    return {"project": pid, "clips": [_summary(c, i) for i, c in enumerate(r["clips"], 1)]}

@mcp.tool()
def get_captions(project: str, clip: int) -> dict:
    """Return the caption words (in order) and hook title of a rendered clip, for editing."""
    d = _proj(project); c = json.loads((d / "report.json").read_text())["clips"][clip-1]
    ws = json.loads((d / "work" / (Path(c["file"]).stem + ".words.json")).read_text())
    return {"title": c.get("title"), "words": [w["word"] for w in ws]}

@mcp.tool()
def edit_captions(project: str, clip: int, words: list[str] | None = None, replace: dict[str, str] | None = None,
                  title: str | None = None) -> dict:
    """Edit captions of a rendered clip and re-render. Either pass the full `words` list (same length as get_captions,
    '' deletes a word) or a `replace` map {old_word: new_word}. `title` changes the hook headline."""
    d = _proj(project); cur = get_captions(project, clip)["words"]
    if words is None:
        rep = {k.lower(): v for k, v in (replace or {}).items()}
        words = [rep.get(w.lower(), w) for w in cur]
    c = engine.rerender_with_text(d, clip, words, title)
    return _summary(c, clip) | {"size_mb": c["size_mb"], "edited": c.get("edited")}

@mcp.tool()
def edit_sections(project: str, clip: int, remove: list[list[float]] | None = None, add: list[list[float]] | None = None, at: str = "end") -> dict:
    """Transcript-based edit: cut [start,end] ranges out of a clip and/or add ranges from elsewhere in the transcript."""
    c = engine.edit_sections(_proj(project), clip, remove or [], add or [], at); return _summary(c, clip) | {"duration": c["duration"]}

@mcp.tool()
def export_platforms(project: str, clip: int, platforms: list[str]) -> dict:
    """Render a clip for several platforms (tiktok, reels, shorts, youtube, x, linkedin, ...) and zip them."""
    return {"zip": str(engine.export_platforms(_proj(project), clip, platforms))}

@mcp.tool()
def export_xml(project: str, clip: int, kind: str = "fcpxml") -> dict:
    """Export a clip's edit as FCPXML (Final Cut/Resolve) or 'xmeml' (Premiere)."""
    return {"file": str(engine.export_xml(_proj(project), clip, kind))}

@mcp.tool()
def get_project(project: str) -> dict:
    """Full report of a project (clips, scores, files)."""
    d = _proj(project); rp = d / "report.json"
    return json.loads(rp.read_text()) if rp.exists() else json.loads((d / "candidates.json").read_text())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--http", type=int, help="serve streamable HTTP on this port")
    ap.add_argument("--host", default="127.0.0.1"); a = ap.parse_args()
    if a.http:
        try: mcp.run("streamable-http", host=a.host, port=a.http)
        except TypeError:  # mcp 1.x: host/port live on settings
            mcp.settings.host, mcp.settings.port = a.host, a.http; mcp.run("streamable-http")
    else: mcp.run()
if __name__ == "__main__": main()
