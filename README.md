# Typermonitor — GitHub Actions

GitHub Actions uruchamia `monitor.py` co 5 minut (`*/5 * * * *`), sprawdza profile z `data/profiles.json` na zawodtyper.pl i wysyła powiadomienie, gdy pojawi się nowy typ. Nie wymaga serwera.

## Uruchomienie
1. Folder `.github/workflows/` musi być w repozytorium (przy wgrywaniu ZIP-a przez przeglądarkę folder z kropką bywa pomijany — dodawaj pliki przez `git push`, nie przez „Upload files").
2. Settings → Actions → General: Actions dozwolone, *Workflow permissions* = **Read and write**.
3. Dodaj sekrety (Settings → Secrets and variables → Actions) — patrz niżej.
4. Actions → „Typermonitor — sprawdzanie profili” → **Run workflow**. W logu pierwszy przebieg pokaże `BASELINE` dla każdego profilu (stare typy nie są zgłaszane).

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
- Parser szuka `a[href*="#comment-"]` w HTML-u profilu. Jeśli lista typów ładuje się JavaScriptem, w logu zobaczysz `0 existing entries` — wtedy parser trzeba zmienić.
- Repozytorium publiczne ma darmowe minuty Actions; w prywatnym ~288 uruchomień dziennie może przekroczyć limit planu.
