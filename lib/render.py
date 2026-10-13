"""Render an agt-snapshot work dir into <stamp>.json and <stamp>.html. Called by bin/agt-snapshot."""
import json, sys, os, glob, re, shlex, html, datetime
work, out, stamp, restore_bin = sys.argv[1:5]
home = os.path.expanduser("~")
UUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
SHELLS = {"zsh", "bash", "fish", "sh", "login"}

def tilde(p): return "~" + p[len(home):] if p and p.startswith(home) else (p or "")
def prog(argv): return os.path.basename(argv[0]).lstrip("-") if argv else ""

live = {}
for line in open(f"{work}/claude.tsv"):
    a, s = line.rstrip("\n").split("\t"); live[a.upper()] = s.lower()

def user_text(o):
    m = o.get("message") or {}
    c = m.get("content")
    if isinstance(c, str): return c
    if isinstance(c, list):
        t = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
        return "\n".join(t) if t else None
    return None

def transcript(sid):
    if not sid: return None
    m = glob.glob(f"{home}/.claude/projects/*/{sid.lower()}.jsonl")
    if not m: return None
    info = {"sid": sid.lower(), "cwd": None, "title": None, "custom": None, "first": None, "last": None, "prompts": 0}
    with open(m[0], errors="replace") as f:
        for line in f:
            if '"type"' not in line: continue
            try: o = json.loads(line)
            except ValueError: continue
            t = o.get("type")
            if t == "custom-title": info["custom"] = o.get("customTitle") or info["custom"]
            elif t == "ai-title": info["title"] = o.get("aiTitle") or info["title"]
            elif t == "user" and not o.get("isMeta"):
                if info["cwd"] is None: info["cwd"] = o.get("cwd")
                txt = user_text(o)
                if txt and not txt.startswith("<"):
                    info["prompts"] += 1
                    info["first"] = info["first"] or txt
                    info["last"] = txt
    info["title"] = info.pop("custom") or info["title"]
    info["modified"] = datetime.datetime.fromtimestamp(os.path.getmtime(m[0])).strftime("%Y-%m-%d %H:%M")
    return info

def conversation(sess_id, fg):
    sid = live.get(sess_id.upper())
    if not sid and prog(fg) == "claude":
        for i, a in enumerate(fg[:-1]):
            if a in ("-r", "--resume", "--session-id") and UUID.match(fg[i + 1]): sid = fg[i + 1]
    # the fish wrapper names a tab's conversation after the agterm session id
    return transcript(sid) or transcript(sess_id)

def resume_line(conv, fg, cwd):
    p = prog(fg)
    if p and p not in SHELLS and p != "claude": return shlex.join([p] + fg[1:])
    if conv:
        line = f"claude --resume {conv['sid']}"
        return line if not conv["cwd"] or conv["cwd"] == cwd else f"cd {shlex.quote(conv['cwd'])} && {line}"
    return None

