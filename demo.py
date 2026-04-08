"""demo.py — Agentic Dungeons: flusso completo del Game Engine.

Copre tutte le fasi implementate:
  Fase 1  — Modelli base (WorldTime, GameTick, entità, eventi)
  Fase 2  — VisibilityEngine, EventLogger SQLite, CooldownTracker
  Fase 3  — ConsequenceEngine, ScheduledEventProcessor
  Fase 5  — NarrativeSlice, QuestSlice, MoodCalculator
  Fase 6  — PlayerAction, ActionFilterEngine, IntentScheduler
  Fase 8  — SnapshotManager msgpack, SaveManager
  Fase 9  — Bridge: spawn_entity, resolve_combat, apply_movement,
              apply_inventory, apply_xp

Eseguire da root del progetto:
    python demo.py
"""

from __future__ import annotations

import asyncio
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Forza UTF-8 su stdout Windows (cp1252 non supporta i caratteri box)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Game Engine imports ───────────────────────────────────────────────────────
from game_engine.bridge.game_engine import (
    apply_inventory,
    apply_movement,
    apply_xp,
    resolve_combat,
    spawn_entity,
)
from game_engine.engine.action import ActionFilterEngine, IntentScheduler
from game_engine.engine.consequence import ConsequenceEngine, ScheduledEventProcessor
from game_engine.engine.cooldown import CooldownTracker
from game_engine.engine.knowledge import PlayerKnowledgeBase, VisibilityEngine
from game_engine.engine.slice_builder import NarrativeSliceBuilder, QuestSliceBuilder
from game_engine.engine.world_clock import WorldClock
from game_engine.engine.world_state import WorldState
from game_engine.models.base import DayMoment, EntityKind, EntityStatus, GameTick, WorldTime
from game_engine.models.entity import (
    EntityIdentity,
    EntityMeta,
    NPCBehaviour,
    NPCEntity,
    PlayerEntity,
)
from game_engine.models.event import EventActor, EventVerb, EventVisibility, GameEvent
from game_engine.models.slice import SliceRequest
from game_engine.persistence.event_log import EventLogger
from game_engine.persistence.save_manager import SaveManager

# ── ANSI ─────────────────────────────────────────────────────────────────────
R   = "\033[0m"
B   = "\033[1m"
DIM = "\033[2m"
CYN = "\033[96m"
GRN = "\033[92m"
YLW = "\033[93m"
RED = "\033[91m"
MAG = "\033[95m"
BLU = "\033[94m"


def hdr(title: str) -> None:
    print(f"\n{B}{CYN}{'=' * 62}{R}")
    print(f"{B}{CYN}  {title}{R}")
    print(f"{B}{CYN}{'=' * 62}{R}")


def sec(title: str) -> None:
    print(f"\n{B}{YLW}>> {title}{R}")


