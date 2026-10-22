# Poetry Everyday

A random poem from [PoetryDB](https://poetrydb.org/) pops up once a day at a random time. The popup has two buttons: **Dismiss** and **Open in Text Editor**.

## Install / uninstall

```bash
./install.sh            # copies the script to ~/.poetry-everyday and adds the cron job
./uninstall.sh          # removes the cron job
./uninstall.sh --purge  # also deletes ~/.poetry-everyday (saved poems, log)
```

Run `./install.sh` again after editing `poem_of_the_day.py` so the installed copy gets your changes.

## How it works

Cron can't run a job "once at a random time", and it skips jobs that come due while the Mac is off or asleep. So cron runs the script **every 15 minutes**, and the script decides what to do:

1. The first run of the day picks a random target time between 9:00am and 9:00pm and saves it in `~/.poetry-everyday/state.json`.
2. Runs before the target time exit without doing anything.
3. The first run at or after the target time fetches a poem, saves it, shows the popup, and marks the day as `sent`.
4. Once a day is marked `sent`, every later run that day does nothing. You never get a second popup.

If your Mac is off or asleep at the target time, the first run after it wakes up shows the poem. If you first turn the computer on mid-day, the target is picked from what's left of the window. If you first turn it on after 9pm, the poem shows right away. If the network is down, the day isn't marked `sent`, so the next run tries again.

## Files

| Path | What |
|---|---|
| `~/.poetry-everyday/poem_of_the_day.py` | Installed copy that cron runs |
| `~/.poetry-everyday/state.json` | Today's target time and whether the poem has been sent |
| `~/.poetry-everyday/poems/` | Every poem you've received, as `.txt` |
| `~/.poetry-everyday/log.txt` | Log output |

## Handy commands

```bash
python3 ~/.poetry-everyday/poem_of_the_day.py --status   # see today's scheduled time
python3 ~/.poetry-everyday/poem_of_the_day.py --force    # show a poem now (ignores schedule)
crontab -l                                                # confirm the cron job exists
```

## Settings

Edit the constants at the top of `poem_of_the_day.py`, then re-run `./install.sh`:

- `WINDOW_START_HOUR` / `WINDOW_END_HOUR`: earliest and latest time a poem can be scheduled.
- `MAX_POEM_LINES`: only poems with at most this many lines (default 14) are picked, so they fit in the popup. This uses PoetryDB's `linecount,random/-14;1` query, which returns one random poem of 14 lines or fewer.
