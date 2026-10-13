"""Render an agt-snapshot work dir into <stamp>.json and <stamp>.html. Called by bin/agt-snapshot."""
import collections, datetime, glob, json, os, re, shlex, sys

work, out, stamp, restore_bin = sys.argv[1:5]
home = os.path.expanduser("~")
UUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
SHELLS = {"zsh", "bash", "fish", "sh", "login"}
MAX_TURNS, MAX_TEXT = 200, 6000  # per conversation, keeps a page with dozens of agents in the low MBs


def tilde(p): return "~" + p[len(home):] if p and p.startswith(home) else (p or "")
def prog(argv): return os.path.basename(argv[0]).lstrip("-") if argv else ""
def clip(t): return t if len(t) <= MAX_TEXT else t[:MAX_TEXT] + f"\n… [{len(t) - MAX_TEXT} more characters]"


live = {}
for line in open(f"{work}/claude.tsv"):
    a, s = line.rstrip("\n").split("\t")
    live[a.upper()] = s.lower()


def blocks(o):
    c = (o.get("message") or {}).get("content")
    if isinstance(c, str): return [{"type": "text", "text": c}]
    return [x for x in c if isinstance(x, dict)] if isinstance(c, list) else []


def transcript(sid):
    if not sid: return None
    m = glob.glob(f"{home}/.claude/projects/*/{sid.lower()}.jsonl")
    if not m: return None
    info = {"sid": sid.lower(), "path": tilde(m[0]), "size": os.path.getsize(m[0]), "cwd": None, "branch": None,
            "model": None, "version": None, "started": None, "title": None, "prompts": 0, "replies": 0}
    custom, tools, turns = None, collections.Counter(), []
    with open(m[0], errors="replace") as f:
        for line in f:
            if '"type"' not in line: continue
            try: o = json.loads(line)
            except ValueError: continue
            t, ts = o.get("type"), o.get("timestamp")
            if t == "custom-title": custom = o.get("customTitle") or custom
            elif t == "ai-title": info["title"] = o.get("aiTitle") or info["title"]
            if t not in ("user", "assistant") or o.get("isMeta") or o.get("isSidechain"): continue
            info["started"] = info["started"] or ts
            info["cwd"] = info["cwd"] or o.get("cwd")
            info["branch"] = o.get("gitBranch") or info["branch"]
            info["version"] = o.get("version") or info["version"]
            text = "\n".join(b.get("text", "") for b in blocks(o) if b.get("type") == "text").strip()
            if t == "assistant":
                info["model"] = (o.get("message") or {}).get("model") or info["model"]
                for b in blocks(o):
                    if b.get("type") == "tool_use": tools[b.get("name") or "?"] += 1
                if text:
                    info["replies"] += 1
                    turns.append({"role": "assistant", "ts": ts, "text": clip(text)})
            elif text and not text.startswith("<"):
                info["prompts"] += 1
                turns.append({"role": "user", "ts": ts, "text": clip(text)})
    info["title"] = custom or info["title"]
    info["modified"] = datetime.datetime.fromtimestamp(os.path.getmtime(m[0])).strftime("%Y-%m-%d %H:%M")
    info["tools"] = tools.most_common()
    info["omitted"] = max(0, len(turns) - MAX_TURNS)
    info["turns"] = turns[-MAX_TURNS:]
    prompts = [x["text"] for x in turns if x["role"] == "user"]
    info["first"], info["last"] = (prompts[0], prompts[-1]) if prompts else (None, None)
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
                   "restore": resume_line(conv, fg, cwd), "split": split, "screen": screen,
                   "snippet": f"{tilde(restore_bin)} {tilde(f'{out}/{stamp}.json')} {s['id']}"}
            snap["sessions"].append(rec)
            wsn["sessions"].append(rec["id"])
        wsn["snippet"] = f"{tilde(restore_bin)} {tilde(f'{out}/{stamp}.json')} --workspace {ws['id']}"
        win["workspaces"].append(wsn)
    snap["windows"].append(win)

jpath = f"{out}/{stamp}.json"
snap["file"] = tilde(jpath)
json.dump(snap, open(jpath, "w"), indent=1, ensure_ascii=False)

data = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/")
page = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.html")).read()
hpath = f"{out}/{stamp}.html"
open(hpath, "w").write(page.replace("/*__SNAPSHOT__*/null", data, 1))
latest = f"{out}/latest.html"
if os.path.lexists(latest): os.remove(latest)
os.symlink(os.path.basename(hpath), latest)
print(hpath)
