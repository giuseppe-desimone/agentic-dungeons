"""Test per engine/knowledge.py: PlayerKnowledgeBase, KnowledgeUpdate."""

from __future__ import annotations

import pytest

from game_engine.models.base import DayMoment, EntityKind, GameTick, WorldTime
from game_engine.models.event import EventActor, EventVerb, GameEvent
from game_engine.engine.knowledge import (
    KnownEntityState,
    KnownEventEntry,
    KnowledgeUpdate,
    PlayerKnowledgeBase,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_world_time(day: int = 1, moment: DayMoment = DayMoment.MORNING) -> WorldTime:
    return WorldTime(year=0, season="spring", day=day, moment=moment)


def make_event(
    emitter_id: str = "npc_001",
    verb: str = EventVerb.ATTACKED,
    tick_val: int = 0,
    day: int = 1,
) -> GameEvent:
    return GameEvent(
        tick=GameTick(tick_val),
        world_time=make_world_time(day=day),
        type="conflict",
        verb=verb,
        emitter=EventActor(id=emitter_id, kind=EntityKind.NPC, name="Aldric"),
    )


def make_update(
    event: GameEvent,
    how_learned: str = "direct_witness",
    certainty: float = 1.0,
    learned_at: WorldTime | None = None,
) -> KnowledgeUpdate:
    return KnowledgeUpdate(
        event_id=event.id,
        how_learned=how_learned,
        certainty=certainty,
        learned_at=learned_at,
    )


def make_kb(player_id: str = "player_1") -> PlayerKnowledgeBase:
    return PlayerKnowledgeBase(player_id=player_id)


# ── KnowledgeUpdate ───────────────────────────────────────────────────────────

class TestKnowledgeUpdate:
    def test_creation(self) -> None:
        event = make_event()
        update = make_update(event)
        assert update.event_id == event.id
        assert update.how_learned == "direct_witness"
        assert update.certainty == 1.0
        assert update.learned_at is None

    def test_with_learned_at(self) -> None:
        event = make_event()
        wt = make_world_time(day=3)
        update = KnowledgeUpdate(
            event_id=event.id,
            how_learned="rumor",
            certainty=0.4,
            learned_at=wt,
        )
        assert update.learned_at is not None
        assert update.learned_at.day == 3


# ── PlayerKnowledgeBase.apply_update ─────────────────────────────────────────

class TestApplyUpdate:
    def test_direct_witness_not_in_rumors(self) -> None:
        kb = make_kb()
        event = make_event()
        update = make_update(event, certainty=1.0)
        kb.apply_update(update, event, make_world_time())

        assert event.id not in kb.active_rumors
        assert len(kb.known_events) == 1
        assert kb.known_events[0].certainty == 1.0

    def test_rumor_goes_to_active_rumors(self) -> None:
        kb = make_kb()
        event = make_event()
        update = make_update(event, how_learned="rumor", certainty=0.4)
        kb.apply_update(update, event, make_world_time())

        assert event.id in kb.active_rumors
        assert kb.known_events[0].how_learned == "rumor"

    def test_informed_not_in_rumors(self) -> None:
        """certainty=0.9 → non è un rumor."""
        kb = make_kb()
        event = make_event()
        update = make_update(event, how_learned="informed", certainty=0.9)
        kb.apply_update(update, event, make_world_time())

        assert event.id not in kb.active_rumors

    def test_certainty_border_069_is_rumor(self) -> None:
        """certainty < 0.7 → rumor."""
        kb = make_kb()
        event = make_event()
        update = make_update(event, certainty=0.69)
        kb.apply_update(update, event, make_world_time())
        assert event.id in kb.active_rumors

    def test_certainty_border_07_is_not_rumor(self) -> None:
        """certainty >= 0.7 → non rumor."""
        kb = make_kb()
        event = make_event()
        update = make_update(event, certainty=0.7)
        kb.apply_update(update, event, make_world_time())
        assert event.id not in kb.active_rumors

    def test_known_entity_created(self) -> None:
        """Dopo apply_update, l'emittente appare in known_entities."""
        kb = make_kb()
        event = make_event(emitter_id="npc_001")
        update = make_update(event, certainty=1.0)
        kb.apply_update(update, event, make_world_time(day=5))

        assert "npc_001" in kb.known_entities
        assert kb.known_entities["npc_001"].last_seen_at.day == 5

    def test_known_entity_not_updated_for_low_certainty(self) -> None:
        """certainty < 0.5 → last_seen_at non aggiornato."""
        kb = make_kb()
        event = make_event(emitter_id="npc_002")

        # Prima visita certa
        update1 = make_update(event, certainty=0.9)
        kb.apply_update(update1, event, make_world_time(day=1))
        first_seen = kb.known_entities["npc_002"].last_seen_at.day

        # Secondo aggiornamento con certezza troppo bassa
        event2 = make_event(emitter_id="npc_002", tick_val=1, day=5)
        update2 = make_update(event2, certainty=0.3)
        kb.apply_update(update2, event2, make_world_time(day=5))

        # last_seen_at non deve essere aggiornato al giorno 5
        assert kb.known_entities["npc_002"].last_seen_at.day == first_seen

    def test_learned_at_uses_update_if_provided(self) -> None:
        """Se KnowledgeUpdate.learned_at è impostato, usa quello."""
        kb = make_kb()
        event = make_event()
        specific_time = make_world_time(day=10)
        update = KnowledgeUpdate(
            event_id=event.id,
            how_learned="informed",
            certainty=0.9,
            learned_at=specific_time,
        )
        kb.apply_update(update, event, make_world_time(day=1))

        assert kb.known_events[0].learned_at.day == 10

    def test_learned_at_fallback_to_world_time(self) -> None:
        """Se KnowledgeUpdate.learned_at è None, usa il world_time passato."""
        kb = make_kb()
        event = make_event()
        update = make_update(event, certainty=1.0, learned_at=None)
        kb.apply_update(update, event, make_world_time(day=7))

        assert kb.known_events[0].learned_at.day == 7

    def test_multiple_events_accumulate(self) -> None:
        kb = make_kb()
        for i in range(5):
            event = make_event(tick_val=i, day=i + 1)
            update = make_update(event, certainty=1.0)
            kb.apply_update(update, event, make_world_time(day=i + 1))

        assert len(kb.known_events) == 5


# ── get_events_since ─────────────────────────────────────────────────────────

class TestGetEventsSince:
    def test_filters_by_world_day(self) -> None:
        kb = make_kb()
        world_time = make_world_time()

        for day in [1, 3, 5, 8, 10]:
            event = make_event(tick_val=day, day=day)
            update = make_update(event, certainty=1.0, learned_at=make_world_time(day=day))
            kb.apply_update(update, event, make_world_time(day=day))

        since_day_5 = kb.get_events_since(world_day=4)
        # Giorni assoluti: day=5 → abs=4, day=8 → abs=7, day=10 → abs=9
        assert len(since_day_5) == 3

    def test_empty_if_all_before(self) -> None:
        kb = make_kb()
        event = make_event(day=1)
        update = make_update(event, certainty=1.0, learned_at=make_world_time(day=1))
        kb.apply_update(update, event, make_world_time(day=1))

        result = kb.get_events_since(world_day=100)
        assert result == []

    def test_all_if_day_zero(self) -> None:
        kb = make_kb()
        for i in range(3):
            event = make_event(tick_val=i, day=i + 1)
            wt = make_world_time(day=i + 1)
            update = make_update(event, certainty=1.0, learned_at=wt)
            kb.apply_update(update, event, wt)

        result = kb.get_events_since(world_day=0)
        assert len(result) == 3
