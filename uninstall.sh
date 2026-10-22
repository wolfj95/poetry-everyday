#!/bin/bash
# Removes the poetry-everyday cron job. Pass --purge to also delete
# ~/.poetry-everyday (including saved poems and the log).
set -euo pipefail

MARKER="# poetry-everyday"
{ crontab -l 2>/dev/null | grep -v "$MARKER" || true; } | crontab -
echo "Removed cron job."

if [[ "${1:-}" == "--purge" ]]; then
  rm -rf "$HOME/.poetry-everyday"
  echo "Deleted ~/.poetry-everyday"
fi
