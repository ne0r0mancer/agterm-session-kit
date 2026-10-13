#!/bin/bash
# Link bin/* into ~/.local/bin (or $1). With --fish, also install the per-tab `claude` fish wrapper.
set -eu
root=$(cd "$(dirname "$0")" && pwd)
fish=; [ "${1:-}" = --fish ] && { fish=1; shift; }
dest=${1:-$HOME/.local/bin}
mkdir -p "$dest"
chmod +x "$root"/bin/*
for f in "$root"/bin/*; do ln -sfn "$f" "$dest/$(basename "$f")"; echo "linked $dest/$(basename "$f")"; done
case ":$PATH:" in *":$dest:"*) ;; *) echo "note: $dest is not on PATH";; esac

if [ -n "$fish" ]; then
  fn=$HOME/.config/fish/functions/claude.fish
  mkdir -p "$(dirname "$fn")"
  if [ -f "$fn" ] && ! cmp -s "$fn" "$root/fish/claude.fish"; then
    cp "$fn" "$fn.bak.$(date +%s)"; echo "backed up existing $fn"
  fi
  cp "$root/fish/claude.fish" "$fn"; echo "installed $fn"
fi