snap = {"stamp": stamp, "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "windows": [], "sessions": []}
for w in json.load(open(f"{work}/windows.json"))["result"]["windows"]:
    path = f"{work}/tree-{w['id']}.json"
    if not os.path.exists(path): continue
    tree = json.load(open(path))["result"]["tree"]
    win = {"id": w["id"], "name": w.get("name") or "window", "workspaces": []}
    for ws in tree.get("workspaces", []):
        wsn = {"id": ws["id"], "name": ws.get("name", ""), "sessions": []}
        for s in ws.get("sessions", []):
            fg, cwd = s.get("foreground") or [], s.get("cwd") or home
            conv = conversation(s["id"], fg)
            split = None
            if s.get("hasSplit") or s.get("split"):
                sfg, scwd = s.get("splitForeground") or [], s.get("splitCwd") or cwd
                sline = shlex.join(sfg) if sfg and prog(sfg) not in SHELLS else None
                if scwd != cwd: sline = f"cd {shlex.quote(scwd)}" + (f" && {sline}" if sline else "")
                split = {"cwd": scwd, "foreground": sfg, "restore": sline}
            try: screen = open(f"{work}/screen-{s['id']}.txt", errors="replace").read().rstrip()
            except OSError: screen = ""
            rec = {"id": s["id"], "name": s.get("name", ""), "title": s.get("title"), "workspace": wsn["name"],
                   "workspaceId": ws["id"], "window": win["name"], "cwd": cwd, "foreground": fg,
                   "flagged": bool(s.get("flagged")), "status": s.get("status"), "claude": conv,
                   "restore": resume_line(conv, fg, cwd), "split": split, "screen": screen}
            snap["sessions"].append(rec); wsn["sessions"].append(rec["id"])
        win["workspaces"].append(wsn)
    snap["windows"].append(win)

jpath = f"{out}/{stamp}.json"
json.dump(snap, open(jpath, "w"), indent=1, ensure_ascii=False)

e = lambda x: html.escape(str(x or ""), quote=True)
restore = f"{tilde(restore_bin)} {tilde(jpath)}"
by_id = {s["id"]: s for s in snap["sessions"]}
def short(t, n=160): t = " ".join((t or "").split()); return t if len(t) <= n else t[:n] + "…"

def session_html(s):
    snippet = f"{restore} {s['id']}"
    badges = []
    if s["claude"]: badges.append('<span class="b claude">claude</span>')
    p = prog(s["foreground"])
    if p and p not in SHELLS and p != "claude": badges.append(f'<span class="b run">{e(p)}</span>')
    if s["split"]: badges.append('<span class="b">split</span>')
    if s["flagged"]: badges.append('<span class="b flag">flagged</span>')
    rows = [("id", s["id"]), ("directory", tilde(s["cwd"])),
            ("running", " ".join(s["foreground"]) or "shell prompt"),
            ("terminal title", s["title"])]
    c = s["claude"]
    if c:
        rows += [("conversation", c["title"] or "untitled"), ("conversation id", c["sid"]),
                 ("claude dir", tilde(c["cwd"])), ("last activity", c["modified"]),
                 ("prompts", c["prompts"]), ("first prompt", short(c["first"], 400)), ("last prompt", short(c["last"], 400))]
    if s["split"]:
        rows += [("split dir", tilde(s["split"]["cwd"])), ("split running", " ".join(s["split"]["foreground"]) or "shell prompt")]
    rows.append(("restores with", s["restore"] or "plain shell"))
    table = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in rows if v not in (None, ""))
    screen = f'<div class="lbl">last screen lines</div><pre class="screen">{e(s["screen"])}</pre>' if s["screen"] else ""
    sub = (c and c["title"] and c["title"] != s["name"].lstrip("✳ ")) and f'<span class="sub">{e(c["title"])}</span>' or ""
    search = " ".join([s["name"], s["workspace"], s["cwd"], " ".join(s["foreground"]), (c or {}).get("title") or "", (c or {}).get("last") or ""])
    return f'''<details class="sess" data-q="{e(search.lower())}">
<summary><span class="ico">›_</span><span class="nm">{e(s["name"])}</span>{sub}<span class="badges">{"".join(badges)}</span>
<button class="copy" data-s="{e(snippet)}" title="copy restore snippet">copy</button></summary>
<div class="body"><table>{table}</table>{screen}
<div class="lbl">restore snippet</div><code class="snip">{e(snippet)}</code></div></details>'''

parts = []
for win in snap["windows"]:
    parts.append(f'<h2>{e(win["name"])}</h2>')
    for ws in win["workspaces"]:
        snippet = f"{restore} --workspace {ws['id']}"
        parts.append(f'''<section class="ws"><div class="wsh"><span class="chev">⌄</span><span class="wsi">⊞</span>
<span class="wsn">{e(ws["name"])}</span><span class="cnt">{len(ws["sessions"])}</span>
<button class="copy" data-s="{e(snippet)}" title="copy snippet restoring the whole workspace">copy workspace</button></div>
{"".join(session_html(by_id[i]) for i in ws["sessions"])}</section>''')

