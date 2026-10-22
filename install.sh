#!/bin/bash
# Installs poem_of_the_day.py into ~/.poetry-everyday and adds a cron job that
# runs it every 15 minutes. (The script itself makes sure only one poem is
# shown per day, at a random time.)
#
# The script is copied out of this folder because macOS blocks cron from
# reading files in ~/Desktop, ~/Documents, and ~/Downloads.
set -euo pipefail

APP_DIR="$HOME/.poetry-everyday"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
MARKER="# poetry-everyday"
CRON_LINE="*/15 * * * * /usr/bin/python3 $APP_DIR/poem_of_the_day.py >> $APP_DIR/log.txt 2>&1 $MARKER"

mkdir -p "$APP_DIR"
cp "$SRC_DIR/poem_of_the_day.py" "$APP_DIR/poem_of_the_day.py"
chmod +x "$APP_DIR/poem_of_the_day.py"

# Replace any previous poetry-everyday entry, keep everything else.
{ crontab -l 2>/dev/null | grep -v "$MARKER" || true; echo "$CRON_LINE"; } | crontab -

echo "Installed to $APP_DIR"
echo "Cron entry:"
crontab -l | grep "$MARKER"
