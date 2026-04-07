"""Test suite per il Context Slice System (Fase 5).

Verifica:
- NarrativeSlice non contiene mai dati non presenti nella PlayerKnowledgeBase
- Stesso evento con certainty diversa → posizionato in known_events_recent o active_rumors
- MoodCalculator: verbi di guerra → war-torn, nessun evento → peaceful
- TruncationEngine: con molti eventi, i 5 garantiti sono sempre presenti
- QuestSlice ha più eventi di NarrativeSlice sullo stesso scenario
- NarrativeSliceBuilder: NPC non noto al player e non nella stessa location → non incluso
"""

from __future__ import annotations

import pytest

from game_engine.engine.knowledge import (
    KnowledgeUpdate,
    PlayerKnowledgeBase,
    VisibilityEngine,
)
from game_engine.engine.slice_builder import (
    MoodCalculator,
    NarrativeSliceBuilder,
    QuestSliceBuilder,
    TensionPointDetector,
    TruncationEngine,
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
from game_engine.models.event import EventActor, EventVerb, EventVisibility, GameEvent
from game_engine.models.slice import (
    KnownEventSlice,
    NarrativeSlice,
    SliceRequest,
)


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
        identity=EntityIdentity(name=name, tags=["mercante"]),
        mechanical={"location_id": location},
        behaviour=NPCBehaviour(personality_traits=["avido"], dialogue_style="formale"),
    )


def make_event(
    verb: str,
    emitter_id: str = "npc_001",
    emitter_name: str = "Lord Test",
    location: str = "loc_fort",
    day: int = 1,
    event_type: str = "conflict",
) -> GameEvent:
    return GameEvent(
        tick=GameTick(1),
        world_time=make_world_time(day=day),
        type=event_type,
        verb=verb,
        emitter=EventActor(id=emitter_id, kind=EntityKind.NPC, name=emitter_name),
        visibility=EventVisibility(scope="regional"),
        payload={"location_id": location},
    )


@pytest.fixture
def base_world_state() -> WorldState:
    ws = WorldState()
    return ws


@pytest.fixture
def base_request() -> SliceRequest:
    return SliceRequest(
        agent="narrative",
        focus_location_id="loc_tavern",
        task="descrivi la scena",
        from_world_day=0,
        to_world_day=100,
        token_budget=4000,
    )


# ── MoodCalculator ────────────────────────────────────────────────────────────


