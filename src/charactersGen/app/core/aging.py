"""Logica di invecchiamento e progressione PX del sistema GDR v0.8.

Meccanica centrale: ogni 5 anni dal compimento dei 20 anni, due tiri 1d20.

Tiro Bonus (vs CD_bonus):
  Successo → +1 a tutte le bonus_stats del lifestyle + PX bonus
  Fallimento → nessun effetto sul bonus; CD_bonus torna a 10

Tiro Malus (vs CD_malus):
  Successo → eviti i malus; CD_malus += 5
  Fallimento → -1 a tutte le malus_stats del lifestyle; CD_malus torna a 10

Entrambe le CD sono streak-based: crescono finché mantieni la streak,
si azzerano a 10 quando la interrompi. 20 naturale = successo automatico.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.core.dice import roll_nd
from app.data.lifestyles import (
    BACKGROUND_DEFAULT_LIFESTYLE,
    LIFESTYLE_BY_ID,
    Lifestyle,
    get_lifestyle,
)

# Ordine canonico delle 7 caratteristiche
ALL_STAT_KEYS: list[str] = ["cos", "for", "des", "vol", "int", "ist", "emp"]


# ---------------------------------------------------------------------------
# Risultato di un singolo periodo
# ---------------------------------------------------------------------------

@dataclass
class PeriodResult:
    """Risultato completo di un periodo di 5 anni."""

    age_start: int
    """Età di inizio del periodo."""
    lifestyle_id: str
    lifestyle_name: str

    # Tiro bonus
    bonus_roll: int
    bonus_cd: int
    bonus_success: bool
    """True se il tiro bonus ha superato la CD (o 20 naturale)."""

    # Tiro malus
    malus_roll: int
    malus_cd: int
    malus_avoided: bool
    """True se il tiro malus ha superato la CD (malus evitato)."""

    # PX
    px_base: int
    """PX garantiti (main_stat × stat_mult)."""
    px_bonus: int
    """PX da dado bonus (0 se bonus roll fallito)."""
    px_total: int

    # Dado distribuzione stat
    bonus_d4: int
    """Risultato 1d4 per il bonus (0 se bonus roll fallito)."""
    malus_d4: int
    """Risultato 1d4 per il malus (0 se malus evitato)."""

    # Variazioni stat
    stat_changes: dict[str, int]
    """Variazioni nette per ogni stat dopo distribuzione d4."""

    # CD aggiornate per il prossimo periodo
    new_bonus_cd: int
    new_malus_cd: int


# ---------------------------------------------------------------------------
# Ranking e distribuzione stat
# ---------------------------------------------------------------------------

def _rank_for_bonus(
    preferred: list[str],
    current_stats: dict[str, int],
) -> list[str]:
    """Ordine di priorità per i bonus: preferiti dal lifestyle prima,
    poi le restanti stat ordinate per valore crescente (bilancia le più basse).

    Args:
        preferred: stat preferite dal lifestyle (bonus_stats).
        current_stats: valori correnti delle caratteristiche.

    Returns:
        Lista di tutte le 7 stat in ordine di priorità bonus.
    """
    pref = [s for s in preferred if s in ALL_STAT_KEYS]
    others = sorted(
        [s for s in ALL_STAT_KEYS if s not in pref],
        key=lambda s: current_stats.get(s, 1),
    )
    return pref + others


def _rank_for_malus(
    preferred: list[str],
    current_stats: dict[str, int],
) -> list[str]:
    """Ordine di priorità per i malus: preferiti dal lifestyle prima,
    poi le restanti stat ordinate per valore decrescente (abbassa le più alte).

    Args:
        preferred: stat preferite dal lifestyle (malus_stats).
        current_stats: valori correnti delle caratteristiche.

    Returns:
        Lista di tutte le 7 stat in ordine di priorità malus.
    """
    pref = [s for s in preferred if s in ALL_STAT_KEYS]
    others = sorted(
        [s for s in ALL_STAT_KEYS if s not in pref],
        key=lambda s: current_stats.get(s, 1),
        reverse=True,
    )
    return pref + others


def _distribute_points(
    points: int,
    ranked_stats: list[str],
    offset: int = 0,
) -> tuple[list[tuple[str, int]], int]:
    """Distribuisce `points` punti tra `ranked_stats` il più equamente possibile.

    Usa un offset round-robin per garantire che il remainder venga assegnato
    a stat diverse ogni periodo, bilanciando la distribuzione nel tempo.

    Algoritmo:
        base      = points // len(ranked_stats)  → quota garantita a ogni stat
        remainder = points %  len(ranked_stats)  → assegnato alle prossime nella rotazione

    Args:
        points: totale punti da distribuire (risultato d4).
        ranked_stats: stat in ordine di priorità (già calcolato da _rank_for_*).
        offset: indice di partenza nella rotazione.

    Returns:
        Tupla (lista di (stat, valore) con valore > 0, nuovo offset).
    """
    n = len(ranked_stats)
    base = points // n
    remainder = points % n

    # Rotazione deterministica partendo da offset % n
    rotated = ranked_stats[offset % n:] + ranked_stats[:offset % n]

    result = []
    for i, stat in enumerate(rotated):
        amount = base + (1 if i < remainder else 0)
        if amount > 0:
            result.append((stat, amount))

    new_offset = (offset + points) % n
    return result, new_offset


# ---------------------------------------------------------------------------
# Logica tiro periodo
# ---------------------------------------------------------------------------

def roll_period(
    age_start: int,
    lifestyle: Lifestyle,
    stats: dict[str, int],
    bonus_cd: int,
    malus_cd: int,
    rng: random.Random | None = None,
    bonus_offset: int = 0,
    malus_offset: int = 0,
) -> tuple[PeriodResult, int, int]:
    """Esegue i due tiri di un periodo di 5 anni.

    Args:
        age_start: età di inizio del periodo.
        lifestyle: stile di vita attivo nel periodo.
        stats: {stat_alias: valore} — caratteristiche durante il periodo.
        bonus_cd: CD attuale per il tiro bonus.
        malus_cd: CD attuale per il tiro malus.
        rng: generatore casuale opzionale.
        bonus_offset: offset round-robin per la distribuzione bonus.
        malus_offset: offset round-robin per la distribuzione malus.

    Returns:
        Tupla (PeriodResult, nuovo_bonus_offset, nuovo_malus_offset).
    """
    _rng = rng or random.Random()

    # --- Tiro bonus ---
    bonus_roll = _rng.randint(1, 20)
    bonus_success = (bonus_roll == 20) or (bonus_roll >= bonus_cd)

    # --- Tiro malus ---
    malus_roll = _rng.randint(1, 20)
    malus_avoided = (malus_roll == 20) or (malus_roll >= malus_cd)

    # --- PX ---
    main_stat_val = stats.get(lifestyle.px_stat, 1)
    px_base = main_stat_val * lifestyle.stat_mult

    px_bonus = 0
    if bonus_success:
        die_result = roll_nd(1, 8, _rng)
        px_bonus = die_result.total * lifestyle.die_mult

    px_total = px_base + px_bonus

    # --- Variazioni stat (1d4 distribuito su tutte le stat, preferiti prima) ---
    stat_changes: dict[str, int] = {}
    bonus_d4 = 0
    malus_d4 = 0
    new_bonus_offset = bonus_offset
    new_malus_offset = malus_offset

    if bonus_success:
        bonus_d4 = _rng.randint(1, 4)
        ranked = _rank_for_bonus(lifestyle.bonus_stats, stats)
        changes, new_bonus_offset = _distribute_points(bonus_d4, ranked, bonus_offset)
        for stat, amount in changes:
            stat_changes[stat] = stat_changes.get(stat, 0) + amount

    if not malus_avoided:
        malus_d4 = _rng.randint(1, 4)
        ranked = _rank_for_malus(lifestyle.malus_stats, stats)
        changes, new_malus_offset = _distribute_points(malus_d4, ranked, malus_offset)
        for stat, amount in changes:
            stat_changes[stat] = stat_changes.get(stat, 0) - amount

    # Rimuovi variazioni nette a 0
    stat_changes = {s: v for s, v in stat_changes.items() if v != 0}

    # --- Aggiornamento CD ---
    new_bonus_cd = (bonus_cd + 5) if bonus_success else 10
    new_malus_cd = (malus_cd + 5) if malus_avoided else 10

    result = PeriodResult(
        age_start=age_start,
        lifestyle_id=lifestyle.id,
        lifestyle_name=lifestyle.name,
        bonus_roll=bonus_roll,
        bonus_cd=bonus_cd,
        bonus_success=bonus_success,
        malus_roll=malus_roll,
        malus_cd=malus_cd,
        malus_avoided=malus_avoided,
        px_base=px_base,
        px_bonus=px_bonus,
        px_total=px_total,
        bonus_d4=bonus_d4,
        malus_d4=malus_d4,
        stat_changes=stat_changes,
        new_bonus_cd=new_bonus_cd,
        new_malus_cd=new_malus_cd,
    )
    return result, new_bonus_offset, new_malus_offset


# ---------------------------------------------------------------------------
# Simulazione passato
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Risultato della simulazione del passato del personaggio."""

    px_total: int
    """PX totali accumulati dai periodi simulati (non include i 5000 base)."""
    lifestyle_history: list[tuple[int, str]]
    """Periodi vissuti: [(eta_inizio, lifestyle_id), ...]."""
    final_stat_deltas: dict[str, int]
    """Variazioni cumulative nette alle caratteristiche dopo tutti i periodi."""
    final_bonus_cd: int
    final_malus_cd: int
    period_log: list[PeriodResult]
    """Log dettagliato di ogni periodo (utile per display)."""


