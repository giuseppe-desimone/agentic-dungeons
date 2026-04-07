"""Test suite per i modelli PlayerIntent, ActiveInteraction, SkipSession (Fase 6)."""

from __future__ import annotations

import pytest

from game_engine.models.base import DayMoment, WorldTime
from game_engine.models.intent import ActiveInteraction, PlayerIntent, SkipSession


def make_world_time(day: int = 1, moment: str = DayMoment.MORNING) -> WorldTime:
    return WorldTime(year=1, season="spring", day=day, moment=moment)


# ── PlayerIntent ──────────────────────────────────────────────────────────────


class TestPlayerIntent:
    def test_default_status_is_pending(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
        )
        assert intent.status == "pending"

    def test_is_active_for_pending(self):
        intent = PlayerIntent(
            action_id="travel_short",
            scheduled_at=make_world_time(),
            estimated_duration_units=4,
            completes_at_world_day=1,
            status="pending",
        )
        assert intent.is_active() is True

    def test_is_active_for_in_progress(self):
        intent = PlayerIntent(
            action_id="travel_short",
            scheduled_at=make_world_time(),
            estimated_duration_units=4,
            completes_at_world_day=1,
            status="in_progress",
        )
        assert intent.is_active() is True

    def test_is_not_active_for_completed(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
            status="completed",
        )
        assert intent.is_active() is False

    def test_is_terminal_for_completed(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
            status="completed",
        )
        assert intent.is_terminal() is True

    def test_is_terminal_for_interrupted(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
            status="interrupted",
            interrupt_event_id="evt_001",
        )
        assert intent.is_terminal() is True

    def test_is_terminal_for_cancelled(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
            status="cancelled",
        )
        assert intent.is_terminal() is True

    def test_is_not_terminal_for_pending(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
            status="pending",
        )
        assert intent.is_terminal() is False

    def test_interrupt_event_id_stored(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
            status="interrupted",
            interrupt_event_id="evt_xyz",
        )
        assert intent.interrupt_event_id == "evt_xyz"

    def test_unique_ids(self):
        i1 = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
        )
        i2 = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
        )
        assert i1.id != i2.id

    def test_target_id_optional(self):
        intent = PlayerIntent(
            action_id="rest_full",
            scheduled_at=make_world_time(),
            estimated_duration_units=20,
            completes_at_world_day=2,
        )
        assert intent.target_id is None

    def test_payload_stored(self):
        intent = PlayerIntent(
            action_id="travel_short",
            target_id="loc_market",
            payload={"reason": "shopping"},
            scheduled_at=make_world_time(),
            estimated_duration_units=4,
            completes_at_world_day=1,
        )
        assert intent.payload["reason"] == "shopping"


# ── ActiveInteraction ─────────────────────────────────────────────────────────


class TestActiveInteraction:
    def test_default_open_to_intrusion(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan", "npc_mira"],
            location_id="loc_tavern",
        )
        assert interaction.open_to_intrusion is True

    def test_closed_to_intrusion(self):
        interaction = ActiveInteraction(
            type="ritual",
            participants=["player_elan"],
            location_id="loc_shrine",
            open_to_intrusion=False,
        )
        assert interaction.open_to_intrusion is False

    def test_is_not_suspended_initially(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan", "npc_mira"],
            location_id="loc_tavern",
        )
        assert interaction.is_suspended() is False

    def test_is_suspended_after_setting_suspended_at(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan"],
            location_id="loc_tavern",
            suspended_at=make_world_time(day=3),
        )
        assert interaction.is_suspended() is True

    def test_expires_at_world_day_none_never_expires(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan"],
            location_id="loc_tavern",
        )
        assert interaction.is_expired(current_world_day=999) is False

    def test_expires_when_day_reached(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan", "npc_mira"],
            location_id="loc_tavern",
            expires_at_world_day=10,
        )
        assert interaction.is_expired(current_world_day=10) is True

    def test_not_expired_before_day(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan", "npc_mira"],
            location_id="loc_tavern",
            expires_at_world_day=10,
        )
        assert interaction.is_expired(current_world_day=9) is False

    def test_state_stored(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan"],
            location_id="loc_tavern",
            state={"topic": "guerra", "turn": 2},
        )
        assert interaction.state["topic"] == "guerra"

    def test_resumable_default_true(self):
        interaction = ActiveInteraction(
            type="dialogue",
            participants=["player_elan"],
            location_id="loc_tavern",
        )
        assert interaction.resumable is True


# ── SkipSession ───────────────────────────────────────────────────────────────


class TestSkipSession:
    def test_not_interrupted_initially(self):
        session = SkipSession(
            target_world_day=20,
            started_at_world_day=5,
        )
        assert session.is_interrupted() is False

    def test_interrupted_when_interrupted_at_set(self):
        session = SkipSession(
            target_world_day=20,
            started_at_world_day=5,
            interrupted_at=make_world_time(day=10),
            interruption_event_id="evt_battle",
        )
        assert session.is_interrupted() is True

    def test_interruption_event_id_stored(self):
        session = SkipSession(
            target_world_day=20,
            started_at_world_day=5,
            interrupted_at=make_world_time(day=10),
            interruption_event_id="evt_battle",
        )
        assert session.interruption_event_id == "evt_battle"

    def test_days_skipped_calculation(self):
        session = SkipSession(
            target_world_day=20,
            started_at_world_day=5,
        )
        assert session.days_skipped(current_world_day=12) == 7

    def test_events_accumulated_empty_initially(self):
        session = SkipSession(
            target_world_day=20,
            started_at_world_day=5,
        )
        assert session.events_accumulated == []

    def test_events_accumulated_stored(self):
        session = SkipSession(
            target_world_day=20,
            started_at_world_day=5,
            events_accumulated=["evt_001", "evt_002"],
        )
        assert len(session.events_accumulated) == 2

    def test_days_skipped_zero_at_start(self):
        session = SkipSession(
            target_world_day=20,
            started_at_world_day=5,
        )
        assert session.days_skipped(current_world_day=5) == 0
