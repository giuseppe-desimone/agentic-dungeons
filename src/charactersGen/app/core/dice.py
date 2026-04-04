"""Motore dadi per il sistema GDR v0.8.

Meccaniche principali:
- roll_nd(n, d) → tira n dadi a d facce
- roll_advantage(d) → 2d prendi il maggiore
- roll_disadvantage(d) → 2d prendi il minore
- roll_1d20() → tiro base
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class DiceResult:
    """Risultato di un lancio di dadi."""

    rolls: list[int]
    total: int
    kept: int  # valore tenuto (utile per vantaggio/svantaggio)

    def __str__(self) -> str:
        return f"[{', '.join(str(r) for r in self.rolls)}] → {self.kept}"


def roll_nd(n: int, d: int, rng: random.Random | None = None) -> DiceResult:
    """Tira n dadi a d facce e restituisce la somma.

    Args:
        n: numero di dadi.
        d: numero di facce per dado.
        rng: generatore casuale opzionale (per i test).

    Returns:
        DiceResult con tutti i valori e il totale.
    """
    _rng = rng or random
    rolls = [_rng.randint(1, d) for _ in range(n)]
    total = sum(rolls)
    return DiceResult(rolls=rolls, total=total, kept=total)


def roll_advantage(d: int, rng: random.Random | None = None) -> DiceResult:
    """Tira 2 dadi a d facce e tiene il risultato più alto (Vantaggio).

    Args:
        d: numero di facce del dado.
        rng: generatore casuale opzionale.

    Returns:
        DiceResult con entrambi i tiri e il valore tenuto.
    """
    _rng = rng or random
    r1 = _rng.randint(1, d)
    r2 = _rng.randint(1, d)
    kept = max(r1, r2)
    return DiceResult(rolls=[r1, r2], total=r1 + r2, kept=kept)


def roll_disadvantage(d: int, rng: random.Random | None = None) -> DiceResult:
    """Tira 2 dadi a d facce e tiene il risultato più basso (Svantaggio).

    Args:
        d: numero di facce del dado.
        rng: generatore casuale opzionale.

    Returns:
        DiceResult con entrambi i tiri e il valore tenuto.
    """
    _rng = rng or random
    r1 = _rng.randint(1, d)
    r2 = _rng.randint(1, d)
    kept = min(r1, r2)
    return DiceResult(rolls=[r1, r2], total=r1 + r2, kept=kept)


def roll_1d20(rng: random.Random | None = None) -> DiceResult:
    """Tira 1d20 (tiro base del sistema).

    Args:
        rng: generatore casuale opzionale.

    Returns:
        DiceResult.
    """
    return roll_nd(1, 20, rng)


def roll_characteristic(num_dice: int, die: int = 4, rng: random.Random | None = None) -> int:
    """Tira i dadi per una caratteristica e restituisce il totale.

    Args:
        num_dice: numero di dadi (2 per personaggi <20 anni, 3 per ≥20).
        die: tipo di dado (default d4 per umani/nani).
        rng: generatore casuale opzionale.

    Returns:
        Valore totale della caratteristica.
    """
    return roll_nd(num_dice, die, rng).total


def skill_check(
    characteristic: int,
    grades: int,
    bonus: int = 0,
    advantage: bool = False,
    disadvantage: bool = False,
    rng: random.Random | None = None,
) -> tuple[DiceResult, int]:
    """Esegue un tiro abilità completo.

    Competente (grades >= 1): 1d20 + caratteristica + gradi + bonus
    Non competente (grades == 0): 2d20 minore + caratteristica//2 + bonus
    Vantaggio: 2d20 maggiore
    Svantaggio: 2d20 minore

    Args:
        characteristic: valore della caratteristica collegata.
        grades: gradi nell'abilità.
        bonus: bonus/malus situazionale.
        advantage: se True, tiro con vantaggio.
        disadvantage: se True, tiro con svantaggio.
        rng: generatore casuale opzionale.

    Returns:
        Tupla (DiceResult, risultato_finale).
    """
    competent = grades >= 1

    if advantage and not disadvantage:
        dice = roll_advantage(20, rng)
    elif disadvantage or not competent:
        dice = roll_disadvantage(20, rng)
    else:
        dice = roll_1d20(rng)

    stat_bonus = characteristic if competent else characteristic // 2
    final = dice.kept + stat_bonus + (grades if competent else 0) + bonus
    return dice, final
