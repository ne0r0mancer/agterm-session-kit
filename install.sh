#!/bin/bash
# Link bin/* into ~/.local/bin (or DEST). --fish also installs the per-tab `claude` fish wrapper.
# Files the kit did not create are left alone unless --force, which backs each one up first.
# Usage: ./install.sh [--fish] [--force] [DEST]
set -eu
root=$(cd "$(dirname "$0")" && pwd)
fish= force= dest=$HOME/.local/bin
for a in "$@"; do
  case $a in
    --fish) fish=1 ;;
    --force) force=1 ;;
    -h|--help) sed -n '2,4p' "$0" | sed 's/^# //'; exit 0 ;;
    -*) echo "unknown option: $a" >&2; exit 1 ;;
    *) dest=$a ;;
  esac
done
stamp=$(date +%s); skipped=0

backup() { mv "$1" "$1.bak.$stamp"; echo "backed up $1 -> $1.bak.$stamp"; }

mkdir -p "$dest"
chmod +x "$root"/bin/*
for f in "$root"/bin/*; do
  t=$dest/$(basename "$f")
  if [ -e "$t" ] || [ -L "$t" ]; then
    if [ "$(readlink "$t" || true)" = "$f" ]; then echo "up to date $t"; continue; fi
    if [ -z "$force" ]; then echo "skipped $t: exists and is not this kit's (use --force)"; skipped=1; continue; fi
    backup "$t"
  fi
  ln -s "$f" "$t"; echo "linked $t"
done
case ":$PATH:" in *":$dest:"*) ;; *) echo "note: $dest is not on PATH";; esac

if [ -n "$fish" ]; then
  fn=$HOME/.config/fish/functions/claude.fish
  mkdir -p "$(dirname "$fn")"
  if [ -f "$fn" ] && cmp -s "$fn" "$root/fish/claude.fish"; then
    echo "up to date $fn"
  elif [ -e "$fn" ] && [ -z "$force" ]; then
    echo "skipped $fn: a different claude function exists (use --force)"; skipped=1
  else
    [ -e "$fn" ] && backup "$fn"
    cp "$root/fish/claude.fish" "$fn"; echo "installed $fn"
  fi
fi
[ "$skipped" = 0 ] || echo "some files were skipped; rerun with --force to replace them (originals are backed up)"
