#!/usr/bin/env bash
# cs-eco statusline: "eco on · saved ≈12.3k tok · ctx 43%".
#
# Claude Code pipes its statusline JSON to stdin. Point `statusLine.command` in
# your own settings at this file (`/cs-eco snippet` prints the exact path), or
# call it from your existing statusline script with the same stdin. The plugin
# never writes your settings for you.
here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
exec python3 "$here/eco_ctl.py" statusline
