"""Test suite per ActionFilterEngine, IntentScheduler, InteractionManager (Fase 6)."""

from __future__ import annotations

import pytest

from game_engine.engine.action import (
    ActionFilterEngine,
    IntentScheduler,
    InteractionManager,
    PlayerAction,
)
from game_engine.engine.knowledge import KnowledgeUpdate, PlayerKnowledgeBase
from game_engine.engine.world_clock import WORLD_TIME_COST, WORLD_UNITS_PER_DAY, WorldClock
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
from game_engine.models.event import EventActor, EventVerb, EventVisibility, GameEvent
from game_engine.models.intent import ActiveInteraction, PlayerIntent


# ── Fixtures ──────────────────────────────────────────────────────────────────


def make_world_time(day: int = 1, moment: str = DayMoment.MORNING) -> WorldTime:
    return WorldTime(year=1, season="spring", day=day, moment=moment)


def make_player(location: str = "loc_tavern") -> PlayerEntity:
    return PlayerEntity(
        id="player_elan",
        meta=EntityMeta(created_at=make_world_time(), created_by="test", status=EntityStatus.ACTIVE),
        identity=EntityIdentity(name="Elan"),
        mechanical={"location_id": location},
    )


def make_npc(npc_id: str, name: str, location: str = "loc_tavern") -> NPCEntity:
    return NPCEntity(
        id=npc_id,
        meta=EntityMeta(created_at=make_world_time(), created_by="test", status=EntityStatus.ACTIVE),
        identity=EntityIdentity(name=name),
        mechanical={"location_id": location},
        behaviour=NPCBehaviour(),
    )


def make_event(
    verb: str,
    location: str = "loc_tavern",
    day: int = 1,
) -> GameEvent:
    return GameEvent(
        tick=GameTick(1),
        world_time=make_world_time(day=day),
        type="conflict",
        verb=verb,
        emitter=EventActor(id="npc_001", kind=EntityKind.NPC, name="NPC Test"),
        visibility=EventVisibility(scope="local"),
        payload={"location_id": location},
    )


# ── PlayerAction ──────────────────────────────────────────────────────────────


class TestPlayerAction:
    def test_create_action(self):
        action = PlayerAction(
            label="Guarda intorno",
            action_type="player_action_quick",
            world_time_cost=0,
        )
        assert action.label == "Guarda intorno"
        assert action.world_time_cost == 0

    def test_action_with_target(self):
        action = PlayerAction(
            label="Parla con Mira",
            action_type="player_action_quick",
            world_time_cost=0,
            target_id="npc_mira",
        )
        assert action.target_id == "npc_mira"

    def test_unique_ids(self):
        a1 = PlayerAction(
            label="A", action_type="player_action_quick", world_time_cost=0
        )
        a2 = PlayerAction(
            label="A", action_type="player_action_quick", world_time_cost=0
        )
        assert a1.id != a2.id


# ── ActionFilterEngine ────────────────────────────────────────────────────────


class TestActionFilterEngine:
    def test_menu_contains_base_actions(self):
        ws = WorldState()
        player = make_player()
        ws.add_entity(player)
        clock = WorldClock()
        engine = ActionFilterEngine()

        menu = engine.build_menu(ws, player, clock)

        labels = [a.label for a in menu]
        assert any("Guarda" in lbl for lbl in labels)
        assert any("Aspetta" in lbl for lbl in labels)

    def test_menu_contains_rest_actions(self):
        ws = WorldState()
        player = make_player()
        ws.add_entity(player)
        clock = WorldClock()
        engine = ActionFilterEngine()

        menu = engine.build_menu(ws, player, clock)
        labels = [a.label for a in menu]
        assert any("Riposa" in lbl for lbl in labels)

    def test_npc_in_location_adds_contextual_actions(self):
        ws = WorldState()
        player = make_player(location="loc_tavern")
        npc = make_npc("npc_mira", "Lady Mira", "loc_tavern")
        ws.add_entity(player)
        ws.add_entity(npc)
        clock = WorldClock()
        engine = ActionFilterEngine()

        menu = engine.build_menu(ws, player, clock)
        labels = [a.label for a in menu]

        assert any("Lady Mira" in lbl for lbl in labels)

    def test_npc_in_other_location_no_contextual_actions(self):
        ws = WorldState()
        player = make_player(location="loc_tavern")
        npc = make_npc("npc_aldric", "Lord Aldric", "loc_fort")
        ws.add_entity(player)
        ws.add_entity(npc)
        clock = WorldClock()
        engine = ActionFilterEngine()

        menu = engine.build_menu(ws, player, clock)
        labels = [a.label for a in menu]

        assert not any("Lord Aldric" in lbl for lbl in labels)

    def test_pause_mode_only_immediate_actions(self):
        from game_engine.engine.world_clock import TimeScale

        ws = WorldState()
        player = make_player()
        ws.add_entity(player)
        clock = WorldClock()
        clock.scale = TimeScale.PAUSE
        engine = ActionFilterEngine()

        menu = engine.build_menu(ws, player, clock)

        # In PAUSE: solo azioni con cost == 0
        for action in menu:
            assert action.world_time_cost == 0, f"Azione '{action.label}' ha cost > 0 in PAUSE"

    def test_flow_mode_includes_costly_actions(self):
        ws = WorldState()
        player = make_player()
        ws.add_entity(player)
        clock = WorldClock()  # default FLOW
        engine = ActionFilterEngine()

        menu = engine.build_menu(ws, player, clock)

        # In FLOW: devono esserci azioni con cost > 0
        costly = [a for a in menu if a.world_time_cost > 0]
        assert len(costly) > 0


