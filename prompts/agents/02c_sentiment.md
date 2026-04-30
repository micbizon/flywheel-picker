{{ CORE_RULES }}

{{ COMPANY_NAME_CONTEXT }}

Analizuj krajobraz informacyjny wokół [TICKER].

Zwróć wyłącznie JSON:
{
  "ticker": "",
  "agent": "sentiment",
  "verdict": "PASS|WATCH|REJECT",
  "summary": "MAX 2 zdania. Narracja + główny katalizator.",
  "narrative_status": "AHEAD|BEHIND|DISTORTED",
  "next_catalyst": "np. Q2 earnings + spodziewany efekt w MAX 10 słowach.",
  "next_catalyst_date": "",
  "key_strengths": ["MAX 2 pozycje. MAX 10 słów każda."],
  "key_risks": ["MAX 2 pozycje. MAX 10 słów każda."],
  "raw_analysis": "MAX 50 słów."
}
