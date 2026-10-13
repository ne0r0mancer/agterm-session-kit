#!/bin/bash
# Regenerate docs/screenshot.png from the fake docs/demo/sample-snapshot.json (no real data).
set -eu
cd "$(dirname "$0")"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
/usr/bin/python3 -c '
import json, sys
d = json.dumps(json.load(open("sample-snapshot.json")), ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
open(sys.argv[1], "w").write(open("../../lib/page.html").read().replace("/*__SNAPSHOT__*/null", d, 1))
' "$tmp/demo.html"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --user-data-dir="$tmp/profile" \
  --disable-gpu --hide-scrollbars --force-device-scale-factor=2 --window-size=1400,1040 --virtual-time-budget=3000 \
  --force-prefers-color-scheme=light --screenshot="$PWD/../screenshot.png" "file://$tmp/demo.html#7FDE503A-124C-5534-A407-6054A231BAF4" 2>/dev/null
echo "wrote docs/screenshot.png"
