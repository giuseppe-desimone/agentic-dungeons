"""Test per engine/cooldown.py — CooldownTracker."""

from __future__ import annotations

import pytest

from game_engine.engine.cooldown import COOLDOWN_DAYS, CooldownTracker


class TestCooldownTracker:
    def test_not_on_cooldown_initially(self) -> None:
        tracker = CooldownTracker()
        assert not tracker.is_on_cooldown("npc_001", "attacked", current_world_day=0)

    def test_on_cooldown_immediately_after_set(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        assert tracker.is_on_cooldown("npc_001", "attacked", current_world_day=10)

    def test_on_cooldown_within_window(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        # Dopo 2 giorni (< 3) → ancora in cooldown
        assert tracker.is_on_cooldown("npc_001", "attacked", current_world_day=12)

    def test_on_cooldown_last_day(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        # Dopo 2 giorni (10+2=12, elapsed=2, 2 < 3) → in cooldown
        assert tracker.is_on_cooldown("npc_001", "attacked", current_world_day=12)

    def test_off_cooldown_after_expiry(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        # Dopo 3+ giorni → scaduto
        assert not tracker.is_on_cooldown("npc_001", "attacked", current_world_day=13)

    def test_off_cooldown_well_after_expiry(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        assert not tracker.is_on_cooldown("npc_001", "attacked", current_world_day=100)

    def test_different_verb_no_cooldown(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        # Verbo diverso → nessun cooldown
        assert not tracker.is_on_cooldown("npc_001", "declared_war", current_world_day=10)

    def test_different_entity_no_cooldown(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        # Entità diversa → nessun cooldown
        assert not tracker.is_on_cooldown("npc_002", "attacked", current_world_day=10)

    def test_custom_cooldown_days(self) -> None:
        tracker = CooldownTracker(cooldown_days=7)
        tracker.set_cooldown("npc_001", "attacked", world_day=0)
        assert tracker.is_on_cooldown("npc_001", "attacked", current_world_day=6)
        assert not tracker.is_on_cooldown("npc_001", "attacked", current_world_day=7)

    def test_clear_resets_all(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        tracker.set_cooldown("npc_002", "raided", world_day=10)
        tracker.clear()
        assert not tracker.is_on_cooldown("npc_001", "attacked", current_world_day=10)
        assert not tracker.is_on_cooldown("npc_002", "raided", current_world_day=10)

    def test_reset_cooldown_on_new_trigger(self) -> None:
        tracker = CooldownTracker()
        tracker.set_cooldown("npc_001", "attacked", world_day=0)
        # Scade al giorno 3
        assert not tracker.is_on_cooldown("npc_001", "attacked", current_world_day=3)
        # Nuova occorrenza al giorno 5
        tracker.set_cooldown("npc_001", "attacked", world_day=5)
        assert tracker.is_on_cooldown("npc_001", "attacked", current_world_day=6)

    def test_remaining_days_zero_when_not_set(self) -> None:
        tracker = CooldownTracker()
        assert tracker.remaining_days("npc_001", "attacked", current_world_day=0) == 0

    def test_remaining_days_correct(self) -> None:
        tracker = CooldownTracker(cooldown_days=3)
        tracker.set_cooldown("npc_001", "attacked", world_day=10)
        assert tracker.remaining_days("npc_001", "attacked", current_world_day=10) == 3
        assert tracker.remaining_days("npc_001", "attacked", current_world_day=11) == 2
        assert tracker.remaining_days("npc_001", "attacked", current_world_day=12) == 1
        assert tracker.remaining_days("npc_001", "attacked", current_world_day=13) == 0

    def test_default_cooldown_days_constant(self) -> None:
        assert COOLDOWN_DAYS == 3
        tracker = CooldownTracker()
        tracker.set_cooldown("x", "y", world_day=0)
        assert tracker.is_on_cooldown("x", "y", current_world_day=2)
        assert not tracker.is_on_cooldown("x", "y", current_world_day=3)
