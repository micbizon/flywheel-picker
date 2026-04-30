# Changelog - all entries are generated

## 2026-04-30 — Dwufazowy portfolio manager, TOP_N z .env, pre-fetch yfinance w L4, temperature opcjonalna

**Dwufazowy portfolio manager (`layer5_portfolio_manager`):** `05_portfolio_manager.md` zastąpiony dwoma promptami — `05a_portfolio_screener.md` (faza 1: 3 pytania dla wszystkich kandydatów, kompaktowy JSON `{ticker, q1, q2, q3, verdict/preliminary_action, note}`) i `05b_portfolio_allocator.md` (faza 2: tylko BUY_CANDIDATE + pozycje z portfolio, pełne decyzje alokacyjne). `batch.py` przepisany: faza 1 ewaluuje wszystkich, filtruje do BUY+portfolio, faza 2 alokuje; tickery PASS z fazy 1 automatycznie wchodzą do wyniku końcowego. `context_builder_batch.py` otrzymał nową funkcję `build_allocator_context` — lżejszy kontekst dla fazy 2 (phase1 note + bull upside/target + technical entry/stop). Tickery z portfolio sortowane na początek listy kandydatów. Rozwiązuje problem gubienia tickerów przez model przy dużej liczbie kandydatów.

**`TOP_N` przeniesiony do `.env`:** Zmienna `TOP_N` z `layer3_selector/weights.py` czytana przez `os.getenv("TOP_N", "20")`. Dodany wpis w `.env.example`. Jeden punkt konfiguracji dla całego pipeline'u.

**L3 selector — dokładnie TOP_N tickerów do L5:** `run_selector` zmieniony z `non_portfolio[:TOP_N]` na `non_portfolio[:TOP_N - len(portfolio_entries)]`, żeby portfolio + non-portfolio = dokładnie TOP_N. Usunięty `_TOP_N_FOR_PM` z `orchestrator.py`; L5 używa bezpośrednio `[e["ticker"] for e in selected]`.

**Pre-fetch yfinance w L4 (`layer4_cases`):** Ten sam wzorzec co L2 — `get_price_context` wywołany raz sekwencyjnie w `run_cases` przed równoległymi agentami; `price_ctx` przekazany przez `functools.partial` do `run_bull` i `run_bear`. `_run_bull_single` i `_run_bear_single` przyjmują `price_ctx: str` zamiast wywoływać yfinance samodzielnie. Eliminuje do 9 równoległych połączeń HTTP przy 3 agentach × 3 instancjach.

**`temperature` opcjonalna w `llm_client.py`:** `_call_claude` buduje `kwargs` dict i dodaje `temperature` tylko gdy `cfg["temperature"] is not None`. To samo dla `_call_openrouter`. `config_loader.py` zwraca `None` dla temperature gdy `LLM_TEMPERATURE` nie jest ustawione w `.env` (zamiast domyślnych `0.2`). Rozwiązuje błąd `400 temperature is deprecated` dla modeli Claude 4 (np. `claude-opus-4-7`).

---

## 2026-04-29 — Obsługa wielu providerów LLM (claude / openrouter / ollama)

**Refaktoryzacja `get_llm_config()` w `config_loader.py`:** Zmienna `USE_CLAUDE_API=true/false` zastąpiona przez `LLM_PROVIDER` z wartościami `claude | openrouter | ollama`. Env vary przemianowane: `ANTHROPIC_MODEL_ANALYSIS` → `LLM_MODEL_ANALYSIS`, `ANTHROPIC_MODEL_PORTFOLIO_MANAGER` → `LLM_MODEL_PORTFOLIO_MANAGER`, `ANTHROPIC_TEMPERATURE` → `LLM_TEMPERATURE`. Dodana obsługa `OPENROUTER_API_KEY`. `get_active_model()` zwraca teraz `cfg["model_analysis"]` bezpośrednio. `.env.example` zaktualizowany do nowych nazw.

**Nowy provider OpenRouter w `llm_client.py`:** Dodano `_call_openrouter()` — streaming przez `httpx` SSE (`/api/v1/chat/completions`), te same timeouty co claude (`connect=30s, read/write/pool=600s`). `_call_ollama()` zaktualizowany o obsługę `model_tier`. `call_llm()` zmieniony z if/else na dispatch dict `_callers` po kluczu `cfg["provider"]`. `reset_claude_client()` przemianowany na `reset_llm_clients()` (zeruje też `_openrouter_client`). Wszystkie odwołania do kluczy `anthropic_*` w cfg zmienione na nazwy generyczne.

**`orchestrator.py`:** Import `reset_claude_client` → `reset_llm_clients`.

**`prefilter.py`:** Dodano `yf.set_tz_cache_location(None)` przy imporcie modułu — wyłącza SQLite cache yfinance, który tworzył non-daemon wątki blokujące zakończenie procesu po Ctrl+C.

**`CORE_RULES.md`:** Horyzont asymetrii zmieniony z `5 lat` na `3 lata`.

**Dane:** `data/watchlist.yaml` rozbudowana do 87 tickerów (65 ze screenera 25.04 + ręcznie: AMD, ASTS, INTC, RKLB, TXN 27.04; NBIS, CRWD, S, PANW, CYBR, ADYEY, BILL, PCTY, TOST, APPF, CWAN, ASAN, MNDY, VEEV, DOCS, PHVS 28.04). `data/portfolio.yaml`: usunięta pozycja RDW, dodana INTC 10%, COST zmniejszony z 20% do 10%, gotówka zwiększona z 60% do 70%.