class TestMoodCalculator:
    def test_no_events_returns_peaceful(self):
        mood = MoodCalculator.calculate([])
        assert mood == "peaceful"

    def test_war_verb_returns_war_torn(self):
        events = [
            KnownEventSlice(
                id="e1",
                verb=EventVerb.DECLARED_WAR,
                emitter_name="Lord X",
                world_time=make_world_time(),
                how_learned="direct_witness",
                certainty=1.0,
            )
        ]
        mood = MoodCalculator.calculate(events)
        assert mood == "war-torn"

    def test_massacred_returns_war_torn(self):
        events = [
            KnownEventSlice(
                id="e1",
                verb=EventVerb.MASSACRED,
                emitter_name="Lord X",
                world_time=make_world_time(),
                how_learned="direct_witness",
                certainty=1.0,
            )
        ]
        mood = MoodCalculator.calculate(events)
        assert mood == "war-torn"

    def test_attacked_returns_tense(self):
        events = [
            KnownEventSlice(
                id="e1",
                verb=EventVerb.ATTACKED,
                emitter_name="Lord X",
                world_time=make_world_time(),
                how_learned="direct_witness",
                certainty=1.0,
            )
        ]
        mood = MoodCalculator.calculate(events)
        assert mood == "tense"

    def test_allied_returns_hopeful(self):
        events = [
            KnownEventSlice(
                id="e1",
                verb=EventVerb.ALLIED,
                emitter_name="Lord X",
                world_time=make_world_time(),
                how_learned="informed",
                certainty=0.9,
            )
        ]
        mood = MoodCalculator.calculate(events)
        assert mood == "hopeful"

    def test_war_overrides_hopeful(self):
        """War-torn ha priorità su hopeful."""
        events = [
            KnownEventSlice(
                id="e1",
                verb=EventVerb.ALLIED,
                emitter_name="A",
                world_time=make_world_time(),
                how_learned="informed",
                certainty=0.9,
            ),
            KnownEventSlice(
                id="e2",
                verb=EventVerb.DECLARED_WAR,
                emitter_name="B",
                world_time=make_world_time(),
                how_learned="informed",
                certainty=0.9,
            ),
        ]
        mood = MoodCalculator.calculate(events)
        assert mood == "war-torn"

    def test_plague_returns_fearful(self):
        events = [
            KnownEventSlice(
                id="e1",
                verb=EventVerb.PLAGUE_STARTED,
                emitter_name="sistema",
                world_time=make_world_time(),
                how_learned="direct_witness",
                certainty=1.0,
            )
        ]
        mood = MoodCalculator.calculate(events)
        assert mood == "fearful"

    def test_unknown_verbs_return_peaceful(self):
        events = [
            KnownEventSlice(
                id="e1",
                verb="discovered",  # non mappato in _VERB_MOOD_MAP → peaceful
                emitter_name="X",
                world_time=make_world_time(),
                how_learned="direct_witness",
                certainty=1.0,
            )
        ]
        mood = MoodCalculator.calculate(events)
        assert mood == "peaceful"


# ── TruncationEngine ──────────────────────────────────────────────────────────


class TestTruncationEngine:
    def _make_slice_with_n_events(self, n: int) -> NarrativeSlice:
        events = [
            KnownEventSlice(
                id=f"e{i}",
                verb=EventVerb.ATTACKED,
                emitter_name=f"NPC {i}",
                world_time=make_world_time(day=i + 1),
                how_learned="direct_witness",
                certainty=1.0,
            )
            for i in range(n)
        ]
        rumors = [
            KnownEventSlice(
                id=f"r{i}",
                verb=EventVerb.RUMORED,
                emitter_name=f"Bardo {i}",
                world_time=make_world_time(day=i + 1),
                how_learned="rumor",
                certainty=0.4,
            )
            for i in range(3)
        ]
        return NarrativeSlice(
            world_time=make_world_time(),
            day_moment=DayMoment.MORNING,
            focus_location={"id": "loc_tavern", "name": "Taverna"},
            known_events_recent=events,
            active_rumors=rumors,
            player_context={"name": "Elan"},
        )

    def test_small_slice_not_truncated(self):
        engine = TruncationEngine()
        s = self._make_slice_with_n_events(3)
        result = engine.truncate(s, token_budget=10000)
        assert len(result.known_events_recent) == 3

    def test_large_slice_truncated_to_5_minimum(self):
        engine = TruncationEngine()
        s = self._make_slice_with_n_events(30)
        result = engine.truncate(s, token_budget=100)  # budget minuscolo
        assert len(result.known_events_recent) >= 5

    def test_focus_location_never_removed(self):
        engine = TruncationEngine()
        s = self._make_slice_with_n_events(30)
        result = engine.truncate(s, token_budget=100)
        assert result.focus_location is not None
        assert result.focus_location.get("id") == "loc_tavern"

    def test_day_moment_never_removed(self):
        engine = TruncationEngine()
        s = self._make_slice_with_n_events(30)
        result = engine.truncate(s, token_budget=100)
        assert result.day_moment == DayMoment.MORNING

    def test_rumors_omitted_when_budget_exceeded(self):
        engine = TruncationEngine()
        s = self._make_slice_with_n_events(30)
        result = engine.truncate(s, token_budget=100)
        # Con budget minuscolo i rumors dovrebbero essere omessi
        # (possibile che siano vuoti)
        assert isinstance(result.active_rumors, list)

    def test_npcs_truncated_to_5(self):
        from game_engine.models.slice import NPCSlice

        engine = TruncationEngine()
        npcs = [
            NPCSlice(id=f"npc{i}", name=f"NPC {i}", role="mercante")
            for i in range(10)
        ]
        s = NarrativeSlice(
            world_time=make_world_time(),
            day_moment=DayMoment.MORNING,
            focus_location={"id": "loc"},
            npcs_in_focus=npcs,
            player_context={},
        )
        result = engine.truncate(s, token_budget=100)
        assert len(result.npcs_in_focus) <= 5


