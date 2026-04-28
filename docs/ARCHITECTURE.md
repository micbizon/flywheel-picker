# Multi-Agent Investment System — Architecture

## Cel systemu

System automatycznej selekcji spółek small/mid-cap (głównie USA) z przewagą wynikającą z małej
kapitalizacji — obszaru gdzie duże fundusze instytucjonalne nie mogą efektywnie operować.
Decyzje inwestycyjne oparte o framework "Costco Algorithm": spółki z flywheel'em reinwestującym
korzyści skali w niższe ceny / wyższą wartość dla klienta końcowego.

**Zakres kapitalizacji:** $2B+(mid+ cap)  
**Horyzont inwestycyjny:** 3–10 lat per pozycja  
**Liczba pozycji:** 3–7 jednocześnie  
**Filozofia:** concentrated, high-conviction, long-only

---

## Filozofia inwestycyjna (Costco Algorithm)

Spółka przechodzi przez system tylko jeśli posiada strukturalne cechy flywheel'u:

1. **Economies of scale shared** — wzrost skali → niższe koszty jednostkowe → niższe ceny lub
   wyższa wartość dla klienta → więcej klientów → wzrost skali (pętla zamknięta)
2. **Goodwill compounding** — długoterminowe budowanie lojalności klientów jako niemierzalny, ale
   realny aktyw
3. **Reinvestment over margin expansion** — preferencja dla spółek które reinwestują zyski w
   produkt/cenę zamiast optymalizować krótkoterminowy EPS
4. **Asymmetric upside** — teza musi mieć potencjał 3–10x w horyzoncie 5–7 lat przy zdefiniowanym
   ryzyku downside

---

## Stack technologiczny

Środowisko zarządzane przez `uv`. Backend LLM konfigurowany globalnie przez `USE_CLAUDE_API`:
- `true` → Claude API (`claude-sonnet-4-6`)
- `false` → Ollama (model z `OLLAMA_MODEL_NAME`, domyślnie `llama3.2:3b`)

---

## Architektura systemu — warstwy

```
┌─────────────────────────────────────────────────────────┐
│  WARSTWA 0: Idea Generation                             │
│  Źródła: Finviz screeners, insider buying (OpenInsider) │
│  Output: lista TICKER-ów → watchlist.yaml               │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  WARSTWA 1: Pre-Screener (Costco Algorithm Filter)      │
│  Prompt: /prompts/agents/01_prescreener.md              │
│  Output: PASS / CONDITIONAL PASS / REJECT               │
│  Ticki z portfolio.yaml omijają tę warstwę              │
└─────────────────────┬───────────────────────────────────┘
                      │ (tylko PASS i CONDITIONAL PASS)
┌─────────────────────▼───────────────────────────────────┐
│  WARSTWA 2: Równoległa analiza (4 agenty)               │
│                                                         │
│  ┌───────────────┐  ┌──────────────┐                    │
│  │ 2A Fundamental│  │ 2B Technical │                    │
│  └───────────────┘  └──────────────┘                    │
│  ┌───────────────┐  ┌──────────────┐                    │
│  │ 2C Sentiment  │  │ 2D Ownership │                    │
│  └───────────────┘  └──────────────┘                    │
│                                                         │
│  Każdy zwraca: { score: 1-10, verdict, summary, ... }   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  WARSTWA 3: Selekcja                                    │
│  Ranking weighted score z warstwy 2                     │
│  Wagi: Fundamental 35%, Ownership 30%,                  │
│        Sentiment 20%, Technical 15%                     │
│  Top 20 kandydatów + spółki z portfolio (zawsze)        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  WARSTWA 4: Bull / Bear / Pre-Mortem                    │
│                                                         │
│  Każdy agent uruchamiany AGENT_INSTANCES razy równolegle│
│  następnie synthesizer wyciąga konsensus:               │
│                                                         │
│  [Bull×N] → Bull Synthesizer   → consensus_strength     │
│  [Bear×N] → Bear Synthesizer   → consensus_strength     │
│  [PM×N]   → PreMortem Synthesizer → top 5 scenariuszy   │
│                                                         │
│  Pre-Mortem: zakłada -65% za 2 lata i odtwarza przyczynę│
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  WARSTWA 5: Portfolio Manager Agent                     │
│  Prompt: /prompts/agents/05_portfolio_manager.md        │
│  Kontekst: portfolio.yaml + decisions_log.yaml          │
│            + consensus_strength z warstwy 4             │
│                                                         │
│  Decyzje: BUY / ADD / HOLD / SELL / PASS                │
│  PASS → tylko log, nie zapisuje do decisions_log.yaml   │
│  Output: rationale + stop-loss + checkin_1yr_criteria   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  WARSTWA 6: Feedback Loop (uruchamiany co 6/12 miesięcy)│
│  Prompt: /prompts/system/feedback_loop.md               │
│  Wejście: decisions_log.yaml (decyzje starsze niż 6 msc)│
│  Output: ocena rationale i założeń — co się sprawdziło  │
│  → Zapisuje feedback_6m / feedback_12m                  │
└─────────────────────────────────────────────────────────┘
```

---