---

## 2026-04-28 — Pre-filtr yfinance przed warstwą L1

Stworzono `src/layer1_prescreener/prefilter.py` z `apply_prefilter(tickers)` — odrzuca spółki niespełniające progów finansowych przed wysłaniem do LLM. Pobiera metryki przez `yf.Ticker().info`: market cap ($1B–$100B), revenue growth YoY (≥10%), gross margin (≥35%), current ratio (≥1.2x), net debt/revenue (<3x, obliczane jako `(totalDebt - totalCash) / totalRevenue`), EV/Revenue (0.5x–25x), insider ownership (≥3%). Brak danych (None) lub wyjątek yfinance → ticker przepuszczany bez odrzucania. `run_prescreener_batch` w `main.py` wywołuje `apply_prefilter` na wejściowej liście i uruchamia pętlę LLM tylko na tickerach które przeszły filtr.

---

## 2026-04-28 — Flaga --broker

Dodano `load_broker_tickers()` do `config_loader.py` — publiczny wrapper na `_load_available_tickers()`, zwraca posortowaną listę tickerów z `available-tickers.pdf` lub rzuca `FileNotFoundError` ze ścieżką do pliku. W `pipeline/main.py` dodano flagę `--broker` do grupy mutually exclusive — ładuje wszystkie tickery dostępne u brokera i przekazuje je do `run_pipeline()` zamiast watchlisty; można łączyć z `--portfolio-manager`.

---

## 2026-04-28 — Streaming odpowiedzi Anthropic zamiast single request

W `_call_claude` w `llm_client.py` zastąpiono `client.messages.create()` wywołaniem `client.messages.stream()` z context managerem i `stream.get_final_text()`. Timeout `read=600s` przy pojedynczym żądaniu resetował się co 10 minut dla długich odpowiedzi portfolio managera (8192 tokenów) powodując `httpx.ReadTimeout`; przy streamingu timeout działa między kolejnymi tokenami, więc długie odpowiedzi nie są przerywane.

---

## 2026-04-28 — TASK-034: Skrócenie kontekstu per ticker w build_batch_context

W `context_builder_batch.py` zastąpiono `_candidate_section` (przekazywała pełny `json.dumps` L2 i L4 per ticker) nową funkcją `_format_ticker_context` — wyciąga tylko kluczowe pola: z L2 `fundamental.summary/key_strengths/key_risks` i `technical.summary/entry_zone/invalidation_level`; z L4 `bull.core_thesis/flywheel_mechanism/upside_x/price_target_3yr/key_assumptions`, `bear.central_thesis/top_risk/stress_test/what_would_change_mind`, `premortem.failure_scenarios[:2]`. Pomijane: `raw_analysis` wszystkich agentów, `historical_analogs`, więcej niż 2 scenariusze premortem. `build_batch_context` zaktualizowany do wywołania nowej funkcji. W `batch.py` naprawiono dwa blokujące błędy: usunięto `quit()` pozostawiony z debugowania i zmieniono `model_tier="decision"` → `"portfolio_manager"`; `logger.debug` dla długości promptu zmieniony na `logger.info` żeby trafił do `pipeline.log`.

---

## 2026-04-28

**Rename projektu i zakres kapitalizacji:** `README.md`, `ARCHITECTURE.md` i prompt `02a_fundamental.md` zaktualizowane — projekt przemianowany z `small-cap-picker` na `flywheel-picker`, zakres kapitalizacji zmieniony z `$1B–$100B` na `$2B+`.

**Flaga `--portfolio-manager` i opcjonalna warstwa 5:** W `pipeline/main.py` dodano `--portfolio-manager`; `run_pipeline()` w `orchestrator.py` przyjmuje `run_l5: bool = False` — warstwa 5 nie uruchamia się domyślnie, tylko gdy przekazana flaga. `_TOP_N_FOR_PM` zwiększone z 5 do 15 kandydatów.

**Retry: wykrywanie błędów sieci z resetem klienta:** W `_call_with_retry` w `orchestrator.py` dodano detekcję `ConnectionError`/`ConnectError` — przy błędzie sieciowym wywoływane `reset_claude_client()` (nowa funkcja w `llm_client.py` zerująca singleton `_claude_client`). Wait zmieniony z `2^(attempt-1)` na `60 * attempt` sekund (attempt 1→60s, 2→120s). Naprawiono indeksowanie: `range(max_retries + 1)` zamiast `range(1, max_retries + 1)`.

**Timeouty HTTP dla klienta Anthropic:** `_get_claude_client` tworzy klienta z `httpx.Timeout(connect=30s, read=600s, write=600s, pool=600s)` — poprzedni brak timeout powodował zawieszanie się przy długich wywołaniach PM.

**Filtrowanie watchlist przez `available-tickers.pdf`:** W `config_loader.py` dodano `_load_available_tickers()` — jeśli plik `data/available-tickers.pdf` istnieje, `load_watchlist()` filtruje ticki do tych dostępnych na giełdzie US. Parsowanie PDF przez `pypdf` (nowa zależność w `pyproject.toml`), wzorzec `r"\b[A-Z]{1,6}:US\b"`. Plik PDF dodany do `.gitignore`.