n_claude = sum(1 for s in snap["sessions"] if s["claude"])
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>agterm snapshot</title><style>
:root{{--bg:#f6f5f1;--panel:#fff;--fg:#1d1f1c;--mut:#6b6f68;--line:#e2e0d8;--acc:#2f6b3f;--accbg:#e4efe6;--code:#f0efe9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151715;--panel:#1d201d;--fg:#e7e9e4;--mut:#9aa096;--line:#2c312c;--acc:#7fc18f;--accbg:#22362a;--code:#121412}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:980px;margin:0 auto;padding:24px 16px 64px}}header{{display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;justify-content:space-between}}
h1{{font-size:20px;margin:0}}.meta{{color:var(--mut);font-size:13px}}
#q{{width:100%;margin:16px 0 8px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--fg);font-size:14px}}
h2{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);margin:24px 0 8px}}
.ws{{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:0 0 10px;overflow:hidden}}
.wsh{{display:flex;align-items:center;gap:8px;padding:9px 12px;font-weight:600;border-bottom:1px solid var(--line)}}
.chev,.wsi{{color:var(--mut)}}.wsn{{flex:1;min-width:0}}.cnt{{color:var(--mut);font-weight:400;font-size:12px}}
.sess{{border-top:1px solid var(--line)}}.sess:first-of-type{{border-top:0}}
summary{{display:flex;align-items:center;gap:8px;padding:7px 12px 7px 28px;cursor:pointer;list-style:none;min-width:0}}
summary::-webkit-details-marker{{display:none}}summary:hover{{background:var(--accbg)}}
.ico{{font:11px ui-monospace,Menlo,monospace;color:var(--mut);border:1px solid var(--line);border-radius:4px;padding:0 3px}}
.nm{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.sub{{color:var(--mut);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}}
.badges{{display:flex;gap:4px;margin-left:auto;flex-shrink:0}}.b{{font-size:11px;padding:1px 6px;border-radius:999px;border:1px solid var(--line);color:var(--mut)}}
.b.claude{{color:var(--acc);border-color:var(--acc)}}.b.run{{color:#b5651d;border-color:#b5651d}}.b.flag{{color:#c0392b;border-color:#c0392b}}
.copy{{flex-shrink:0;font:12px inherit;padding:3px 10px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}}
.copy:hover{{border-color:var(--acc);color:var(--acc)}}.copy.ok{{background:var(--acc);color:var(--panel);border-color:var(--acc)}}
.body{{padding:4px 12px 14px 28px}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{text-align:left;color:var(--mut);font-weight:500;white-space:nowrap;padding:3px 12px 3px 0;vertical-align:top;width:1%}}td{{padding:3px 0;word-break:break-word}}
.lbl{{color:var(--mut);font-size:12px;margin:10px 0 4px}}
pre.screen,code.snip{{display:block;background:var(--code);border:1px solid var(--line);border-radius:6px;padding:8px 10px;font:12px/1.4 ui-monospace,Menlo,monospace;overflow-x:auto;white-space:pre;margin:0}}
code.snip{{white-space:pre-wrap;word-break:break-all}}.hide{{display:none}}
footer{{margin-top:28px;color:var(--mut);font-size:13px}}footer code{{background:var(--code);padding:1px 5px;border-radius:4px}}
</style></head><body><main>
<header><h1>agterm snapshot</h1><span class="meta">{e(snap["created"])} · {len(snap["sessions"])} sessions · {n_claude} with a Claude conversation</span></header>
<input id="q" type="search" placeholder="filter by name, directory, command, conversation…" autofocus>
{"".join(parts)}
<footer>Copy a snippet and paste it into any agterm shell. A session that is still open is selected instead of duplicated.
A restored session is a new shell in the saved directory that resumes its Claude conversation or re-runs its command.
Snapshot data: <code>{e(tilde(jpath))}</code></footer></main>
<script>
document.addEventListener("click",ev=>{{const b=ev.target.closest(".copy");if(!b)return;ev.preventDefault();ev.stopPropagation();
const t=b.dataset.s,done=()=>{{const o=b.textContent;b.textContent="copied";b.classList.add("ok");setTimeout(()=>{{b.textContent=o;b.classList.remove("ok")}},1200)}};
const fb=()=>{{const a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();document.execCommand("copy");a.remove();done()}};
navigator.clipboard?navigator.clipboard.writeText(t).then(done,fb):fb()}});
document.getElementById("q").addEventListener("input",ev=>{{const q=ev.target.value.toLowerCase().trim();
document.querySelectorAll(".ws").forEach(ws=>{{let any=false;ws.querySelectorAll(".sess").forEach(s=>{{const m=!q||s.dataset.q.includes(q);s.classList.toggle("hide",!m);any=any||m}});
ws.classList.toggle("hide",!any&&!!q&&!ws.querySelector(".wsn").textContent.toLowerCase().includes(q))}})}});
</script></body></html>'''
hpath = f"{out}/{stamp}.html"
open(hpath, "w").write(page)
latest = f"{out}/latest.html"
if os.path.lexists(latest): os.remove(latest)
os.symlink(os.path.basename(hpath), latest)
print(hpath)
