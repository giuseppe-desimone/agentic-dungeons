"""Test per persistence/event_log.py — EventLogger SQLite async."""

from __future__ import annotations

import pytest

from game_engine.models.base import DayMoment, EntityKind, GameTick, WorldTime
from game_engine.models.event import EventActor, EventVerb, EventVisibility, GameEvent
from game_engine.persistence.event_log import SCHEMA_VERSION, EventLogger


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_world_time(day: int = 1) -> WorldTime:
    return WorldTime(year=0, season="spring", day=day, moment=DayMoment.MORNING)


def make_event(
    tick_val: int = 0,
    day: int = 1,
    verb: str = EventVerb.ATTACKED,
    emitter_id: str = "npc_001",
) -> GameEvent:
    return GameEvent(
        tick=GameTick(tick_val),
        world_time=make_world_time(day),
        type="conflict",
        verb=verb,
        emitter=EventActor(id=emitter_id, kind=EntityKind.NPC, name="Aldric"),
        visibility=EventVisibility(scope="local", known_to=[]),
        payload={"location_id": "loc_tavern"},
    )


async def fresh_logger() -> EventLogger:
    """Crea un EventLogger in-memory con schema inizializzato e connessione aperta."""
    log = EventLogger(":memory:")
    await log.open()
    await log.init_schema()
    return log


# ── Schema initialization ──────────────────────────────────────────────────────

class TestInitSchema:
    async def test_init_creates_tables(self) -> None:
        log = await fresh_logger()
        # Se init_schema non lancia → le tabelle esistono

    async def test_init_is_idempotent(self) -> None:
        log = await fresh_logger()
        await log.init_schema()  # seconda chiamata → nessun errore

    async def test_schema_version_set(self) -> None:
        log = await fresh_logger()
        version = await log.get_schema_version()
        assert version == SCHEMA_VERSION


# ── append ────────────────────────────────────────────────────────────────────

class TestAppend:
    async def test_append_single_event(self) -> None:
        log = await fresh_logger()
        event = make_event()
        await log.append(event)
        rows = await log.query_since(world_day=0)
        assert len(rows) == 1
        assert rows[0]["id"] == event.id

    async def test_append_preserves_fields(self) -> None:
        log = await fresh_logger()
        event = make_event(tick_val=5, day=3, verb=EventVerb.TRADED, emitter_id="npc_merchant")
        await log.append(event)
        rows = await log.query_since(world_day=0)
        r = rows[0]
        assert r["tick"] == 5
        assert r["world_day"] == 2  # day=3 → absolute=2 (day-1)
        assert r["verb"] == "traded"
        assert r["emitter_id"] == "npc_merchant"
        assert r["visibility_scope"] == "local"

    async def test_append_idempotent_same_id(self) -> None:
        """Doppio append stesso id → INSERT OR IGNORE, nessun errore, 1 sola riga."""
        log = await fresh_logger()
        event = make_event()
        await log.append(event)
        await log.append(event)  # secondo append dello stesso evento
        rows = await log.query_since(world_day=0)
        assert len(rows) == 1

    async def test_append_multiple_events(self) -> None:
        log = await fresh_logger()
        for i in range(5):
            await log.append(make_event(tick_val=i, day=i + 1))
        rows = await log.query_since(world_day=0)
        assert len(rows) == 5

    async def test_append_with_target(self) -> None:
        from game_engine.models.event import EventActor
        log = await fresh_logger()
        event = make_event()
        # evento con target
        event2 = GameEvent(
            tick=GameTick(1),
            world_time=make_world_time(),
            type="conflict",
            verb=EventVerb.ATTACKED,
            emitter=EventActor(id="npc_001", kind=EntityKind.NPC, name="Aldric"),
            target=EventActor(id="player_1", kind=EntityKind.PLAYER, name="Elan"),
        )
        await log.append(event2)
        rows = await log.query_since(world_day=0)
        assert rows[0]["target_id"] == "player_1"
        assert rows[0]["target_name"] == "Elan"


# ── query_since ───────────────────────────────────────────────────────────────