**Zmiana routingu modeli: `decision` → `portfolio_manager`:** Env var `ANTHROPIC_MODEL_DECISION` przemianowana na `ANTHROPIC_MODEL_PORTFOLIO_MANAGER`; `model_tier="decision"` → `"portfolio_manager"` w `llm_client.py` i `batch.py`. `max_tokens` podniesione do 8192 dla wywołań PM (wszystkie inne nadal 4096).

**Uproszczenie schematów bull/bear synthesizer:** `04a_bull_synthesizer.md` — usunięto `score`, `historical_analogs`, `consensus_strength`; dodano `upside_x` i zmieniono opisy pól na instrukcje z limitami. `04b_bear_synthesizer.md` — uproszczono do 4 pól: `central_thesis`, `top_risk`, `stress_test`, `what_would_change_mind`; usunięto `score`, `key_risks`, `consensus_strength` i pola ryzyk szczegółowych.

**Uproszczenie promptu portfolio managera:** `05_portfolio_manager.md` — matryca 7-polowa (KROK 1–2) zastąpiona 3 pytaniami jakościowymi (flywheel mechaniczny? upside >2x? bull silniejszy niż bear?); skrócono zasady do minimum; PM nadal zwraca listę decyzji dla wszystkich kandydatów naraz.

**Aktualizacja danych:** `data/watchlist.yaml` wypełniona 65 tickerami z screenera (25 kwiecień) i ręcznie dodanymi (AMD, ASTS, INTC, RKLB, TXN). `data/portfolio.yaml` — usunięta pozycja RDW, COST zmniejszony z 20% do 10%, gotówka zwiększona z 60% do 80%.

---

## 2026-04-26 — TASK-033: Portfolio manager jako decyzja portfelowa — wszystkie ticki naraz

Stworzono `src/layer5_portfolio_manager/context_builder_batch.py` z `build_batch_context(candidates, portfolio)` — buduje jeden kontekst dla wszystkich kandydatów z sekcjami: aktualny portfel, P&L per pozycja, poprzednie decyzje z feedbackiem, system insights, dane L2 i L4 per ticker. Stworzono `src/layer5_portfolio_manager/batch.py` z `run_portfolio_manager_batch(candidates, portfolio)` — jedno wywołanie LLM zwraca listę decyzji dla wszystkich kandydatów jednocześnie; zapisuje do `decisions_log` tylko akcje nie-PASS. Zaktualizowano prompt `05_portfolio_manager.md` — PM otrzymuje wszystkich kandydatów naraz, szereguje wg conviction (bull_score - bear_score) i alokuje gotówkę od najwyższego; output zmieniony z pojedynczego obiektu na listę. W `orchestrator.py` warstwa L5 zamieniona z pętli per-ticker na budowanie listy `candidates` + jedno wywołanie `run_portfolio_manager_batch`; wyniki zapisywane przez `save_checkpoint(run_id, "l5", ...)` (checkpoint per warstwa, nie per ticker). `_safe_parse_json` rozszerzony o obsługę `list` — detekcja przez pierwszy znak JSON (`{` vs `[`). Deduplikacja P&L: `get_pnl_pct(ticker, entry_price)` przeniesione do `shared/market_data.py` i używane w `context_builder.py` i `orchestrator.py` zamiast inline kalkulacji.

---

## 2026-04-27 — TASK-032: Kumulatywny checkpoint dzienny z automatycznym czyszczeniem

Usunięto `clear_checkpoint(run_id)` z końca `run_pipeline()` — checkpoint teraz żyje cały dzień i kumuluje wyniki kolejnych uruchomień (nowe ticki dopisują się do istniejących). Dodano `cleanup_old_checkpoints(max_age_days=2)` w `checkpoint.py` (wymaga `import time` i `logging.getLogger`) — skanuje `CHECKPOINT_DIR/*.json` i usuwa pliki starsze niż 2 dni. Wywoływana jako pierwsza instrukcja `run_pipeline()`.

---

## 2026-04-27 — TASK-031: Checkpoint per ticker w warstwach 2, 4 i 5

Do `checkpoint.py` dodano `save_ticker_result`, `get_ticker_result` i `get_completed_tickers` — checkpoint przechowuje wyniki per ticker jako `{stage: {ticker: data}}`. W `orchestrator.py` warstwy L2 i L4 zamieniono z `ThreadPoolExecutor` na sekwencyjne pętle (wewnętrzna równoległość agentów zachowana w `run_parallel_analysis` i `run_cases`): na starcie ładowane są już ukończone ticki z checkpointu, każdy nowy wynik zapisywany natychmiast po zakończeniu. L5 analogicznie — `save_ticker_result` po sukcesie PM agenta, `finally: close_decision_logger`. L1 i L3 pozostają na checkpoint per warstwa. `clear_checkpoint` wywoływany tylko po pełnym sukcesie pipeline.

---

## 2026-04-26 — TASK-030: Checkpointy pipeline — wznawianie po błędzie

