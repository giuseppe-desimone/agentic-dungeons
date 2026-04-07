"""Test per models/base.py: GameTick, WorldTime, DayMoment, enums."""

from __future__ import annotations

import pytest

from game_engine.models.base import (
    DayMoment,
    EntityKind,
    EntityStatus,
    GameTick,
    LocationMood,
    RelationType,
    WorldTime,
)


# ── GameTick ──────────────────────────────────────────────────────────────────

class TestGameTick:
    def test_default_value(self) -> None:
        tick = GameTick()
        assert tick.value == 0

    def test_add_creates_new_instance(self) -> None:
        tick = GameTick(0)
        tick2 = tick + 3
        assert tick2.value == 3
        assert tick.value == 0  # immutabilità

    def test_add_is_cumulative(self) -> None:
        tick = GameTick(5)
        assert (tick + 1).value == 6
        assert (tick + 10).value == 15

    def test_lt_ordering(self) -> None:
        assert GameTick(0) < GameTick(1)
        assert not GameTick(5) < GameTick(5)
        assert not GameTick(6) < GameTick(5)

    def test_frozen(self) -> None:
        tick = GameTick(0)
        with pytest.raises((AttributeError, TypeError)):
            tick.value = 99  # type: ignore[misc]


# ── WorldTime.to_absolute_days ────────────────────────────────────────────────

class TestWorldTimeAbsoluteDays:
    def test_origin(self) -> None:
        """Anno 0, spring, giorno 1 = 0 giorni assoluti."""
        wt = WorldTime(year=0, season="spring", day=1, moment=DayMoment.MORNING)
        assert wt.to_absolute_days() == 0

    def test_spring_day_2(self) -> None:
        wt = WorldTime(year=0, season="spring", day=2)
        assert wt.to_absolute_days() == 1

    def test_summer_start(self) -> None:
        """Inizio estate = giorno 90 (spring 90 giorni)."""
        wt = WorldTime(year=0, season="summer", day=1)
        assert wt.to_absolute_days() == 90

    def test_autumn_start(self) -> None:
        wt = WorldTime(year=0, season="autumn", day=1)
        assert wt.to_absolute_days() == 180

    def test_winter_start(self) -> None:
        wt = WorldTime(year=0, season="winter", day=1)
        assert wt.to_absolute_days() == 270

    def test_year_boundary(self) -> None:
        """Anno 1, spring, giorno 1 = 360 giorni assoluti."""
        wt = WorldTime(year=1, season="spring", day=1)
        assert wt.to_absolute_days() == 360

    def test_year_1_summer_day_1(self) -> None:
        """Anno 1, summer, giorno 1 = 360 + 90 = 450."""
        wt = WorldTime(year=1, season="summer", day=1)
        assert wt.to_absolute_days() == 450


# ── WorldTime ordering ────────────────────────────────────────────────────────

class TestWorldTimeOrdering:
    def test_lt_by_year(self) -> None:
        wt0 = WorldTime(year=0, season="spring", day=1)
        wt1 = WorldTime(year=1, season="spring", day=1)
        assert wt0 < wt1
        assert not wt1 < wt0

    def test_lt_by_season(self) -> None:
        wt_spring = WorldTime(year=0, season="spring", day=1)
        wt_summer = WorldTime(year=0, season="summer", day=1)
        assert wt_spring < wt_summer

    def test_lt_by_day(self) -> None:
        wt1 = WorldTime(year=0, season="spring", day=1)
        wt2 = WorldTime(year=0, season="spring", day=2)
        assert wt1 < wt2

    def test_lt_by_moment_same_day(self) -> None:
        wt_dawn = WorldTime(year=0, season="spring", day=1, moment=DayMoment.DAWN)
        wt_eve = WorldTime(year=0, season="spring", day=1, moment=DayMoment.EVENING)
        assert wt_dawn < wt_eve

    def test_not_lt_equal(self) -> None:
        wt = WorldTime(year=0, season="spring", day=1, moment=DayMoment.MORNING)
        assert not wt < wt

    def test_le_equal(self) -> None:
        wt = WorldTime(year=0, season="spring", day=1)
        assert wt <= wt

    def test_le_less(self) -> None:
        wt1 = WorldTime(year=0, season="spring", day=1)
        wt2 = WorldTime(year=0, season="spring", day=2)
        assert wt1 <= wt2

    def test_frozen(self) -> None:
        wt = WorldTime()
        with pytest.raises((AttributeError, TypeError)):
            wt.year = 99  # type: ignore[misc]


# ── DayMoment ordering ────────────────────────────────────────────────────────

class TestDayMoment:
    def test_order_is_dawn_to_night(self) -> None:
        moments = list(DayMoment)
        assert moments[0] == DayMoment.DAWN
        assert moments[-1] == DayMoment.NIGHT

    def test_count(self) -> None:
        assert len(list(DayMoment)) == 5


# ── Enums presenza valori ─────────────────────────────────────────────────────

class TestEnums:
    def test_entity_kind_values(self) -> None:
        kinds = {k.value for k in EntityKind}
        assert "npc" in kinds
        assert "player" in kinds
        assert "faction" in kinds

    def test_entity_status_legendary(self) -> None:
        assert EntityStatus.LEGENDARY == "legendary"

    def test_relation_type(self) -> None:
        assert RelationType.MEMBER_OF == "member_of"

    def test_location_mood(self) -> None:
        assert LocationMood.WAR_TORN == "war-torn"
