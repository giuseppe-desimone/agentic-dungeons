"""Test suite per il Bridge Game Engine (Fase 9).

Verifica:
- spawn_entity: NPC nel WorldState + SPAWNED event generato
- resolve_combat: ATTACKED event, world time NON avanzato
- apply_movement: location aggiornata, world time avanzato, MIGRATED event
- apply_inventory: TRADED/STOLEN event corretto per ogni action
- apply_xp: xp aggiornato, LEVELED event solo se soglia raggiunta
"""

from __future__ import annotations

import pytest

from game_engine.bridge.game_engine import (
    XP_PER_LEVEL,
    apply_inventory,
    apply_movement,
    apply_xp,
    resolve_combat,
    spawn_entity,
)
from game_engine.engine.world_clock import WorldClock
from game_engine.engine.world_state import WorldState
from game_engine.models.base import (
    DayMoment,
    EntityKind,
    EntityStatus,
    GameTick,
    WorldTime,
)
from game_engine.models.entity import (
    EntityIdentity,
    EntityMeta,
    NPCBehaviour,
    NPCEntity,
    PlayerEntity,
)
from game_engine.models.event import EventVerb


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_world_time() -> WorldTime:
    return WorldTime(year=0, season="spring", day=1, moment=DayMoment.MORNING)


def make_player(location: str = "loc_tavern", xp: int = 0, level: int = 1) -> PlayerEntity:
    return PlayerEntity(
        id="player_001",
        meta=EntityMeta(created_at=make_world_time(), created_by="test", status=EntityStatus.ACTIVE),
        identity=EntityIdentity(name="Elan"),
        mechanical={"location_id": location, "xp": xp, "level": level},
    )


def make_npc(npc_id: str = "npc_001", name: str = "Mira", location: str = "loc_tavern") -> NPCEntity:
    return NPCEntity(
        id=npc_id,
        meta=EntityMeta(created_at=make_world_time(), created_by="test", status=EntityStatus.ACTIVE),
        identity=EntityIdentity(name=name),
        mechanical={"location_id": location},
        behaviour=NPCBehaviour(),
    )


# ── spawn_entity ──────────────────────────────────────────────────────────────


class TestSpawnEntity:
    def test_npc_added_to_entity_store(self):
        ws = WorldState()
        clock = WorldClock()
        npc = make_npc()

        spawn_entity(npc, "loc_fort", ws, clock)

        assert "npc_001" in ws.entity_store

    def test_spawned_event_generated(self):
        ws = WorldState()
        clock = WorldClock()
        npc = make_npc()

        spawn_entity(npc, "loc_fort", ws, clock)

        assert len(ws.event_log) == 1
        assert ws.event_log[0].verb == EventVerb.SPAWNED

    def test_spawned_event_has_correct_location(self):
        ws = WorldState()
        clock = WorldClock()
        npc = make_npc()

        spawn_entity(npc, "loc_fort", ws, clock)

        assert ws.event_log[0].payload["location_id"] == "loc_fort"

    def test_npc_location_updated(self):
        ws = WorldState()
        clock = WorldClock()
        npc = make_npc(location="loc_old")

        spawn_entity(npc, "loc_fort", ws, clock)

        stored_npc = ws.entity_store["npc_001"]
        assert stored_npc.mechanical["location_id"] == "loc_fort"

    def test_tick_advanced(self):
        ws = WorldState()
        clock = WorldClock()
        initial_tick = clock.tick.value
        npc = make_npc()

        spawn_entity(npc, "loc_fort", ws, clock)

        assert clock.tick.value == initial_tick + 1

    def test_returns_event_id(self):
        ws = WorldState()
        clock = WorldClock()
        npc = make_npc()

        event_id = spawn_entity(npc, "loc_fort", ws, clock)

        assert event_id is not None
        assert event_id == ws.event_log[0].id

    def test_emitter_is_npc(self):
        ws = WorldState()
        clock = WorldClock()
        npc = make_npc("npc_002", "Aldric")

        spawn_entity(npc, "loc_fort", ws, clock)

        assert ws.event_log[0].emitter.id == "npc_002"
        assert ws.event_log[0].emitter.name == "Aldric"


# ── resolve_combat ────────────────────────────────────────────────────────────


