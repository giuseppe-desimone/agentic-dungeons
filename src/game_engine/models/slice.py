"""Context Slice System — modelli per i context slice degli agenti AI.

Principio di separazione:
    NarrativeSlice → SOLO da PlayerKnowledgeBase (mai world state globale)
    QuestSlice     → dal world state globale filtrato per area
    CultureSlice, NpcSpawnSlice → dal world state globale filtrato per area

L'Agente Narrativo riceve SEMPRE e SOLO NarrativeSlice.
Gli altri agenti ricevono slice dal world state globale.
Questa separazione è non negoziabile.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import DayMoment, WorldTime


class SliceRequest(BaseModel):
    """Richiesta di un context slice da parte di un agente.

    Args:
        agent: Tipo di agente destinatario ("narrative"|"culture"|"quest"|"npc_spawn").
        focus_location_id: Location principale di interesse.
        focus_entity_id: Entità specifica di interesse (opzionale).
        radius: Raggio geografico ("local"|"regional"|"global").
        task: Descrizione del task che l'agente deve eseguire.
        from_world_day: Giorno narrativo di inizio del range eventi.
        to_world_day: Giorno narrativo di fine del range eventi.
        token_budget: Budget massimo di token per il contesto (default 4000).
    """

    agent: str
    focus_location_id: str
    focus_entity_id: Optional[str] = None
    radius: str = "local"
    task: str
    from_world_day: int
    to_world_day: int
    token_budget: int = 4000


# ── Narrative Slice (da PlayerKnowledgeBase) ──────────────────────────────────


class KnownEventSlice(BaseModel):
    """Versione ridotta di un evento noto al player.

    Contiene solo i dati necessari all'Agente Narrativo.
    La certezza riflette quanto il player è sicuro che l'evento sia reale.

    Args:
        id: ID evento originale (GameEvent.id).
        verb: Verb dell'evento.
        emitter_name: Nome dell'entità emittente.
        target_name: Nome dell'entità target (se presente).
        world_time: Tempo narrativo dell'evento.
        how_learned: Come il player ha appreso l'evento.
        certainty: Certezza del player (0.0-1.0).
        payload: Payload originale dell'evento (dati contestuali).
    """

    id: str
    verb: str
    emitter_name: str
    target_name: Optional[str] = None
    world_time: WorldTime
    how_learned: str
    certainty: float
    payload: dict[str, Any] = Field(default_factory=dict)


class NPCSlice(BaseModel):
    """Dati di un NPC visibili al player.

    Contiene solo ciò che il player può conoscere:
    nessun segreto, nessun goal privato, nessuna relazione nascosta.

    Args:
        id: ID entità NPC.
        name: Nome del NPC.
        role: Ruolo narrativo (es. "mercante", "guardia").
        personality_traits: Tratti di personalità noti al player.
        dialogue_style: Stile di dialogo del NPC.
        current_goal: Goal corrente, se noto al player.
        last_known_location: Ultima location nota al player.
        available_at_moment: Momenti della giornata in cui è raggiungibile.
        relations_known_to_player: Relazioni note al player.
    """

    id: str
    name: str
    role: str = ""
    personality_traits: list[str] = Field(default_factory=list)
    dialogue_style: str = ""
    current_goal: Optional[dict[str, Any]] = None
    last_known_location: Optional[str] = None
    available_at_moment: list[str] = Field(default_factory=list)
    relations_known_to_player: list[dict[str, Any]] = Field(default_factory=list)


class NarrativeSlice(BaseModel):
    """Slice per l'Agente Narrativo.

    TUTTI i dati provengono dalla PlayerKnowledgeBase.
    Non contiene MAI informazioni che il player non può conoscere.

    Struttura della priorità di troncamento (SLICE_TRUNCATION_PRIORITY):
    - never_truncate: focus_location, known_events_recent[:5], player_context,
                      day_moment, active_interaction
    - truncate_payload_keep_structure: npcs_in_focus[:5]
    - summarize_to_text: relations_known_to_player
    - omit_if_needed: active_rumors, non_critical_secrets

    Args:
        world_time: Tempo narrativo corrente.
        day_moment: Momento della giornata — MAI troncato.
        focus_location: Dati della location {id, name, biome, atmosphere, mood}.
                        mood calcolato dagli eventi NOTI AL PLAYER.
        known_events_recent: Ultimi N eventi noti, ordinati per learned_at.
        active_rumors: Rumor con certainty < 0.7.
        npcs_in_focus: NPC noti al player o fisicamente presenti nella location.
        player_context: Contesto del player {narrative_traits, choices_log_summary, relations_known}.
        active_interaction: Contesto interazione in corso (se presente).
    """

    world_time: WorldTime
    day_moment: DayMoment
    focus_location: dict[str, Any] = Field(default_factory=dict)
    known_events_recent: list[KnownEventSlice] = Field(default_factory=list)
    active_rumors: list[KnownEventSlice] = Field(default_factory=list)
    npcs_in_focus: list[NPCSlice] = Field(default_factory=list)
    player_context: dict[str, Any] = Field(default_factory=dict)
    active_interaction: Optional[dict[str, Any]] = None


# ── Quest Slice (dal world state globale) ─────────────────────────────────────


class TensionPoint(BaseModel):
    """Un punto di tensione nel mondo rilevato dal TensionPointDetector.

    Rappresenta una situazione che potrebbe generare una quest interessante.
    Basato sul world state globale, non sulla PlayerKnowledgeBase.

    Args:
        description: Descrizione narrativa della tensione.
        entities_involved: entity_id delle entità coinvolte.
        urgency: Livello di urgenza ("critical"|"high"|"medium"|"low").
        suggested_verb: EventVerb suggerito per la risoluzione.
        world_days_active: Da quanti giorni narrativi persiste la tensione.
    """

    description: str
    entities_involved: list[str] = Field(default_factory=list)
    urgency: str = "medium"
    suggested_verb: str = ""
    world_days_active: int = 0


class QuestSlice(BaseModel):
    """Slice per l'Agente Quest.

    Riceve world state globale filtrato per area geografica.
    L'Agente Quest può sapere cose che il player non sa ancora,
    perché genera quest basate sulla realtà del mondo,
    non sulla percezione del player.

    Args:
        world_time: Tempo narrativo corrente.
        day_moment: Momento della giornata.
        focus_location: Dati della location {id, name, biome, atmosphere}.
        recent_events: Eventi recenti dal world state globale (non filtrati per player).
        factions_present: Fazioni presenti nell'area.
        tension_points: Punti di tensione rilevati dal TensionPointDetector.
        available_npcs: NPC disponibili nell'area (dati completi).
        available_locations: Location disponibili nel raggio.
        player_level: Livello del player (per bilanciare la difficoltà).
        player_active_quests: Quest attive del player (per evitare conflitti).
        reward_budget: Budget reward per la quest generata.
    """

    world_time: WorldTime
    day_moment: DayMoment
    focus_location: dict[str, Any] = Field(default_factory=dict)
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    factions_present: list[dict[str, Any]] = Field(default_factory=list)
    tension_points: list[TensionPoint] = Field(default_factory=list)
    available_npcs: list[dict[str, Any]] = Field(default_factory=list)
    available_locations: list[dict[str, Any]] = Field(default_factory=list)
    player_level: int = 0
    player_active_quests: list[str] = Field(default_factory=list)
    reward_budget: dict[str, Any] = Field(default_factory=dict)


# ── Culture / NPC Spawn Slice (dal world state globale) ───────────────────────


class CultureSlice(BaseModel):
    """Slice per l'Agente Cultura.

    Riceve dati del world state globale per area.
    Non ha accesso alla PlayerKnowledgeBase.

    Args:
        world_time: Tempo narrativo corrente.
        day_moment: Momento della giornata.
        focus_location: Dati della location focus.
        dominant_factions: Fazioni dominanti nell'area.
        recent_events: Eventi recenti rilevanti per la cultura.
        existing_cultures: Culture già presenti nell'area.
        population_data: Dati demografici e sociali dell'area.
    """

    world_time: WorldTime
    day_moment: DayMoment
    focus_location: dict[str, Any] = Field(default_factory=dict)
    dominant_factions: list[dict[str, Any]] = Field(default_factory=list)
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    existing_cultures: list[dict[str, Any]] = Field(default_factory=list)
    population_data: dict[str, Any] = Field(default_factory=dict)


class NpcSpawnSlice(BaseModel):
    """Slice per l'Agente NPC Spawn.

    Riceve dati del world state globale per area.
    Non ha accesso alla PlayerKnowledgeBase.

    Args:
        world_time: Tempo narrativo corrente.
        day_moment: Momento della giornata.
        focus_location: Dati della location dove spawnare.
        existing_npcs: NPC già presenti nella location.
        faction_context: Contesto fazioni per il NPC da spawnare.
        spawn_reason: Motivo dello spawn (es. "replacement", "new_faction", "event_trigger").
        trigger_event: Evento che ha triggerato lo spawn (opzionale).
    """

    world_time: WorldTime
    day_moment: DayMoment
    focus_location: dict[str, Any] = Field(default_factory=dict)
    existing_npcs: list[dict[str, Any]] = Field(default_factory=list)
    faction_context: dict[str, Any] = Field(default_factory=dict)
    spawn_reason: str = "new_faction"
    trigger_event: Optional[dict[str, Any]] = None
