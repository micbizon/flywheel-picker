{{ CORE_RULES }}

{{ COMPANY_NAME_CONTEXT }}

Analizuj [TICKER] przez lens flywheel'u. Spółki powyej $2B.

Zwróć wyłącznie JSON:
{
  "ticker": "",
  "agent": "fundamental",
  "verdict": "PASS|WATCH|REJECT",
  "summary": "MAX 2 zdania. Co decyduje o verdict. Musi zawierać liczbę.",
  "key_strengths": ["MAX 3 pozycje. Każda MAX 10 słów z liczbą lub datą."],
  "key_risks": ["MAX 3 pozycje. Każda MAX 10 słów z konkretnym mechanizmem."],
  "raw_analysis": "MAX 100 słów. Tylko to czego nie ma w polach wyżej."
}