Stworzono `src/pipeline/checkpoint.py` z funkcjami `save_checkpoint`, `load_checkpoint`, `clear_checkpoint` i `today_run_id` — dane zapisywane do `logs/checkpoints/YYYY-MM-DD.json` (jeden plik per dzień, etapy jako klucze JSON). W `orchestrator.py` każda warstwa (L1–L4) owinięta w `if "lN" in cp: wczytaj else: przelicz + save_checkpoint`; `close_decision_logger` wywoływany tylko w gałęzi `else` (przy wczytaniu z cache loggery nie były otwarte); po sukcesie L5 `clear_checkpoint` usuwa plik. Uruchomienie po błędzie w warstwie 4 pomija L1–L3 i wznawia od L4.

---

## 2026-04-26 — Exponential backoff w retry pipeline

W `_call_with_retry` w `orchestrator.py` dodano opóźnienie między próbami: `wait = 2 ** (attempt - 1)` sekund (próba 1 → 1s, próba 2 → 2s, ostatnia próba → rzuca wyjątek bez czekania). Natychmiastowy retry był bezużyteczny przy chwilowych błędach sieciowych i DNS — kolejna próba trafiała na ten sam problem.

---

## 2026-04-26 — Naprawa: race condition w get_decision_logger powodujący EMFILE w warstwie 4

`get_decision_logger` miało klasyczny race condition typu check-then-act: wiele wątków jednocześnie widziało `logger.handlers == []` i każdy dodawał własny `FileHandler`. W warstwie 4 zagnieżdżone executory (4 tickery × 3 agenty × 3 instancje = 36 współbieżnych wątków) mnożyły FD per ticker, przekraczając limit OS. Naprawiono przez dodanie `_logger_lock = threading.Lock()` i owinięcie całej sekcji inicjalizacyjnej w `with _logger_lock:`.

---

## 2026-04-25 — TASK-029: Dwa modele — Haiku dla analizy, Sonnet dla decyzji

Wprowadzono dwupoziomowy routing modeli przez parametr `model_tier: "analysis" | "decision"` w `call_llm()` i `_call_claude()`. `get_llm_config()` w `config_loader.py` zwraca teraz dwa klucze modelu: `anthropic_model_analysis` (default: `claude-haiku-4-5-20251001`) i `anthropic_model_decision` (default: `claude-sonnet-4-6`). Usunięto stałą `_CLAUDE_MODEL`. Warstwy decyzyjne — 3 synthesizery w `layer4/agents.py`, `layer5/main.py`, `layer6/feedback_agent.py` — wywołują `call_llm(..., model_tier="decision")`; wszystkie agenty analizy (L1, L2, L4 instancje) pozostają na domyślnym `"analysis"`. Konfiguracja modeli przez `ANTHROPIC_MODEL_ANALYSIS` i `ANTHROPIC_MODEL_DECISION` w `.env`.

---

## 2026-04-25 — Naprawa: SyncHttpxClientWrapper AttributeError przy zamknięciu

`_call_claude` tworzył nowy `anthropic.Anthropic(...)` przy każdym wywołaniu — przy zamknięciu interpretera Python 3.14 GC niszczył obiekt w momencie gdy `httpx.Client._state` był już niedostępny, generując `AttributeError` w `__del__`. Wprowadzono singleton `_claude_client` inicjalizowany przez `_get_claude_client(cfg)` przy pierwszym wywołaniu i reużywany przez cały czas życia procesu.

---

## 2026-04-25 — Naprawa: Too many open files przy dużym watchlist

`get_decision_logger(ticker)` tworzył `FileHandler` dla każdego tickera i nigdy go nie zamykał — 200+ otwartych deskryptorów po prescreenerze wyczerpywało limit OS przed layer2. Naprawy: (1) dodano `close_decision_logger(ticker)` w `logging_config.py`, wywoływane w bloku `finally` po każdym tickerze w `run_prescreener_batch`; (2) wyodrębniono `read_template(path)` z `@lru_cache` do `shared/context.py` — pliki promptów czytane raz, nie per ticker; `load_core_rules()` korzysta z `read_template` zamiast własnego cache; (3) usunięto błędny `@lru_cache` z `_load_prompt` w `layer2/agents.py`, `layer4/agents.py` i `layer1/agent.py` — cache kluczował po unikatowych danych per ticker (nigdy nie trafiał), wszystkie trzy zastąpione wywołaniem `read_template`.

---

## 2026-04-25 — Naprawa: błąd parsowania JSON w prescreenerze nie wysadza pipeline'u

Ticker `PL` (Planet Labs, NYSE) spowodował konwersacyjną odpowiedź Claude zamiast JSON — model zinterpretował dwuliterowy ticker jako kod języka polskiego. Nieobsłużony `ValueError` przerywał cały pipeline. W `run_prescreener_batch` dodano `try/except` wokół `run_prescreener(ticker)` — wyjątek jest logowany jako `WARNING` i ticker jest traktowany jako REJECT, pipeline kontynuuje działanie. Przy okazji naprawiono składnię Python 2 w `llm_client.py` linia 64: `except json.JSONDecodeError, ValueError:` → `except (json.JSONDecodeError, ValueError):`.

---

## 2026-04-25 — Logowanie w warstwie 1 (prescreener)

W `layer1_prescreener/agent.py` dodano `logger.debug` z treścią promptu oraz `log_agent_result(ticker, "prescreener", result)` zapisujący verdict do per-ticker decision loggera. W `layer1_prescreener/main.py` dodano `logger.info` per ticker z verdyktem oraz podsumowanie `X/N tickerów przeszło filtr` po zakończeniu batcha.

