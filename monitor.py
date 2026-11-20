import json, os, re, sys
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx

BASE = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(BASE, "data", "profiles.json")
STATE_FILE = os.path.join(BASE, "data", "monitor_state.json")

API_URL = "https://zawodtyper.pl/wp-content/NP_ajax.php"  # to samo API, którego używa strona profilu

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "").strip()
WA_PHONE = os.getenv("WHATSAPP_PHONE", "").strip()      # CallMeBot, np. 48123456789
WA_APIKEY = os.getenv("WHATSAPP_APIKEY", "").strip()
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()        # ntfy.sh — push na telefon, bez konta
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").strip().rstrip("/")

# Powyżej tylu nowych typów naraz wysyłamy jedno zbiorcze powiadomienie.
MAX_INDIVIDUAL_ALERTS = 8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def normalize(url):
    u = urlparse(url)
    if u.scheme not in ("http", "https") or u.netloc.lower() not in ("zawodtyper.pl", "www.zawodtyper.pl"):
        raise ValueError("Nieprawidłowa domena profilu: " + url)
    m = re.fullmatch(r"/typer/(\d+)/?", u.path)
    if not m:
        raise ValueError("Adres musi mieć postać https://zawodtyper.pl/typer/ID/")
    return f"https://zawodtyper.pl/typer/{m.group(1)}/", m.group(1)


def fetch_name(client, url):
    """Nazwa typera z <title> strony profilu (używane tylko, gdy jeszcze jej nie znamy)."""
    try:
        r = client.get(url)
        r.raise_for_status()
        m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    except Exception as e:
        print("Nie udało się pobrać nazwy:", type(e).__name__)
    return ""


def fetch_tips(client, tid, profile_url):
    r = client.post(API_URL, json={"endpoint": "api_get_user_bets", "user_id": int(tid)},
                    headers={"Origin": "https://zawodtyper.pl", "Referer": profile_url})
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, dict) or not payload.get("success") or not isinstance(payload.get("data"), list):
        raise ValueError("Nieoczekiwana odpowiedź API: " + str(payload)[:150])
    tips = []
    for b in payload["data"]:
        cid = str(b.get("comment_id", "")).strip()
        if not cid or b.get("post_status", "publish") != "publish":
            continue
        tips.append({
            "id": cid,
            "event": (b.get("match_name") or "").strip(),
            "pick": (b.get("type") or "").strip(),
            "odds": str(b.get("rate") or "").strip(),
            "bookmaker": (b.get("bookmaker") or "").strip(),
            "discipline": (b.get("discipline") or "").strip(),
            "when": ((b.get("bet_day") or "")[:10] + " " + (b.get("hour") or "")).strip(),
            "url": profile_url,
        })
    return tips


def notifications_configured():
    return bool((TG_TOKEN and TG_CHAT) or (WA_PHONE and WA_APIKEY) or NTFY_TOPIC)


def notify(text):
    """Wysyła na wszystkie skonfigurowane kanały. True, jeśli dotarło przynajmniej na jeden."""
    delivered = False
    if TG_TOKEN and TG_CHAT:
        try:
            r = httpx.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                           json={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": True},
                           timeout=20)
            r.raise_for_status()
            delivered = True
        except Exception as e:
            print("Telegram send failed:", type(e).__name__)  # bez treści błędu: URL zawiera token
    if WA_PHONE and WA_APIKEY:
        try:
            r = httpx.get("https://api.callmebot.com/whatsapp.php",
                          params={"phone": WA_PHONE, "text": text, "apikey": WA_APIKEY},
                          timeout=30)
            r.raise_for_status()
            delivered = True
        except Exception as e:
            print("WhatsApp send failed:", type(e).__name__)
    if NTFY_TOPIC:
        try:
            headers = {"Title": "Typermonitor", "Priority": "high", "Tags": "bell"}
            link = next((l for l in text.split("\n") if l.startswith("http")), "")
            if link:
                headers["Click"] = link
            r = httpx.post(f"{NTFY_SERVER}/{NTFY_TOPIC}", content=text.encode("utf-8"),
                           headers=headers, timeout=20)
            r.raise_for_status()
            delivered = True
        except Exception as e:
            print("ntfy send failed:", type(e).__name__)
    return delivered


