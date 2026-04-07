"""Test per engine/consequence.py — ConsequenceEngine e ScheduledEventProcessor."""

from __future__ import annotations

import random

import pytest

from game_engine.models.base import DayMoment, EntityKind, EntityStatus, GameTick, WorldTime
from game_engine.models.entity import EntityIdentity, EntityMeta, PlayerEntity
from game_engine.models.event import EventActor, EventVerb, EventVisibility, GameEvent
from game_engine.engine.cooldown import CooldownTracker
from game_engine.engine.consequence import (
    MAX_CASCADE_DEPTH,
    ConsequenceEngine,
    ConsequenceRule,
    CONFLICT_RULES,
    SOCIAL_RULES,
    RELIGION_RULES,
    ALL_RULES,
    ScheduledEventProcessor,
)
from game_engine.engine.knowledge import PlayerKnowledgeBase, VisibilityEngine
from game_engine.engine.world_clock import WorldClock
from game_engine.engine.world_state import WorldState


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_world_time(day: int = 1) -> WorldTime:
    return WorldTime(year=0, season="spring", day=day, moment=DayMoment.MORNING)


def make_clock(day: int = 1) -> WorldClock:
    return WorldClock(initial_time=make_world_time(day))


def make_actor(entity_id: str = "faction_001", kind: EntityKind = EntityKind.FACTION, name: str = "Iron Legion") -> EventActor:
    return EventActor(id=entity_id, kind=kind, name=name)


def make_event(
    verb: str = EventVerb.ATTACKED,
    emitter_id: str = "faction_001",
    cascade_depth: int = 0,
    location_id: str | None = "loc_border",
    tick_val: int = 0,
    day: int = 1,
) -> GameEvent:
    payload = {}
    if location_id:
        payload["location_id"] = location_id
    return GameEvent(
        tick=GameTick(tick_val),
        world_time=make_world_time(day),
        type="conflict",
        verb=verb,
        emitter=make_actor(emitter_id),
        cascade_depth=cascade_depth,
        payload=payload,
    )


def make_engine(seed: int = 42) -> tuple[ConsequenceEngine, CooldownTracker, VisibilityEngine]:
    cooldown = CooldownTracker()
    visibility = VisibilityEngine()
    rng = random.Random(seed)
    engine = ConsequenceEngine(cooldown, visibility, rng)
    return engine, cooldown, visibility


def make_player(location_id: str = "loc_border") -> PlayerEntity:
    meta = EntityMeta(created_at=make_world_time(), created_by="system", status=EntityStatus.ACTIVE)
    return PlayerEntity(
        id="player_1",
        meta=meta,
        identity=EntityIdentity(name="Elan"),
        mechanical={"location_id": location_id},
    )


# ── Regole: struttura ─────────────────────────────────────────────────────────

class TestRulesStructure:
    def test_all_rules_have_trigger_and_consequence(self) -> None:
        for rule in ALL_RULES:
            assert rule.trigger_verb
            assert rule.consequence_verb
            assert rule.consequence_type

    def test_delay_min_le_max(self) -> None:
        for rule in ALL_RULES:
            assert rule.delay_min_days <= rule.delay_max_days

    def test_conflict_rules_present(self) -> None:
        verbs = {r.trigger_verb for r in CONFLICT_RULES}
        assert "declared_war" in verbs
        assert "attacked" in verbs
        assert "assassinated" in verbs

    def test_social_rules_present(self) -> None:
        verbs = {r.trigger_verb for r in SOCIAL_RULES}
        assert "betrayed" in verbs
        assert "joined" in verbs

    def test_religion_rules_present(self) -> None:
        verbs = {r.trigger_verb for r in RELIGION_RULES}
        assert "desecrated" in verbs
        assert "converted" in verbs


# ── Conseguenze immediate ─────────────────────────────────────────────────────

