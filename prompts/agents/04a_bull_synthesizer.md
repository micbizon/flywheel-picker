{{ CORE_RULES }}

Otrzymujesz [N] niezależnych analiz bull case dla [TICKER].
Twoim zadaniem jest synteza — nie uśrednianie, lecz wyciąganie sygnału z szumu.

ANALIZY DO SYNTEZY:
[BULL_ANALYSES]

Wykonaj w tej kolejności:

1. KONSENSUS: Argumenty obecne w minimum 2 z [N] analiz.
   To są twarde punkty tezy — wysoka pewność.

2. UNIKALNE SYGNAŁY: Argumenty obecne tylko w jednej analizie.
   Oceń każdy: czy to przeoczony czynnik czy halucynacja?
   Oznacz jako WARTO_ZBADAĆ lub ODRZUCAM z jednozdaniowym powodem.

3. SPRZECZNOŚCI: Miejsca gdzie analizy się kłócą.
   Wskaż co jest sprzeczne i która wersja wydaje się bardziej ugruntowana w faktach.

4. SYNTETYCZNY BULL CASE: Jeden spójny raport bazujący na powyższym.
   Nie powtarzaj treści z kroków 1-3 — napisz narrację która z nich wynika.

Zwróć wyłącznie JSON:
{
  "ticker": "",
  "agent": "bull",
  "core_thesis": "2 zdania — najsilniejszy argument bull.",
  "flywheel_mechanism": "1 zdanie — mechanizm wzrostu.",
  "key_assumptions": ["max 3, każde falsifiable z progiem"],
  "price_target_3yr": 0,
  "upside_x": 0.0,
  "underappreciated_factor": "",
  "raw_analysis": "MAX 150 słów — syntetyczny bull case."
}

Zasady wypełnienia:
- key_assumptions: tylko te z sekcji KONSENSUS
- underappreciated_factor: najlepszy sygnał z UNIKALNE SYGNAŁY oznaczony WARTO_ZBADAĆ (lub null jeśli brak)
- raw_analysis: narracja z kroku 4 (SYNTETYCZNY BULL CASE)