"""Test per engine/world_clock.py: WorldClock, TimeScale, WORLD_TIME_COST."""

from __future__ import annotations

import pytest

from game_engine.engine.world_clock import (
    WORLD_TIME_COST,
    WORLD_UNITS_PER_DAY,
    TimeScale,
    WorldClock,
)
from game_engine.models.base import DayMoment, WorldTime


class TestWorldTimeCost:
    def test_rest_full_costs_one_day(self) -> None:
        """rest_full deve costare esattamente 1 giorno narrativo (20 world_units)."""
        assert WORLD_TIME_COST["rest_full"] == WORLD_UNITS_PER_DAY

    def test_instant_actions_cost_zero(self) -> None:
        assert WORLD_TIME_COST["player_action_quick"] == 0
        assert WORLD_TIME_COST["combat"] == 0

    def test_travel_costs(self) -> None:
        assert WORLD_TIME_COST["travel_short"] < WORLD_TIME_COST["travel_medium"]
        assert WORLD_TIME_COST["travel_medium"] < WORLD_TIME_COST["travel_long"]


class TestWorldClockTick:
    def test_advance_tick(self) -> None:
        clock = WorldClock()
        assert clock.tick.value == 0
        t1 = clock.advance_tick()
        assert t1.value == 1
        t2 = clock.advance_tick()
        assert t2.value == 2

    def test_tick_is_immutable(self) -> None:
        clock = WorldClock()
        t0 = clock.tick
        clock.advance_tick()
        assert clock.tick.value == 1
        assert t0.value == 0  # il vecchio riferimento non cambia


class TestAdvanceWorldTime:
    def test_rest_full_advances_one_day(self) -> None:
        """advance_world_time("rest_full") deve avanzare esattamente 1 giorno narrativo."""
        clock = WorldClock()
        initial_day = clock.world_time.to_absolute_days()
        clock.advance_world_time("rest_full")
        assert clock.world_time.to_absolute_days() == initial_day + 1

    def test_instant_action_does_not_advance(self) -> None:
        clock = WorldClock()
        initial_units = clock.world_units_total
        clock.advance_world_time("player_action_quick")
        assert clock.world_units_total == initial_units

    def test_combat_does_not_advance(self) -> None:
        clock = WorldClock()
        initial_units = clock.world_units_total
        clock.advance_world_time("combat")
        assert clock.world_units_total == initial_units

    def test_unknown_action_does_not_advance(self) -> None:
        clock = WorldClock()
        initial_units = clock.world_units_total
        clock.advance_world_time("nonexistent_action")
        assert clock.world_units_total == initial_units

    def test_travel_short_advances(self) -> None:
        clock = WorldClock()
        clock.advance_world_time("travel_short")
        assert clock.world_units_total == WORLD_TIME_COST["travel_short"]

    def test_multiple_actions_accumulate(self) -> None:
        clock = WorldClock()
        clock.advance_world_time("travel_short")   # 4
        clock.advance_world_time("rest_short")      # 4
        assert clock.world_units_total == 8

    def test_full_day_then_rest_advances_two_days(self) -> None:
        clock = WorldClock()
        clock.advance_world_time("rest_full")  # giorno 1
        clock.advance_world_time("rest_full")  # giorno 2
        assert clock.world_time.to_absolute_days() == 2


class TestAdvanceRealTime:
    def test_60_seconds_advances_2_world_units(self) -> None:
        """1 min reale = 30 min narrativi = 2 world_units."""
        clock = WorldClock()
        clock.advance_real_time(60.0)
        assert clock.world_units_total == 2

    def test_30_seconds_not_enough_for_one_unit(self) -> None:
        """30 sec reali = 1 world_unit, ma l'accumulo non supera 1 intero."""
        clock = WorldClock()
        clock.advance_real_time(30.0)
        # 30s * (2/60) = 1.0 world_unit → avanza
        assert clock.world_units_total >= 1

    def test_10_seconds_not_enough(self) -> None:
        """10 sec reali = 0.33 world_unit → nessun avanzamento."""
        clock = WorldClock()
        clock.advance_real_time(10.0)
        assert clock.world_units_total == 0

    def test_skip_mode_does_not_advance_real_time(self) -> None:
        clock = WorldClock()
        clock.scale = TimeScale.SKIP
        clock.advance_real_time(60.0)
        assert clock.world_units_total == 0

    def test_pause_mode_does_not_advance_real_time(self) -> None:
        clock = WorldClock()
        clock.scale = TimeScale.PAUSE
        clock.advance_real_time(3600.0)
        assert clock.world_units_total == 0


class TestPauseMode:
    def test_pause_blocks_advance_world_time(self) -> None:
        clock = WorldClock()
        clock.scale = TimeScale.PAUSE
        clock.advance_world_time("rest_full")
        assert clock.world_units_total == 0

    def test_pause_blocks_real_time(self) -> None:
        clock = WorldClock()
        clock.scale = TimeScale.PAUSE
        clock.advance_real_time(3600.0)
        assert clock.world_units_total == 0


class TestSkipMode:
    def test_start_skip_sets_scale(self) -> None:
        clock = WorldClock()
        clock.start_skip(target_world_day=10)
        assert clock.scale == TimeScale.SKIP

    def test_interrupt_skip_sets_pause(self) -> None:
        clock = WorldClock()
        clock.start_skip(target_world_day=10)
        clock.interrupt_skip()
        assert clock.scale == TimeScale.PAUSE


class TestWorldTimeRecalculation:
    def test_initial_world_time(self) -> None:
        clock = WorldClock()
        wt = clock.world_time
        assert wt.year == 0
        assert wt.season == "spring"
        assert wt.day == 1
        assert wt.moment == DayMoment.MORNING

    def test_20_units_advances_one_day(self) -> None:
        """20 world_units = 1 giorno narrativo completo."""
        clock = WorldClock()
        clock.advance_world_time("rest_full")  # 20 units
        wt = clock.world_time
        assert wt.to_absolute_days() == 1

    def test_season_rollover(self) -> None:
        """Dopo 90 giorni narrativi (90×20 = 1800 units) si cambia stagione."""
        clock = WorldClock()
        for _ in range(90):
            clock.advance_world_time("rest_full")
        assert clock.world_time.season == "summer"

    def test_year_rollover(self) -> None:
        """Dopo 360 giorni narrativi si passa all'anno 1."""
        clock = WorldClock()
        for _ in range(360):
            clock.advance_world_time("rest_full")
        assert clock.world_time.year == 1
        assert clock.world_time.season == "spring"

    def test_custom_initial_time(self) -> None:
        initial = WorldTime(year=2, season="winter", day=45, moment=DayMoment.NIGHT)
        clock = WorldClock(initial_time=initial)
        assert clock.world_time.year == 2
        assert clock.world_time.season == "winter"
