Suspend a session or workspace: end its processes, keep its row, resume in place

I keep 9 workspaces / 32 sessions across 3 windows, most of them Claude Code sessions I finished hours ago but want to come back to. They cost memory I'm not using: right now 22 `claude` processes under agterm hold ~5.3 GB RSS, plus their node/MCP children. Same thing @timurvafin described in #196.

#492 took care of the GPU side (hidden surfaces release their swap chains), so what's left is the processes themselves, and agterm has no way to stop them without also losing the session's place.

## what exists today and why it doesn't fit

- **session close / workspace delete**: ends the processes and keeps a `SessionSnapshot` in Recent Closed, but the row leaves the sidebar, the list is capped at 20, and I have to remember what I closed and dig it out of Reopen Closed one item at a time
- **window close**: in Live mode the daemons keep running with zero clients, so nothing is freed. In Fresh/Re-run modes the shells end, but it only works per window, and closing a non-last window clears the captured foreground commands
- **`cookbook/park-and-resume`**: closest to what I want, but it works by deleting and recreating, so splits, session ids, flags, backgrounds, context and restore pins are lost, it needs a name prefix per project, works only on the frontmost window, and parked work is invisible in agterm (it lives in a JSON file under `~/.agterm-projects`)

The missing piece is a state between "running" and "closed": the row stays where it is, nothing runs behind it.

## proposal

A suspended session keeps its model node and everything `SessionSnapshot` already covers (name, cwd, split layout and ratio, flag, context, backgrounds, restore pins), but has no surfaces and no processes.

- **suspend** (session or workspace, batch like `session close`): capture the foreground command per pane, then tear down surfaces and kill the daemons through the existing close/finalize path. Scratch and overlays go away as they do on close
- **resume**: rebuild the panes from the stored state and run them through `CommandRestore.restorePlan` as a launch would, so precedence stays pin > captured foreground > initial command. With a `SessionStart` hook pinning `claude --resume <id>` via `session restore`, the agent comes back in the same conversation
- **persisted**: a session suspended at quit stays suspended at launch and is not mounted in the deck, which also cuts launch time and memory for people with big trees
- **sidebar**: the row is dimmed. Selecting it either resumes it, or shows a placeholder with a Resume button (open question below)
- **control API**: `session suspend|resume [--target ...]`, `workspace suspend|resume`, and `suspended: true` on the tree session node (omitted otherwise), plus `session.suspended` / `session.resumed` events for hooks. Menu + palette entries go through the same action seam

Auto-suspend after N idle hours stays out of scope. With `statusChangedAt` and the events it's a recipe.

## what is lost on suspend

Scrollback and the live process, same as close. That's the point: the memory goes away. Users who want a process kept alive while hidden already have Live mode plus window close.

## open questions

1. is this in scope, or should it stay a recipe? I think it needs core support: a recipe can't keep a row in the tree without a live shell behind it
2. resume on select, or only an explicit Resume? Resume on select is simpler but makes it easy to wake a session by accident while moving through the sidebar
3. the deck mounts every session eagerly. A suspended session would be the first one deliberately left out of it. `realized: false` already exists for the display-asleep case (#416), is that the right place to hang this?
4. what does Live mode do: kill the daemons (frees memory), or keep them and only drop surfaces (frees almost nothing since #492)? I'd kill them, otherwise the feature does nothing in Live mode

Happy to do the PR if the direction is acceptable.
