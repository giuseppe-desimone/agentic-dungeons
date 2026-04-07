"""demo.py — Dimostrazione del game engine in stato attuale (Fasi 1-3).

Simula un piccolo scenario narrativo:
  - Una fazione dichiara guerra a un'altra
  - Il ConsequenceEngine genera conseguenze (assedi, ritorsioni, ecc.)
  - Il player assiste in prima persona ad alcuni eventi
  - La PlayerKnowledgeBase aggiorna solo ciò che il player può sapere

Esegui con:
    uv run python demo.py
    oppure
    python demo.py  (se src/ è nel PYTHONPATH)
"""

from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

# Aggiungi src/ al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from game_engine.engine.consequence import ConsequenceEngine, ScheduledEventProcessor
from game_engine.engine.cooldown import CooldownTracker
from game_engine.engine.knowledge import PlayerKnowledgeBase, VisibilityEngine
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
from game_engine.models.event import (
    EventActor,
    EventVerb,
    EventVisibility,
    GameEvent,
)
from game_engine.persistence.event_log import EventLogger

# ── ANSI colors ───────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
CYAN   = "\033[36m"
WHITE  = "\033[37m"
MAGENTA = "\033[35m"


def sep(title: str = "", char: str = "─", width: int = 60) -> None:
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{DIM}{char * pad}{RESET} {BOLD}{title}{RESET} {DIM}{char * pad}{RESET}")
    else:
        print(f"{DIM}{char * width}{RESET}")


def tick_label(clock: WorldClock) -> str:
    wt = clock.world_time
    day_abs = wt.to_absolute_days()
    return f"{DIM}[tick {clock.tick.value:>4} | day {day_abs:>3} | {wt.moment}]{RESET}"


def fmt_event(event: GameEvent, prefix: str = "") -> str:
    verb_color = RED if event.type == "conflict" else CYAN if event.type == "religion" else YELLOW
    cascade = f" {DIM}(cascade {event.cascade_depth}){RESET}" if event.cascade_depth > 0 else ""
    location = event.payload.get("location_id", "?")
    return (
        f"{prefix}{verb_color}{BOLD}{event.verb.upper()}{RESET}"
        f" by {WHITE}{event.emitter.name}{RESET}"
        f" @ {BLUE}{location}{RESET}"
        f"{cascade}"
    )


def fmt_kb_entry(entry, event: GameEvent) -> str:
    certainty_color = GREEN if entry.certainty >= 0.9 else YELLOW if entry.certainty >= 0.5 else MAGENTA
    return (
        f"  {certainty_color}[{entry.how_learned} {entry.certainty:.1f}]{RESET} "
        f"{event.verb.upper()} by {event.emitter.name}"
    )


# ── Setup ─────────────────────────────────────────────────────────────────────

def make_world_time(day: int = 1, moment: str = DayMoment.MORNING) -> WorldTime:
    return WorldTime(year=1, season="spring", day=day, moment=moment)


def make_player(location: str = "loc_tavern") -> PlayerEntity:
    meta = EntityMeta(
        created_at=make_world_time(),
        created_by="system",
        status=EntityStatus.ACTIVE,
    )
    identity = EntityIdentity(name="Elan Morin", age=25, gender="m")
    return PlayerEntity(
        id="player_elan",
        meta=meta,
        identity=identity,
        mechanical={"location_id": location},
    )


def make_npc(npc_id: str, name: str, location: str) -> NPCEntity:
    meta = EntityMeta(
        created_at=make_world_time(),
        created_by="system",
        status=EntityStatus.ACTIVE,
    )
    identity = EntityIdentity(name=name, age=40, gender="m")
    behaviour = NPCBehaviour(faction_id="faction_iron_hand")
    return NPCEntity(
        id=npc_id,
        meta=meta,
        identity=identity,
        mechanical={"location_id": location},
        behaviour=behaviour,
    )