class TestQuerySince:
    async def test_filter_by_world_day(self) -> None:
        log = await fresh_logger()
        for day in [1, 3, 5, 8]:
            await log.append(make_event(tick_val=day, day=day))
        # world_day=4 (assoluto) = day=5 in poi
        rows = await log.query_since(world_day=4)
        # day=5 → abs=4, day=8 → abs=7
        assert len(rows) == 2

    async def test_empty_result_before_all_events(self) -> None:
        log = await fresh_logger()
        await log.append(make_event(day=1))
        rows = await log.query_since(world_day=100)
        assert rows == []

    async def test_returns_all_if_day_zero(self) -> None:
        log = await fresh_logger()
        for i in range(3):
            await log.append(make_event(tick_val=i, day=i + 1))
        rows = await log.query_since(world_day=0)
        assert len(rows) == 3

    async def test_ordered_by_world_day_and_tick(self) -> None:
        log = await fresh_logger()
        await log.append(make_event(tick_val=2, day=3))
        await log.append(make_event(tick_val=1, day=1))
        await log.append(make_event(tick_val=3, day=2))
        rows = await log.query_since(world_day=0)
        days = [r["world_day"] for r in rows]
        assert days == sorted(days)


# ── mark_known + query_since con player_id ────────────────────────────────────

class TestMarkKnown:
    async def test_mark_known_filters_by_player(self) -> None:
        log = await fresh_logger()
        event1 = make_event(tick_val=1, day=1, emitter_id="npc_a")
        event2 = make_event(tick_val=2, day=2, emitter_id="npc_b")
        await log.append(event1)
        await log.append(event2)
        # Solo event1 è noto al player_1
        await log.mark_known("player_1", event1.id, "direct_witness", 1.0, 0)

        rows = await log.query_since(world_day=0, player_id="player_1")
        assert len(rows) == 1
        assert rows[0]["id"] == event1.id

    async def test_mark_known_preserves_metadata(self) -> None:
        log = await fresh_logger()
        event = make_event()
        await log.append(event)
        await log.mark_known("player_1", event.id, "rumor", 0.4, 5)

        rows = await log.query_since(world_day=0, player_id="player_1")
        assert rows[0]["how_learned"] == "rumor"
        assert rows[0]["certainty"] == pytest.approx(0.4)
        assert rows[0]["learned_at_day"] == 5

    async def test_query_without_player_returns_all(self) -> None:
        log = await fresh_logger()
        event1 = make_event(tick_val=1, day=1)
        event2 = make_event(tick_val=2, day=2)
        await log.append(event1)
        await log.append(event2)
        await log.mark_known("player_1", event1.id, "informed", 0.9, 0)

        # Senza player_id → tutti gli eventi
        rows = await log.query_since(world_day=0)
        assert len(rows) == 2

    async def test_mark_known_idempotent(self) -> None:
        """INSERT OR REPLACE → doppio mark_known → 1 sola riga."""
        log = await fresh_logger()
        event = make_event()
        await log.append(event)
        await log.mark_known("player_1", event.id, "rumor", 0.4, 0)
        await log.mark_known("player_1", event.id, "informed", 0.9, 1)  # override
        rows = await log.query_since(world_day=0, player_id="player_1")
        assert len(rows) == 1
        assert rows[0]["how_learned"] == "informed"


# ── migrate_if_needed ─────────────────────────────────────────────────────────

class TestMigration:
    async def test_migrate_on_fresh_db(self) -> None:
        """migrate_if_needed su DB vuoto → inizializza schema."""
        log = EventLogger(":memory:")
        await log.open()
        await log.migrate_if_needed()
        version = await log.get_schema_version()
        assert version == SCHEMA_VERSION
        await log.close()

    async def test_migrate_on_existing_schema_no_error(self) -> None:
        log = await fresh_logger()
        await log.migrate_if_needed()  # schema già aggiornato → nessun errore
        await log.close()

    async def test_get_schema_version_zero_on_empty_db(self) -> None:
        log = EventLogger(":memory:")
        await log.open()
        # Schema non inizializzato → 0
        version = await log.get_schema_version()
        assert version == 0
        await log.close()