def format_tip(profile_name, t):
    parts = [f"🆕 NOWY TYP — {profile_name}", t["event"] or "Nowy wpis"]
    if t["pick"]:
        parts.append(t["pick"])
    odds = f"Kurs: {t['odds'] or 'brak'}"
    if t["bookmaker"]:
        odds += f" ({t['bookmaker']})"
    parts.append(odds)
    meta = " · ".join(x for x in (t["discipline"], t["when"]) if x)
    if meta:
        parts.append(meta)
    parts.append(t["url"])
    return "\n".join(parts)


def main():
    profiles = read_json(PROFILES_FILE, [])
    state = read_json(STATE_FILE, {"profiles": {}})
    state.setdefault("profiles", {})
    before = json.dumps(state, sort_keys=True)
    enabled = [p for p in profiles if p.get("enabled", True)]
    errors = 0

    if not notifications_configured():
        print("WARNING: brak skonfigurowanych powiadomień (ntfy/Telegram/WhatsApp) — alerty nie będą wysyłane.")

    with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        for item in enabled:
            try:
                url, tid = normalize(item["url"])
                previous = state["profiles"].get(tid)
                name = (previous or {}).get("name") or fetch_name(client, url)
                tips = fetch_tips(client, tid, url)
                label = name or tid
                current = {t["id"] for t in tips}

                if previous is None:
                    # Pierwszy odczyt = baseline, bez alertów dla starych typów.
                    state["profiles"][tid] = {"url": url, "name": name, "seen": sorted(current)}
                    print(f"BASELINE {label}: {len(current)} existing entries")
                    continue

                old = set(previous.get("seen", []))
                if old and not current:
                    errors += 1
                    print(f"ERROR {label}: 0 wpisów, a wcześniej było {len(old)} — pomijam (zmiana API/blokada?)")
                    continue

                new = [t for t in tips if t["id"] not in old]
                sent_ids = set()
                if new:
                    # API zwraca od najnowszego; alerty wysyłamy od najstarszego.
                    ordered = sorted(new, key=lambda t: int(t["id"]) if t["id"].isdigit() else 0)
                    if len(ordered) > MAX_INDIVIDUAL_ALERTS:
                        lines = [f"{t['event'] or t['id']} — {t['pick']} @ {t['odds'] or '?'}" for t in ordered[-15:]]
                        text = f"🆕 {len(ordered)} nowych typów — {label}\n" + "\n".join(lines) + f"\n{url}"
                        if notify(text) or not notifications_configured():
                            sent_ids = {t["id"] for t in ordered}
                        else:
                            errors += 1
                    else:
                        for t in ordered:
                            # Oznaczamy jako widziany dopiero po udanej wysyłce — inaczej alert przepadnie.
                            if notify(format_tip(label, t)) or not notifications_configured():
                                sent_ids.add(t["id"])
                                print("NEW TIP", tid, t["id"], t["event"], t["odds"])
                            else:
                                print("Wysyłka nieudana, ponowię w kolejnym przebiegu:", t["id"])
                                errors += 1
                new_ids = {t["id"] for t in new}
                state["profiles"][tid] = {"url": url, "name": name or previous.get("name", ""),
                                          "seen": sorted(old | (current - new_ids) | sent_ids)}
                print(f"OK {label}: {len(tips)} entries, {len(new)} new")
            except Exception as e:
                errors += 1
                print(f"ERROR {item.get('url')}: {type(e).__name__}: {e}")

    # Data (bez godziny), żeby plik zmieniał się najwyżej raz dziennie, a nie w każdym przebiegu.
    state["last_check_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state.pop("last_run", None)
    if json.dumps(state, sort_keys=True) != before:
        write_json(STATE_FILE, state)
    print(f"Finished. Errors: {errors}")
    if enabled and errors >= len(enabled):
        sys.exit("Wszystkie włączone profile zakończyły się błędem — sprawdź dostęp do API.")


if __name__ == "__main__":
    main()
