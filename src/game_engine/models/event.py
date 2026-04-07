"""Modelli per il sistema eventi del game engine.

Ogni cambiamento di stato nel mondo avviene tramite un GameEvent.
Il log è append-only — gli eventi non vengono mai modificati.

Doppio timestamp:
    tick:       GameTick — ordinamento atomico nel log.
    world_time: WorldTime — tempo narrativo, usato da agenti e decay.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import EntityKind, GameTick, WorldTime


class EventVerb(StrEnum):
    """Verbi canonici per gli eventi del world state.

    Coprono esistenza, relazioni, conflitti, conoscenza, economia,
    religione, stato personale e world events.
    Verb custom del Game Engine: stringa libera "namespace:verb" (non in enum).
    """

    # ── Esistenza ────────────────────────────────────────────────────────────
    SPAWNED = "spawned"
    DIED = "died"
    RESURRECTED = "resurrected"
    FOUNDED = "founded"
    DISSOLVED = "dissolved"
    EXILED = "exiled"
    EMERGED = "emerged"

    # ── Relazione ────────────────────────────────────────────────────────────
    JOINED = "joined"
    LEFT = "left"
    BETRAYED = "betrayed"
    ALLIED = "allied"
    RIVALED = "rivaled"
    MERGED = "merged"
    SUBJUGATED = "subjugated"
    LIBERATED = "liberated"
    PLEDGED = "pledged"
    ABANDONED = "abandoned"

    # ── Conflitto ────────────────────────────────────────────────────────────
    ATTACKED = "attacked"
    DECLARED_WAR = "declared_war"
    NEGOTIATED = "negotiated"
    SURRENDERED = "surrendered"
    ASSASSINATED = "assassinated"
    RAIDED = "raided"
    SIEGED = "sieged"
    MASSACRED = "massacred"
    RETALIATED = "retaliated"

    # ── Conoscenza ───────────────────────────────────────────────────────────
    DISCOVERED = "discovered"
    REVEALED = "revealed"
    CONCEALED = "concealed"
    DECEIVED = "deceived"
    RUMORED = "rumored"
    FORGOTTEN = "forgotten"
    INVESTIGATED = "investigated"

    # ── Economia ─────────────────────────────────────────────────────────────
    TRADED = "traded"
    STOLEN = "stolen"
    TAXED = "taxed"
    DONATED = "donated"
    MONOPOLIZED = "monopolized"
    DEPLETED = "depleted"
    DISCOVERED_RESOURCE = "discovered_resource"

    # ── Religione & Cultura ──────────────────────────────────────────────────
    CONVERTED = "converted"
    PROSELYTIZED = "proselytized"
    DECLARED_HERESY = "declared_heresy"
    PERFORMED_RITUAL = "performed_ritual"
    CANONIZED = "canonized"
    DESECRATED = "desecrated"
    SCHISMED = "schismed"
    SYNCRETIZED = "syncretized"

    # ── Stato Personale ──────────────────────────────────────────────────────
    LEVELED = "leveled"
    TRAUMATIZED = "traumatized"
    RECOVERED = "recovered"
    MOTIVATED = "motivated"
    DEMORALIZED = "demoralized"
    CORRUPTED = "corrupted"
    REDEEMED = "redeemed"
    BONDED = "bonded"
    ESTRANGED = "estranged"

    # ── World ─────────────────────────────────────────────────────────────────
    MIGRATED = "migrated"
    SETTLED = "settled"
    ABANDONED_LOCATION = "abandoned_location"
    NATURAL_DISASTER = "natural_disaster"
    PLAGUE_STARTED = "plague_started"
    PLAGUE_ENDED = "plague_ended"
    SEASON_CHANGED = "season_changed"
    TIME_PASSED = "time_passed"


class EventActor(BaseModel):
    """Riferimento compatto a un'entità coinvolta in un evento.

    Args:
        id: UUID dell'entità.
        kind: Tipo di entità.
        name: Nome corrente dell'entità (denormalizzato per query sul log).
    """

    id: str
    kind: EntityKind
    name: str

    model_config = {"use_enum_values": True}


class EventVisibility(BaseModel):
    """Controllo di chi sa che questo evento è accaduto.

    La separazione world state / player knowledge passa tutta da qui:
    il player è in known_to SOLO se era presente o informato esplicitamente.

    Args:
        scope: Raggio di diffusione ("private" | "local" | "regional" | "global").
        known_to: entity_id[] che sanno dell'evento. Fonte di verità per PlayerKnowledgeBase.
    """

    scope: str = "local"
    known_to: list[str] = Field(default_factory=list)


class GameEvent(BaseModel):
    """Un evento nel world state — l'unità atomica di cambiamento.

    Append-only: una volta creato non viene mai modificato.
    Ha doppio timestamp per supportare sia la simulazione (tick)
    che la narrativa e il decay (world_time).

    Args:
        id: UUID univoco dell'evento.
        tick: GameTick al momento della creazione (ordinamento atomico).
        world_time: WorldTime narrativo (usato da agenti, decay, query narrative).
        cascade_depth: Profondità di cascata (max 5 per evitare loop).
        parent_event_id: evento che ha generato questo (per tracciare cascate).
        type: Categoria semantica dell'evento (es. "conflict", "social", "world").
        verb: Verbo dell'evento — EventVerb o stringa custom "namespace:verb".
        emitter: Entità che ha causato l'evento.
        target: Entità destinataria (opzionale).
        payload: Dati aggiuntivi specifici per tipo di evento.
        visibility: Chi sa che questo evento è accaduto.
        status: "active" | "resolved" | "cancelled".
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tick: GameTick
    world_time: WorldTime
    cascade_depth: int = 0
    parent_event_id: Optional[str] = None
    type: str
    verb: str
    emitter: EventActor
    target: Optional[EventActor] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    visibility: EventVisibility = Field(default_factory=EventVisibility)
    status: str = "active"