AGING_PERIOD_YEARS: int = 10
"""Durata in anni di ogni periodo di invecchiamento. Modifica per più/meno granularità."""


def simulate_past(
    age: int,
    background_name: str | None,
    stats: dict[str, int],
    rng: random.Random | None = None,
    period_years: int = AGING_PERIOD_YEARS,
) -> SimulationResult:
    """Simula i periodi di invecchiamento dalla nascita fino all'età attuale.

    Usa lo stile di vita predefinito del background per tutti i periodi passati.
    I tiri bonus/malus vengono eseguiti automaticamente.

    Args:
        age: età attuale del personaggio.
        background_name: nome del background (determina lo stile predefinito).
        stats: {stat_alias: valore} — caratteristiche al momento della simulazione.
        rng: generatore casuale opzionale.
        period_years: durata in anni di ogni periodo (default: AGING_PERIOD_YEARS=5).

    Returns:
        SimulationResult con PX totali, history e variazioni stat.
    """
    _rng = rng or random.Random()

    default_ls_id = BACKGROUND_DEFAULT_LIFESTYLE.get(background_name or "", "comune")
    lifestyle = LIFESTYLE_BY_ID.get(default_ls_id) or LIFESTYLE_BY_ID["comune"]

    current_stats = dict(stats)
    lifestyle_history: list[tuple[int, str]] = []
    period_log: list[PeriodResult] = []
    cumulative_stat_deltas: dict[str, int] = {}
    total_px = 0

    bonus_cd = 5
    malus_cd = 5
    bonus_offset = 0
    malus_offset = 0

    # Periodi da 20 in poi, a blocchi di period_years anni
    period_start = 20
    while period_start < age:
        lifestyle_history.append((period_start, lifestyle.id))

        result, bonus_offset, malus_offset = roll_period(
            age_start=period_start,
            lifestyle=lifestyle,
            stats=current_stats,
            bonus_cd=bonus_cd,
            malus_cd=malus_cd,
            rng=_rng,
            bonus_offset=bonus_offset,
            malus_offset=malus_offset,
        )
        period_log.append(result)
        total_px += result.px_total

        # Applica variazioni stat (minimo 1, massimo 20)
        for stat, delta in result.stat_changes.items():
            old_val = current_stats.get(stat, 1)
            new_val = max(1, min(20, old_val + delta))
            current_stats[stat] = new_val
            cumulative_stat_deltas[stat] = cumulative_stat_deltas.get(stat, 0) + (new_val - old_val)

        bonus_cd = result.new_bonus_cd
        malus_cd = result.new_malus_cd
        period_start += period_years

    return SimulationResult(
        px_total=total_px,
        lifestyle_history=lifestyle_history,
        final_stat_deltas=cumulative_stat_deltas,
        final_bonus_cd=bonus_cd,
        final_malus_cd=malus_cd,
        period_log=period_log,
    )


