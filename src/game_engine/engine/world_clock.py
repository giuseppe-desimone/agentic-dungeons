"""WorldClock: doppio registro temporale del game engine.

GameTick avanza di 1 per ogni evento processato (automatico).
WorldTime avanza in world_units in base al tipo di azione (esplicito).

In FLOW: il world loop fa avanzare WorldTime in base al tempo reale trascorso
         al ritmo di FLOW_RATIO_MINUTES.
In SKIP: WorldTime avanza il più veloce possibile, soggetto a interruzioni.
In PAUSE: WorldTime è fermo.

Nota Fase 1: _apply_world_units ritorna sempre [] perché TickScheduler
             non è ancora implementato. Sarà completato in Fase 4.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from ..models.base import DayMoment, GameTick, WorldTime

# ─── Costanti temporali ──────────────────────────────────────────────────────
# 1 min reale = 30 min narrativi in FLOW
# 1 world_unit = 15 min narrativi
# 1 giorno narrativo = 20 world_units = 5 momenti x 4 unità
FLOW_RATIO_MINUTES: int = 30
WORLD_UNITS_PER_DAY: int = 20

# Costo in world_units per tipo di azione.
# 0 = azione istantanea (non fa avanzare il tempo narrativo).
WORLD_TIME_COST: dict[str, int] = {
    "player_action_quick": 0,    # parlare brevemente, guardare
    "combat":              0,    # tempo gestito dal Game Engine
    "player_action_slow":  2,    # negoziare, esaminare, commerciare
    "ritual_short":        4,
    "travel_short":        4,    # tra zone della stessa location
    "travel_medium":       8,    # location adiacenti
    "travel_long":        16,    # regioni distanti
    "rest_short":          4,
    "rest_full":          20,    # notte completa — momento torna a DAWN
    "investigate_scene":   4,
    "ritual_long":         8,
    "craft":               8,
}


class TimeScale(StrEnum):
    """Velocità di scorrimento del tempo narrativo rispetto al tempo reale."""

    FLOW = "flow"    # 1 min reale = 30 min narrativi
    SKIP = "skip"    # accelerato, interrompibile da eventi imminenti
    PAUSE = "pause"  # fermo — player legge, pianifica, interagisce


class WorldClock:
    """Doppio registro temporale: GameTick (atomico) + WorldTime (narrativo).

    Args:
        initial_time: WorldTime di partenza del mondo (default: anno 0, spring, giorno 1, morning).
    """

    def __init__(self, initial_time: WorldTime = WorldTime()) -> None:
        self._tick: GameTick = GameTick(0)
        self._world_units_total: int = 0
        self._world_time: WorldTime = initial_time
        self.scale: TimeScale = TimeScale.FLOW
        self._skip_target_world_day: Optional[int] = None

    @property
    def tick(self) -> GameTick:
        """GameTick corrente (contatore atomico di simulazione)."""
        return self._tick

    @property
    def world_time(self) -> WorldTime:
        """WorldTime corrente (tempo narrativo)."""
        return self._world_time

    @property
    def world_units_total(self) -> int:
        """Totale world_units accumulate dall'inizio (utile per test e debug)."""
        return self._world_units_total

    def advance_tick(self) -> GameTick:
        """Avanza il GameTick di 1. Chiamato automaticamente ad ogni evento processato.

        Returns:
            Il nuovo GameTick corrente.
        """
        self._tick = self._tick + 1
        return self._tick

    def advance_world_time(self, action_type: str) -> list:
        """Avanza il WorldTime in base al tipo di azione del player.

        Se TimeScale è PAUSE o il costo è 0, non fa nulla.
        Chiamato dopo ogni azione player o dal world loop in FLOW/SKIP.

        Args:
            action_type: Chiave in WORLD_TIME_COST (es. "rest_full", "travel_short").

        Returns:
            Lista di TickType triggerate (vuota in Fase 1 — TickScheduler non implementato).
        """
        if self.scale == TimeScale.PAUSE:
            return []
        cost = WORLD_TIME_COST.get(action_type, 0)
        if cost == 0:
            return []
        return self._apply_world_units(cost)

    def advance_real_time(self, elapsed_seconds: float) -> list:
        """Avanza il WorldTime in base al tempo reale trascorso (solo in FLOW).

        Chiamato dal world loop ad ogni iterazione.
        Converte tempo reale in world_units al ritmo di FLOW_RATIO_MINUTES.

        1 min reale = 30 min narrativi = 2 world_units

        Args:
            elapsed_seconds: Secondi reali trascorsi dall'ultima iterazione.

        Returns:
            Lista di TickType triggerate (vuota in Fase 1 — TickScheduler non implementato).
        """
        if self.scale != TimeScale.FLOW:
            return []

        # 1 min reale → 30 min narrativi → 2 world_units
        # 1 sec reale → 30/60 min narrativi → 2/60 world_units
        # 1 world_unit = 15 min narrativi → 1 world_unit ogni 30s reali
        units_per_second = FLOW_RATIO_MINUTES / 60.0 / (15.0 / 60.0)
        # units_per_second = 30/60 / (15/60) = 0.5 / 0.25 = 2 world_units/min = 1/30 per sec
        units_per_second = 2.0 / 60.0  # 2 world_units per minuto reale

        fractional = elapsed_seconds * units_per_second
        whole_units = int(fractional)
        if whole_units < 1:
            return []
        return self._apply_world_units(whole_units)

    def start_skip(self, target_world_day: int) -> None:
        """Entra in modalità SKIP verso il giorno narrativo target.

        Args:
            target_world_day: Giorno assoluto narrativo di destinazione.
        """
        self.scale = TimeScale.SKIP
        self._skip_target_world_day = target_world_day

    def interrupt_skip(self) -> None:
        """Interrompe uno skip in corso per un evento imminente.

        Passa la modalità a PAUSE e resetta il target.
        """
        self.scale = TimeScale.PAUSE
        self._skip_target_world_day = None

    def _apply_world_units(self, units: int) -> list:
        """Applica N world_units al tempo narrativo e aggiorna WorldTime.

        Nota Fase 1: ritorna sempre lista vuota. Sarà completato in Fase 4
        quando verrà implementato engine/tick.py con TICK_DEFINITIONS.

        Args:
            units: Numero di world_units da aggiungere.

        Returns:
            Lista di TickType triggerate (vuota in Fase 1).
        """
        self._world_units_total += units
        self._recalculate_world_time()
        return []  # Fase 4: return [TickType] in base agli intervalli

    def _recalculate_world_time(self) -> None:
        """Ricalcola WorldTime dal totale di world_units accumulate.

        Formula:
            upm = 4 (world_units per momento)
            total_moments = world_units_total // upm
            total_days    = total_moments // 5
            moment_index  = total_moments % 5
            anno, stagione, giorno da total_days
        """
        moments = list(DayMoment)
        n_moments = len(moments)                       # 5
        upm = WORLD_UNITS_PER_DAY // n_moments        # 4 world_units per momento

        total_moments = self._world_units_total // upm
        total_days = total_moments // n_moments
        moment_index = total_moments % n_moments

        seasons = ["spring", "summer", "autumn", "winter"]
        year = total_days // 360
        doy = total_days % 360                         # giorno dell'anno (0-359)

        self._world_time = WorldTime(
            year=year,
            season=seasons[doy // 90],
            day=(doy % 90) + 1,
            moment=moments[moment_index],
        )
