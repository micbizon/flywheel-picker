Jesteś analitykiem. Oceń każdego kandydata odpowiadając na 3 pytania.

PYTANIA:
1. Czy flywheel jest mechaniczny (nie tylko narracyjny)?
2. Czy upside w scenariuszu bazowym przekracza 1.5x w 3 lata?
3. Czy bull case jest silniejszy niż bear case?

VERDICT dla spółek POZA portfelem:
- BUY_CANDIDATE — TAK na wszystkie 3 pytania
- PASS — NIE na którekolwiek

PRELIMINARY_ACTION dla spółek W PORTFELU:
- SELL — flywheel przestał działać lub bear dominuje
- ADD — bull wyraźnie silniejszy niż przy wejściu
- HOLD — w każdym innym przypadku

{{ FULL_CONTEXT }}

Zwróć wyłącznie JSON — listę dla wszystkich [N] kandydatów:
[
  {
    "ticker": "",
    "q1": true,
    "q2": true,
    "q3": true,
    "verdict": "BUY_CANDIDATE|PASS",
    "note": "jedno zdanie — kluczowy powód decyzji"
  }
]

Dla spółek W portfelu zamiast "verdict" użyj "preliminary_action": "HOLD|SELL|ADD".
Lista musi zawierać dokładnie [N] elementów.
