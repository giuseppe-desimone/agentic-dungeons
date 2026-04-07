"""Modelli Pydantic per le entità del world state.

Gerarchia:
    BaseEntity          — comune a tutte le entità
    ├── NPCEntity       — personaggi non-player
    └── PlayerEntity    — il giocatore

Le entità faction, religion, guild, location sono stub — saranno espanse in Fase 3.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import EntityKind, EntityStatus, RelationType, WorldTime


class Secret(BaseModel):
    """Un segreto legato a un'entità, noto solo ad alcuni.

    Args:
        content: Testo del segreto.
        known_to: Lista di entity_id che conoscono questo segreto.
    """

    content: str
    known_to: list[str] = Field(default_factory=list)


class EntityNarrative(BaseModel):
    """Contesto narrativo di un'entità: storia, segreti, note per gli agenti.

    Args:
        description: Descrizione narrativa dell'entità.
        secrets: Lista di segreti dell'entità.
        agent_notes: Note riservate agli agenti AI (non mostrate al player).
    """

    description: str = ""
    secrets: list[Secret] = Field(default_factory=list)
    agent_notes: str = ""


class EntityMeta(BaseModel):
    """Metadati di lifecycle di un'entità.

    Args:
        created_at: WorldTime in cui l'entità è stata creata.
        created_by: entity_id o sistema che ha creato questa entità.
        status: Stato corrente dell'entità.
    """

    created_at: WorldTime
    created_by: str
    status: EntityStatus = EntityStatus.ACTIVE


class EntityIdentity(BaseModel):
    """Identità pubblica di un'entità: nome, alias, cultura, tag.

    Args:
        name: Nome primario dell'entità.
        aliases: Nomi alternativi o titoli.
        culture_id: ID della cultura di appartenenza (opzionale).
        tags: Tag liberi per filtraggio e query (es. ["merchant", "hostile"]).
    """

    name: str
    aliases: list[str] = Field(default_factory=list)
    culture_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class Relation(BaseModel):
    """Relazione tra due entità nel world state.

    Args:
        target_id: entity_id dell'entità target.
        type: Tipo di relazione.
        strength: Intensità della relazione (0.0 = neutra, 1.0 = massima).
        known_to: entity_id che conoscono questa relazione.
        since: WorldTime in cui è iniziata la relazione.
    """

    target_id: str
    type: RelationType
    strength: float = 0.0
    known_to: list[str] = Field(default_factory=list)
    since: WorldTime


class BaseEntity(BaseModel):
    """Classe base per tutte le entità del world state.

    Args:
        id: UUID univoco dell'entità.
        kind: Tipo di entità (NPC, PLAYER, FACTION, ...).
        meta: Metadati di lifecycle.
        identity: Identità pubblica.
        relations: Relazioni con altre entità.
        event_log: Lista di event_id in cui questa entità è coinvolta.
        known_events: event_id noti all'entità (usato per NPC con memoria).
        narrative: Contesto narrativo.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: EntityKind
    meta: EntityMeta
    identity: EntityIdentity
    relations: list[Relation] = Field(default_factory=list)
    event_log: list[str] = Field(default_factory=list)
    known_events: list[str] = Field(default_factory=list)
    narrative: EntityNarrative = Field(default_factory=EntityNarrative)

    model_config = {"use_enum_values": True}


class NPCBehaviour(BaseModel):
    """Comportamento e psicologia di un NPC.

    Args:
        personality_traits: Tratti caratteriali (es. ["coraggioso", "impulsivo"]).
        motivations: Obiettivi e desideri profondi.
        fears: Paure che influenzano le decisioni.
        current_goal: Obiettivo corrente { verb, target_id, priority, started_at_world_day }.
        dialogue_style: Stile di dialogo per l'Agente Narrativo.
        moral_alignment: Allineamento morale (-1.0 malvagio ↔ 1.0 buono).
        available_at_moments: DayMoment[] in cui è fisicamente raggiungibile.
    """

    personality_traits: list[str] = Field(default_factory=list)
    motivations: list[str] = Field(default_factory=list)
    fears: list[str] = Field(default_factory=list)
    current_goal: Optional[dict[str, Any]] = None
    dialogue_style: str = ""
    moral_alignment: float = 0.0
    available_at_moments: list[str] = Field(default_factory=list)


class NPCEntity(BaseEntity):
    """Entità NPC — personaggio non-player.

    Args:
        physical: Attributi fisici (dict libero, es. {"hp": 20, "str": 14}).
        mechanical: Attributi meccanici di gioco (armi, equipaggiamento, ecc.).
        behaviour: Comportamento e psicologia.
        spawn: Parametri di spawn usati dall'Agente NPC Spawn.
    """

    kind: EntityKind = EntityKind.NPC
    physical: dict[str, Any] = Field(default_factory=dict)
    mechanical: dict[str, Any] = Field(default_factory=dict)
    behaviour: NPCBehaviour = Field(default_factory=NPCBehaviour)
    spawn: Optional[dict[str, Any]] = None


class ChoiceLogEntry(BaseModel):
    """Una scelta del player e la sua conseguenza, per la memoria narrativa.

    Args:
        event_id: L'evento a cui il player ha risposto.
        choice: Descrizione testuale della scelta fatta.
        consequence_event_id: L'evento conseguenza generato.
        world_time: Quando è avvenuta la scelta.
    """

    event_id: str
    choice: str
    consequence_event_id: str
    world_time: WorldTime


class PlayerNarrative(EntityNarrative):
    """Estensione narrativa per il player: include il log delle scelte.

    Args:
        choices_log: Storico delle scelte rilevanti del player.
    """

    choices_log: list[ChoiceLogEntry] = Field(default_factory=list)


class PlayerEntity(BaseEntity):
    """Entità Player — il personaggio controllato dal giocatore.

    Args:
        mechanical: Attributi meccanici (stats, HP, inventario, ecc.).
        narrative: Contesto narrativo con log delle scelte.
    """

    kind: EntityKind = EntityKind.PLAYER
    mechanical: dict[str, Any] = Field(default_factory=dict)
    narrative: PlayerNarrative = Field(default_factory=PlayerNarrative)