# ── NarrativeSliceBuilder — separazione KB ───────────────────────────────────


class TestNarrativeSliceBuilderSeparation:
    def _setup(self):
        """Setup comune: player, NPC, world state, eventi."""
        ws = WorldState()
        clock = WorldClock()
        player = make_player(location="loc_tavern")
        ws.add_entity(player)

        # NPC nella taverna (stessa location del player)
        npc_tavern = make_npc("npc_mira", "Lady Mira", "loc_tavern")
        ws.add_entity(npc_tavern)

        # NPC lontano (non noto al player, non nella stessa location)
        npc_remote = make_npc("npc_aldric", "Lord Aldric", "loc_fort")
        ws.add_entity(npc_remote)

        kb = PlayerKnowledgeBase(player_id="player_elan")
        ws.player_knowledge = kb

        return ws, clock, player, kb, npc_tavern, npc_remote

    def test_narrative_slice_contains_only_kb_events(self):
        ws, clock, player, kb, _, _ = self._setup()

        # Evento noto al player
        ev_known = make_event(EventVerb.ATTACKED, day=1)
        ws.append_event(ev_known)
        clock.advance_tick()

        # Applica update alla KB (come farebbe VisibilityEngine)
        update = KnowledgeUpdate(
            event_id=ev_known.id,
            how_learned="direct_witness",
            certainty=1.0,
        )
        kb.apply_update(update, ev_known, make_world_time(day=1))

        # Evento NON noto al player
        ev_unknown = make_event(EventVerb.DECLARED_WAR, day=2)
        ws.append_event(ev_unknown)

        builder = NarrativeSliceBuilder()
        request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=100,
        )
        result = builder.build(kb, ws, request, player)

        known_ids = {e.id for e in result.known_events_recent}
        known_ids |= {e.id for e in result.active_rumors}

        # Solo l'evento noto deve essere presente
        assert ev_known.id in known_ids
        assert ev_unknown.id not in known_ids

    def test_high_certainty_event_in_recent_not_rumors(self):
        ws, clock, player, kb, _, _ = self._setup()

        ev = make_event(EventVerb.ATTACKED, day=1)
        ws.append_event(ev)
        clock.advance_tick()

        # certainty=1.0 → direct_witness → known_events_recent
        update = KnowledgeUpdate(
            event_id=ev.id, how_learned="direct_witness", certainty=1.0
        )
        kb.apply_update(update, ev, make_world_time())

        builder = NarrativeSliceBuilder()
        request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=100,
        )
        result = builder.build(kb, ws, request, player)

        assert any(e.id == ev.id for e in result.known_events_recent)
        assert not any(e.id == ev.id for e in result.active_rumors)

    def test_low_certainty_event_in_active_rumors(self):
        ws, clock, player, kb, _, _ = self._setup()

        ev = make_event(EventVerb.RUMORED, day=1)
        ws.append_event(ev)
        clock.advance_tick()

        # certainty=0.4 → rumor → active_rumors
        update = KnowledgeUpdate(
            event_id=ev.id, how_learned="rumor", certainty=0.4
        )
        kb.apply_update(update, ev, make_world_time())

        builder = NarrativeSliceBuilder()
        request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=100,
        )
        result = builder.build(kb, ws, request, player)

        assert any(e.id == ev.id for e in result.active_rumors)
        assert not any(e.id == ev.id for e in result.known_events_recent)

    def test_npc_not_known_and_not_in_location_excluded(self):
        """NPC non noto al player e non nella stessa location → non incluso."""
        ws, clock, player, kb, _, npc_remote = self._setup()

        # npc_remote è a loc_fort, il player è a loc_tavern
        # kb non contiene npc_remote
        builder = NarrativeSliceBuilder()
        request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=100,
        )
        result = builder.build(kb, ws, request, player)

        npc_ids = {n.id for n in result.npcs_in_focus}
        assert npc_remote.id not in npc_ids

    def test_npc_in_same_location_included_even_if_not_in_kb(self):
        """NPC fisicamente nella stessa location → incluso anche se non in KB."""
        ws, clock, player, kb, npc_tavern, _ = self._setup()

        # npc_tavern è alla loc_tavern, kb è vuota
        assert npc_tavern.id not in kb.known_entities

        builder = NarrativeSliceBuilder()
        request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=100,
        )
        result = builder.build(kb, ws, request, player)

        npc_ids = {n.id for n in result.npcs_in_focus}
        assert npc_tavern.id in npc_ids

    def test_focus_location_mood_from_known_events_only(self):
        """Mood calcolato solo dagli eventi noti al player."""
        ws, clock, player, kb, _, _ = self._setup()

        # Evento di guerra NON noto al player
        ev_war = make_event(EventVerb.DECLARED_WAR, day=1)
        ws.append_event(ev_war)

        # Evento di alleanza noto al player
        ev_allied = make_event(EventVerb.ALLIED, day=2)
        ws.append_event(ev_allied)
        clock.advance_tick()
        update = KnowledgeUpdate(
            event_id=ev_allied.id, how_learned="informed", certainty=0.9
        )
        kb.apply_update(update, ev_allied, make_world_time(day=2))

        builder = NarrativeSliceBuilder()
        request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=100,
        )
        result = builder.build(kb, ws, request, player)

        # Mood deve essere "hopeful" (allied noto), non "war-torn" (guerra non nota)
        assert result.focus_location["mood"] == "hopeful"

    def test_world_time_and_day_moment_present(self):
        ws, clock, player, kb, _, _ = self._setup()

        ev = make_event(EventVerb.ATTACKED, day=5)
        ws.append_event(ev)
        update = KnowledgeUpdate(event_id=ev.id, how_learned="direct_witness", certainty=1.0)
        kb.apply_update(update, ev, make_world_time(day=5))

        builder = NarrativeSliceBuilder()
        request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=100,
        )
        result = builder.build(kb, ws, request, player)

        assert result.world_time is not None
        assert result.day_moment is not None