# ── IntentScheduler ───────────────────────────────────────────────────────────


class TestIntentScheduler:
    def test_schedule_creates_pending_intent(self):
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Riposa",
            action_type="rest_full",
            world_time_cost=WORLD_TIME_COST["rest_full"],
        )
        intent = scheduler.schedule(action, clock)

        assert intent.status == "pending"
        assert intent.action_id == "rest_full"

    def test_schedule_cost_0_still_creates_intent(self):
        """cost=0 è gestito da ActionFilterEngine (immediato), ma lo scheduler può crearlo."""
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Guarda",
            action_type="player_action_quick",
            world_time_cost=0,
        )
        intent = scheduler.schedule(action, clock)
        # completes_at_world_day = current_day + max(1, 0 // 20) = current_day + 1
        assert intent.completes_at_world_day >= clock.world_time.to_absolute_days()

    def test_schedule_rest_full_completes_in_1_day(self):
        """rest_full costa 20 world_units = 1 giorno narrativo."""
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Riposa (notte)",
            action_type="rest_full",
            world_time_cost=WORLD_TIME_COST["rest_full"],
        )
        intent = scheduler.schedule(action, clock)

        current_day = clock.world_time.to_absolute_days()
        expected_duration = WORLD_TIME_COST["rest_full"] // WORLD_UNITS_PER_DAY
        assert intent.completes_at_world_day == current_day + expected_duration

    def test_is_completed_when_day_reached(self):
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Riposa",
            action_type="rest_full",
            world_time_cost=WORLD_TIME_COST["rest_full"],
        )
        intent = scheduler.schedule(action, clock)

        # Avanza il tempo fino al giorno di completamento
        clock.advance_world_time("rest_full")

        assert scheduler.is_completed(intent, clock) is True

    def test_is_not_completed_before_day(self):
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Viaggio lungo",
            action_type="travel_long",
            world_time_cost=WORLD_TIME_COST["travel_long"],
        )
        intent = scheduler.schedule(action, clock)

        # Non avanziamo il tempo → non completato
        assert scheduler.is_completed(intent, clock) is False

    def test_interrupt_sets_status(self):
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Riposa",
            action_type="rest_full",
            world_time_cost=WORLD_TIME_COST["rest_full"],
        )
        intent = scheduler.schedule(action, clock)
        interrupted = scheduler.interrupt(intent, event_id="evt_battle")

        assert interrupted.status == "interrupted"
        assert interrupted.interrupt_event_id == "evt_battle"

    def test_interrupt_does_not_mutate_original(self):
        """model_copy → l'originale rimane invariato."""
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Riposa",
            action_type="rest_full",
            world_time_cost=WORLD_TIME_COST["rest_full"],
        )
        intent = scheduler.schedule(action, clock)
        _ = scheduler.interrupt(intent, "evt_battle")

        assert intent.status == "pending"  # originale invariato

    def test_complete_sets_status(self):
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Riposa",
            action_type="rest_full",
            world_time_cost=WORLD_TIME_COST["rest_full"],
        )
        intent = scheduler.schedule(action, clock)
        completed = scheduler.complete(intent)

        assert completed.status == "completed"

    def test_is_completed_for_terminal_interrupted(self):
        clock = WorldClock()
        scheduler = IntentScheduler()
        action = PlayerAction(
            label="Riposa",
            action_type="rest_full",
            world_time_cost=WORLD_TIME_COST["rest_full"],
        )
        intent = scheduler.schedule(action, clock)
        interrupted = scheduler.interrupt(intent, "evt")

        # is_completed per un interrupted → False (non è "completed")
        assert scheduler.is_completed(interrupted, clock) is False


# ── InteractionManager ────────────────────────────────────────────────────────


