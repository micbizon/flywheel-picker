# flywheel-picker

Multi-agentowy pipeline do identyfikacji i analizy spółek z kapitalizacją $2bln+.

**Filozofia:** Concentrated, high-conviction, long-only. Skupiony na spółkach z "Costco flywheel" — ekonomia skali reinwestowana w niższe ceny / wyższą wartość dla klienta zamiast ekspansji marż. 3–7 pozycji, horyzont 3–10 lat.

## Pipeline

```
Warstwa 0: Idea Generation      — Finviz screeners, insider buying, 13F filings
Warstwa 1: Pre-Screener         — Filtr Costco Algorithm (PASS / CONDITIONAL / REJECT)
Warstwa 2: Równoległa analiza   — Fundamental · Technical · Sentiment · Ownership (4 agenty)
Warstwa 3: Selekcja             — Ranking ważony (Fundamental 35%, Ownership 30%, Sentiment 20%, Technical 15%)
Warstwa 4: Bull/Bear/Pre-Mortem — N instancji każdego agenta + synthesizer (consensus_strength)
Warstwa 5: Portfolio Manager    — BUY / ADD / HOLD / SELL + position sizing
Warstwa 6: Feedback Loop        — Przegląd decyzji starszych niż 6/12 miesięcy
```

Backend LLM konfigurowany globalnie przez `USE_CLAUDE_API` (Claude lub Ollama).

## Setup

```bash
cp .env.example .env
# uzupełnij ANTHROPIC_API_KEY lub OLLAMA_BASE_URL
uv sync
```

## Uruchamianie

```bash
# Warstwa 0: znajdź spółki przez Finviz/OpenInsider → data/watchlist.yaml
uv run python src/pipeline/main.py --discover

# Pipeline L1–L5 na spółkach z watchlist.yaml (+ zawsze spółki z portfolio)
uv run python src/pipeline/main.py

# Pipeline L1–L5 na konkretnych tickerach (własny dobór)
uv run python src/pipeline/main.py --tickers AAPL COST DUOL

# Feedback loop (warstwa 6)
uv run python src/pipeline/main.py --feedback
```

## Zmienne konfiguracyjne

| Zmienna | Opis |
|---|---|
| `ANTHROPIC_API_KEY` | Klucz Claude API |
| `USE_CLAUDE_API` | `true` = Claude, `false` = Ollama |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL_NAME` | Endpoint lokalnego modelu |
| `ANTHROPIC_TEMPERATURE` | Losowość LLM (0.0–1.0) |
| `RUN_MODE` | `production` = `decisions_log.yaml`, `test` = `decisions_log_test.yaml` |
| `MAX_WORKERS` | Liczba równoległych workerów |
| `AGENT_INSTANCES` | Liczba instancji agentów Bull/Bear/Pre-Mortem (domyślnie 3) |
| `LLM_MAX_RETRIES` | Liczba ponowień przy błędzie LLM |
| `LOG_LEVEL` | `INFO` lub `DEBUG` (DEBUG pokazuje pełne prompty i raw responses) |

Wyniki zapisywane do: `data/portfolio.yaml`, `data/decisions_log.yaml`, `data/watchlist.yaml`.
