"""PlayerIntent, ActiveInteraction, SkipSession — modelli per le intenzioni del player.

In un mondo di tipo B (world-driven), il player non esegue azioni immediate.
Esprime **intenzioni** che si svolgono nel tempo narrativo.
Le azioni con world_time_cost == 0 rimangono immediate.

Cicli di vita:
    PlayerIntent: pending → in_progress → completed | interrupted | cancelled
    ActiveInteraction: active → suspended → resumed | expired
    SkipSession: active → completed | interrupted
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import GameTick, WorldTime


class PlayerIntent(BaseModel):
    """Un'intenzione del player schedulata nel tempo narrativo.

    Le azioni con world_time_cost > 0 diventano PlayerIntent.
    Completano quando il world_time raggiunge completes_at_world_day.
    Possono essere interrotte da eventi del mondo.

    Args:
        id: UUID univoco dell'intenzione.
        action_id: Identificatore del tipo di azione (es. "rest_full", "travel_short").
        target_id: Entità target dell'azione (opzionale).
        payload: Dati contestuali dell'azione.
        scheduled_at: WorldTime in cui è stata schedulata.
        estimated_duration_units: Durata prevista in world_units.
        completes_at_world_day: Giorno narrativo assoluto di completamento.
        status: Stato corrente del ciclo di vita.
        interrupt_event_id: ID dell'evento che ha causato l'interruzione (se interrotta).
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str
    target_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)

    scheduled_at: WorldTime
    estimated_duration_units: int
    completes_at_world_day: int

    status: str = "pending"
    # "pending" | "in_progress" | "completed" | "interrupted" | "cancelled"

    interrupt_event_id: Optional[str] = None

    def is_active(self) -> bool:
        """Ritorna True se l'intenzione è in stato attivo (pending o in_progress)."""
        return self.status in ("pending", "in_progress")

    def is_terminal(self) -> bool:
        """Ritorna True se l'intenzione ha raggiunto uno stato terminale."""
        return self.status in ("completed", "interrupted", "cancelled")


class ActiveInteraction(BaseModel):
    """Un'interazione in corso tra il player e entità nel mondo.

    Ha un contesto spaziale: eventi che accadono nella stessa location
    possono entrarvi come intrusioni narrative.

    Non esistono livelli di urgenza — l'unico criterio per le intrusioni
    è la prossimità fisica (stessa location_id).

    Args:
        id: UUID univoco dell'interazione.
        type: Tipo di interazione ("dialogue"|"trade"|"ritual"|"exploration").
        participants: entity_id dei partecipanti all'interazione.
        location_id: Location dove si svolge l'interazione.
        state: Contesto narrativo corrente — passato all'Agente Narrativo.
        open_to_intrusion: Se False, nessun evento può intrudere
                           (interazioni in isolamento fisico, riti segreti).
        suspended_at: WorldTime in cui l'interazione è stata sospesa.
        resumable: Se True, può essere ripresa dopo una sospensione.
        expires_at_world_day: Giorno narrativo in cui scade (se non ripresa).
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    participants: list[str] = Field(default_factory=list)
    location_id: str

    state: dict[str, Any] = Field(default_factory=dict)
    open_to_intrusion: bool = True

    suspended_at: Optional[WorldTime] = None
    resumable: bool = True
    expires_at_world_day: Optional[int] = None

    def is_suspended(self) -> bool:
        """Ritorna True se l'interazione è attualmente sospesa."""
        return self.suspended_at is not None

    def is_expired(self, current_world_day: int) -> bool:
        """Ritorna True se l'interazione è scaduta al giorno corrente.

        Args:
            current_world_day: Giorno narrativo assoluto corrente.

        Returns:
            True se expires_at_world_day è settato e il giorno corrente lo ha superato.
        """
        if self.expires_at_world_day is None:
            return False
        return current_world_day >= self.expires_at_world_day


class SkipSession(BaseModel):
    """Traccia lo stato di uno skip temporale in corso.

    Durante lo skip il tempo narrativo avanza in accelerato.
    La sessione può essere interrotta da eventi rilevanti per il player
    (stessa location, relazione forte, faction del player).

    Args:
        target_world_day: Giorno narrativo assoluto target dello skip.
        started_at_world_day: Giorno narrativo assoluto di inizio skip.
        events_accumulated: event_id[] accaduti durante lo skip — per il riassunto finale.
        interrupted_at: WorldTime in cui è stato interrotto (se interrotto).
        interruption_event_id: ID dell'evento che ha causato l'interruzione.
    """

    target_world_day: int
    started_at_world_day: int
    events_accumulated: list[str] = Field(default_factory=list)
    interrupted_at: Optional[WorldTime] = None
    interruption_event_id: Optional[str] = None

    def is_interrupted(self) -> bool:
        """Ritorna True se lo skip è stato interrotto."""
        return self.interrupted_at is not None

    def days_skipped(self, current_world_day: int) -> int:
        """Giorni narrativi saltati fino al giorno corrente.

        Args:
            current_world_day: Giorno narrativo assoluto corrente.

        Returns:
            Numero di giorni narrativi saltati dall'inizio dello skip.
        """
        return current_world_day - self.started_at_world_day