## Struktura plików projektu

```
/flywheel-picker
│
├── /docs
│   ├── ARCHITECTURE.md
│   ├── PHILOSOPHY.md
│
├── /prompts
│   ├── CORE_RULES.md          ← 5 kryteriów flywheel'u (injektowane do agentów)
│   ├── RESPONSE_RULES.md      ← zasady formatu: tylko JSON, MAX 30 słów per pole
│   ├── /agents
│   │   ├── 01_prescreener.md
│   │   ├── 02a_fundamental.md
│   │   ├── 02b_technical.md
│   │   ├── 02c_sentiment.md
│   │   ├── 02d_ownership.md
│   │   ├── 04a_bull.md
│   │   ├── 04a_bull_synthesizer.md
│   │   ├── 04b_bear.md
│   │   ├── 04b_bear_synthesizer.md
│   │   ├── 04c_premortem.md
│   │   ├── 04c_premortem_synthesizer.md
│   │   └── 05_portfolio_manager.md
│   └── /system
│       └── feedback_loop.md
│
├── /data
│   ├── portfolio.yaml              ← aktualne pozycje i ceny wejścia
│   ├── watchlist.yaml              ← spółki do obserwacji
│   ├── decisions_log.yaml          ← historia decyzji (produkcja, RUN_MODE=production)
│   ├── decisions_log_test.yaml     ← historia decyzji (testy, RUN_MODE=test)
│   └── system_insights.yaml        ← accuracy agentów i wzorce błędów
│
├── /src
│   ├── /layer0_ideas … /layer6_feedback
│   ├── /pipeline              ← orchestrator + main.py (CLI)
│   └── /shared                ← llm_client, config_loader, logging, …
│
├── /logs
│   ├── pipeline.log
│   └── /decisions             ← YYYY-MM-DD_[TICKER].log (pełna analiza)
│
├── .env
├── TASKS.md
├── CHANGELOG.md
└── README.md
```

---

## Format danych między warstwami

### Output agentów warstwy 2

```json
{
  "ticker": "AAPL",
  "agent": "fundamental",
  "score": 7,
  "verdict": "PASS|WATCH|REJECT",
  "summary": "MAX 2 zdania z liczbą.",
  "key_strengths": ["MAX 3 pozycje, MAX 10 słów każda"],
  "key_risks": ["MAX 3 pozycje, MAX 10 słów każda"],
  "raw_analysis": "MAX 100 słów."
}
```

### Output synthesizerów warstwy 4 (bull/bear)

```json
{
  "ticker": "AAPL",
  "agent": "bull",
  "score": 7,
  "consensus_strength": "HIGH|MEDIUM|LOW",
  "core_thesis": "...",
  "key_assumptions": ["tylko z sekcji KONSENSUS"],
  "raw_analysis": "MAX 150 słów."
}
```

### Schema decisions_log.yaml (jeden wpis)

```yaml
decision_id: DEC-042
date: "2026-04-21"
ticker: AAPL
action: BUY              # BUY / ADD / HOLD / SELL  (PASS nie jest zapisywany)
current_position_size_pct: 0
target_position_size_pct: 15
entry_price: 185.50
entry_price_currency: USD
rationale: "3 zdania: (1) dlaczego teraz, (2) główne ryzyko, (3) co musi być prawdą."
stop_loss_price: 155.00
stop_loss_fundamental: "Jeden konkretny warunek z progiem liczbowym."
checkin_1yr_criteria: "MAX 3 warunki z liczbami."
feedback_6m: null
feedback_12m: null
```

---

## Źródła pomysłów na spółki (Warstwa 0)

**Zaimplementowane:**
- Finviz: market cap $2B+, revenue growth YoY > 15%, insider ownership > 10%
- OpenInsider: insider buying CEO/CFO (aktualnie stub — endpoint niedostępny)

**Planowane:**
- 13F filings funduszy $50M–$500M AUM
- SEC EDGAR: spin-offy i IPO z ostatnich 18 miesięcy

**Human input:**
- Ręczne dodanie do `watchlist.yaml` (Peter Lynch trigger)

---

## Zasady position sizing

- Maksimum 25% w jedną pozycję
- Pierwsza pozycja: maksimum 15% (próbna pozycja)
- Suma pozycji o podobnym ryzyku makro: maksimum 40%
- Nowa pozycja przy pełnym portfolio wymaga wskazania której pozycji sprzedać

---

## Feedback Loop — zasady działania

Uruchamiany dla każdej decyzji starszej niż 6 miesięcy gdzie `feedback_6m = null`.

Agent ocenia czy `rationale` z dnia decyzji okazał się trafny, które sygnały z warstwy 2
były predyktywne, a które misleading. Output zapisywany do `feedback_6m` / `feedback_12m`.

Długoterminowy cel: identyfikacja które agenty mają najwyższą predyktywność i dostosowanie
wag w warstwie 3.

---

## Otwarte pytania

- [ ] Jak często uruchamiać pełny pipeline? (tygodniowo? na żądanie?)
- [ ] Czy system ma obsługiwać spółki polskie (GPW)?
- [ ] Alert system przy stop-loss?