def ok(msg: str) -> None:   print(f"  {GRN}[OK]{R}  {msg}")
def nfo(msg: str) -> None:  print(f"  {DIM}     {msg}{R}")
def wrn(msg: str) -> None:  print(f"  {YLW}[!]{R}  {msg}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def wt(year=1, season="autumn", day=1, moment=DayMoment.MORNING) -> WorldTime:
    return WorldTime(year=year, season=season, day=day, moment=moment)


def meta(world_time: WorldTime) -> EntityMeta:
    return EntityMeta(created_at=world_time, created_by="demo", status=EntityStatus.ACTIVE)


def make_player(location: str = "loc_city") -> PlayerEntity:
    t = wt()
    return PlayerEntity(
        id="player_elan",
        meta=meta(t),
        identity=EntityIdentity(name="Elan Voss"),
        mechanical={"location_id": location, "level": 1, "xp": 0},
    )


def make_npc(npc_id: str, name: str, location: str,
             traits: list[str] | None = None) -> NPCEntity:
    t = wt()
    return NPCEntity(
        id=npc_id,
        meta=meta(t),
        identity=EntityIdentity(name=name),
        mechanical={"location_id": location},
        behaviour=NPCBehaviour(personality_traits=traits or []),
    )


def make_event_manual(verb: str, emitter_id: str, emitter_name: str,
                      kind: EntityKind, location: str, event_type: str,
                      scope: str, clock: WorldClock) -> GameEvent:
    return GameEvent(
        tick=clock.advance_tick(),
        world_time=clock.world_time,
        type=event_type,
        verb=verb,
        emitter=EventActor(id=emitter_id, kind=kind, name=emitter_name),
        visibility=EventVisibility(scope=scope),
        payload={"location_id": location},
    )


# ─────────────────────────────────────────────────────────────────────────────

async def run_demo() -> None:
    rng = random.Random(42)

    hdr("AGENTIC DUNGEONS — Game Engine Demo (Fasi 1-3, 5-6, 8-9)")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. SETUP
    # ─────────────────────────────────────────────────────────────────────────
    sec("1. Setup — WorldClock, WorldState, Entità")

    clock    = WorldClock(initial_time=wt(year=1, season="autumn", day=1))
    world    = WorldState()
    cooldown = CooldownTracker()
    vis_eng  = VisibilityEngine()
    kb       = PlayerKnowledgeBase(player_id="player_elan")

    consequence_engine = ConsequenceEngine(
        cooldown_tracker=cooldown,
        visibility_engine=vis_eng,
        rng=rng,
    )

    event_log = EventLogger(":memory:")
    await event_log.open()
    await event_log.init_schema()

    player = make_player("loc_city")
    world.add_entity(player)
    world.player_knowledge = kb

    ok(f"Player: {B}{player.identity.name}{R}  @  {BLU}loc_city{R}")
    nfo(f"Anno {clock.world_time.year}, {clock.world_time.season.title()}, "
        f"Giorno {clock.world_time.day}, {clock.world_time.moment.title()}")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. BRIDGE — SPAWN
    # ─────────────────────────────────────────────────────────────────────────
    sec("2. Bridge — spawn_entity")

    mira   = make_npc("npc_mira",   "Mira Soldath", "loc_city",   ["curious", "loyal"])
    aldric = make_npc("npc_aldric", "Aldric Kael",  "loc_market", ["aggressive", "greedy"])
    rebel  = make_npc("npc_rebel",  "Ser Dray",     "loc_forest", ["ruthless"])

    for npc, loc in [(mira, "loc_city"), (aldric, "loc_market"), (rebel, "loc_forest")]:
        spawn_entity(npc, loc, world, clock)
        ok(f"Spawned {B}{npc.identity.name}{R} → {BLU}{loc}{R}")

    nfo(f"Entities nel world state: {len(world.entity_store)}  |  "
        f"Events logged: {len(world.event_log)}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. BRIDGE — COMBAT (tempo narrativo: FERMO)
    # ─────────────────────────────────────────────────────────────────────────
    sec("3. Bridge — resolve_combat  (WorldTime NON avanza)")

    units_before = clock.world_units_total
    result = resolve_combat("player_elan", "npc_aldric", world, clock)

    ok(f"{B}Elan Voss{R} ATTACKED {B}Aldric Kael{R}  →  outcome: {result['outcome']}")
    if clock.world_units_total == units_before:
        ok("WorldTime invariato — corretto (il combat non avanza il tempo narrativo)")
    nfo(f"event_id: {result['event_id'][:12]}...")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. BRIDGE — MOVEMENT (tempo narrativo: AVANZA)
    # ─────────────────────────────────────────────────────────────────────────
    sec("4. Bridge — apply_movement  (WorldTime avanza)")

    moment_before = clock.world_time.moment
    ev_move = apply_movement("player_elan", "loc_city", "loc_market",
                              "travel_short", world, clock)

    ok(f"Elan si sposta: {BLU}loc_city{R} → {BLU}loc_market{R}  (travel_short, 4 world_units)")
    ok(f"Momento: {moment_before.title()} → {clock.world_time.moment.title()}")
    nfo(f"World units totali: {clock.world_units_total}")

    updated_player = world.get_entity("player_elan")
    nfo(f"Location aggiornata nel world state: {updated_player.mechanical['location_id']}")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. BRIDGE — INVENTORY
    # ─────────────────────────────────────────────────────────────────────────
    sec("5. Bridge — apply_inventory")

    apply_inventory("player_elan",  "item_sword",  "take",  world, clock)
    apply_inventory("npc_aldric",   "item_pouch",  "steal", world, clock)
    apply_inventory("player_elan",  "item_cloak",  "give",  world, clock)

    traded = [e for e in world.event_log if e.verb == "traded"]
    stolen = [e for e in world.event_log if e.verb == "stolen"]
    ok(f"TRADED events: {len(traded)}  (take, give)")
    ok(f"STOLEN events: {len(stolen)}  (steal)")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. BRIDGE — XP & LEVEL-UP
    # ─────────────────────────────────────────────────────────────────────────
    sec("6. Bridge — apply_xp + level-up  (soglia: level × 100 XP)")

    p = world.get_entity("player_elan")
    nfo(f"Prima — Livello: {p.mechanical['level']}  XP: {p.mechanical['xp']}")

    r1 = apply_xp("player_elan", 50, world, clock)
    r2 = apply_xp("player_elan", 60, world, clock)   # totale 110 ≥ 100 → level-up

    p = world.get_entity("player_elan")
    if r1 is None:
        ok("apply_xp(+50): XP accumulati, nessun level-up")
    if r2:
        ok(f"apply_xp(+60): {B}LEVELED UP!{R} → Livello {p.mechanical['level']}, "
           f"XP: {p.mechanical['xp']}")
        nfo(f"LEVELED event: {r2[:12]}...")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. VISIBILITY ENGINE → PLAYER KNOWLEDGE BASE
    # ─────────────────────────────────────────────────────────────────────────
    sec("7. VisibilityEngine — filtraggio eventi → PlayerKnowledgeBase")

    player_entity = world.get_entity("player_elan")
    applied = 0
    rumors  = 0
    for event in world.event_log:
        update = vis_eng.evaluate(event, player_entity, world)
        if update:
            kb.apply_update(update, event, clock.world_time)
            await event_log.append(event)
            await event_log.mark_known(
                "player_elan", event.id,
                update.how_learned, update.certainty,
                clock.world_time.to_absolute_days(),
            )
            applied += 1
            if update.certainty < 0.7:
                rumors += 1

    ok(f"Events nel world state: {len(world.event_log)}")
    ok(f"Events filtrati in KB: {len(kb.known_events)}  (player non sa tutto)")
    ok(f"Di cui rumors (certainty < 0.7): {rumors}")
    if kb.known_entities:
        ok(f"Entità note al player: {list(kb.known_entities.keys())}")

    # ─────────────────────────────────────────────────────────────────────────
    # 8. CONSEQUENCE ENGINE — cascata
    # ─────────────────────────────────────────────────────────────────────────
    sec("8. ConsequenceEngine — cascata causa-effetto")

    # Evento trigger: dichiarazione di guerra remota
    war_event = make_event_manual(
        verb=EventVerb.DECLARED_WAR,
        emitter_id="npc_rebel",
        emitter_name="Ser Dray",
        kind=EntityKind.NPC,
        location="loc_forest",
        event_type="conflict",
        scope="regional",
        clock=clock,
    )
    world.append_event(war_event)

    player_entity = world.get_entity("player_elan")
    consequences = consequence_engine.process_event(
        war_event, world, clock,
        player=player_entity, player_kb=kb,
    )

    ok(f"Evento trigger: {B}DECLARED_WAR{R} (Ser Dray, loc_forest)")
    ok(f"Conseguenze immediate: {len(consequences)}")
    for c in consequences:
        ok(f"  → {B}{c.verb.upper()}{R}  [{c.type}]  scope={c.visibility.scope}")

    if world.scheduled_events:
        ok(f"Conseguenze schedulate (future): {len(world.scheduled_events)}")
        current_day = clock.world_time.to_absolute_days()
        for s in world.scheduled_events:
            verb = s.event_template.get("verb", "?")
            ok(f"  → {B}{verb.upper()}{R} al giorno narrativo {s.trigger_world_day} "
               f"(in ~{s.trigger_world_day - current_day} giorni)")

    # Simula salto temporale e processa gli scheduled events
    for _ in range(15):
        clock.advance_world_time("rest_full")

    processor = ScheduledEventProcessor(consequence_engine)
    triggered = processor.run(world, clock, player=player_entity, player_kb=kb)
    if triggered:
        ok(f"Dopo 15 giorni narrativi — {len(triggered)} scheduled events scattati:")
        for ev in triggered:
            ok(f"  → {B}{ev.verb.upper()}{R}  ({ev.type})")

    # ─────────────────────────────────────────────────────────────────────────
    # 9. NARRATIVE SLICE
    # ─────────────────────────────────────────────────────────────────────────
    sec("9. NarrativeSlice — contesto per l'Agente Narrativo  (solo KB)")

    narrative_builder = NarrativeSliceBuilder()
    request = SliceRequest(
        agent="narrative",
        focus_location_id="loc_market",
        task="Descrivi la situazione al player",
        from_world_day=0,
        to_world_day=100_000,
    )

    player_entity = world.get_entity("player_elan")
    nslice = narrative_builder.build(kb, world, request, player_entity)

    loc_id   = nslice.focus_location.get("id", "?")
    loc_mood = nslice.focus_location.get("mood", "peaceful")
    ok(f"NarrativeSlice costruita {B}SOLO{R} da PlayerKnowledgeBase")
    ok(f"Location focus: {BLU}{loc_id}{R}  |  Momento: {nslice.day_moment}")
    ok(f"Mood location: {B}{loc_mood}{R}")
    ok(f"Eventi noti recenti: {len(nslice.known_events_recent)}")
    if nslice.known_events_recent:
        ev = nslice.known_events_recent[0]
        cert = f"certezza {ev.certainty:.0%}" if ev.certainty < 1.0 else "testimone diretto"
        ok(f"  Ultimo: [{ev.verb}] da {ev.emitter_name}  ({cert})")
    ok(f"NPC visibili: {len(nslice.npcs_in_focus)}")
    for n in nslice.npcs_in_focus:
        ok(f"  -> {n.name}  @  {n.last_known_location}")
    if nslice.active_rumors:
        wrn(f"Rumors attivi nel slice: {len(nslice.active_rumors)}")

    # ─────────────────────────────────────────────────────────────────────────
    # 10. QUEST SLICE
    # ─────────────────────────────────────────────────────────────────────────
    sec("10. QuestSlice — contesto per l'Agente Quest  (world state globale)")

    quest_builder = QuestSliceBuilder()
    qrequest = SliceRequest(
        agent="quest",
        focus_location_id="loc_market",
        task="Genera una quest basata sulle tensioni del mondo",
        from_world_day=0,
        to_world_day=100_000,
    )

    qslice = quest_builder.build(world, qrequest, player_entity)

    ok(f"QuestSlice costruita dal {B}world state globale{R} (omnisciente)")
    ok(f"Eventi visibili all'agente Quest: {len(qslice.recent_events)}")
    ok(f"Tension points rilevati: {len(qslice.tension_points)}")
    for tp in qslice.tension_points:
        urgency_color = RED if tp.urgency == "critical" else YLW
        ok(f"  [!!] [{urgency_color}{tp.urgency.upper()}{R}]  {tp.description[:65]}")
    nfo("Il Quest Agent SA cose che il player NON conosce ancora")

    # ─────────────────────────────────────────────────────────────────────────
    # 11. ACTION SYSTEM
    # ─────────────────────────────────────────────────────────────────────────
    sec("11. ActionFilterEngine + IntentScheduler")

    filter_engine = ActionFilterEngine()
    scheduler     = IntentScheduler()

    player_entity = world.get_entity("player_elan")
    menu = filter_engine.build_menu(world, player_entity, clock)

    ok(f"Menu azioni per {B}{player_entity.identity.name}{R} "
       f"@ {BLU}{player_entity.mechanical['location_id']}{R}:")
    for action in menu:
        cost_str = f"({action.world_time_cost} wu)" if action.world_time_cost > 0 else "(immediata)"
        tgt_str  = f" → {action.target_id}" if action.target_id else ""
        ok(f"  [{action.action_type}]  {action.label}{tgt_str}  {DIM}{cost_str}{R}")

    # Schedula la prima azione con costo
    slow = [a for a in menu if a.world_time_cost > 0]
    if slow:
        chosen = slow[0]
        intent = scheduler.schedule(chosen, clock)
        ok(f"\nAzione schedulata: '{chosen.label}'")
        ok(f"  Status: {intent.status}  |  completa al giorno: {intent.completes_at_world_day}")

    # ─────────────────────────────────────────────────────────────────────────
    # 12. SAVE & LOAD
    # ─────────────────────────────────────────────────────────────────────────
    sec("12. SaveManager — save + load  (msgpack + JSON)")

    config = {
        "seed": 42,
        "flow_ratio": 30,
        "world_name": "Aethoria",
        "player_name": player.identity.name,
    }

    with tempfile.TemporaryDirectory() as tmp:
        save_dir = Path(tmp) / "demo_save"
        sm = SaveManager(save_dir=save_dir)
        sm.save(world, kb, config)

        ok(f"Save in: {save_dir.name}/")
        ok(f"  state.msgpack     → {(save_dir / 'state.msgpack').stat().st_size:,} bytes")
        ok(f"  knowledge.msgpack → {(save_dir / 'knowledge.msgpack').stat().st_size:,} bytes")
        ok(f"  config.json       → {(save_dir / 'config.json').stat().st_size:,} bytes")

        loaded_world, loaded_kb, loaded_config = sm.load()

        ok(f"\nLoad — round-trip verificato:")
        ok(f"  Entities:       {len(loaded_world.entity_store):>3}  "
           f"(orig: {len(world.entity_store)})")
        ok(f"  Events:         {len(loaded_world.event_log):>3}  "
           f"(orig: {len(world.event_log)})")
        ok(f"  Scheduled:      {len(loaded_world.scheduled_events):>3}  "
           f"(orig: {len(world.scheduled_events)})")
        ok(f"  KB known_events:{len(loaded_kb.known_events):>3}  "
           f"(orig: {len(kb.known_events)})")
        ok(f"  Config: world='{loaded_config['world_name']}'  seed={loaded_config['seed']}")

        lp = loaded_world.get_entity("player_elan")
        ok(f"  Player lvl: {lp.mechanical['level']}  xp: {lp.mechanical['xp']}  "
           f"loc: {lp.mechanical['location_id']}")

    # ─────────────────────────────────────────────────────────────────────────
    # RIEPILOGO
    # ─────────────────────────────────────────────────────────────────────────
    hdr("RIEPILOGO STATO FINALE")

    await event_log.close()

    print(f"""
  {B}WorldClock{R}
    GameTick:      {clock.tick.value}
    WorldTime:     Anno {clock.world_time.year}, {clock.world_time.season.title()},
                   Giorno {clock.world_time.day}, {clock.world_time.moment.title()}
    Giorno ass.:   {clock.world_time.to_absolute_days()}
    World units:   {clock.world_units_total}

  {B}WorldState{R}
    Entities:      {len(world.entity_store)}
    Events log:    {len(world.event_log)}
    Scheduled:     {len(world.scheduled_events)}
    Cooldowns:     {len(cooldown._last_triggered)}

  {B}PlayerKnowledgeBase{R}
    Known events:  {len(kb.known_events)}
    Rumors:        {len(kb.active_rumors)}
    Known entities:{len(kb.known_entities)}

  {B}Player (Elan Voss){R}
    Livello:       {world.get_entity("player_elan").mechanical["level"]}
    XP:            {world.get_entity("player_elan").mechanical["xp"]}
    Location:      {world.get_entity("player_elan").mechanical["location_id"]}

  {DIM}Fasi non ancora implementate: 4 (WorldLoop), 7 (AI Agents), 10 (Playtest){R}
""")


if __name__ == "__main__":
    asyncio.run(run_demo())
