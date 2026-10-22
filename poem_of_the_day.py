#!/usr/bin/env python3
"""Show a random poem from PoetryDB once per day, at a random time.

Cron runs this script every few minutes. The script itself decides whether
it is time to show today's poem:

  1. The first run of each day picks a random target time in the window
     (WINDOW_START_HOUR..WINDOW_END_HOUR) and saves it to the state file.
  2. Each later run exits quietly until the target time has passed.
  3. The first run at/after the target time shows the poem and records
     that today's poem was sent, so no further popups appear that day.

If the computer is off or asleep at the target time, the next cron run after
it wakes up will see that the target has passed and show the poem then.

Usage:
  poem_of_the_day.py            normal (cron) mode
  poem_of_the_day.py --force    show a poem right now, ignoring the schedule
  poem_of_the_day.py --status   print today's schedule and exit
"""

import fcntl
import json
import random
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

WINDOW_START_HOUR = 9   # earliest time a poem may be scheduled (9:00 am)
WINDOW_END_HOUR = 21    # latest time a poem may be scheduled (9:00 pm)
MAX_POEM_LINES = 14     # only pick poems short enough to fit in the popup

# "linecount/-14" means 14 lines or fewer; "random/1" picks one such poem.
API_URL = f"https://poetrydb.org/linecount,random/-{MAX_POEM_LINES};1"
APP_DIR = Path.home() / ".poetry-everyday"
STATE_FILE = APP_DIR / "state.json"
LOCK_FILE = APP_DIR / ".lock"
POEMS_DIR = APP_DIR / "poems"

OPEN_BUTTON = "Open in Text Editor"
DISMISS_BUTTON = "Dismiss"

DIALOG_SCRIPT = """
on run argv
    set theTitle to item 1 of argv
    set theBody to item 2 of argv
    activate
    set r to display dialog theBody with title theTitle ¬
        buttons {"%s", "%s"} default button "%s" with icon note
    return button returned of r
end run
""" % (DISMISS_BUTTON, OPEN_BUTTON, DISMISS_BUTTON)


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def todays_state(now):
    """Return today's state, picking a random target time if this is the first run today."""
    state = load_state()
    if state.get("date") == now.date().isoformat():
        return state

    window_start = now.replace(hour=WINDOW_START_HOUR, minute=0, second=0, microsecond=0)
    window_end = now.replace(hour=WINDOW_END_HOUR, minute=0, second=0, microsecond=0)
    # Don't schedule in the past: if the computer was first turned on mid-day,
    # pick from what's left of the window (or right now, if the window is over).
    earliest = max(now, window_start)
    if earliest >= window_end:
        target = now
    else:
        span = (window_end - earliest).total_seconds()
        target = earliest + timedelta(seconds=random.uniform(0, span))

    state = {"date": now.date().isoformat(), "target": target.isoformat(timespec="seconds"), "sent": False}
    save_state(state)
    log(f"Scheduled today's poem for {target:%H:%M}")
    return state


def fetch_poem():
    """Return a random poem with at most MAX_POEM_LINES lines."""
    req = urllib.request.Request(API_URL, headers={"User-Agent": "poetry-everyday"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    poem = data[0] if isinstance(data, list) and data else data
    if "lines" not in poem:
        raise ValueError(f"Unexpected API response: {data!r}")
    return poem


def save_poem(poem):
    POEMS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", poem["title"]).strip("-")[:60] or "poem"
    path = POEMS_DIR / f"{date.today().isoformat()}-{slug}.txt"
    body = "\n".join(poem["lines"])
    path.write_text(f"{poem['title']}\nby {poem['author']}\n\n{body}\n")
    return path


def show_dialog(poem):
    """Show the popup. Returns the button clicked, or None if the dialog failed to appear."""
    body = "\n".join(poem["lines"])
    text = f"{poem['title']}\nby {poem['author']}\n\n{body}"

    result = subprocess.run(
        ["/usr/bin/osascript", "-", "Poem of the Day", text],
        input=DIALOG_SCRIPT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        log(f"Dialog failed: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def deliver_poem():
    """Fetch, save, and display a poem. Returns True if the popup was shown."""
    poem = fetch_poem()
    path = save_poem(poem)
    log(f"Showing '{poem['title']}' by {poem['author']} (saved to {path})")
    button = show_dialog(poem)
    if button == OPEN_BUTTON:
        subprocess.run(["/usr/bin/open", "-t", str(path)])
    return button is not None


def main():
    APP_DIR.mkdir(parents=True, exist_ok=True)

    if "--force" in sys.argv:
        deliver_poem()
        return

    now = datetime.now()
    state = todays_state(now)

    if "--status" in sys.argv:
        print(json.dumps(state, indent=2))
        return

    if state["sent"] or now < datetime.fromisoformat(state["target"]):
        return

    # Hold a lock so overlapping cron runs can't show two popups.
    lock = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return

    # Mark as sent *before* the popup appears: the dialog stays open until you
    # click a button, and later cron runs must not show a second one meanwhile.
    state["sent"] = True
    save_state(state)
    try:
        shown = deliver_poem()
    except Exception as e:  # network down, API error, etc.
        log(f"Could not deliver poem: {e}")
        shown = False
    if not shown:
        # Retry on the next cron run.
        state["sent"] = False
        save_state(state)


if __name__ == "__main__":
    main()
