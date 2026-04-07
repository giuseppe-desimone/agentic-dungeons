"""Test per engine/knowledge.py — VisibilityEngine."""

from __future__ import annotations

import pytest

from game_engine.models.base import DayMoment, EntityKind, EntityStatus, GameTick, WorldTime
from game_engine.models.entity import EntityIdentity, EntityMeta, PlayerEntity
from game_engine.models.event import EventActor, EventVerb, EventVisibility, GameEvent
from game_engine.engine.knowledge import KnowledgeUpdate, PlayerKnowledgeBase, VisibilityEngine
from game_engine.engine.world_state import WorldState


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_world_time() -> WorldTime:
    return WorldTime(year=0, season="spring", day=1, moment=DayMoment.MORNING)


def make_player(player_id: str = "player_1", location_id: str | None = "loc_tavern") -> PlayerEntity:
    meta = EntityMeta(created_at=make_world_time(), created_by="system", status=EntityStatus.ACTIVE)
    identity = EntityIdentity(name="Elan")
    mechanical = {}
    if location_id is not None:
        mechanical["location_id"] = location_id
    return PlayerEntity(id=player_id, meta=meta, identity=identity, mechanical=mechanical)


def make_event(
    verb: str = EventVerb.ATTACKED,
    location_id: str | None = "loc_tavern",
    scope: str = "local",
    known_to: list[str] | None = None,
    emitter_id: str = "npc_001",
) -> GameEvent:
    visibility = EventVisibility(scope=scope, known_to=known_to or [])
    payload = {}
    if location_id is not None:
        payload["location_id"] = location_id
    return GameEvent(
        tick=GameTick(0),
        world_time=make_world_time(),
        type="conflict",
        verb=verb,
        emitter=EventActor(id=emitter_id, kind=EntityKind.NPC, name="Aldric"),
        visibility=visibility,
        payload=payload,
    )


# ── Regola 1: direct_witness ──────────────────────────────────────────────────

class TestDirectWitness:
    def test_same_location_returns_direct_witness(self) -> None:
        engine = VisibilityEngine()
        player = make_player(location_id="loc_tavern")
        event = make_event(location_id="loc_tavern")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is not None
        assert result.how_learned == "direct_witness"
        assert result.certainty == 1.0
        assert result.event_id == event.id

    def test_different_location_no_witness(self) -> None:
        engine = VisibilityEngine()
        player = make_player(location_id="loc_market")
        event = make_event(location_id="loc_tavern")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is None

    def test_event_no_location_no_witness(self) -> None:
        engine = VisibilityEngine()
        player = make_player(location_id="loc_tavern")
        event = make_event(location_id=None)  # evento senza location
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        # Non può essere direct_witness → potrebbe essere informed se in known_to
        assert result is None

    def test_player_no_location_no_witness(self) -> None:
        engine = VisibilityEngine()
        player = make_player(location_id=None)  # player senza location
        event = make_event(location_id="loc_tavern")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is None


# ── Regola 2: informed ────────────────────────────────────────────────────────

class TestInformed:
    def test_player_in_known_to(self) -> None:
        engine = VisibilityEngine()
        player = make_player(player_id="player_1", location_id="loc_market")
        event = make_event(location_id="loc_tavern", known_to=["player_1"])
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is not None
        assert result.how_learned == "informed"
        assert result.certainty == 0.9

    def test_player_not_in_known_to(self) -> None:
        engine = VisibilityEngine()
        player = make_player(player_id="player_1", location_id="loc_market")
        event = make_event(location_id="loc_tavern", known_to=["npc_999"])
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is None

    def test_direct_witness_takes_priority_over_informed(self) -> None:
        """Se il player è sia in known_to sia nella location → direct_witness."""
        engine = VisibilityEngine()
        player = make_player(player_id="player_1", location_id="loc_tavern")
        event = make_event(location_id="loc_tavern", known_to=["player_1"])
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is not None
        assert result.how_learned == "direct_witness"  # priorità
        assert result.certainty == 1.0


# ── Regola 3: rumor ───────────────────────────────────────────────────────────

class TestRumor:
    def test_rumor_regional_scope_reaches_player(self) -> None:
        engine = VisibilityEngine()
        player = make_player(location_id="loc_market")
        event = make_event(verb=EventVerb.RUMORED, scope="regional", location_id="loc_faraway")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is not None
        assert result.how_learned == "rumor"
        assert result.certainty == 0.4

    def test_rumor_local_scope_same_location_gives_direct_witness(self) -> None:
        """Rumor + stessa location → regola 1 ha priorità (direct_witness, non rumor)."""
        engine = VisibilityEngine()
        player = make_player(location_id="loc_tavern")
        event = make_event(verb=EventVerb.RUMORED, scope="local", location_id="loc_tavern")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        # Regola 1 (stesso luogo) scatta prima della regola 3 (rumor)
        assert result is not None
        assert result.how_learned == "direct_witness"
        assert result.certainty == 1.0

    def test_rumor_local_scope_different_location(self) -> None:
        engine = VisibilityEngine()
        player = make_player(location_id="loc_market")
        event = make_event(verb=EventVerb.RUMORED, scope="local", location_id="loc_tavern")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is None

    def test_rumor_global_scope_does_not_match_rule3(self) -> None:
        """Scope 'global' non rientra nella regola rumor (che copre local/regional)."""
        engine = VisibilityEngine()
        player = make_player(location_id="loc_market")
        event = make_event(verb=EventVerb.RUMORED, scope="global", location_id="loc_tavern")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        # Nessuna regola attivata
        assert result is None

    def test_non_rumor_verb_does_not_trigger_rule3(self) -> None:
        """ATTACKED non è un rumor: la regola 3 non si attiva."""
        engine = VisibilityEngine()
        player = make_player(location_id="loc_market")
        event = make_event(verb=EventVerb.ATTACKED, scope="regional", location_id="loc_tavern")
        ws = WorldState()

        result = engine.evaluate(event, player, ws)

        assert result is None


# ── Integrazione con PlayerKnowledgeBase ──────────────────────────────────────

class TestVisibilityIntegration:
    def test_direct_witness_applies_to_kb(self) -> None:
        engine = VisibilityEngine()
        player = make_player(player_id="p1", location_id="loc_tavern")
        event = make_event(location_id="loc_tavern")
        ws = WorldState()
        kb = PlayerKnowledgeBase(player_id="p1")

        update = engine.evaluate(event, player, ws)
        assert update is not None
        kb.apply_update(update, event, make_world_time())

        assert len(kb.known_events) == 1
        assert event.id not in kb.active_rumors

    def test_rumor_appears_in_active_rumors(self) -> None:
        engine = VisibilityEngine()
        player = make_player(player_id="p1", location_id="loc_market")
        event = make_event(verb=EventVerb.RUMORED, scope="regional", location_id="loc_faraway")
        ws = WorldState()
        kb = PlayerKnowledgeBase(player_id="p1")

        update = engine.evaluate(event, player, ws)
        assert update is not None
        kb.apply_update(update, event, make_world_time())

        assert event.id in kb.active_rumors
        assert kb.known_events[0].certainty == 0.4

    def test_unknown_event_not_in_kb(self) -> None:
        engine = VisibilityEngine()
        player = make_player(player_id="p1", location_id="loc_market")
        event = make_event(location_id="loc_dungeon", known_to=[])
        ws = WorldState()
        kb = PlayerKnowledgeBase(player_id="p1")

        update = engine.evaluate(event, player, ws)
        assert update is None
        # KB non viene aggiornata
        assert len(kb.known_events) == 0
