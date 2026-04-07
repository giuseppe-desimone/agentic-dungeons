"""Test per models/entity.py: serializzazione Pydantic e struttura entità."""

from __future__ import annotations

import json

import pytest

from game_engine.models.base import (
    DayMoment,
    EntityKind,
    EntityStatus,
    RelationType,
    WorldTime,
)
from game_engine.models.entity import (
    BaseEntity,
    ChoiceLogEntry,
    EntityIdentity,
    EntityMeta,
    EntityNarrative,
    NPCBehaviour,
    NPCEntity,
    PlayerEntity,
    PlayerNarrative,
    Relation,
    Secret,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_world_time() -> WorldTime:
    return WorldTime(year=0, season="spring", day=1, moment=DayMoment.MORNING)


def make_entity_meta(status: EntityStatus = EntityStatus.ACTIVE) -> EntityMeta:
    return EntityMeta(
        created_at=make_world_time(),
        created_by="system",
        status=status,
    )


def make_entity_identity(name: str = "Aldric") -> EntityIdentity:
    return EntityIdentity(name=name, aliases=["Il Vecchio"], tags=["merchant"])


# ── Secret ────────────────────────────────────────────────────────────────────

class TestSecret:
    def test_creation(self) -> None:
        s = Secret(content="Conosce la via nascosta", known_to=["player_1"])
        assert s.content == "Conosce la via nascosta"
        assert "player_1" in s.known_to

    def test_default_known_to_empty(self) -> None:
        s = Secret(content="test")
        assert s.known_to == []


# ── BaseEntity ────────────────────────────────────────────────────────────────

class TestBaseEntity:
    def test_creation_generates_uuid(self) -> None:
        e1 = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        e2 = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        assert e1.id != e2.id

    def test_kind_is_enum_value(self) -> None:
        e = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        # use_enum_values=True — il campo è la stringa, non l'enum
        assert e.kind == "npc"

    def test_default_relations_empty(self) -> None:
        e = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        assert e.relations == []

    def test_default_narrative(self) -> None:
        e = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        assert e.narrative.description == ""
        assert e.narrative.secrets == []

    def test_serialization_round_trip(self) -> None:
        e = NPCEntity(
            meta=make_entity_meta(),
            identity=make_entity_identity("Brann"),
        )
        data = e.model_dump()
        e2 = NPCEntity.model_validate(data)
        assert e2.id == e.id
        assert e2.identity.name == "Brann"

    def test_json_serialization(self) -> None:
        e = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        json_str = e.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["kind"] == "npc"
        assert "id" in parsed


# ── NPCEntity ─────────────────────────────────────────────────────────────────

class TestNPCEntity:
    def test_default_kind(self) -> None:
        npc = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        assert npc.kind == EntityKind.NPC

    def test_behaviour_defaults(self) -> None:
        npc = NPCEntity(meta=make_entity_meta(), identity=make_entity_identity())
        assert npc.behaviour.personality_traits == []
        assert npc.behaviour.moral_alignment == 0.0

    def test_with_behaviour(self) -> None:
        behaviour = NPCBehaviour(
            personality_traits=["coraggioso", "impulsivo"],
            motivations=["proteggere la città"],
            moral_alignment=0.8,
        )
        npc = NPCEntity(
            meta=make_entity_meta(),
            identity=make_entity_identity("Capitano"),
            behaviour=behaviour,
        )
        assert "coraggioso" in npc.behaviour.personality_traits

    def test_physical_mechanical_dicts(self) -> None:
        npc = NPCEntity(
            meta=make_entity_meta(),
            identity=make_entity_identity(),
            physical={"hp": 30, "str": 14},
            mechanical={"weapon": "sword"},
        )
        assert npc.physical["hp"] == 30
        assert npc.mechanical["weapon"] == "sword"

    def test_round_trip_with_behaviour(self) -> None:
        npc = NPCEntity(
            meta=make_entity_meta(),
            identity=make_entity_identity("Kira"),
            behaviour=NPCBehaviour(personality_traits=["astuta"]),
        )
        data = npc.model_dump()
        npc2 = NPCEntity.model_validate(data)
        assert npc2.behaviour.personality_traits == ["astuta"]


# ── PlayerEntity ──────────────────────────────────────────────────────────────

class TestPlayerEntity:
    def test_default_kind(self) -> None:
        meta = EntityMeta(created_at=make_world_time(), created_by="player")
        identity = EntityIdentity(name="Elan")
        player = PlayerEntity(meta=meta, identity=identity)
        assert player.kind == EntityKind.PLAYER

    def test_narrative_is_player_narrative(self) -> None:
        meta = EntityMeta(created_at=make_world_time(), created_by="player")
        identity = EntityIdentity(name="Elan")
        player = PlayerEntity(meta=meta, identity=identity)
        assert isinstance(player.narrative, PlayerNarrative)
        assert player.narrative.choices_log == []

    def test_round_trip(self) -> None:
        meta = EntityMeta(created_at=make_world_time(), created_by="player")
        identity = EntityIdentity(name="Elan", tags=["hero"])
        player = PlayerEntity(meta=meta, identity=identity)
        data = player.model_dump()
        player2 = PlayerEntity.model_validate(data)
        assert player2.identity.name == "Elan"


# ── Relation ──────────────────────────────────────────────────────────────────

class TestRelation:
    def test_relation_creation(self) -> None:
        rel = Relation(
            target_id="npc_123",
            type=RelationType.ALLIED,
            strength=0.8,
            since=make_world_time(),
        )
        assert rel.target_id == "npc_123"
        assert rel.strength == 0.8

    def test_relation_in_entity(self) -> None:
        rel = Relation(
            target_id="npc_456",
            type=RelationType.RIVAL,
            strength=0.5,
            since=make_world_time(),
        )
        npc = NPCEntity(
            meta=make_entity_meta(),
            identity=make_entity_identity(),
            relations=[rel],
        )
        assert len(npc.relations) == 1
        assert npc.relations[0].target_id == "npc_456"
