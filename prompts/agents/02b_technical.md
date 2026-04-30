{{ CORE_RULES }}

{{ COMPANY_NAME_CONTEXT }}
{{ PRICE_CONTEXT }}

Oceń setup techniczny [TICKER] pod kątem długoterminowego wejścia.
Nie przewiduj krótkoterminowych ruchów.

Zwróć wyłącznie JSON:
{
  "ticker": "",
  "agent": "technical",
  "verdict": "PASS|WATCH|REJECT",
  "summary": "MAX 2 zdania. Trend + jakość wejścia.",
  "entry_zone": "np. $95-102. Jeden powód w MAX 5 słowach.",
  "invalidation_level": "np. $87.50 — tygodniowe zamknięcie poniżej.",
  "key_strengths": ["MAX 2 pozycje. MAX 10 słów każda."],
  "key_risks": ["MAX 2 pozycje. MAX 10 słów każda."],
  "raw_analysis": "MAX 50 słów."
}