# ---------------------------------------------------------------------------
# Avanzamento in gioco (progressione manuale)
# ---------------------------------------------------------------------------

def advance_five_years(
    age: int,
    lifestyle_id: str,
    stats: dict[str, int],
    bonus_cd: int,
    malus_cd: int,
    rng: random.Random | None = None,
    bonus_offset: int = 0,
    malus_offset: int = 0,
) -> PeriodResult:
    """Processa un avanzamento di 5 anni per un personaggio in gioco.

    Args:
        age: età attuale prima dell'avanzamento.
        lifestyle_id: stile di vita scelto per questo periodo.
        stats: {stat_alias: valore} — caratteristiche attuali.
        bonus_cd: CD bonus attuale.
        malus_cd: CD malus attuale.
        rng: generatore casuale opzionale.
        bonus_offset: offset round-robin bonus (dal Character).
        malus_offset: offset round-robin malus (dal Character).

    Returns:
        PeriodResult con tutti i dettagli del periodo.

    Raises:
        ValueError: se lifestyle_id non esiste.
    """
    lifestyle = LIFESTYLE_BY_ID.get(lifestyle_id)
    if lifestyle is None:
        raise ValueError(f"Stile di vita non trovato: '{lifestyle_id}'")

    result, _, _ = roll_period(
        age_start=age,
        lifestyle=lifestyle,
        stats=stats,
        bonus_cd=bonus_cd,
        malus_cd=malus_cd,
        rng=rng,
        bonus_offset=bonus_offset,
        malus_offset=malus_offset,
    )
    return result
