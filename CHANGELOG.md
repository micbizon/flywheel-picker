# Changelog

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
