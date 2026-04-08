"""Test suite per SnapshotManager e SaveManager (Fase 8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game_engine.engine.knowledge import KnowledgeUpdate, PlayerKnowledgeBase
from game_engine.engine.world_clock import WorldClock
from game_engine.engine.world_state import ScheduledEvent, WorldState
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
from game_engine.models.event import EventActor, EventVerb, EventVisibility, GameEvent
from game_engine.persistence.save_manager import SaveManager
from game_engine.persistence.snapshot import SnapshotManager


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_world_time(day: int = 5, moment: str = DayMoment.EVENING) -> WorldTime:
    return WorldTime(year=2, season="autumn", day=day, moment=moment)


def make_player() -> PlayerEntity:
    return PlayerEntity(
        id="player_001",
        meta=EntityMeta(created_at=make_world_time(), created_by="test", status=EntityStatus.ACTIVE),
        identity=EntityIdentity(name="Elan"),
        mechanical={"location_id": "loc_city", "level": 3, "xp": 250},
    )


def make_npc(npc_id: str = "npc_001", name: str = "Mira") -> NPCEntity:
    return NPCEntity(
        id=npc_id,
        meta=EntityMeta(created_at=make_world_time(), created_by="test", status=EntityStatus.ACTIVE),
        identity=EntityIdentity(name=name),
        mechanical={"location_id": "loc_city"},
        behaviour=NPCBehaviour(personality_traits=["curious"]),
    )


def make_event(verb: str = EventVerb.ATTACKED, day: int = 5) -> GameEvent:
    return GameEvent(
        tick=GameTick(10),
        world_time=make_world_time(day=day),
        type="conflict",
        verb=verb,
        emitter=EventActor(id="npc_001", kind=EntityKind.NPC, name="Mira"),
        visibility=EventVisibility(scope="regional"),
        payload={"location_id": "loc_city"},
    )


def make_world_state_with_data() -> WorldState:
    ws = WorldState()
    ws.add_entity(make_player())
    ws.add_entity(make_npc())
    ev = make_event()
    ws.append_event(ev)
    sched = ScheduledEvent(
        trigger_world_day=100,
        event_template={"verb": "declared_war"},
        created_at=make_world_time(),
        created_by_event_id=ev.id,
    )
    ws.schedule_event(sched)
    return ws


# ── SnapshotManager — WorldState ──────────────────────────────────────────────


class TestSnapshotManagerWorldState:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        ws = make_world_state_with_data()
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        assert path.exists()

        loaded = SnapshotManager.load_world_state(path)
        assert len(loaded.entity_store) == len(ws.entity_store)
        assert len(loaded.event_log) == len(ws.event_log)

    def test_entity_ids_preserved(self, tmp_path: Path):
        ws = make_world_state_with_data()
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        assert "player_001" in loaded.entity_store
        assert "npc_001" in loaded.entity_store

    def test_event_log_preserved(self, tmp_path: Path):
        ws = make_world_state_with_data()
        ev_id = ws.event_log[0].id
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        loaded_ids = {e.id for e in loaded.event_log}
        assert ev_id in loaded_ids

    def test_world_time_fields_preserved(self, tmp_path: Path):
        ws = make_world_state_with_data()
        original_wt = ws.event_log[0].world_time
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        loaded_wt = loaded.event_log[0].world_time
        assert loaded_wt.year == original_wt.year
        assert loaded_wt.season == original_wt.season
        assert loaded_wt.day == original_wt.day
        assert loaded_wt.moment == original_wt.moment

    def test_game_tick_value_preserved(self, tmp_path: Path):
        ws = make_world_state_with_data()
        original_tick = ws.event_log[0].tick.value
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        assert loaded.event_log[0].tick.value == original_tick

    def test_scheduled_events_preserved(self, tmp_path: Path):
        ws = make_world_state_with_data()
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        assert len(loaded.scheduled_events) == len(ws.scheduled_events)
        assert loaded.scheduled_events[0].trigger_world_day == 100

    def test_event_verb_preserved(self, tmp_path: Path):
        ws = make_world_state_with_data()
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        assert loaded.event_log[0].verb == EventVerb.ATTACKED

    def test_load_nonexistent_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            SnapshotManager.load_world_state(tmp_path / "missing.msgpack")

    def test_multiple_events_preserved(self, tmp_path: Path):
        ws = WorldState()
        for i in range(5):
            ev = make_event(day=i + 1)
            ws.append_event(ev)
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        assert len(loaded.event_log) == 5

    def test_payload_dict_preserved(self, tmp_path: Path):
        ws = WorldState()
        ev = make_event()
        ws.append_event(ev)
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws, path)
        loaded = SnapshotManager.load_world_state(path)

        assert loaded.event_log[0].payload["location_id"] == "loc_city"

    def test_overwrite_on_second_save(self, tmp_path: Path):
        ws1 = WorldState()
        ws1.append_event(make_event())
        path = tmp_path / "state.msgpack"

        SnapshotManager.save_world_state(ws1, path)

        ws2 = WorldState()
        for i in range(3):
            ws2.append_event(make_event(day=i + 1))
        SnapshotManager.save_world_state(ws2, path)

        loaded = SnapshotManager.load_world_state(path)
        assert len(loaded.event_log) == 3


# ── SnapshotManager — PlayerKnowledgeBase ─────────────────────────────────────


class TestSnapshotManagerKnowledgeBase:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        kb = PlayerKnowledgeBase(player_id="player_001")
        ev = make_event()
        update = KnowledgeUpdate(event_id=ev.id, how_learned="direct_witness", certainty=1.0)
        kb.apply_update(update, ev, make_world_time())
        path = tmp_path / "knowledge.msgpack"

        SnapshotManager.save_knowledge_base(kb, path)
        loaded = SnapshotManager.load_knowledge_base(path)

        assert loaded.player_id == "player_001"
        assert len(loaded.known_events) == 1

    def test_known_event_ids_preserved(self, tmp_path: Path):
        kb = PlayerKnowledgeBase(player_id="player_001")
        ev = make_event()
        update = KnowledgeUpdate(event_id=ev.id, how_learned="direct_witness", certainty=1.0)
        kb.apply_update(update, ev, make_world_time())
        path = tmp_path / "knowledge.msgpack"

        SnapshotManager.save_knowledge_base(kb, path)
        loaded = SnapshotManager.load_knowledge_base(path)

        assert loaded.known_events[0].event_id == ev.id

    def test_active_rumors_preserved(self, tmp_path: Path):
        kb = PlayerKnowledgeBase(player_id="player_001")
        ev = make_event(verb=EventVerb.RUMORED)
        update = KnowledgeUpdate(event_id=ev.id, how_learned="rumor", certainty=0.4)
        kb.apply_update(update, ev, make_world_time())
        path = tmp_path / "knowledge.msgpack"

        SnapshotManager.save_knowledge_base(kb, path)
        loaded = SnapshotManager.load_knowledge_base(path)

        assert ev.id in loaded.active_rumors

    def test_known_entities_preserved(self, tmp_path: Path):
        kb = PlayerKnowledgeBase(player_id="player_001")
        ev = make_event()
        update = KnowledgeUpdate(event_id=ev.id, how_learned="informed", certainty=0.9)
        kb.apply_update(update, ev, make_world_time())
        path = tmp_path / "knowledge.msgpack"

        SnapshotManager.save_knowledge_base(kb, path)
        loaded = SnapshotManager.load_knowledge_base(path)

        assert "npc_001" in loaded.known_entities

    def test_certainty_preserved(self, tmp_path: Path):
        kb = PlayerKnowledgeBase(player_id="player_001")
        ev = make_event()
        update = KnowledgeUpdate(event_id=ev.id, how_learned="informed", certainty=0.75)
        kb.apply_update(update, ev, make_world_time())
        path = tmp_path / "knowledge.msgpack"

        SnapshotManager.save_knowledge_base(kb, path)
        loaded = SnapshotManager.load_knowledge_base(path)

        assert loaded.known_events[0].certainty == pytest.approx(0.75)

    def test_empty_kb_roundtrip(self, tmp_path: Path):
        kb = PlayerKnowledgeBase(player_id="player_empty")
        path = tmp_path / "knowledge.msgpack"

        SnapshotManager.save_knowledge_base(kb, path)
        loaded = SnapshotManager.load_knowledge_base(path)

        assert loaded.player_id == "player_empty"
        assert len(loaded.known_events) == 0

    def test_load_nonexistent_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            SnapshotManager.load_knowledge_base(tmp_path / "missing.msgpack")


# ── SaveManager ───────────────────────────────────────────────────────────────


class TestSaveManager:
    def _make_save_data(self):
        ws = make_world_state_with_data()
        kb = PlayerKnowledgeBase(player_id="player_001")
        ev = ws.event_log[0]
        update = KnowledgeUpdate(event_id=ev.id, how_learned="direct_witness", certainty=1.0)
        kb.apply_update(update, ev, make_world_time())
        config = {"seed": 42, "flow_ratio": 30, "world_name": "Aethoria"}
        return ws, kb, config

    def test_save_creates_files(self, tmp_path: Path):
        ws, kb, config = self._make_save_data()
        sm = SaveManager(save_dir=tmp_path)
        sm.save(ws, kb, config)

        assert (tmp_path / "state.msgpack").exists()
        assert (tmp_path / "knowledge.msgpack").exists()
        assert (tmp_path / "config.json").exists()

    def test_save_load_roundtrip_entities(self, tmp_path: Path):
        ws, kb, config = self._make_save_data()
        sm = SaveManager(save_dir=tmp_path)
        sm.save(ws, kb, config)

        loaded_ws, loaded_kb, loaded_config = sm.load()

        assert len(loaded_ws.entity_store) == len(ws.entity_store)
        assert len(loaded_ws.event_log) == len(ws.event_log)

    def test_save_load_roundtrip_kb(self, tmp_path: Path):
        ws, kb, config = self._make_save_data()
        sm = SaveManager(save_dir=tmp_path)
        sm.save(ws, kb, config)

        _, loaded_kb, _ = sm.load()

        assert loaded_kb.player_id == kb.player_id
        assert len(loaded_kb.known_events) == len(kb.known_events)

    def test_save_load_config(self, tmp_path: Path):
        ws, kb, config = self._make_save_data()
        sm = SaveManager(save_dir=tmp_path)
        sm.save(ws, kb, config)

        _, _, loaded_config = sm.load()

        assert loaded_config["seed"] == 42
        assert loaded_config["flow_ratio"] == 30
        assert loaded_config["world_name"] == "Aethoria"

    def test_save_exists_false_on_empty_dir(self, tmp_path: Path):
        sm = SaveManager(save_dir=tmp_path)
        assert sm.save_exists() is False

    def test_save_exists_true_after_save(self, tmp_path: Path):
        ws, kb, config = self._make_save_data()
        sm = SaveManager(save_dir=tmp_path)
        sm.save(ws, kb, config)

        assert sm.save_exists() is True

    def test_double_save_overwrites(self, tmp_path: Path):
        ws1, kb1, config1 = self._make_save_data()
        sm = SaveManager(save_dir=tmp_path)
        sm.save(ws1, kb1, config1)

        # Secondo save con config diversa
        ws2, kb2, _ = self._make_save_data()
        config2 = {"seed": 999, "flow_ratio": 60, "world_name": "Neverland"}
        sm.save(ws2, kb2, config2)

        _, _, loaded_config = sm.load()
        assert loaded_config["seed"] == 999
        assert loaded_config["world_name"] == "Neverland"

    def test_load_missing_state_raises(self, tmp_path: Path):
        sm = SaveManager(save_dir=tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError):
            sm.load()

    def test_creates_directory_if_missing(self, tmp_path: Path):
        save_dir = tmp_path / "new_save" / "slot1"
        ws, kb, config = self._make_save_data()
        sm = SaveManager(save_dir=save_dir)
        sm.save(ws, kb, config)

        assert save_dir.exists()
        assert (save_dir / "state.msgpack").exists()

    def test_db_path_property(self, tmp_path: Path):
        sm = SaveManager(save_dir=tmp_path)
        assert sm.db_path == tmp_path / "world.db"

    def test_config_is_valid_json(self, tmp_path: Path):
        ws, kb, config = self._make_save_data()
        sm = SaveManager(save_dir=tmp_path)
        sm.save(ws, kb, config)

        config_text = (tmp_path / "config.json").read_text()
        parsed = json.loads(config_text)
        assert parsed["seed"] == 42
