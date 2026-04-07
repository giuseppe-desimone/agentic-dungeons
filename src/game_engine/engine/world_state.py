"""WorldState: il world state globale, omnisciente, append-only.

Principio fondamentale: il world state è la fonte di verità del mondo.
La PlayerKnowledgeBase è una vista soggettiva derivata da esso —
i due flussi non si mescolano mai.

WorldState contiene:
    entity_store     — tutte le entità vive e legendarie
    event_log        — tutti gli eventi (append-only)
    consequence_queue — eventi in attesa di elaborazione dal ConsequenceEngine
    scheduled_events — eventi programmati per giorno narrativo futuro
    player_knowledge — PlayerKnowledgeBase del player corrente
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from ..models.base import WorldTime
from ..models.entity import BaseEntity
from ..models.event import GameEvent

if TYPE_CHECKING:
    from .knowledge import PlayerKnowledgeBase


class ScheduledEvent(BaseModel):
    """Un evento programmato per essere generato in un giorno narrativo futuro.

    Usato dal ConsequenceEngine per pianificare conseguenze ritardate
    (es. un assedio che inizia tra 10 giorni narrativi).

    Args:
        id: UUID univoco dell'evento schedulato.
        trigger_world_day: Giorno assoluto narrativo in cui deve scattare.
        event_template: Template dell'evento da generare (dict libero).
        created_at: WorldTime in cui è stato schedulato.
        created_by_event_id: Evento che ha generato questo schedule (opzionale).
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger_world_day: int
    event_template: dict = Field(default_factory=dict)
    created_at: WorldTime
    created_by_event_id: Optional[str] = None


class WorldState:
    """World state globale: entità, eventi, code e schedule.

    Omnisciente — conosce tutto ciò che accade nel mondo.
    La separazione dalla PlayerKnowledgeBase è gestita dal VisibilityEngine (Fase 2).

    Il log eventi è append-only: append_event() non modifica mai eventi esistenti.
    """

    def __init__(self) -> None:
        self.entity_store: dict[str, BaseEntity] = {}
        self.event_log: list[GameEvent] = []
        self.consequence_queue: list[GameEvent] = []
        self.scheduled_events: list[ScheduledEvent] = []
        self.player_knowledge: Optional["PlayerKnowledgeBase"] = None

    # ── Entity Store ────────────────────────────────────────────────────────

    def add_entity(self, entity: BaseEntity) -> None:
        """Aggiunge una nuova entità al world state.

        Args:
            entity: L'entità da aggiungere.

        Raises:
            ValueError: Se un'entità con lo stesso id esiste già.
        """
        if entity.id in self.entity_store:
            raise ValueError(f"Entity {entity.id!r} già presente nel world state.")
        self.entity_store[entity.id] = entity

    def get_entity(self, entity_id: str) -> Optional[BaseEntity]:
        """Recupera un'entità per id.

        Args:
            entity_id: UUID dell'entità.

        Returns:
            L'entità se presente, None altrimenti.
        """
        return self.entity_store.get(entity_id)

    def update_entity(self, entity: BaseEntity) -> None:
        """Aggiorna un'entità esistente nel world state.

        Args:
            entity: L'entità aggiornata (deve avere id già presente).

        Raises:
            KeyError: Se l'entità non esiste nel world state.
        """
        if entity.id not in self.entity_store:
            raise KeyError(f"Entity {entity.id!r} non trovata nel world state.")
        self.entity_store[entity.id] = entity

    # ── Event Log (append-only) ──────────────────────────────────────────────

    def append_event(self, event: GameEvent) -> None:
        """Aggiunge un evento al log. Il log è append-only: non modifica mai.

        Args:
            event: L'evento da appendere.

        Raises:
            ValueError: Se un evento con lo stesso id esiste già nel log.
        """
        if any(e.id == event.id for e in self.event_log):
            raise ValueError(f"Evento {event.id!r} già presente nel log.")
        self.event_log.append(event)

    def get_events_since(self, world_day: int) -> list[GameEvent]:
        """Restituisce tutti gli eventi dal giorno narrativo indicato in poi.

        Args:
            world_day: Giorno narrativo assoluto di inizio (incluso).

        Returns:
            Lista di eventi ordinata per tick.
        """
        return [
            e for e in self.event_log
            if e.world_time.to_absolute_days() >= world_day
        ]

    # ── Consequence Queue ────────────────────────────────────────────────────

    def enqueue_consequence(self, event: GameEvent) -> None:
        """Mette un evento nella coda del ConsequenceEngine.

        Args:
            event: L'evento conseguenza da elaborare.
        """
        self.consequence_queue.append(event)

    def drain_consequence_queue(self) -> list[GameEvent]:
        """Svuota e restituisce la coda delle conseguenze.

        Returns:
            Lista degli eventi in attesa di elaborazione.
        """
        events = list(self.consequence_queue)
        self.consequence_queue.clear()
        return events

    # ── Scheduled Events ────────────────────────────────────────────────────

    def schedule_event(self, scheduled: ScheduledEvent) -> None:
        """Aggiunge un evento schedulato per un giorno futuro.

        Args:
            scheduled: L'evento schedulato.
        """
        self.scheduled_events.append(scheduled)

    def pop_due_events(self, current_world_day: int) -> list[ScheduledEvent]:
        """Estrae e rimuove gli eventi schedulati con trigger_world_day <= giorno corrente.

        Args:
            current_world_day: Giorno narrativo assoluto corrente.

        Returns:
            Lista degli eventi schedulati pronti a essere generati.
        """
        due = [s for s in self.scheduled_events if s.trigger_world_day <= current_world_day]
        self.scheduled_events = [s for s in self.scheduled_events if s.trigger_world_day > current_world_day]
        return due
