"""Decyduje, czy dany przebieg crona ma sprawdzać profile (godziny w czasie polskim).

Harmonogramy w workflow są w UTC, więc obejmują zakres szerszy niż potrzeba
(zmiana czasu zimowy/letni przesuwa godziny o 1 h). Dokładne okna pilnuje ta funkcja.

Okna (Europa/Warszawa):
  Pn–Pt 07:00–14:59  co 20 min   (cron "slow")
  Pn–Pt 15:00–23:59  co 5 min    (cron "fast weekday")
  So–Nd 11:00–23:59  co 5 min    (cron "fast weekend")
  poza tym: bez sprawdzania (noc, weekendowy ranek)
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

SLOW = "*/20 5-14 * * 1-5"
FAST_WEEKDAY = "*/5 13-22 * * 1-5"
FAST_WEEKEND = "*/5 9-22 * * 0,6"


def decide(event, schedule, now):
    dow = now.weekday()              # 0 = poniedziałek … 6 = niedziela
    t = now.hour * 60 + now.minute
    if event != "schedule":
        return True, "uruchomienie ręczne"
    if schedule == SLOW:
        ok = dow < 5 and 7 * 60 <= t < 15 * 60
    elif schedule == FAST_WEEKDAY:
        ok = dow < 5 and t >= 15 * 60
    elif schedule == FAST_WEEKEND:
        ok = dow >= 5 and t >= 11 * 60
    else:
        return True, "nieznany harmonogram — uruchamiam"
    return ok, ("w oknie czasowym" if ok else "poza oknem czasowym")


if __name__ == "__main__":
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    run, why = decide(os.getenv("EVENT", ""), os.getenv("SCHEDULE", ""), now)
    print(f"{now:%A %H:%M} (Warszawa), harmonogram={os.getenv('SCHEDULE') or '-'}: {why} -> {'URUCHAMIAM' if run else 'pomijam'}")
    out = os.getenv("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"run={'true' if run else 'false'}\n")
