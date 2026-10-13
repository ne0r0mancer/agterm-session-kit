# Sourced by bin/*. Resolves the kit root, agtermctl, jq, python3 and the snapshot dir.
KIT_ROOT=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
SNAP_DIR=${AGT_SNAP_DIR:-$HOME/agterm-snapshots}

pick() { for c in "$@"; do [ -n "$c" ] && [ -x "$c" ] && { echo "$c"; return; }; done; }
CTL=$(pick "${AGTERMCTL:-}" /Applications/agterm.app/Contents/MacOS/agtermctl \
  "$HOME/Applications/agterm.app/Contents/MacOS/agtermctl" "$(command -v agtermctl || true)")
JQ=$(pick /usr/bin/jq "$(command -v jq || true)" /opt/homebrew/bin/jq)
PY=$(pick /usr/bin/python3 "$(command -v python3 || true)")

need() { [ -n "$CTL" ] || { echo "agtermctl not found (set AGTERMCTL)" >&2; exit 1; }
         [ -n "$JQ" ] || { echo "jq not found" >&2; exit 1; }; }

# "<session-id>\t<foreground argv>" for every session in every open window
open_sessions() {
  for w in $("$CTL" window list --json | "$JQ" -r '.result.windows[] | select(.open) | .id'); do
    "$CTL" tree --window "$w" --json |
      "$JQ" -r '.result.tree.workspaces[].sessions[] | [.id, ((.foreground // []) | join(" "))] | @tsv'
  done
}
