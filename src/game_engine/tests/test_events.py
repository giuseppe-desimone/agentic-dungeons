"""Test per models/event.py: GameEvent, EventVerb, serializzazione."""

from __future__ import annotations

import json

import pytest

from game_engine.models.base import DayMoment, EntityKind, GameTick, WorldTime
from game_engine.models.event import (
    EventActor,
    EventVerb,
    EventVisibility,
    GameEvent,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_tick(n: int = 0) -> GameTick:
    return GameTick(n)


def make_world_time() -> WorldTime:
    return WorldTime(year=0, season="spring", day=1, moment=DayMoment.MORNING)


def make_actor(name: str = "Aldric", kind: EntityKind = EntityKind.NPC) -> EventActor:
    return EventActor(id="entity_001", kind=kind, name=name)


# ── EventVerb ─────────────────────────────────────────────────────────────────

class TestEventVerb:
    def test_all_verbs_are_strings(self) -> None:
        for verb in EventVerb:
            assert isinstance(verb.value, str)

    def test_key_verbs_present(self) -> None:
        verbs = {v.value for v in EventVerb}
        assert "spawned" in verbs
        assert "died" in verbs
        assert "attacked" in verbs
        assert "rumored" in verbs
        assert "traded" in verbs
        assert "leveled" in verbs
        assert "season_changed" in verbs

    def test_verb_count(self) -> None:
        assert len(list(EventVerb)) >= 50


# ── EventActor ────────────────────────────────────────────────────────────────

class TestEventActor:
    def test_creation(self) -> None:
        actor = make_actor()
        assert actor.id == "entity_001"
        assert actor.name == "Aldric"

    def test_kind_is_string_value(self) -> None:
        actor = make_actor(kind=EntityKind.PLAYER)
        assert actor.kind == "player"


# ── EventVisibility ───────────────────────────────────────────────────────────

class TestEventVisibility:
    def test_defaults(self) -> None:
        vis = EventVisibility()
        assert vis.scope == "local"
        assert vis.known_to == []

    def test_custom_scope(self) -> None:
        vis = EventVisibility(scope="regional", known_to=["player_1", "npc_2"])
        assert vis.scope == "regional"
        assert len(vis.known_to) == 2


# ── GameEvent ─────────────────────────────────────────────────────────────────

class TestGameEvent:
    def test_creation_with_explicit_tick(self) -> None:
        event = GameEvent(
            tick=make_tick(5),
            world_time=make_world_time(),
            type="conflict",
            verb=EventVerb.ATTACKED,
            emitter=make_actor(),
        )
        assert event.tick.value == 5
        assert event.verb == EventVerb.ATTACKED

    def test_uuid_generated_by_default(self) -> None:
        e1 = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="social", verb=EventVerb.JOINED, emitter=make_actor(),
        )
        e2 = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="social", verb=EventVerb.JOINED, emitter=make_actor(),
        )
        assert e1.id != e2.id

    def test_default_status_active(self) -> None:
        event = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="world", verb=EventVerb.SPAWNED, emitter=make_actor(),
        )
        assert event.status == "active"

    def test_cascade_depth_default_zero(self) -> None:
        event = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="conflict", verb=EventVerb.RETALIATED, emitter=make_actor(),
        )
        assert event.cascade_depth == 0

    def test_parent_event_id(self) -> None:
        parent = GameEvent(
            tick=make_tick(0), world_time=make_world_time(),
            type="conflict", verb=EventVerb.ATTACKED, emitter=make_actor(),
        )
        child = GameEvent(
            tick=make_tick(1), world_time=make_world_time(),
            type="conflict", verb=EventVerb.RETALIATED, emitter=make_actor(),
            parent_event_id=parent.id,
            cascade_depth=1,
        )
        assert child.parent_event_id == parent.id
        assert child.cascade_depth == 1

    def test_with_target(self) -> None:
        target = EventActor(id="npc_002", kind=EntityKind.PLAYER, name="Elan")
        event = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="conflict", verb=EventVerb.ATTACKED,
            emitter=make_actor(),
            target=target,
        )
        assert event.target is not None
        assert event.target.name == "Elan"

    def test_with_payload(self) -> None:
        event = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="economy", verb=EventVerb.TRADED,
            emitter=make_actor(),
            payload={"item": "sword", "gold": 50},
        )
        assert event.payload["item"] == "sword"

    def test_with_visibility(self) -> None:
        vis = EventVisibility(scope="global", known_to=["player_1"])
        event = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="world", verb=EventVerb.NATURAL_DISASTER,
            emitter=make_actor(),
            visibility=vis,
        )
        assert event.visibility.scope == "global"
        assert "player_1" in event.visibility.known_to

    def test_custom_verb_string(self) -> None:
        """Verb custom del Game Engine: stringa libera 'namespace:verb'."""
        event = GameEvent(
            tick=make_tick(), world_time=make_world_time(),
            type="custom", verb="combat:critical_hit",
            emitter=make_actor(),
        )
        assert event.verb == "combat:critical_hit"


# ── Serializzazione ───────────────────────────────────────────────────────────

class TestGameEventSerialization:
    def test_model_dump_json(self) -> None:
        event = GameEvent(
            tick=make_tick(3), world_time=make_world_time(),
            type="conflict", verb=EventVerb.ALLIED, emitter=make_actor(),
        )
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert parsed["verb"] == "allied"
        assert parsed["status"] == "active"

    def test_round_trip(self) -> None:
        event = GameEvent(
            tick=make_tick(7), world_time=make_world_time(),
            type="religion", verb=EventVerb.CONVERTED,
            emitter=make_actor(kind=EntityKind.FACTION),
            payload={"from_religion": "old_faith", "to_religion": "new_faith"},
        )
        data = event.model_dump()
        event2 = GameEvent.model_validate(data)
        assert event2.id == event.id
        assert event2.payload["from_religion"] == "old_faith"