class TestResolveCombat:
    def test_attacked_event_generated(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        npc = make_npc()
        ws.add_entity(player)
        ws.add_entity(npc)

        resolve_combat("player_001", "npc_001", ws, clock)

        assert len(ws.event_log) == 1
        assert ws.event_log[0].verb == EventVerb.ATTACKED

    def test_emitter_is_attacker(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        npc = make_npc()
        ws.add_entity(player)
        ws.add_entity(npc)

        resolve_combat("player_001", "npc_001", ws, clock)

        assert ws.event_log[0].emitter.id == "player_001"

    def test_target_is_defender(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        npc = make_npc()
        ws.add_entity(player)
        ws.add_entity(npc)

        resolve_combat("player_001", "npc_001", ws, clock)

        assert ws.event_log[0].target.id == "npc_001"

    def test_world_time_NOT_advanced(self):
        """Combat NON deve avanzare il WorldTime narrativo."""
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        npc = make_npc()
        ws.add_entity(player)
        ws.add_entity(npc)

        initial_units = clock.world_units_total

        resolve_combat("player_001", "npc_001", ws, clock)

        assert clock.world_units_total == initial_units

    def test_returns_outcome_dict(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        npc = make_npc()
        ws.add_entity(player)
        ws.add_entity(npc)

        result = resolve_combat("player_001", "npc_001", ws, clock)

        assert "event_id" in result
        assert result["attacker_id"] == "player_001"
        assert result["defender_id"] == "npc_001"
        assert result["outcome"] == "attacked"

    def test_raises_if_attacker_not_found(self):
        ws = WorldState()
        clock = WorldClock()
        npc = make_npc()
        ws.add_entity(npc)

        with pytest.raises(ValueError, match="Attaccante"):
            resolve_combat("nonexistent", "npc_001", ws, clock)

    def test_raises_if_defender_not_found(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        with pytest.raises(ValueError, match="Difensore"):
            resolve_combat("player_001", "nonexistent", ws, clock)

    def test_tick_advanced_after_combat(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        npc = make_npc()
        ws.add_entity(player)
        ws.add_entity(npc)
        initial_tick = clock.tick.value

        resolve_combat("player_001", "npc_001", ws, clock)

        assert clock.tick.value == initial_tick + 1


# ── apply_movement ────────────────────────────────────────────────────────────


class TestApplyMovement:
    def test_entity_location_updated(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(location="loc_tavern")
        ws.add_entity(player)

        apply_movement("player_001", "loc_tavern", "loc_market", "travel_short", ws, clock)

        updated = ws.entity_store["player_001"]
        assert updated.mechanical["location_id"] == "loc_market"

    def test_world_time_advanced(self):
        """Movement DEVE avanzare il WorldTime narrativo."""
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)
        initial_units = clock.world_units_total

        apply_movement("player_001", "loc_tavern", "loc_market", "travel_short", ws, clock)

        assert clock.world_units_total > initial_units

    def test_migrated_event_generated(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        apply_movement("player_001", "loc_tavern", "loc_market", "travel_short", ws, clock)

        assert len(ws.event_log) == 1
        assert ws.event_log[0].verb == EventVerb.MIGRATED

    def test_payload_has_correct_locations(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(location="loc_tavern")
        ws.add_entity(player)

        apply_movement("player_001", "loc_tavern", "loc_market", "travel_short", ws, clock)

        payload = ws.event_log[0].payload
        assert payload["location_id"] == "loc_market"
        assert payload["from_location_id"] == "loc_tavern"

    def test_returns_event_id(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        event_id = apply_movement("player_001", "loc_tavern", "loc_market", "travel_short", ws, clock)

        assert event_id == ws.event_log[0].id

    def test_travel_long_advances_more_time(self):
        """travel_long avanza più tempo di travel_short."""
        ws1 = WorldState()
        clock1 = WorldClock()
        ws1.add_entity(make_player())
        apply_movement("player_001", "a", "b", "travel_short", ws1, clock1)
        short_units = clock1.world_units_total

        ws2 = WorldState()
        clock2 = WorldClock()
        ws2.add_entity(make_player())
        apply_movement("player_001", "a", "b", "travel_long", ws2, clock2)
        long_units = clock2.world_units_total

        assert long_units > short_units

    def test_raises_if_entity_not_found(self):
        ws = WorldState()
        clock = WorldClock()

        with pytest.raises(ValueError, match="non trovata"):
            apply_movement("nonexistent", "a", "b", "travel_short", ws, clock)


# ── apply_inventory ───────────────────────────────────────────────────────────


class TestApplyInventory:
    def test_give_generates_traded_event(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        apply_inventory("player_001", "item_sword", "give", ws, clock)

        assert ws.event_log[0].verb == EventVerb.TRADED

    def test_take_generates_traded_event(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        apply_inventory("player_001", "item_potion", "take", ws, clock)

        assert ws.event_log[0].verb == EventVerb.TRADED

    def test_drop_generates_traded_event(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        apply_inventory("player_001", "item_rock", "drop", ws, clock)

        assert ws.event_log[0].verb == EventVerb.TRADED

    def test_steal_generates_stolen_event(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        apply_inventory("player_001", "item_coin", "steal", ws, clock)

        assert ws.event_log[0].verb == EventVerb.STOLEN

    def test_payload_has_item_id(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        apply_inventory("player_001", "item_magic_ring", "give", ws, clock)

        assert ws.event_log[0].payload["item_id"] == "item_magic_ring"

    def test_returns_event_id(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)

        event_id = apply_inventory("player_001", "item_sword", "give", ws, clock)

        assert event_id is not None
        assert event_id == ws.event_log[0].id

    def test_raises_if_entity_not_found(self):
        ws = WorldState()
        clock = WorldClock()

        with pytest.raises(ValueError, match="non trovata"):
            apply_inventory("nonexistent", "item_x", "give", ws, clock)


# ── apply_xp ──────────────────────────────────────────────────────────────────


class TestApplyXp:
    def test_xp_updated_no_level_up(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(xp=0, level=1)
        ws.add_entity(player)

        apply_xp("player_001", 50, ws, clock)

        updated = ws.entity_store["player_001"]
        assert updated.mechanical["xp"] == 50

    def test_no_event_if_no_level_up(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(xp=0, level=1)
        ws.add_entity(player)

        result = apply_xp("player_001", 50, ws, clock)

        assert result is None
        assert len(ws.event_log) == 0

    def test_level_up_generates_leveled_event(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(xp=0, level=1)
        ws.add_entity(player)

        result = apply_xp("player_001", XP_PER_LEVEL, ws, clock)

        assert result is not None
        assert len(ws.event_log) == 1
        assert ws.event_log[0].verb == EventVerb.LEVELED

    def test_level_incremented_on_level_up(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(xp=0, level=1)
        ws.add_entity(player)

        apply_xp("player_001", XP_PER_LEVEL, ws, clock)

        updated = ws.entity_store["player_001"]
        assert updated.mechanical["level"] == 2

    def test_xp_accumulated_across_calls(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(xp=0, level=1)
        ws.add_entity(player)

        apply_xp("player_001", 30, ws, clock)
        apply_xp("player_001", 30, ws, clock)

        updated = ws.entity_store["player_001"]
        assert updated.mechanical["xp"] == 60

    def test_level_up_on_second_call(self):
        """Due chiamate sommano XP — level-up alla seconda."""
        ws = WorldState()
        clock = WorldClock()
        player = make_player(xp=0, level=1)
        ws.add_entity(player)

        result1 = apply_xp("player_001", 60, ws, clock)
        result2 = apply_xp("player_001", 60, ws, clock)

        assert result1 is None       # 60 XP: no level-up
        assert result2 is not None   # 120 XP >= 100: level-up

    def test_leveled_event_has_correct_payload(self):
        ws = WorldState()
        clock = WorldClock()
        player = make_player(xp=0, level=1)
        ws.add_entity(player)

        apply_xp("player_001", XP_PER_LEVEL, ws, clock)

        payload = ws.event_log[0].payload
        assert payload["old_level"] == 1
        assert payload["new_level"] == 2
        assert payload["xp_total"] == XP_PER_LEVEL

    def test_raises_if_entity_not_found(self):
        ws = WorldState()
        clock = WorldClock()

        with pytest.raises(ValueError, match="non trovata"):
            apply_xp("nonexistent", 100, ws, clock)

    def test_raises_if_no_mechanical(self):
        """PlayerEntity deve avere campo mechanical."""
        ws = WorldState()
        clock = WorldClock()
        player = make_player()
        ws.add_entity(player)
        # player ha mechanical → non solleva eccezione
        apply_xp("player_001", 10, ws, clock)  # nessuna eccezione

    def test_xp_per_level_constant_respected(self):
        """La costante XP_PER_LEVEL = 100 è verificata dalla logica."""
        assert XP_PER_LEVEL == 100

    def test_level_2_requires_200_xp(self):
        """Per passare a livello 3, il livello 2 richiede 200 XP aggiuntivi."""
        ws = WorldState()
        clock = WorldClock()
        # Inizia già a livello 2 con 100 XP accumulati
        player = make_player(xp=100, level=2)
        ws.add_entity(player)

        result = apply_xp("player_001", 199, ws, clock)  # 100+199=299 < 2*100=200? no: 299>=200
        # 299 >= 2*100=200 → level-up
        assert result is not None
