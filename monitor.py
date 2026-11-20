import json, os, re, sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(BASE, "data", "profiles.json")
STATE_FILE = os.path.join(BASE, "data", "monitor_state.json")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "").strip()
WA_PHONE = os.getenv("WHATSAPP_PHONE", "").strip()      # CallMeBot, np. 48123456789
WA_APIKEY = os.getenv("WHATSAPP_APIKEY", "").strip()
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()        # ntfy.sh — push na telefon, bez konta
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").strip().rstrip("/")

# Powyżej tylu nowych typów naraz wysyłamy jedno zbiorcze powiadomienie
# (ochrona przed zalewem, np. po zmianie wyglądu strony).
MAX_INDIVIDUAL_ALERTS = 8


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


def parse_profile(html, profile_url):
    soup = BeautifulSoup(html, "html.parser")
    name = ""
    for selector in ("span.font-medium.text-2xl", "h1", "title"):
        el = soup.select_one(selector)
        if el:
            name = el.get_text(" ", strip=True)
            if name:
                break
    tips = {}
    for a in soup.select('a[href*="#comment-"]'):
        href = a.get("href", "")
        m = re.search(r"#comment-(\d+)", href)
        if not m:
            continue
        ext = m.group(1)
        img = a.select_one("img[alt]")
        discipline = img.get("alt", "").strip() if img else ""
        event = ""
        for sp in a.select("span"):
            value = sp.get_text(" ", strip=True)
            if " vs " in value.lower():
                event = value
                break
        odds_el = a.select_one("span[style*='color'], .font-bold.text-sm, .font-bold")
        odds = odds_el.get_text(" ", strip=True) if odds_el else ""
        lines = [x.strip() for x in a.stripped_strings if x.strip()]
        excluded = {"Dziś", "Jutro", "Wczoraj"}
        candidates = [x for x in lines
                      if x not in excluded
                      and not re.fullmatch(r"\d{1,2}:\d{2}", x)
                      and x != event and x != odds]
        pick = candidates[-1] if candidates else ""
        tips[ext] = {"id": ext, "event": event, "pick": pick, "odds": odds,
                     "discipline": discipline, "url": urljoin(profile_url, href)}
    return name, list(tips.values())


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
            lines = text.split("\n")
            headers = {"Title": "Typermonitor", "Priority": "high", "Tags": "bell"}
            link = next((l for l in lines if l.startswith("http")), "")
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
    parts = [f"🆕 NOWY TYP — {profile_name}"]
    parts.append(t["event"] or "Nowy wpis")
    if t["pick"]:
        parts.append(t["pick"])
    parts.append(f"Kurs: {t['odds'] or 'brak'}")
    if t["discipline"]:
        parts.append(t["discipline"])
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

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    }
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        for item in enabled:
            try:
                url, tid = normalize(item["url"])
                response = client.get(url)
                response.raise_for_status()
                name, tips = parse_profile(response.text, url)
                label = name or tid
                previous = state["profiles"].get(tid)
                current = {t["id"] for t in tips}

                if previous is None:
                    # Pierwszy odczyt = baseline, bez alertów dla starych typów.
                    state["profiles"][tid] = {"url": url, "name": name, "seen": sorted(current)}
                    msg = f"BASELINE {label}: {len(current)} existing entries"
                    if not current:
                        msg += " (UWAGA: 0 wpisów — profil pusty albo parser nie pasuje do strony)"
                    print(msg)
                    continue

                old = set(previous.get("seen", []))
                if old and not current:
                    # Strona zwróciła 0 wpisów mimo historii: zmiana HTML / blokada — nie ruszamy stanu.
                    errors += 1
                    print(f"ERROR {label}: 0 wpisów, a wcześniej było {len(old)} — pomijam (zmiana HTML/blokada?)")
                    continue

                new = [t for t in tips if t["id"] not in old]
                seen = set(old)
                if new:
                    ordered = list(reversed(new))  # od najstarszego
                    pname = name or previous.get("name") or tid
                    if len(ordered) > MAX_INDIVIDUAL_ALERTS:
                        lines = [f"{t['event'] or t['id']} — {t['pick']} @ {t['odds'] or '?'}" for t in ordered[:15]]
                        text = f"🆕 {len(ordered)} nowych typów — {pname}\n" + "\n".join(lines) + f"\n{url}"
                        if notify(text) or not notifications_configured():
                            seen |= {t["id"] for t in ordered}
                    else:
                        for t in ordered:
                            # Oznaczamy jako widziany dopiero po udanej wysyłce — inaczej alert przepadnie.
                            if notify(format_tip(pname, t)) or not notifications_configured():
                                seen.add(t["id"])
                                print("NEW TIP", tid, t["id"], t["event"], t["odds"])
                            else:
                                print("Wysyłka nieudana, ponowię w kolejnym przebiegu:", t["id"])
                                errors += 1
                state["profiles"][tid] = {"url": url, "name": name or previous.get("name", ""),
                                          "seen": sorted(seen | (current - {x["id"] for x in new}))}
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
        sys.exit("Wszystkie włączone profile zakończyły się błędem — sprawdź dostęp do strony / parser.")


if __name__ == "__main__":
    main()