class TestInteractionManager:
    def _make_interaction(
        self,
        location: str = "loc_tavern",
        open_to_intrusion: bool = True,
    ) -> ActiveInteraction:
        return ActiveInteraction(
            type="dialogue",
            participants=["player_elan", "npc_mira"],
            location_id=location,
            open_to_intrusion=open_to_intrusion,
        )

    def test_try_intrude_same_location_open(self):
        """Evento nella stessa location + open → True."""
        ws = WorldState()
        manager = InteractionManager()
        interaction = self._make_interaction("loc_tavern", open_to_intrusion=True)
        event = make_event(EventVerb.ATTACKED, location="loc_tavern")

        result = manager.try_intrude(event, interaction, ws)
        assert result is True

    def test_try_intrude_different_location(self):
        """Evento in location diversa → False."""
        ws = WorldState()
        manager = InteractionManager()
        interaction = self._make_interaction("loc_tavern")
        event = make_event(EventVerb.ATTACKED, location="loc_fort")

        result = manager.try_intrude(event, interaction, ws)
        assert result is False

    def test_try_intrude_closed_to_intrusion(self):
        """open_to_intrusion=False → False anche se stessa location."""
        ws = WorldState()
        manager = InteractionManager()
        interaction = self._make_interaction("loc_tavern", open_to_intrusion=False)
        event = make_event(EventVerb.ATTACKED, location="loc_tavern")

        result = manager.try_intrude(event, interaction, ws)
        assert result is False

    def test_try_intrude_event_no_location_in_payload(self):
        """Evento senza location_id nel payload → location None → non corrisponde."""
        ws = WorldState()
        manager = InteractionManager()
        interaction = self._make_interaction("loc_tavern")
        event = GameEvent(
            tick=GameTick(1),
            world_time=make_world_time(),
            type="conflict",
            verb=EventVerb.ATTACKED,
            emitter=EventActor(id="npc_001", kind=EntityKind.NPC, name="NPC"),
            visibility=EventVisibility(scope="local"),
            payload={},  # nessuna location_id
        )

        result = manager.try_intrude(event, interaction, ws)
        assert result is False

    def test_suspend_sets_suspended_at(self):
        manager = InteractionManager()
        interaction = self._make_interaction()
        wt = make_world_time(day=5)

        manager.suspend(interaction, wt)

        assert interaction.suspended_at == wt

    def test_suspend_twice_updates_value(self):
        manager = InteractionManager()
        interaction = self._make_interaction()

        manager.suspend(interaction, make_world_time(day=3))
        manager.suspend(interaction, make_world_time(day=7))

        assert interaction.suspended_at.to_absolute_days() == make_world_time(day=7).to_absolute_days()

    def test_resume_elapsed_days(self):
        """elapsed_days calcolato correttamente tra suspended_at e current clock."""
        ws = WorldState()
        ws.player_knowledge = PlayerKnowledgeBase(player_id="player_elan")

        clock = WorldClock()
        manager = InteractionManager()
        interaction = self._make_interaction()

        # Sospendi al giorno 1
        manager.suspend(interaction, make_world_time(day=1))

        # Avanza il tempo a giorno 6 (5 giorni dopo)
        for _ in range(5):
            clock.advance_world_time("rest_full")

        result = manager.resume(interaction, ws, clock)

        current_day = clock.world_time.to_absolute_days()
        suspended_day = make_world_time(day=1).to_absolute_days()
        assert result["elapsed_days"] == current_day - suspended_day

    def test_resume_includes_original_state(self):
        ws = WorldState()
        ws.player_knowledge = PlayerKnowledgeBase(player_id="player_elan")

        clock = WorldClock()
        manager = InteractionManager()
        interaction = self._make_interaction()
        interaction.state["topic"] = "guerra"
        manager.suspend(interaction, make_world_time(day=1))

        result = manager.resume(interaction, ws, clock)

        assert result["original_state"]["topic"] == "guerra"

    def test_resume_known_events_only_from_kb(self):
        """Resume: solo eventi nella KB del player, non tutto il world state."""
        ws = WorldState()
        kb = PlayerKnowledgeBase(player_id="player_elan")
        ws.player_knowledge = kb

        clock = WorldClock()
        manager = InteractionManager()
        interaction = self._make_interaction()

        # Sospendi al giorno 1
        suspension_day = make_world_time(day=1)
        manager.suspend(interaction, suspension_day)

        # Aggiungi eventi al world state — solo il secondo è noto al player
        ev1 = make_event(EventVerb.ATTACKED, day=2)  # NON nella KB
        ev2 = make_event(EventVerb.ALLIED, day=3)    # nella KB

        ws.append_event(ev1)
        ws.append_event(ev2)

        # Solo ev2 viene aggiunto alla KB
        update = KnowledgeUpdate(
            event_id=ev2.id,
            how_learned="informed",
            certainty=0.9,
        )
        kb.apply_update(update, ev2, make_world_time(day=3))

        # Avanza clock a giorno 5
        for _ in range(4):
            clock.advance_world_time("rest_full")

        result = manager.resume(interaction, ws, clock)

        known_during = result["known_events_during_suspension"]
        # ev2 deve essere incluso
        assert ev2.id in known_during
        # ev1 NON deve essere incluso (non nella KB)
        assert ev1.id not in known_during

    def test_resume_not_suspended_returns_zero_elapsed(self):
        """Se non sospesa, elapsed_days = 0 e known_events vuota."""
        ws = WorldState()
        ws.player_knowledge = PlayerKnowledgeBase(player_id="player_elan")
        clock = WorldClock()
        manager = InteractionManager()
        interaction = self._make_interaction()

        result = manager.resume(interaction, ws, clock)

        assert result["elapsed_days"] == 0
        assert result["known_events_during_suspension"] == []