---

## 2026-04-25 — Flaga --discover w CLI

Dodano flagę `--discover` do grupy wzajemnie wykluczających się argumentów w `pipeline/main.py` — wywołuje `run_idea_generation()` z warstwy 0 (Finviz screener + OpenInsider stub) i zapisuje wyniki do `data/watchlist.yaml`. Pipeline analityczny (L1–L5) pozostaje bez zmian i nadal czyta z watchlist przy wywołaniu bez flag.

---

## 2026-04-25 — Rename config/ → data/

Katalog `config/` przemianowany na `data/` — wszystkie pliki YAML (`portfolio.yaml`, `watchlist.yaml`, `decisions_log.yaml`, `decisions_log_test.yaml`, `system_insights.yaml`) to dynamiczny stan systemu generowany w runtime, nie konfiguracja parametrów. W `config_loader.py` zmieniono nazwę stałej `CONFIG_DIR` → `DATA_DIR` (replace_all) i ścieżkę `"config"` → `"data"`; `layer6_feedback/main.py` zaktualizowany w imporcie i w `_PROD_LOG`; `.gitignore` i `ARCHITECTURE.md` zaktualizowane.

---

## 2026-04-25 — TASK-028: Oddzielenie decyzji produkcyjnych od testowych

Dodano prywatną funkcję `_decisions_log_path()` w `config_loader.py` — czyta `RUN_MODE` z `.env` (default: `"test"`) i zwraca ścieżkę do `decisions_log.yaml` (produkcja) lub `decisions_log_test.yaml` (testy); `load_decisions_log()` i `save_decisions_log()` korzystają z tej funkcji. W `layer6_feedback/main.py` zastąpiono import `load_decisions_log`/`save_decisions_log` bezpośrednimi wywołaniami `load_yaml`/`save_yaml` na stałej `_PROD_LOG = CONFIG_DIR / "decisions_log.yaml"` — feedback loop zawsze operuje na produkcji niezależnie od `RUN_MODE`. Stworzono `config/decisions_log_test.yaml` (`decisions: []`), dodano `RUN_MODE=test` do `.env` i `config/decisions_log_test.yaml` do `.gitignore`.

---

## 2026-04-25 — TASK-027: Decision matrix w portfolio managerze

Z `context_builder.py` usunięto sekcję `CORE INVESTMENT RULES` (wywołanie `load_core_rules()` i odpowiadający import) — jej treść pokrywała się z hardkodowanymi regułami w prompcie, generując duplikację w kontekście wysyłanym do LLM. W `05_portfolio_manager.md` zastąpiono jakościową sekcję "ZASADA WYBORU AKCJI" trzystopniową matrycą decyzyjną (KROK 1: wypełnienie 7 pól liczbowych z danych warstw 2/4; KROK 2: mechaniczne reguły progowe dla BUY/PASS/SELL/ADD/HOLD; KROK 3: uzasadnienie bez reinterpretacji); usunięto placeholder `{{ PRICE_CONTEXT }}` który nigdy nie był podmieniony w `main.py` (cena jest już w FULL_CONTEXT przez sekcję STAN PORTFELA); zaktualizowano opis pola `rationale` w schemacie JSON do formatu `"Matryca: flywheel=X/5, bull=X, bear=X, upside=Xx, HIGH_risks=X."`.

---

## 2026-04-22 — TASK-026: Dane finansowe i wolumenowe z yfinance do agentów

Dodano `get_financial_context(ticker)` w `market_data.py` — pobiera z `yf.Ticker.info` 7 metryk (Revenue TTM, growth YoY, gross margin, FCF, dług netto, insider%, EV/Revenue) i zwraca pusty string przy braku danych lub błędzie (z `logger.warning`). Rozszerzono `get_price_context()` o historię 30d: `hist["Volume"].tail(20).mean()` jako avg_vol i ratio dzisiejszego wolumenu do tej średniej. `_load_prompt()` w `agents.py` otrzymał parametr `financial_context` i replace dla `{{ FINANCIAL_CONTEXT }}`; `run_fundamental()` i `run_ownership()` wywołują `get_financial_context()` przed budowaniem promptu. Placeholder `{{ FINANCIAL_CONTEXT }}` wstawiony po `{{ CORE_RULES }}` w `02a_fundamental.md` i `02d_ownership.md`.

---

## 2026-04-21 — TASK-025: Usunięcie score z bull/bear instancji

Pliki 04c_premortem.md i 04c_premortem_synthesizer.md były już czyste (brak pola score). W 04a_bull.md i 04b_bear.md usunięto pole `"score": 0` z sekcji JSON — synthesizery (04a/04b_bull/bear_synthesizer.md) zachowują score i verdict jako finalne outputy trafiające do warstwy 5.

---

## 2026-04-21 — TASK-024: Wymuszenie zwięzłości w schematach JSON agentów

