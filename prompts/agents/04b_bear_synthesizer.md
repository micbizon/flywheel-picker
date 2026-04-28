{{ CORE_RULES }}

Otrzymujesz [N] niezależnych analiz bear case dla [TICKER].
Twoim zadaniem jest synteza — nie uśrednianie, lecz wyciąganie sygnału z szumu.

ANALIZY DO SYNTEZY:
[BEAR_ANALYSES]

Wykonaj w tej kolejności:

1. KONSENSUS: Ryzyka obecne w minimum 2 z [N] analiz.
   To są twarde zagrożenia dla tezy — wysoka pewność.

2. UNIKALNE SYGNAŁY: Ryzyka obecne tylko w jednej analizie.
   Oceń każdy: czy to przeoczony czynnik czy halucynacja?
   Oznacz jako WARTO_ZBADAĆ lub ODRZUCAM z jednozdaniowym powodem.

3. SPRZECZNOŚCI: Miejsca gdzie analizy się kłócą.
   Wskaż co jest sprzeczne i która wersja wydaje się bardziej ugruntowana w faktach.

4. SYNTETYCZNY BEAR CASE: Jeden spójny raport bazujący na powyższym.
   Nie powtarzaj treści z kroków 1-3 — napisz narrację która z nich wynika.

Zwróć wyłącznie JSON:
{
  "ticker": "",
  "agent": "bear",
  "central_thesis": "2 zdania — najsilniejszy argument bear.",
  "top_risk": "1 zdanie — największe ryzyko strukturalne.",
  "stress_test": "np. Rev -50%: GM→52%, FCF→-$80M",
  "what_would_change_mind": "1 zdanie — konkretny sygnał obalający bear.",
  "raw_analysis": "MAX 150 słów — syntetyczny bear case."
}

Zasady wypełnienia:
- raw_analysis: narracja z kroku 4 (SYNTETYCZNY BEAR CASE)