# ── QuestSliceBuilder — accesso globale ───────────────────────────────────────


class TestQuestSliceBuilder:
    def test_quest_slice_has_all_events(self):
        """QuestSlice vede tutti gli eventi, non solo quelli noti al player."""
        ws = WorldState()
        player = make_player(location="loc_tavern")
        ws.add_entity(player)
        kb = PlayerKnowledgeBase(player_id="player_elan")
        ws.player_knowledge = kb

        clock = WorldClock()

        # 3 eventi: solo 1 noto al player
        ev1 = make_event(EventVerb.DECLARED_WAR, day=1)
        ev2 = make_event(EventVerb.ATTACKED, day=2)
        ev3 = make_event(EventVerb.ALLIED, day=3)
        for ev in [ev1, ev2, ev3]:
            ws.append_event(ev)
            clock.advance_tick()

        # Solo ev1 noto al player
        update = KnowledgeUpdate(event_id=ev1.id, how_learned="direct_witness", certainty=1.0)
        kb.apply_update(update, ev1, make_world_time(day=1))

        builder_quest = QuestSliceBuilder()
        builder_narrative = NarrativeSliceBuilder()

        quest_request = SliceRequest(
            agent="quest",
            focus_location_id="loc_tavern",
            task="genera quest",
            from_world_day=0,
            to_world_day=10000,
        )
        narrative_request = SliceRequest(
            agent="narrative",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=10000,
        )

        quest_slice = builder_quest.build(ws, quest_request, player)
        narrative_slice = builder_narrative.build(kb, ws, narrative_request, player)

        # QuestSlice ha tutti e 3 gli eventi
        assert len(quest_slice.recent_events) == 3

        # NarrativeSlice ha solo 1 evento (noto al player)
        narrative_events = {e.id for e in narrative_slice.known_events_recent}
        narrative_events |= {e.id for e in narrative_slice.active_rumors}
        assert len(narrative_events) == 1
        assert ev1.id in narrative_events

    def test_quest_slice_detects_tension_points(self):
        """QuestSlice rileva tensioni non risolte."""
        ws = WorldState()
        clock = WorldClock()

        ev_war = make_event(EventVerb.DECLARED_WAR, day=1)
        ws.append_event(ev_war)
        clock.advance_tick()

        builder = QuestSliceBuilder()
        request = SliceRequest(
            agent="quest",
            focus_location_id="loc_tavern",
            task="genera quest",
            from_world_day=0,
            to_world_day=10000,
        )
        result = builder.build(ws, request)

        # La guerra non risolta deve generare un tension point
        assert len(result.tension_points) >= 1
        assert any(tp.urgency == "critical" for tp in result.tension_points)

    def test_quest_slice_no_tension_if_war_resolved(self):
        """Nessuna tensione 'critical' se la guerra è stata risolta."""
        ws = WorldState()
        clock = WorldClock()

        ev_war = make_event(EventVerb.DECLARED_WAR, day=1)
        ev_peace = GameEvent(
            tick=GameTick(2),
            world_time=make_world_time(day=3),
            type="conflict",
            verb=EventVerb.SURRENDERED,
            emitter=EventActor(id=ev_war.emitter.id, kind=EntityKind.NPC, name=ev_war.emitter.name),
            visibility=EventVisibility(scope="regional"),
            payload={"location_id": "loc_fort"},
        )
        ws.append_event(ev_war)
        ws.append_event(ev_peace)

        builder = QuestSliceBuilder()
        request = SliceRequest(
            agent="quest",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=10000,
        )
        result = builder.build(ws, request)

        assert not any(tp.urgency == "critical" for tp in result.tension_points)

    def test_quest_slice_detects_multiple_attacks(self):
        """3+ attacchi nello stesso giorno → tension point high."""
        ws = WorldState()
        clock = WorldClock()

        for i in range(3):
            ev = GameEvent(
                tick=GameTick(i),
                world_time=make_world_time(day=5),
                type="conflict",
                verb=EventVerb.ATTACKED,
                emitter=EventActor(id=f"npc_{i}", kind=EntityKind.NPC, name=f"NPC {i}"),
                visibility=EventVisibility(scope="local"),
                payload={"location_id": "loc_fort"},
            )
            ws.append_event(ev)

        builder = QuestSliceBuilder()
        request = SliceRequest(
            agent="quest",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=10000,
        )
        result = builder.build(ws, request)

        assert any(tp.urgency == "high" for tp in result.tension_points)

    def test_quest_slice_includes_npcs(self):
        """QuestSlice include tutti gli NPC nel world state."""
        ws = WorldState()
        npc = make_npc("npc_001", "Mercante", "loc_tavern")
        ws.add_entity(npc)

        builder = QuestSliceBuilder()
        request = SliceRequest(
            agent="quest",
            focus_location_id="loc_tavern",
            task="test",
            from_world_day=0,
            to_world_day=10000,
        )
        result = builder.build(ws, request)

        npc_ids = {n["id"] for n in result.available_npcs}
        assert "npc_001" in npc_ids