class TestImmediateConsequences:
    def test_attacked_schedules_retaliated(self) -> None:
        """attacked → retaliated ha delay 1-3 giorni, quindi è schedulato."""
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="attacked")
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        # Nessun evento immediato (delay > 0)
        assert result == []
        # Ma uno schedulato
        assert any(s.event_template["verb"] == "retaliated" for s in ws.scheduled_events)

    def test_betrayed_generates_rivaled(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="betrayed")
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        verbs = [e.verb for e in result]
        assert "rivaled" in verbs

    def test_assassinated_generates_rivaled(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="assassinated")
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        verbs = [e.verb for e in result]
        assert "rivaled" in verbs

    def test_immediate_consequence_has_cascade_depth_1(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="betrayed", cascade_depth=0)
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        assert result[0].cascade_depth == 1

    def test_immediate_consequence_appended_to_world_state(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="betrayed")
        ws.append_event(event)

        engine.process_event(event, ws, clock)

        # event + consequence
        assert len(ws.event_log) == 2

    def test_immediate_consequence_has_parent_event_id(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="betrayed")
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        assert result[0].parent_event_id == event.id

    def test_no_rules_for_unknown_verb_returns_empty(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="time_passed")  # nessuna regola
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        assert result == []


# ── Conseguenze ritardate ─────────────────────────────────────────────────────

