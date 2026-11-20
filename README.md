# Typermonitor — GitHub Actions

GitHub Actions uruchamia `monitor.py` według harmonogramu poniżej, sprawdza profile z `data/profiles.json` na zawodtyper.pl i wysyła powiadomienie, gdy pojawi się nowy typ. Nie wymaga serwera.

## Harmonogram (czas polski)
| Dni | Godziny | Częstotliwość |
|---|---|---|
| Pn–Pt | 07:00–14:59 | co 20 min |
| Pn–Pt | 15:00–23:55 | co 5 min |
| So–Nd | 08:00–10:59 | co 20 min |
| So–Nd | 11:00–23:55 | co 5 min |
| codziennie | noc 00:00–07:00 (w weekend do 08:00) | bez sprawdzania |

Cron w GitHubie działa w UTC, a Polska zmienia czas dwa razy w roku, więc w `monitor.yml` zakresy godzin UTC są szersze niż potrzeba, a dokładne okna pilnuje `gate.py` (strefa Europe/Warsaw). Żeby zmienić godziny, edytuj `gate.py` (warunki w `decide`) i, jeśli rozszerzasz zakres, odpowiadające im zakresy cron w `.github/workflows/monitor.yml`. Ręczne uruchomienie (Run workflow) działa o każdej porze.

## Uruchomienie
1. Folder `.github/workflows/` musi być w repozytorium (przy wgrywaniu ZIP-a przez przeglądarkę folder z kropką bywa pomijany — dodawaj pliki przez `git push`, nie przez „Upload files").
2. Settings → Actions → General: Actions dozwolone, *Workflow permissions* = **Read and write**.
3. Dodaj sekrety (Settings → Secrets and variables → Actions) — patrz niżej.
4. Actions → „Typermonitor — sprawdzanie profili” → **Run workflow**. Pierwszy przebieg pokaże w logu `BASELINE ... N existing entries` (N większe od 0) dla każdego profilu (stare typy nie są zgłaszane).

## Powiadomienia
**ntfy (zalecane, bez konta):** zainstaluj aplikację *ntfy* (Android/iOS), kliknij „+” i zasubskrybuj własny, trudny do odgadnięcia temat, np. `typermonitor-x7k2q9m4`. Ten sam tekst wpisz jako sekret `NTFY_TOPIC`. Każdy, kto zna nazwę tematu, może go czytać i pisać, więc traktuj ją jak hasło. Na iOS powiadomienia mogą docierać z opóźnieniem — w ustawieniach aplikacji włącz powiadomienia i sprawdź tryb „Nie przeszkadzać”.

**Telegram (zalecane, najprościej):** utwórz bota u `@BotFather`, napisz do niego cokolwiek, chat id odczytasz z `https://api.telegram.org/bot<TOKEN>/getUpdates`. Sekrety: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

**WhatsApp (opcjonalnie, przez CallMeBot):** wyślij wiadomość aktywacyjną do bota CallMeBot zgodnie z instrukcją na callmebot.com, dostaniesz klucz API. Sekrety: `WHATSAPP_PHONE` (np. `48123456789`), `WHATSAPP_APIKEY`. To darmowa usługa osób trzecich, bywa zawodna.

Można skonfigurować oba kanały naraz. Alert uznawany jest za wysłany, gdy dotrze na którykolwiek.

## Profile
Edytuj `data/profiles.json` na GitHubie:
```json
[
  {"url":"https://zawodtyper.pl/typer/6560/","enabled":true}
]
```
`"enabled": false` wyłącza profil.

## Stan
`data/monitor_state.json` (commitowany automatycznie) przechowuje identyfikatory widzianych typów. Plik zmienia się tylko przy nowym typie lub raz dziennie (data sprawdzenia).

## Zabezpieczenia
- Typ jest oznaczany jako widziany dopiero po udanej wysyłce, więc nieudany alert zostanie ponowiony.
- Strona zwracająca 0 wpisów dla profilu z historią jest traktowana jako błąd (zmiana HTML/blokada), a stan nie jest nadpisywany.
- Więcej niż 8 nowych typów naraz → jedna wiadomość zbiorcza.

## Ograniczenia
- GitHub nie gwarantuje punktualności crona; opóźnienia rzędu kilku–kilkunastu minut są normalne.
- Lista typów nie jest w HTML profilu (ładuje ją JavaScript), więc monitor pyta to samo API, z którego korzysta strona (`NP_ajax.php`, `api_get_user_bets`). To nieoficjalny endpoint: jeśli właściciel serwisu go zmieni, w logu pojawi się `ERROR`. Zapytań jest niewiele (po jednym na profil co 5 minut), proszę nie skracać interwału.
- Repozytorium publiczne ma darmowe minuty Actions; w prywatnym ~288 uruchomień dziennie może przekroczyć limit planu.
