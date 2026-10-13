# Claude Code: per-agterm-tab session resume.
# Binds each tab's Claude Code session id to the tab's own uuid (AGTERM_SESSION_ID),
# so restoring the terminal resumes that tab's own conversation instead of starting fresh.
# Requires: agterm (exports AGTERM_SESSION_ID, restores running commands) + fish.
function claude --description "Claude Code, pinned to this agterm tab's session"
    set -l sid (string lower -- "$AGTERM_SESSION_ID")

    # Not in an agterm tab -> passthrough.
    if test -z "$sid"
        command claude $argv
        return
    end

    if test (count $argv) -ge 2
        and contains -- $argv[1] --session-id -r --resume
        and test (string lower -- "$argv[2]") = "$sid"
        # Restore replayed our own flag -> drop it and re-decide below.
        if test (count $argv) -gt 2
            set argv $argv[3..-1]
        else
            set argv
        end
    else
        # User steering a session, subcommand, or headless run -> hand off untouched.
        for a in $argv
            if contains -- $a -r --resume --session-id -c --continue -p --print -v --version -h --help mcp update doctor config install migrate-installer setup-token
                command claude $argv
                return
            end
            if string match -qr -- '^(-r|--resume|--session-id)=' $a
                command claude $argv
                return
            end
        end
    end

    # Does this tab's session already exist on disk?
    set -l f ~/.claude/projects/*/$sid.jsonl
    if test (count $f) -gt 0
        command claude --resume "$sid" $argv
    else
        command claude --session-id "$sid" $argv
    end
end
