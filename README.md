# Typermonitor — GitHub Actions

Ta wersja nie wymaga Railway ani stale działającego backendu. GitHub Actions uruchamia `monitor.py` według harmonogramu `*/5 * * * *` (co 5 minut). GitHub może opóźniać zadania cron; nie jest to gwarancja startu dokładnie co 300 sekund.

## Instalacja
1. Rozpakuj ZIP i wgraj całą zawartość do istniejącego repozytorium `szymoooo/Typermonitor`, nadpisując poprzednie pliki.
2. W GitHub otwórz Settings → Actions → General. Upewnij się, że Actions są dozwolone, a workflow ma uprawnienia zapisu do repozytorium (workflow deklaruje `contents: write`).
3. Otwórz Actions → `Typermonitor — sprawdzanie profili` → Run workflow, aby uruchomić pierwszy test ręcznie.
4. W logach sprawdź, czy profile są pobierane i czy parser widzi wpisy.

## Dodawanie / wyłączanie profili
W tej architekturze nie ma serwera API, więc panel statyczny nie może bezpiecznie zapisywać zmian do plików repozytorium. Profile dodaje się w `data/profiles.json` przez GitHub (Edit → Commit changes).
Format:
```json
[
  {"url":"https://zawodtyper.pl/typer/6560/","enabled":true},
  {"url":"https://zawodtyper.pl/typer/12345/","enabled":true}
]
```
Można dodać dowolną liczbę profili. Wyłączenie: `"enabled": false`.

## Telegram
GitHub repo → Settings → Secrets and variables → Actions → New repository secret:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Bez tych sekretów monitoring zapisuje nowe wpisy w stanie, ale nie wysyła alertów.

## Jak działa historia
`data/monitor_state.json` jest aktualizowany i commitowany przez GitHub Actions. Pierwsze uruchomienie dla nowego profilu zapisuje stan początkowy bez alertów dla archiwalnych typów. Następne uruchomienia alarmują tylko dla nowych identyfikatorów `comment-ID`.

## Ważne ograniczenia
- Cron `*/5` oznacza żądany harmonogram co 5 minut, ale GitHub nie gwarantuje punktualnego uruchomienia. GitHub może też ograniczać harmonogramy w okresach dużego obciążenia.
- W tej wersji panel GitHub Pages jest stroną informacyjną. Dodawanie profili odbywa się przez edycję `data/profiles.json`, nie przez formularz na stronie. To ograniczenie wynika z braku stale działającego API.
- Parser szuka linków `a[href*="#comment-"]` w pobranym HTML profilu. Przekazany fragment HTML jest zgodny z tym selektorem, ale trzeba potwierdzić, że cała lista typów jest obecna w odpowiedzi HTTP profilu, a nie doładowywana przez JavaScript. Test jest w logach Actions.
- Pierwsze wykrycie profilu ustanawia baseline: stare typy nie są zgłaszane.
- Repozytorium powinno być publiczne albo prywatne z włączonymi minutami GitHub Actions. Limity zależą od planu i widoczności repozytorium.

## Zmiana interwału
W `.github/workflows/monitor.yml` zmień cron. GitHub Actions nie obsługuje harmonogramu częściej niż raz na 5 minut.
