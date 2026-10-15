# Kolejka zadań implementacyjnych

## Jak używać tego pliku

1. Jedno aktywne zadanie na raz w sekcji **Zadanie aktywne**
2. Przed każdą sesją z Claude Code wklej:

```text
Pracujemy nad projektem multi-agent investment system.
Przeczytaj /docs/ARCHITECTURE.md i /TASKS.md zanim zaczniesz.
Aktywne zadanie to TASK-034.
Nie zmieniaj nic poza plikami wymienionymi w zadaniu.
Po zakończeniu zadania zaktualizuj CHANGELOG.md, 
wpisz datę, 1-3 zdania podsumowania, opisz co faktycznie zostało zrobione tak jak opisałeś w rozumowaniu podejście przed
implementacją, konkretnie, z nazwami funkcji i kluczowymi decyzjami projektowymi.
Nie kopiuj pełnej treści zadania.
```

---

## Zadanie aktywne

*(brak — wybierz następne zadanie z Backlogu)*

---

## Backlog

## Zablokowane / On hold

| Task | Blokada | Czeka na |
|------|---------|---------|
|*(brak)*|--|--|

---

## Otwarte pytania (wymagają decyzji przed implementacją)

- **Batch processing API:** Rozważyć gdy miesięczny koszt API >$50.
  Kandydaci: warstwa 2 (4 agenty per ticker) i instancje bull/bear/premortem.
  Ograniczenie: pipeline ma zależności sekwencyjne — batch tylko w obrębie
  jednej warstwy, nie między warstwami.