class TestDelayedConsequences:
    def test_declared_war_schedules_sieged(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock(day=1)
        event = make_event(verb="declared_war")
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        # Nessun evento immediato (delay > 0)
        assert result == []
        # Ma uno schedulato
        assert len(ws.scheduled_events) == 1
        scheduled = ws.scheduled_events[0]
        assert scheduled.event_template["verb"] == "sieged"

    def test_declared_war_delay_within_range(self) -> None:
        engine, _, _ = make_engine(seed=99)
        ws = WorldState()
        clock = make_clock(day=1)
        event = make_event(verb="declared_war")
        ws.append_event(event)

        engine.process_event(event, ws, clock)

        current_day = clock.world_time.to_absolute_days()  # day=1 → abs=0
        scheduled = ws.scheduled_events[0]
        delay = scheduled.trigger_world_day - current_day
        assert 5 <= delay <= 15

    def test_desecrated_schedules_declared_heresy(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="desecrated")
        ws.append_event(event)

        engine.process_event(event, ws, clock)

        assert len(ws.scheduled_events) == 1
        assert ws.scheduled_events[0].event_template["verb"] == "declared_heresy"

    def test_joined_schedules_allied(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="joined")
        ws.append_event(event)

        engine.process_event(event, ws, clock)

        assert any(s.event_template["verb"] == "allied" for s in ws.scheduled_events)

    def test_converted_schedules_proselytized(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="converted")
        ws.append_event(event)

        engine.process_event(event, ws, clock)

        assert any(s.event_template["verb"] == "proselytized" for s in ws.scheduled_events)


# ── Cooldown (anti-rumore) ────────────────────────────────────────────────────

class TestCooldown:
    def test_same_emitter_verb_within_cooldown_ignored(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock(day=1)

        event1 = make_event(verb="betrayed", tick_val=0)
        ws.append_event(event1)
        engine.process_event(event1, ws, clock)

        # Stesso emitter, stesso verb, stesso giorno → cooldown attivo
        event2 = make_event(verb="betrayed", tick_val=1)
        ws.append_event(event2)
        result2 = engine.process_event(event2, ws, clock)

        assert result2 == []

    def test_different_verb_not_on_cooldown(self) -> None:
        """Verb diverso non è in cooldown → conseguenze generate normalmente."""
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()

        event1 = make_event(verb="betrayed")  # → rivaled (immediato)
        ws.append_event(event1)
        engine.process_event(event1, ws, clock)

        # "assassinated" → "rivaled" (immediato, delay 0,0) — verb diverso da "betrayed"
        event2 = make_event(verb="assassinated")
        ws.append_event(event2)
        result2 = engine.process_event(event2, ws, clock)

        # Deve generare conseguenze (non bloccato dal cooldown di "betrayed")
        assert len(result2) > 0

    def test_different_emitter_not_on_cooldown(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()

        event1 = make_event(verb="betrayed", emitter_id="faction_001")
        ws.append_event(event1)
        engine.process_event(event1, ws, clock)

        event2 = make_event(verb="betrayed", emitter_id="faction_002")  # emitter diverso
        ws.append_event(event2)
        result2 = engine.process_event(event2, ws, clock)

        assert len(result2) > 0

    def test_after_cooldown_expiry_processes_normally(self) -> None:
        engine, cooldown, _ = make_engine()
        ws = WorldState()
        clock = make_clock(day=1)

        event1 = make_event(verb="betrayed", tick_val=0, day=1)
        ws.append_event(event1)
        engine.process_event(event1, ws, clock)

        # Simula avanzamento del mondo di 3+ giorni
        clock2 = make_clock(day=5)
        event2 = make_event(verb="betrayed", tick_val=10, day=5)
        ws.append_event(event2)
        result2 = engine.process_event(event2, ws, clock2)

        assert len(result2) > 0


# ── Cascade depth guard ───────────────────────────────────────────────────────

class TestCascadeDepth:
    def test_cascade_at_max_depth_returns_empty(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="betrayed", cascade_depth=MAX_CASCADE_DEPTH)
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        assert result == []

    def test_cascade_depth_grows_correctly(self) -> None:
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        event = make_event(verb="betrayed", cascade_depth=0)
        ws.append_event(event)

        result = engine.process_event(event, ws, clock)

        # BETRAYED → RIVALED (immediato, cascade_depth=1)
        assert result[0].cascade_depth == 1

    def test_max_cascade_depth_is_5(self) -> None:
        assert MAX_CASCADE_DEPTH == 5


# ── Separazione PlayerKnowledgeBase ──────────────────────────────────────────

class TestPlayerKnowledgeSeparation:
    def test_event_not_in_player_location_not_in_kb(self) -> None:
        """Evento generato lontano dal player → non entra in KB."""
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        player = make_player(location_id="loc_city")  # player altrove
        kb = PlayerKnowledgeBase(player_id="player_1")

        # Evento nella loc_border, player in loc_city
        event = make_event(verb="betrayed", location_id="loc_border")
        ws.append_event(event)
        engine.process_event(event, ws, clock, player, kb)

        # La conseguenza (rivaled) è in loc_border → player non la vede
        assert len(kb.known_events) == 0

    def test_event_in_player_location_enters_kb(self) -> None:
        """Evento generato nella stessa location del player → entra in KB."""
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()
        player = make_player(location_id="loc_border")  # stessa location
        kb = PlayerKnowledgeBase(player_id="player_1")

        event = make_event(verb="betrayed", location_id="loc_border")
        ws.append_event(event)
        engine.process_event(event, ws, clock, player, kb)

        # BETRAYED → RIVALED ha stessa location → player è testimone
        assert len(kb.known_events) == 1
        assert kb.known_events[0].certainty == 1.0
        assert kb.known_events[0].how_learned == "direct_witness"

    def test_no_player_no_kb_update(self) -> None:
        """Senza player/kb → engine funziona ugualmente senza crash."""
        engine, _, _ = make_engine()
        ws = WorldState()
        clock = make_clock()

        event = make_event(verb="betrayed")
        ws.append_event(event)
        result = engine.process_event(event, ws, clock)  # no player, no kb

        assert len(result) > 0  # conseguenze generate


# ── ScheduledEventProcessor ───────────────────────────────────────────────────

class TestScheduledEventProcessor:
    def _setup(self, seed: int = 42):
        engine, _, _ = make_engine(seed)
        processor = ScheduledEventProcessor(engine)
        ws = WorldState()
        return engine, processor, ws

    def test_processes_due_events(self) -> None:
        engine, processor, ws = self._setup()
        clock = make_clock(day=20)

        from game_engine.engine.world_state import ScheduledEvent
        scheduled = ScheduledEvent(
            trigger_world_day=0,  # già scaduto
            created_at=make_world_time(day=1),
            event_template={
                "verb": "sieged",
                "type": "conflict",
                "emitter_id": "faction_001",
                "emitter_kind": "faction",
                "emitter_name": "Iron Legion",
                "target_id": None,
                "target_kind": None,
                "target_name": None,
                "visibility_scope": "regional",
                "cascade_depth": 1,
                "parent_event_id": None,
            },
        )
        ws.schedule_event(scheduled)

        result = processor.run(ws, clock)

        assert len(result) >= 1
        assert result[0].verb == "sieged"

    def test_ignores_future_events(self) -> None:
        engine, processor, ws = self._setup()
        clock = make_clock(day=1)  # giorno corrente = abs 0

        from game_engine.engine.world_state import ScheduledEvent
        scheduled = ScheduledEvent(
            trigger_world_day=100,  # nel futuro
            created_at=make_world_time(day=1),
            event_template={
                "verb": "sieged",
                "type": "conflict",
                "emitter_id": "faction_001",
                "emitter_kind": "faction",
                "emitter_name": "Iron Legion",
                "target_id": None, "target_kind": None, "target_name": None,
                "visibility_scope": "regional",
                "cascade_depth": 1,
                "parent_event_id": None,
            },
        )
        ws.schedule_event(scheduled)

        result = processor.run(ws, clock)

        assert result == []
        assert len(ws.scheduled_events) == 1  # ancora in lista

    def test_empty_queue_returns_empty(self) -> None:
        engine, processor, ws = self._setup()
        clock = make_clock()

        result = processor.run(ws, clock)

        assert result == []

    def test_processed_event_appended_to_world_state(self) -> None:
        engine, processor, ws = self._setup()
        clock = make_clock(day=20)

        from game_engine.engine.world_state import ScheduledEvent
        scheduled = ScheduledEvent(
            trigger_world_day=0,
            created_at=make_world_time(),
            event_template={
                "verb": "surrendered",
                "type": "conflict",
                "emitter_id": "faction_002",
                "emitter_kind": "faction",
                "emitter_name": "Defenders",
                "target_id": None, "target_kind": None, "target_name": None,
                "visibility_scope": "regional",
                "cascade_depth": 1,
                "parent_event_id": None,
            },
        )
        ws.schedule_event(scheduled)

        processor.run(ws, clock)

        assert any(e.verb == "surrendered" for e in ws.event_log)

    def test_full_pipeline_declared_war_to_sieged(self) -> None:
        """Test end-to-end: DECLARED_WAR → schedule SIEGED → ScheduledEventProcessor → SIEGED in world state."""
        engine, _, _ = make_engine(seed=0)
        processor = ScheduledEventProcessor(engine)
        ws = WorldState()

        # Giorno 1: faction dichiara guerra
        clock_day1 = make_clock(day=1)
        war_event = make_event(verb="declared_war", day=1)
        ws.append_event(war_event)
        immediate = engine.process_event(war_event, ws, clock_day1)

        assert immediate == []  # nessuna conseguenza immediata
        assert len(ws.scheduled_events) == 1

        # Avanza al giorno del trigger
        scheduled = ws.scheduled_events[0]
        trigger_day = scheduled.trigger_world_day
        clock_future = WorldClock(initial_time=WorldTime(year=0, season="spring", day=trigger_day + 1))

        generated = processor.run(ws, clock_future)

        assert any(e.verb == "sieged" for e in generated)
        # Il SIEGED processato è stato rimosso dalla lista scheduled.
        # Possono essere presenti nuovi scheduled generati dalla cascata (es. surrendered).
        assert not any(
            s.event_template["verb"] == "sieged" and s.trigger_world_day == scheduled.trigger_world_day
            for s in ws.scheduled_events
        )
