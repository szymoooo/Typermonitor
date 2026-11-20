# Typermonitor — dashboard prototype

Initial UI for the Typermonitor project: a dashboard to manage tipster profiles and later monitor new picks.

## Included
- `index.html` — standalone interactive dashboard
- add profile by pasted URL (extracts profile ID)
- enable/disable and remove profiles
- duplicate profile prevention
- profile list and summary cards
- browser `localStorage` persistence
- empty history table prepared for pick records

## Run locally
Open `index.html` in any modern browser. This version has no build step.

## Current status / limitations
This is a frontend prototype only. It does **not** scrape ZawódTyper, poll in the background, capture picks, or send alerts. The site parser/API has not been verified. The next implementation step is a server-side worker, persistent database, scheduled polling (target every 3–5 minutes), duplicate detection, and notification delivery (Telegram is a practical first option).