W schematach JSON wszystkich 11 plików promptów zastąpiono puste stringi i puste listy opisami z twardymi limitami słownymi. Warstwy 2 (`02a`–`02d`): `summary` ← MAX 2 zdania z liczbą, `key_strengths`/`key_risks` ← MAX 2-3 pozycje po MAX 10 słów, `raw_analysis` ← MAX 50–100 słów. Warstwa 4 pojedyncze instancje (`04a`–`04c`): pola narracyjne z przykładami liczbowymi (np. `financial_stress_result`, `historical_analogs`), `raw_analysis` ← MAX 75 słów. PM (`05`): `rationale` ← wymuszona struktura 3-zdaniowa, `checkin_1yr_criteria` ← MAX 3 warunki z liczbami. Synthesizery (`04a/b/c_synthesizer`): `raw_analysis` ← MAX 150 słów (celowo więcej niż instancje). Sekcje instrukcji przed JSON oraz `CORE_RULES.md` pozostały bez zmian.

---

## 2026-04-21 — TASK-023: Wielu agentów Bull/Bear/Pre-Mortem z syntezą

Stworzono 3 prompty synthesizer (`04a_bull_synthesizer.md`, `04b_bear_synthesizer.md`, `04c_premortem_synthesizer.md`) — bull/bear stosują logikę konsensus/unikalne sygnały/sprzeczności i zwracają pole `consensus_strength` (HIGH/MEDIUM/LOW na podstawie spreadu score'ów), premortem stosuje deduplikację i ranking skumulowany (HIGH=3/MEDIUM=2/LOW=1) zamiast konsensusu. W `agents.py` wyodrębniono `_run_bull/bear/premortem_single` (obecna logika + log z sufiksem `_instance`), dodano `_run_*_synthesizer` z `_load_synthesizer_prompt` oraz `_get_instances()` z `AGENT_INSTANCES` env var; `run_bull/bear/premortem` uruchamia N instancji równolegle przez `ThreadPoolExecutor`, następnie synthesizer. W `context_builder.py` dodano `_consensus_section()` która odczytuje `consensus_strength` z `layer4["bull"]` i `layer4["bear"]` i dodaje sekcję "PEWNOŚĆ ANALIZY" do kontekstu PM.

---

## 2026-04-21 — TASK-022: Refaktoryzacja decisions_log — tylko akcje do wykonania

W `05_portfolio_manager.md` zastąpiono JSON schema: `rationale` zamiast `core_thesis`/`key_assumptions`, usunięto `scores`/`premortem_top_risk`/`expected_value_reasoning`, dodano `entry_price` i instrukcję minimalnego wypełnienia dla PASS. W `main.py` uproszczono `_build_decision_payload()` (teraz przyjmuje tylko `ticker` i `pm_result`, bez `layer2`/`layer4`) i dodano wczesny return dla PASS z logiem do dec_log bez zapisu YAML. W `logger.py` wprowadzono `_DECISION_FIELDS` jako whitelist pól zapisywanych do YAML oraz guard `if action == PASS: return`. W `decisions_log.yaml` dodano komentarz dokumentujący schemat.

---

## 2026-04-21 — TASK-021: Naprawa logowania bypass prescreenera i diagnostyka podziału tickerów

W `run_pipeline()` w `orchestrator.py` zastąpiono blok z `extra` trzema osobnymi logami: lista tickerów z portfolio (bypass prescreener), lista z watchlist (przez prescreener) oraz opcjonalny log tickerów w obu miejscach (walrus operator `overlap`). Dodano dwie asercje `logger.error` — po zbudowaniu `layer2_tickers` sprawdzającą czy `in_portfolio` trafiło do warstwy 2, oraz przed warstwą 5 sprawdzającą obecność `in_portfolio` w `layer4_results` — dzięki czemu problem z cichym wypadaniem tickera z portfolio jest widoczny zanim pipeline zakończy działanie.

---

## 2026-04-21 — TASK-020: Zmniejszenie losowości agentów

Dodanie zmiennej środowiskowej `ANTHROPIC_TEMPERATURE`, która jest ładowna w `get_llm_config()` w celu zarządzania losowością agentów.

---


## 2026-04-19 — TASK-019: Naprawa logiki akcji portfolio managera

W `context_builder.py` dodano `_position_section(ticker, portfolio)` która odczytuje `current_weight_pct` z portfolio.yaml i buduje jawny blok "POZYCJA W PORTFELU: TAK/NIE, Aktualny rozmiar: X%" — sekcja trafia do `build_context()` jako nowy element przed danymi L2/L4. W `05_portfolio_manager.md` zastąpiono ogólną listę akcji 3-krokowymi ZASADAMI WYBORU AKCJI z zakazami NIGDY, a w JSON schema `position_size_pct` rozdzielono na `current_position_size_pct` i `target_position_size_pct`. W `_build_decision_payload()` w `main.py` zaktualizowano mapowanie pól z `pm_result`. W `config/decisions_log.yaml` dokonano rename pola we wszystkich wpisach DEC-001…DEC-005 z semantycznym rozróżnieniem (BUY: current=0, target=10; SELL/HOLD: oba=0). Poprawiono też log w `orchestrator.py` pokazujący current→target dla każdego tickera.

---


## 2026-04-19 — TASK-018: Centralny system logowania

Stworzono `src/shared/logging_config.py` z `setup_logging()` (StreamHandler + `TimedRotatingFileHandler` na `logs/pipeline.log`, rotacja midnight, backupCount=30, czyszczenie plików decisions starszych niż 90 dni) i `get_decision_logger(ticker)` (idempotentny logger per ticker+dzień, `propagate=False`, zapis do `logs/decisions/YYYY-MM-DD_{ticker}.log`). W `pipeline/main.py` dodano wywołanie `setup_logging()` na początku `main()`. We wszystkich plikach `src/` zastąpiono `print()` przez `logger = logging.getLogger(__name__)` z mapowaniem: postęp → `info`, retry → `warning`, błędy parsowania → `error`, prompty i raw responses → `debug`. W agentach warstwy 2, 4 i 5 dodano `get_decision_logger` z logowaniem score/verdict (info) i raw_analysis (debug, bez obcinania). Naprawiono błąd składni Python 2 w `llm_client.py` (`except json.JSONDecodeError, ValueError` → `except (json.JSONDecodeError, ValueError)`). Dodano `LOG_LEVEL=INFO` do `.env`.

---


## 2026-04-19 — TASK-017: Przekazywanie aktualnych cen rynkowych do agentów

Stworzono `/src/shared/market_data.py` z funkcją `get_price_context(ticker)` opartą na `yfinance.Ticker.fast_info` — zwraca sformatowany string z ceną, 52-tygodniowym minimum i maksimum, a przy wyjątku loguje ostrzeżenie i zwraca pusty string. W `_load_prompt()` warstwy 2 i 4 dodano parametr `price_context: str = ""` z zastąpieniem `{{ PRICE_CONTEXT }}`. Funkcje `run_technical()`, `run_bull()`, `run_bear()` wywołują `get_price_context()` i przekazują wynik do `_load_prompt()`. W `context_builder.py` (warstwa 5) `_portfolio_state_section()` rozszerzono o parametr `price_ctx`, dodany na końcu sekcji "STAN PORTFELA". Placeholder `{{ PRICE_CONTEXT }}` dodany do 4 plików promptów: `02b_technical.md`, `04a_bull.md`, `04b_bear.md`, `05_portfolio_manager.md`.

---

## 2026-04-19 — TASK-015: Centralizacja MAX_WORKERS przez zmienną środowiskową

Dodano `get_max_workers()` do `config_loader.py` — czyta `MAX_WORKERS` z `.env`, domyślnie `4`. We wszystkich trzech miejscach z hardkodowanymi wartościami (`layer2_analysis/main.py` → 4, `layer4_cases/main.py` → 3, `pipeline/orchestrator.py` → 8×2) zastąpiono stałe wywołaniem `get_max_workers()` (w orchestratorze jako `min(len(tickers), get_max_workers())`). Dodano `MAX_WORKERS=` do `.env.example`.

---

## 2026-04-19 — TASK-014: Naprawa parsowania JSON i retry w warstwie 2 i 4

`_safe_parse_json` w `llm_client.py` przepisany na 4-krokowy fallback: `json.loads(response)` → `json.loads(response[start:end+1])` → `repair_json(response[start:])` (krok c obsługuje ucięty JSON bez zamykającego `}`) → `ValueError`. W `orchestrator.py` naprawiony retry w warstwie 2 i 4: zamiast `_call_with_retry(future.result)` (odczytywał zapamiętany wyjątek z zakończonego future) retry przeniesiony do workerów jako `ex.submit(_call_with_retry, run_parallel_analysis, t)` — równoległość między tickerami zachowana, ponowienie wywołuje agenta od nowa.

---

## 2026-04-19 — TASK-013: Integracja portfolio.yaml z pipeline

W `orchestrator.py` force-add wszystkich tickerów z `portfolio_tickers` do pipelinu przed podziałem na `non_portfolio`/`in_portfolio` — tickery spoza watchlist trafiają teraz zawsze do warstwy 2+. W `layer3_selector/main.py` dodano `print` warning gdy `weighted_score < MIN_SCORE_THRESHOLD` dla spółki z portfolio — sygnał psującej się tezy. W `context_builder.py` wyodrębniono `_portfolio_state_section()` która buduje czytelną sekcję "STAN PORTFELA" z listą tickerów i `cash_pct`, z dodatkową linią ostrzegawczą gdy `cash_pct < 5%`.

---

## 2026-04-19 — TASK-012: Usunięcie calculate_recommended_size

Usunięto `position_sizing.py` w całości. Z `context_builder.py` usunięto import, wywołanie `calculate_recommended_size()` oraz sekcję "RECOMMENDED POSITION SIZE" z kontekstu budowanego dla agenta. Z `_build_decision_payload()` w `main.py` usunięto pola `recommended_position_size_pct` i `sizing_override_reason`. Z JSON output w `05_portfolio_manager.md` usunięto te same dwa pola. Z `decisions_log.yaml` usunięto te pola z wpisu DEC-001.

---

## 2026-04-18 — TASK-011: Naprawa źródeł danych w warstwie 0

`fetch_insider_buys()` w `insider_buying.py` zastąpiony stubem zwracającym `[]` z `logger.warning` — OpenInsider niedostępny ze środowiska. `screener.py` przepisany na `finvizfinance.screener.overview.Overview` z filtrami `Market Cap.: Small`, `Sales growthqtr over qtr: Over 15%`, `InsiderOwnership: Over 10%` — poprawne nazwy filtrów ustalone empirycznie (Finviz używa `InsiderOwnership` bez spacji). `aggregator.py` loguje info gdy tylko jedno źródło aktywne. Wynik: 227 tickerów dodanych do watchlist.yaml.

---


## 2026-04-18 — TASK-010: Wyodrębnienie call_llm do współdzielonego modułu

Stworzono `/src/shared/llm_client.py` z funkcjami `_call_claude`, `_call_ollama`, `_safe_parse_json` (json.loads → repair_json → ValueError) i publicznym `call_llm(prompt, expect_json=True)` który wybiera backend z `get_llm_config()`. Usunięto lokalne implementacje z warstw 1, 2, 4, 5 i 6 — każdy agent importuje teraz tylko `call_llm`. Grep na `ollama_base_url` zwraca wyłącznie `llm_client.py` i `config_loader.py`.

---


## 2026-04-18 — TASK-009: Warstwa 0 — Idea Generation (automatyczny watchlist)

`fetch_insider_buys()` w `insider_buying.py` pobiera CSV z OpenInsider przez `httpx`, filtruje transakcje typu P dla ról CEO/CFO/Director z wartością ≥ $100K i weryfikuje market cap $100M–$25B przez `yfinance.fast_info`. `fetch_screener_candidates()` w `screener.py` pobiera CSV z Finviz export z filtrami `cap_small,cap_mid,iown_o10`, następnie weryfikuje revenue growth YoY ≥ 15% przez `yfinance.financials`. `run_idea_generation()` w `aggregator.py` łączy oba źródła, deduplikuje względem istniejących wpisów w watchlist.yaml i dopisuje nowe jako `{ticker, source, discovery_date}` — format zgodny z `t["ticker"]` używanym przez orchestrator. Dodano `yfinance` do zależności przez `uv add`.

---


## 2026-04-18 — TASK-008: Pipeline — Orchestrator łączący wszystkie warstwy

`run_pipeline()` w `orchestrator.py` łączy warstwy 1–5 w jeden spójny przepływ: ticki portfolio omijają warstwę 1, warstwy 2 i 4 wykonywane są równolegle między tickerami (`ThreadPoolExecutor`), warstwa 5 ograniczona do top 5 + portfolio żeby kontrolować koszt Claude API. `main.py` jako punkt wejścia CLI obsługuje `--tickers`, `--feedback` i tryb domyślny z `watchlist.yaml`.

---

## 2026-04-18 — TASK-007: Warstwa 6 — Feedback Loop Agent

Stworzono agenta warstwy 6: `feedback_agent.py` ładuje prompt z `feedback_loop.md`, podstawia `[DECISION]`, `[CURRENT_DATA]`, `[MONTHS]` i wywołuje LLM (Claude API lub Ollama w zależności od `USE_CLAUDE_API`). `insights_updater.py` aktualizuje liczniki `agent_accuracy` w `system_insights.yaml` i dodaje `recurring_pattern` bez duplikatów. `main.py` skanuje `decisions_log.yaml` i wypełnia `feedback_6m`/`feedback_12m` dla decyzji starszych niż 6/12 miesięcy.

---

## 2026-04-17 — TASK-006: Warstwa 5 — Portfolio Manager Agent

Stworzono agenta warstwy 5 opartego na Claude API: `context_builder` składa pełny kontekst z 7 sekcji (CORE_RULES, portfolio, feedback, system_insights, wyniki L2/L4, recommended size), `main.py` wywołuje `claude-sonnet-4-6` i zapisuje decyzję do `decisions_log.yaml` przez `save_decision()`.

---

## 2026-04-17 — TASK-005: Warstwa 4 — Bull, Bear i Pre-Mortem agenty

Stworzono 3 prompty i agenty warstwy 4 uruchamiane równolegle; pre-mortem podstawia rok `now+2` jako `[FUTURE_YEAR]`, wszystkie trzy dostają kontekst z warstwy 2 jako JSON.

---

## 2026-04-17 — TASK-004: Warstwa 3 — Selektor i ranking

`run_selector()` agreguje wyniki 4 agentów warstwy 2 w weighted score i zwraca top 20 kandydatów; spółki z portfolio zawsze trafiają do outputu z flagą `in_portfolio: true` niezależnie od score'u.

---

## 2026-04-17 — TASK-003: Warstwa 2 — Cztery agenty analizy równoległej

Stworzono 4 prompty dla agentów warstwy 2 (fundamental, technical, sentiment, ownership) oraz `agents.py` z osobną funkcją dla każdego agenta. `main.py` uruchamia wszystkie cztery równolegle przez `ThreadPoolExecutor` — czas wykonania równy najwolniejszemu agentowi.

---

## 2026-04-17 — TASK-002: Warstwa 1 — Pre-screener agent

Stworzono agenta warstwy 1: `agent.py` ładuje prompt z pliku, podstawia CORE_RULES i ticker, wysyła do ollama i parsuje JSON z fallbackiem na regex. `main.py` uruchamia batch i filtruje tylko PASS/CONDITIONAL_PASS.

---

## 2026-04-17 — TASK-001: Infrastruktura bazowa

Stworzono shared utilities: `config_loader.py` (load/save YAML dla portfolio, watchlist, decisions_log, system_insights), `context.py` (load_core_rules z pliku), `logger.py` (save_decision z auto-incrementem DEC-NNN). Dodano pliki konfiguracyjne: `decisions_log.yaml`, `system_insights.yaml`, `portfolio.yaml`, `watchlist.yaml`.
