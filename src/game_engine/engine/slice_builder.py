"""Slice Builder — costruisce i context slice per ogni agente AI.

Principio fondamentale:
    NarrativeSliceBuilder legge SOLO da PlayerKnowledgeBase.
    QuestSliceBuilder legge dal world state globale.
    Questa separazione è non negoziabile.

Componenti:
    MoodCalculator       — calcola il mood di una location dagli eventi noti al player
    TensionPointDetector — rileva tensioni nel world state globale per l'agente Quest
    TruncationEngine     — tronca il slice rispettando la priorità di troncamento
    NarrativeSliceBuilder — costruisce NarrativeSlice dalla PlayerKnowledgeBase
    QuestSliceBuilder     — costruisce QuestSlice dal world state globale
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from ..models.base import DayMoment
from ..models.entity import NPCEntity, PlayerEntity
from ..models.slice import (
    KnownEventSlice,
    NPCSlice,
    NarrativeSlice,
    QuestSlice,
    SliceRequest,
    TensionPoint,
)

if TYPE_CHECKING:
    from .knowledge import PlayerKnowledgeBase
    from .world_state import WorldState

logger = logging.getLogger(__name__)

# ── Priorità di troncamento ───────────────────────────────────────────────────

SLICE_TRUNCATION_PRIORITY: dict[str, list[str]] = {
    "never_truncate": [
        "focus_location",
        "known_events_recent[:5]",
        "player_context",
        "day_moment",
        "active_interaction",
    ],
    "truncate_payload_keep_structure": ["npcs_in_focus[:5]"],
    "summarize_to_text": ["relations_known_to_player"],
    "omit_if_needed": ["active_rumors", "non_critical_secrets"],
}

# Stima approssimativa: 1 token ≈ 4 caratteri
_CHARS_PER_TOKEN = 4

# ── Mood Calculator ───────────────────────────────────────────────────────────

# Mappa verb → mood (ordine di priorità: il mood più grave vince)
_VERB_MOOD_MAP: dict[str, str] = {
    # War-torn
    "declared_war": "war-torn",
    "massacred": "war-torn",
    "sieged": "war-torn",
    # Fearful
    "plague_started": "fearful",
    "natural_disaster": "fearful",
    "assassinated": "fearful",
    # Tense
    "attacked": "tense",
    "retaliated": "tense",
    "raided": "tense",
    "rivaled": "tense",
    "betrayed": "tense",
    "surrendered": "tense",
    # Grieving
    "died": "grieving",
    "dissolved": "grieving",
    # Suspicious
    "deceived": "suspicious",
    "concealed": "suspicious",
    "rumored": "suspicious",
    "investigated": "suspicious",
    # Hopeful
    "allied": "hopeful",
    "bonded": "hopeful",
    "liberated": "hopeful",
    "recovered": "hopeful",
    "redeemed": "hopeful",
    # Bustling
    "traded": "bustling",
    "founded": "bustling",
    "settled": "bustling",
    # Chaotic
    "schismed": "chaotic",
    "desecrated": "chaotic",
}

_MOOD_PRIORITY: dict[str, int] = {
    "war-torn": 9,
    "fearful": 8,
    "tense": 7,
    "grieving": 6,
    "chaotic": 5,
    "suspicious": 4,
    "haunted": 3,
    "hopeful": 2,
    "bustling": 1,
    "curious": 0,
    "stagnant": 0,
    "peaceful": 0,
}


class MoodCalculator:
    """Calcola il mood di una location dagli eventi noti al player.

    Opera SOLO su KnownEventSlice — non su GameEvent raw.
    Il mood riflette la percezione soggettiva del player, non la realtà.
    """

    @staticmethod
    def calculate(known_events: list[KnownEventSlice]) -> str:
        """Calcola il mood dominante dagli eventi noti al player.

        Args:
            known_events: Lista di eventi noti al player.

        Returns:
            Stringa del mood dominante (conforme a LocationMood).
        """
        if not known_events:
            return "peaceful"

        best_mood = "peaceful"
        best_priority = -1

        for event in known_events:
            mood = _VERB_MOOD_MAP.get(event.verb)
            if mood is None:
                continue
            priority = _MOOD_PRIORITY.get(mood, 0)
            if priority > best_priority:
                best_priority = priority
                best_mood = mood

        return best_mood


# ── Tension Point Detector ────────────────────────────────────────────────────


class TensionPointDetector:
    """Rileva punti di tensione nel world state globale per l'agente Quest.

    Opera su world_state.event_log direttamente (non sulla KB del player).
    L'agente Quest vede la realtà del mondo, non la percezione del player.
    """

    def detect(
        self,
        world_state: "WorldState",
        focus_location_id: str,
        from_world_day: int,
        to_world_day: int,
    ) -> list[TensionPoint]:
        """Rileva tensioni nell'area di interesse.

        Args:
            world_state: World state globale.
            focus_location_id: Location di focus per il filtro geografico.
            from_world_day: Giorno narrativo di inizio del range.
            to_world_day: Giorno narrativo di fine del range.

        Returns:
            Lista di TensionPoint rilevati nell'area.
        """
        events_in_range = [
            e
            for e in world_state.event_log
            if from_world_day <= e.world_time.to_absolute_days() <= to_world_day
        ]

        tension_points: list[TensionPoint] = []

        # Rileva: DECLARED_WAR senza SURRENDERED/NEGOTIATED successivo
        war_events = [e for e in events_in_range if e.verb == "declared_war"]
        resolved_verbs = {"surrendered", "negotiated", "allied"}
        for war in war_events:
            resolved = any(
                e.verb in resolved_verbs
                and e.emitter.id in (war.emitter.id, getattr(war.target, "id", None))
                and e.world_time.to_absolute_days() > war.world_time.to_absolute_days()
                for e in events_in_range
            )
            if not resolved:
                involved = [war.emitter.id]
                if war.target:
                    involved.append(war.target.id)
                tp = TensionPoint(
                    description=(
                        f"{war.emitter.name} ha dichiarato guerra e il conflitto è ancora aperto."
                    ),
                    entities_involved=involved,
                    urgency="critical",
                    suggested_verb="sieged",
                    world_days_active=to_world_day - war.world_time.to_absolute_days(),
                )
                tension_points.append(tp)

        # Rileva: 3+ ATTACKED nello stesso giorno narrativo
        attack_by_day: dict[int, list[Any]] = {}
        for e in events_in_range:
            if e.verb == "attacked":
                day = e.world_time.to_absolute_days()
                attack_by_day.setdefault(day, []).append(e)

        for day, attacks in attack_by_day.items():
            if len(attacks) >= 3:
                involved_ids = list({a.emitter.id for a in attacks})
                tp = TensionPoint(
                    description=(
                        f"{len(attacks)} attacchi nel giorno {day} — conflitto in escalation."
                    ),
                    entities_involved=involved_ids,
                    urgency="high",
                    suggested_verb="retaliated",
                    world_days_active=to_world_day - day,
                )
                tension_points.append(tp)

        # Rileva: ASSASSINATED senza conseguenza di RIVALED o DECLARED_WAR
        assassination_events = [e for e in events_in_range if e.verb == "assassinated"]
        consequence_verbs = {"rivaled", "declared_war", "retaliated"}
        for assass in assassination_events:
            has_consequence = any(
                e.verb in consequence_verbs
                and e.world_time.to_absolute_days() > assass.world_time.to_absolute_days()
                for e in events_in_range
            )
            if not has_consequence:
                involved = [assass.emitter.id]
                if assass.target:
                    involved.append(assass.target.id)
                tp = TensionPoint(
                    description=(
                        f"Assassinio senza ritorsione — potenziale punto di esplosione."
                    ),
                    entities_involved=involved,
                    urgency="high",
                    suggested_verb="rivaled",
                    world_days_active=to_world_day - assass.world_time.to_absolute_days(),
                )
                tension_points.append(tp)

        return tension_points


# ── Truncation Engine ─────────────────────────────────────────────────────────


class TruncationEngine:
    """Tronca un NarrativeSlice rispettando la priorità di troncamento.

    Priorità (dalla spec):
    - MAI troncati: focus_location, known_events_recent[:5], player_context,
                    day_moment, active_interaction
    - Mantieni struttura, tronca payload: npcs_in_focus[:5]
    - Ometti se necessario: active_rumors, non_critical_secrets
    """

    MAX_RECENT_EVENTS = 20
    MAX_RECENT_EVENTS_TRUNCATED = 5
    MAX_NPCS = 5

    def truncate(self, narrative_slice: NarrativeSlice, token_budget: int) -> NarrativeSlice:
        """Tronca il slice per rispettare il budget di token.

        Args:
            narrative_slice: Slice originale da troncare.
            token_budget: Budget massimo in token.

        Returns:
            Slice troncato (copia immutabile via model_copy).
        """
        # Stima token attuali
        current_tokens = self._estimate_tokens(narrative_slice)

        if current_tokens <= token_budget:
            return narrative_slice

        # Passo 1: Tronca npcs_in_focus a max 5
        npcs = narrative_slice.npcs_in_focus[: self.MAX_NPCS]

        # Passo 2: Se ancora troppo, ometti active_rumors
        rumors: list[KnownEventSlice] = narrative_slice.active_rumors
        current_tokens = self._estimate_tokens(
            narrative_slice.model_copy(update={"npcs_in_focus": npcs})
        )
        if current_tokens > token_budget:
            rumors = []

        # Passo 3: Tronca known_events_recent a min 5 (mai sotto)
        events = narrative_slice.known_events_recent
        current_tokens = self._estimate_tokens(
            narrative_slice.model_copy(
                update={"npcs_in_focus": npcs, "active_rumors": rumors}
            )
        )
        if current_tokens > token_budget:
            events = events[: self.MAX_RECENT_EVENTS_TRUNCATED]

        return narrative_slice.model_copy(
            update={
                "known_events_recent": events,
                "active_rumors": rumors,
                "npcs_in_focus": npcs,
            }
        )

    @staticmethod
    def _estimate_tokens(narrative_slice: NarrativeSlice) -> int:
        """Stima grossolana del numero di token nel slice.

        Args:
            narrative_slice: Slice da stimare.

        Returns:
            Stima del numero di token.
        """
        return len(narrative_slice.model_dump_json()) // _CHARS_PER_TOKEN


# ── Narrative Slice Builder ───────────────────────────────────────────────────


class NarrativeSliceBuilder:
    """Costruisce NarrativeSlice SOLO dalla PlayerKnowledgeBase.

    Regola fondamentale: nessun dato viene letto da world_state.event_log.
    La location e gli NPC fisicamente presenti sono letti dal world_state
    (entità pubbliche), ma gli eventi e la storia sono SOLO dalla KB del player.
    """

    def __init__(
        self,
        truncation_engine: Optional[TruncationEngine] = None,
    ) -> None:
        """Inizializza il builder.

        Args:
            truncation_engine: Motore di troncamento (crea uno di default se None).
        """
        self._truncation = truncation_engine or TruncationEngine()
        self._mood_calculator = MoodCalculator()

    def build(
        self,
        player_kb: "PlayerKnowledgeBase",
        world_state: "WorldState",
        request: SliceRequest,
        player: PlayerEntity,
    ) -> NarrativeSlice:
        """Costruisce il NarrativeSlice per l'Agente Narrativo.

        Args:
            player_kb: Knowledge base del player — fonte primaria di dati.
            world_state: World state globale — usato SOLO per entità pubbliche.
            request: Richiesta del slice con parametri di filtro.
            player: Entità player.

        Returns:
            NarrativeSlice con SOLO dati noti al player.
        """
        # ── Recupera eventi noti al player nel range richiesto ────────────────
        known_entries = player_kb.get_events_since(request.from_world_day)
        event_map = {e.id: e for e in world_state.event_log}

        known_event_slices: list[KnownEventSlice] = []
        rumor_slices: list[KnownEventSlice] = []

        for entry in known_entries:
            raw = event_map.get(entry.event_id)
            if raw is None:
                continue
            kes = KnownEventSlice(
                id=entry.event_id,
                verb=raw.verb,
                emitter_name=raw.emitter.name,
                target_name=raw.target.name if raw.target else None,
                world_time=raw.world_time,
                how_learned=entry.how_learned,
                certainty=entry.certainty,
                payload=raw.payload,
            )

            if entry.event_id in player_kb.active_rumors:
                rumor_slices.append(kes)
            else:
                known_event_slices.append(kes)

        # Ordina per learned_at (più recente per ultimi)
        known_event_slices.sort(key=lambda e: e.world_time.to_absolute_days())
        rumor_slices.sort(key=lambda e: e.world_time.to_absolute_days())

        # ── Costruisci focus_location ─────────────────────────────────────────
        location_entity = world_state.get_entity(request.focus_location_id)
        mood = self._mood_calculator.calculate(
            known_event_slices + rumor_slices
        )

        focus_location: dict[str, Any] = {
            "id": request.focus_location_id,
            "mood": mood,
        }
        if location_entity is not None:
            focus_location["name"] = location_entity.identity.name
            focus_location["tags"] = location_entity.identity.tags

        # ── Costruisci npcs_in_focus (solo noti al player) ────────────────────
        npcs_in_focus: list[NPCSlice] = []

        # NPC noti al player tramite known_entities
        for entity_id, known_state in player_kb.known_entities.items():
            entity = world_state.get_entity(entity_id)
            if entity is None or not isinstance(entity, NPCEntity):
                continue

            # Includi se il player conosce questa entità tramite KB
            npc_slice = NPCSlice(
                id=entity_id,
                name=entity.identity.name,
                role=entity.identity.tags[0] if entity.identity.tags else "",
                personality_traits=entity.behaviour.personality_traits,
                dialogue_style=entity.behaviour.dialogue_style,
                current_goal=entity.behaviour.current_goal if not hasattr(known_state, "certainty") or known_state.certainty >= 0.7 else None,
                last_known_location=known_state.last_known_location_id,
                available_at_moment=entity.behaviour.available_at_moments,
                relations_known_to_player=[
                    {"target_id": r.target_id, "type": r.type, "strength": r.strength}
                    for r in entity.relations
                    if player.id in r.known_to or not r.known_to
                ],
            )
            npcs_in_focus.append(npc_slice)

        # NPC fisicamente nella stessa location (anche se non noti dalla KB)
        player_location = player.mechanical.get("location_id")
        if player_location == request.focus_location_id:
            for entity in world_state.entity_store.values():
                if not isinstance(entity, NPCEntity):
                    continue
                if entity.id in player_kb.known_entities:
                    continue  # già aggiunto sopra
                npc_location = entity.mechanical.get("location_id")
                if npc_location == request.focus_location_id:
                    npc_slice = NPCSlice(
                        id=entity.id,
                        name=entity.identity.name,
                        role=entity.identity.tags[0] if entity.identity.tags else "",
                        personality_traits=entity.behaviour.personality_traits,
                        dialogue_style=entity.behaviour.dialogue_style,
                        available_at_moment=entity.behaviour.available_at_moments,
                    )
                    npcs_in_focus.append(npc_slice)

        # ── Costruisci player_context ─────────────────────────────────────────
        player_context: dict[str, Any] = {
            "name": player.identity.name,
            "narrative_traits": player.narrative.description,
            "choices_log_summary": len(player.narrative.choices_log),
            "location_id": player.mechanical.get("location_id"),
            "relations_known": [
                {
                    "target_id": r.target_id,
                    "type": r.type,
                    "strength": r.strength,
                }
                for r in player.relations
            ],
        }

        # ── Assembla e tronca il slice ────────────────────────────────────────
        clock_world_time = world_state.event_log[-1].world_time if world_state.event_log else None

        # Usa world_time dell'ultimo evento noto, o il primo disponibile
        if known_event_slices:
            current_world_time = known_event_slices[-1].world_time
        elif world_state.event_log:
            current_world_time = world_state.event_log[-1].world_time
        else:
            from ..models.base import WorldTime
            current_world_time = WorldTime()

        narrative_slice = NarrativeSlice(
            world_time=current_world_time,
            day_moment=current_world_time.moment,
            focus_location=focus_location,
            known_events_recent=known_event_slices,
            active_rumors=rumor_slices,
            npcs_in_focus=npcs_in_focus,
            player_context=player_context,
        )

        return self._truncation.truncate(narrative_slice, request.token_budget)


# ── Quest Slice Builder ───────────────────────────────────────────────────────


class QuestSliceBuilder:
    """Costruisce QuestSlice dal world state globale.

    L'agente Quest ha accesso pieno al world state — vede la realtà del mondo,
    non la percezione del player.
    Genera quest basate su tensioni reali, non su ciò che il player sa.
    """

    def __init__(
        self,
        tension_detector: Optional[TensionPointDetector] = None,
    ) -> None:
        """Inizializza il builder.

        Args:
            tension_detector: Rilevatore di tensioni (crea uno di default se None).
        """
        self._detector = tension_detector or TensionPointDetector()

    def build(
        self,
        world_state: "WorldState",
        request: SliceRequest,
        player: Optional[PlayerEntity] = None,
    ) -> QuestSlice:
        """Costruisce il QuestSlice per l'Agente Quest.

        Args:
            world_state: World state globale — fonte primaria.
            request: Richiesta con parametri di filtro.
            player: Entità player (per contesto livello e quest attive).

        Returns:
            QuestSlice con dati dal world state globale filtrato per area.
        """
        # ── Filtra eventi nel range richiesto ─────────────────────────────────
        recent_events_raw = [
            e
            for e in world_state.event_log
            if request.from_world_day
            <= e.world_time.to_absolute_days()
            <= request.to_world_day
        ]

        # Serializza eventi come dict per l'agente
        recent_events = [
            {
                "id": e.id,
                "verb": e.verb,
                "emitter": {"id": e.emitter.id, "name": e.emitter.name},
                "target": {"id": e.target.id, "name": e.target.name} if e.target else None,
                "world_time": e.world_time.to_absolute_days(),
                "payload": e.payload,
                "visibility_scope": e.visibility.scope,
            }
            for e in recent_events_raw
        ]

        # ── Rileva tension points ─────────────────────────────────────────────
        tension_points = self._detector.detect(
            world_state,
            request.focus_location_id,
            request.from_world_day,
            request.to_world_day,
        )

        # ── Recupera NPC nell'area ────────────────────────────────────────────
        available_npcs = [
            {
                "id": e.id,
                "name": e.identity.name,
                "location_id": e.mechanical.get("location_id"),
                "faction_id": e.behaviour.faction_id if hasattr(e, "behaviour") and hasattr(e.behaviour, "faction_id") else None,
                "current_goal": e.behaviour.current_goal if isinstance(e, NPCEntity) else None,
            }
            for e in world_state.entity_store.values()
            if isinstance(e, NPCEntity)
        ]

        # ── Focus location ────────────────────────────────────────────────────
        location_entity = world_state.get_entity(request.focus_location_id)
        focus_location: dict[str, Any] = {"id": request.focus_location_id}
        if location_entity:
            focus_location["name"] = location_entity.identity.name
            focus_location["tags"] = location_entity.identity.tags

        # ── Contesto player ───────────────────────────────────────────────────
        player_level = 0
        player_active_quests: list[str] = []
        if player:
            player_level = player.mechanical.get("level", 0)
            player_active_quests = player.mechanical.get("active_quests", [])

        # ── WorldTime corrente ────────────────────────────────────────────────
        if world_state.event_log:
            current_world_time = world_state.event_log[-1].world_time
        else:
            from ..models.base import WorldTime
            current_world_time = WorldTime()

        return QuestSlice(
            world_time=current_world_time,
            day_moment=current_world_time.moment,
            focus_location=focus_location,
            recent_events=recent_events,
            factions_present=[],  # da implementare con entity store fazioni
            tension_points=tension_points,
            available_npcs=available_npcs,
            available_locations=[],  # da implementare con entity store locations
            player_level=player_level,
            player_active_quests=player_active_quests,
            reward_budget={},
        )