def make_event(
    verb: str,
    emitter_id: str,
    emitter_name: str,
    location_id: str,
    event_type: str = "conflict",
    scope: str = "regional",
    known_to: list[str] | None = None,
    clock: WorldClock | None = None,
    cascade_depth: int = 0,
    parent_event_id: str | None = None,
) -> GameEvent:
    wt = clock.world_time if clock else make_world_time()
    tick = clock.tick if clock else GameTick(0)
    return GameEvent(
        tick=tick,
        world_time=wt,
        type=event_type,
        verb=verb,
        emitter=EventActor(id=emitter_id, kind=EntityKind.NPC, name=emitter_name),
        visibility=EventVisibility(scope=scope, known_to=known_to or []),
        payload={"location_id": location_id},
        cascade_depth=cascade_depth,
        parent_event_id=parent_event_id,
    )


# ── Main demo ─────────────────────────────────────────────────────────────────

async def run_demo() -> None:
    rng = random.Random(42)  # seed fisso per risultati riproducibili

    sep("AGENTIC DUNGEONS — Game Engine Demo", "═")
    print(f"\n{DIM}Fasi implementate: 1 (Modelli), 2 (Visibilità + Persistenza), 3 (ConsequenceEngine){RESET}")
    print(f"{DIM}Seed RNG: 42 (risultati deterministici){RESET}\n")

    # ── Inizializzazione componenti ───────────────────────────────────────────
    sep("Setup mondo")

    clock = WorldClock()
    ws = WorldState()
    cooldown = CooldownTracker()
    visibility_engine = VisibilityEngine()
    kb = PlayerKnowledgeBase(player_id="player_elan")
    consequence_engine = ConsequenceEngine(
        cooldown_tracker=cooldown,
        visibility_engine=visibility_engine,
        rng=rng,
    )

    # EventLogger in-memory
    event_log = EventLogger(":memory:")
    await event_log.open()
    await event_log.init_schema()

    # Entità
    player = make_player(location="loc_tavern")
    aldric = make_npc("npc_aldric", "Lord Aldric", "loc_fort_iron")
    mira = make_npc("npc_mira", "Lady Mira", "loc_tavern")

    ws.add_entity(player)
    ws.add_entity(aldric)
    ws.add_entity(mira)

    print(f"  Player: {BOLD}{player.identity.name}{RESET} @ {BLUE}{player.mechanical['location_id']}{RESET}")
    print(f"  NPC:    {BOLD}{aldric.identity.name}{RESET} @ {BLUE}{aldric.mechanical['location_id']}{RESET}")
    print(f"  NPC:    {BOLD}{mira.identity.name}{RESET} @ {BLUE}{mira.mechanical['location_id']}{RESET}")
    print(f"  Clock:  {tick_label(clock)}")

    # ── Scenario 1: Evento locale — il player è testimone diretto ────────────
    sep("Scenario 1 — Testimone Diretto")

    clock.advance_tick()
    event_brawl = make_event(
        verb=EventVerb.ATTACKED,
        emitter_id="npc_mira",
        emitter_name="Lady Mira",
        location_id="loc_tavern",   # stessa location del player!
        scope="local",
        clock=clock,
    )
    ws.append_event(event_brawl)
    await event_log.append(event_brawl)

    print(f"\n{tick_label(clock)}")
    print(f"  Evento: {fmt_event(event_brawl, '  ')}")

    update = visibility_engine.evaluate(event_brawl, player, ws)
    if update:
        kb.apply_update(update, event_brawl, clock.world_time)
        await event_log.mark_known(
            "player_elan", event_brawl.id,
            update.how_learned, update.certainty,
            clock.world_time.to_absolute_days(),
        )
        print(f"  {GREEN}✓ Player vede direttamente l'evento{RESET}")
        print(f"    → how_learned={BOLD}{update.how_learned}{RESET}, certainty={BOLD}{update.certainty}{RESET}")
    else:
        print(f"  {RED}✗ Player non vede l'evento{RESET}")

    # ── Scenario 2: Evento remoto — dichiarazione di guerra ──────────────────
    sep("Scenario 2 — Dichiarazione di Guerra (remota)")

    clock.advance_world_time("travel_long")   # avanza tempo narrativo
    clock.advance_tick()

    event_war = make_event(
        verb=EventVerb.DECLARED_WAR,
        emitter_id="npc_aldric",
        emitter_name="Lord Aldric",
        location_id="loc_fort_iron",   # lontano dal player
        scope="regional",
        clock=clock,
    )
    ws.append_event(event_war)
    await event_log.append(event_war)

    print(f"\n{tick_label(clock)}")
    print(f"  Evento: {fmt_event(event_war, '  ')}")

    # Visibilità diretta — player non è lì
    update = visibility_engine.evaluate(event_war, player, ws)
    if update:
        kb.apply_update(update, event_war, clock.world_time)
        print(f"  {GREEN}✓ Player apprende l'evento: {update.how_learned}{RESET}")
    else:
        print(f"  {YELLOW}~ Player non vede l'evento direttamente{RESET}")
        print(f"    → Viene processato dal ConsequenceEngine...")

    # ConsequenceEngine elabora la guerra
    consequences = consequence_engine.process_event(
        event_war, ws, clock, player=player, player_kb=kb
    )

    current_day = clock.world_time.to_absolute_days()
    print(f"\n  {BOLD}ConsequenceEngine:{RESET} {len(consequences)} eventi immediati generati")
    print(f"  {BOLD}ScheduledEvents:{RESET} {len(ws.scheduled_events)} eventi programmati")
    for sc in ws.scheduled_events:
        days_from_now = sc.trigger_world_day - current_day
        verb = sc.event_template.get("verb", "?")
        print(f"    → {CYAN}{verb.upper()}{RESET} in ~{days_from_now} giorni narrativi")

    # ── Scenario 3: Il player sente un rumor ─────────────────────────────────
    sep("Scenario 3 — Rumor (scope regional)")

    clock.advance_tick()

    event_rumor = make_event(
        verb=EventVerb.RUMORED,
        emitter_id="npc_bard",
        emitter_name="Il Bardo",
        location_id="loc_crossroads",
        event_type="social",
        scope="regional",   # raggiunge tutti
        clock=clock,
    )
    ws.append_event(event_rumor)
    await event_log.append(event_rumor)

    print(f"\n{tick_label(clock)}")
    print(f"  Evento: {fmt_event(event_rumor, '  ')}")

    update = visibility_engine.evaluate(event_rumor, player, ws)
    if update:
        kb.apply_update(update, event_rumor, clock.world_time)
        await event_log.mark_known(
            "player_elan", event_rumor.id,
            update.how_learned, update.certainty,
            clock.world_time.to_absolute_days(),
        )
        print(f"  {MAGENTA}✓ Player sente un rumor{RESET}")
        print(f"    → how_learned={BOLD}{update.how_learned}{RESET}, certainty={BOLD}{update.certainty}{RESET}")
        print(f"    → Rumor attivi nella KB: {len(kb.active_rumors)}")

    # ── Scenario 4: Fast-forward giorni narrativi (SKIP simulato) ────────────
    sep("Scenario 4 — Salto temporale (SKIP simulato)")

    days_to_skip = 12
    print(f"\n  Salto di {BOLD}{days_to_skip} giorni narrativi{RESET}...")

    for d in range(days_to_skip):
        clock.advance_world_time("rest_full")   # 20 world_units = 1 giorno narrativo
        clock.advance_tick()

    current_day = clock.world_time.to_absolute_days()
    print(f"  {tick_label(clock)}")
    print(f"  Giorno assoluto: {BOLD}{current_day}{RESET}")

    # Processa gli eventi schedulati scaduti
    processor = ScheduledEventProcessor(consequence_engine)
    triggered = processor.run(ws, clock, player=player, player_kb=kb)

    print(f"\n  {BOLD}ScheduledEventProcessor:{RESET} {len(triggered)} eventi scaduti elaborati")
    for ev in triggered:
        print(f"    {fmt_event(ev, '  → ')}")
        update = visibility_engine.evaluate(ev, player, ws)
        if update:
            print(f"       {GREEN}↳ Player viene informato: {update.how_learned} ({update.certainty}){RESET}")
            await event_log.append(ev)
            await event_log.mark_known(
                "player_elan", ev.id,
                update.how_learned, update.certainty,
                current_day,
            )

    remaining = len(ws.scheduled_events)
    print(f"  ScheduledEvents rimanenti: {remaining}")

    # ── Riepilogo PlayerKnowledgeBase ─────────────────────────────────────────
    sep("Riepilogo — PlayerKnowledgeBase")

    event_map = {e.id: e for e in ws.event_log}
    known = kb.known_events

    print(f"\n  Il player {BOLD}{player.identity.name}{RESET} conosce {BOLD}{len(known)}{RESET} eventi:\n")
    for entry in known:
        ev = event_map.get(entry.event_id)
        if ev:
            print(fmt_kb_entry(entry, ev))

    print(f"\n  Rumor attivi: {BOLD}{len(kb.active_rumors)}{RESET}")
    for rumor_id in kb.active_rumors:
        ev = event_map.get(rumor_id)
        if ev:
            print(f"  {MAGENTA}? {ev.verb.upper()} by {ev.emitter.name}{RESET}")

    # ── Riepilogo EventLog SQLite ─────────────────────────────────────────────
    sep("Riepilogo — EventLog SQLite")

    all_events = await event_log.query_since(world_day=0)
    player_events = await event_log.query_since(world_day=0, player_id="player_elan")

    print(f"\n  Totale eventi nel DB:           {BOLD}{len(all_events)}{RESET}")
    print(f"  Eventi noti al player nel DB:   {BOLD}{len(player_events)}{RESET}")

    if player_events:
        print(f"\n  Dettaglio eventi noti (dal DB):")
        for row in player_events:
            lrn = row.get("how_learned", "?")
            cert = row.get("certainty", 0)
            cert_color = GREEN if cert >= 0.9 else YELLOW if cert >= 0.5 else MAGENTA
            print(
                f"  {cert_color}[{lrn} {cert:.1f}]{RESET}"
                f" {row['verb'].upper()} by {row['emitter_name']}"
            )

    # ── Stato motore ──────────────────────────────────────────────────────────
    sep("Stato Motore")

    print(f"""
  {BOLD}WorldClock{RESET}
    Tick:          {clock.tick.value}
    WorldTime:     {clock.world_time}
    Giorno ass.:   {clock.world_time.to_absolute_days()}

  {BOLD}WorldState{RESET}
    Entità:        {len(ws.entity_store)}
    Eventi log:    {len(ws.event_log)}
    Scheduled:     {len(ws.scheduled_events)}
    Cooldowns:     {len(cooldown._last_triggered)}

  {BOLD}PlayerKnowledgeBase{RESET}
    Noti:          {len(kb.known_events)}
    Rumor attivi:  {len(kb.active_rumors)}
    Entità note:   {len(kb.known_entities)}

  {BOLD}EventLogger (SQLite :memory:){RESET}
    Tot. eventi:   {len(all_events)}
    Noti al player:{len(player_events)}
""")

    sep("Fasi mancanti", "─")
    print(f"""
  {DIM}Fase 4 — Tick System & World Loop (asyncio): non implementata
  Fase 5 — Context Slice System (per gli agenti AI): non implementata
  Fase 6 — PlayerIntent & Interaction Manager: non implementata
  Fase 7 — AI Agents (Anthropic SDK): non implementata
  Fase 8 — Persistenza completa (msgpack snapshots): non implementata
  Fase 9 — Bridge completo: stub
  Fase 10 — Playtest & Tuning: non implementata{RESET}
""")

    await event_log.close()
    sep("Fine demo", "═")


if __name__ == "__main__":
    asyncio.run(run_demo())
