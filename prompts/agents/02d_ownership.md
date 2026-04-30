{{ CORE_RULES }}

{{ COMPANY_NAME_CONTEXT }}

Analizuj strukturę własnościową [TICKER].

Zwróć wyłącznie JSON:
{
  "ticker": "",
  "agent": "ownership",
  "verdict": "PASS|WATCH|REJECT",
  "summary": "MAX 2 zdania. Insider signal + float risk.",
  "float_risk": "LOW|MEDIUM|HIGH + powód MAX 8 słów.",
  "insider_signal": "BULLISH|NEUTRAL|BEARISH + np. CEO $2.1M własnych środków mar-2025.",
  "key_strengths": ["MAX 2 pozycje. MAX 10 słów każda."],
  "key_risks": ["MAX 2 pozycje. MAX 10 słów każda."],
  "raw_analysis": "MAX 50 słów."
}
