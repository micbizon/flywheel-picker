{{ CORE_RULES }}

Otrzymujesz [N] niezależnych analiz pre-mortem dla [TICKER].
Pre-mortem różni się od bull/bear — szukamy RÓŻNORODNOŚCI scenariuszy, nie konsensusu.
Każdy unikalny scenariusz failure jest wartościowy.

ANALIZY DO SYNTEZY:
[PREMORTEM_ANALYSES]

Wykonaj w tej kolejności:

1. DEDUPLIKACJA: Połącz scenariusze które są tym samym ryzykiem opisanym różnymi słowami.
   Zostaw jeden najlepiej opisany z każdej grupy.

2. RANKING SKUMULOWANY: Posortuj unikalne scenariusze według sumy probability scores
   ze wszystkich analiz (HIGH=3, MEDIUM=2, LOW=1).

3. PRZEOCZONE RYZYKA: Scenariusze obecne tylko w jednej analizie ale z HIGH probability.
   Mogą być najcenniejsze — inny model widział coś czego pozostałe nie złapały.

Zwróć wyłącznie JSON:
{
  "ticker": "",
  "agent": "premortem",
  "failure_scenarios": [
    {
      "rank": 1,
      "description": "",
      "mechanism": "",
      "type": "company-specific|sector-wide|macro",
      "probability": "LOW|MEDIUM|HIGH",
      "earliest_warning_signal": ""
    }
  ],
  "top_blind_spot": "",
  "raw_analysis": "MAX 150 słów. Synthesizer może być bardziej rozbudowany."
}

Zasady wypełnienia:

- failure_scenarios: top 5 po deduplikacji i rankingu skumulowanym
- top_blind_spot: scenariusz z PRZEOCZONE RYZYKA lub najwyżej rankowany jeśli brak przeoczonych
- raw_analysis: krótkie podsumowanie procesu syntezy
