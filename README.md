# agterm-session-kit

Scripts for [agterm](https://agterm.com) users who keep many workspaces and sessions, most of them running
Claude Code. They let you:

- **snapshot** the whole sidebar tree into a browsable HTML page, with each session's directory, running
  command, Claude conversation and last screen lines;
- **restore** any session or workspace on demand by pasting a one-line snippet copied from that page;
- **upgrade** agterm without losing track of which Claude conversation ran in which session.

Closing a session frees the memory of everything it runs. The snapshot is what lets you close sessions
freely and bring back the ones you need later, each with its own conversation, even when several share a
directory.

## Requirements

- macOS with agterm installed (`/Applications` or `~/Applications`, or set `AGTERMCTL`)
- `jq` and `python3` (both ship with recent macOS / Command Line Tools)
- `fish`, only for the optional `claude` wrapper

## Install

```sh
git clone <this repo> ~/dev/agterm-session-kit
cd ~/dev/agterm-session-kit
./install.sh            # links bin/* into ~/.local/bin
./install.sh --fish     # also installs the fish `claude` wrapper (backs up an existing one)
```

Optional: run the snapshot from agterm's command palette by adding to `~/.config/agterm/keymap.conf`:

```
command "snapshot sessions"  ~/.local/bin/agt-snapshot --open
```

## Commands

| command | what it does |
|---|---|
| `agt-snapshot [--open]` | saves `~/agterm-snapshots/<stamp>.json` + `.html`, `latest.html` points to the newest |
| `agt-restore [--dry-run] SNAP.json ID...` | recreates sessions; a session still open is selected instead |
| `agt-restore [--dry-run] SNAP.json --workspace WS_ID` | recreates every session of a workspace |
| `agt-resume-open [--dry-run] [SNAP.json]` | after a restart: types the restore line into each snapshot session that is open again but idle at a prompt |
| `agt-upgrade` | backs up agterm state, `brew upgrade --cask agterm`, relaunches. Run from Terminal.app after quitting agterm |

You rarely type `agt-restore` yourself: the HTML page has a **copy** button per session and per workspace that
puts the exact command on the clipboard. Paste it into any agterm shell.

Click a session to open its details beside the tree (full screen on a narrow window): directory, running
command, ids, the Claude conversation's title, branch, model, tools used and its message timeline (your
prompts and Claude's replies, searchable, newest first), plus the last 60 screen lines. ↑/↓ moves between
sessions, Esc closes, `/` focuses the filter, and the URL hash links straight to a session.

Snapshots go to `~/agterm-snapshots`; set `AGT_SNAP_DIR` to change it.

## How a session is restored

`agt-restore` creates a new session in the frontmost window, in the workspace with the same name (created if
missing), with the saved name and directory, then types one line into it:

1. if the session was running a program other than Claude (`make dev-watch`), that command;
2. else if it has a Claude conversation, `claude --resume <conversation-id>`;
3. else nothing, a plain shell.

The conversation is found, in order, from the running `claude` process (`~/.claude/sessions/<pid>.json`
mapped to the agterm session through its `AGTERM_SESSION_ID`), from `--resume`/`--session-id` in the running
command, or from a transcript named after the agterm session id (what the fish wrapper creates). Resuming by
id is what keeps several conversations in one directory apart; `claude --continue` would pick the newest.

## The fish `claude` wrapper

`fish/claude.fish` pins each agterm tab to its own conversation: inside agterm, plain `claude` starts
`--session-id <tab id>` the first time and `--resume <tab id>` afterwards. With agterm's
*Re-run commands* restore mode, a restart replays the tab's `claude` and lands back in the same conversation.
Explicit `--resume`, `--continue`, `-p` and subcommands pass through untouched.

## Upgrading agterm

Quitting agterm ends every shell and agent in it. The conversations are saved on disk, so nothing is lost,
but take a snapshot first so you can bring each one back to its own session:

```sh
agt-snapshot          # inside agterm
# Cmd-Q to quit agterm, then in Terminal.app:
agt-upgrade
# back in agterm, once sessions are restored:
agt-resume-open --dry-run   # check
agt-resume-open
```

Window and session state lives in `~/Library/Application Support/agterm/` and survives the upgrade;
`agt-upgrade` also copies it into the snapshot directory first. To roll back the state, quit agterm and copy
the backup back into that folder.

## What is not restored

- scrollback and the live processes: a restored session is a new shell running the saved line
- windows that were closed when the snapshot was taken (`tree` only reports open windows)
- scratch terminals and overlays

## Privacy

Snapshots hold full command lines and the last screen lines of every session, which can include tokens or
keys. Files are created `0600` and `.gitignore` excludes them; do not commit or share a snapshot.

## Notes

`docs/discussion-suspend.md` is a draft agterm feature request for a built-in suspend/resume of sessions and
workspaces, which would make most of this kit unnecessary.
