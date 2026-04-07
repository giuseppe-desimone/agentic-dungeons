"""ConsequenceEngine: regole causa-effetto tra eventi nel world state.

Principio: ogni evento nel mondo può generare conseguenze — immediate o ritardate.
Il ConsequenceEngine opera SEMPRE sul world state globale, mai sulla PlayerKnowledgeBase.
La separazione player/world è garantita dal VisibilityEngine, chiamato dopo ogni append.

Flusso corretto:
    1. ConsequenceEngine.process_event(event, world_state, world_clock)
    2.   → world_state.append_event(consequence_event)
    3.   → VisibilityEngine.evaluate(consequence_event, player, world_state)
    4.   → se KnowledgeUpdate → player_knowledge.apply_update(update, event, world_time)

Il ConsequenceEngine NON chiama advance_world_time — è il WorldLoop (Fase 4) che scandisce.

Anti-rumore: ogni (entity_id, verb) ha un cooldown di 3 giorni narrativi.
Cascate: cascade_depth max 5 per evitare loop infiniti.
Ritardi: le conseguenze ritardate usano WorldState.schedule_event().
"""

from __future__ import annotations

import logging
import random as random_module
from dataclasses import dataclass, field
from typing import Optional

from ..models.base import GameTick, WorldTime
from ..models.entity import PlayerEntity
from ..models.event import EventActor, EventVisibility, GameEvent
from .cooldown import CooldownTracker
from .knowledge import PlayerKnowledgeBase, VisibilityEngine
from .world_state import ScheduledEvent, WorldState
from .world_clock import WorldClock

logger = logging.getLogger(__name__)

MAX_CASCADE_DEPTH: int = 5


# ── Regole ────────────────────────────────────────────────────────────────────

@dataclass
class ConsequenceRule:
    """Una regola causa-effetto tra eventi.

    Args:
        trigger_verb: Verb dell'evento che attiva la regola.
        consequence_verb: Verb dell'evento conseguente generato.
        consequence_type: Categoria semantica della conseguenza.
        delay_min_days: Delay minimo in giorni narrativi (0 = immediato).
        delay_max_days: Delay massimo in giorni narrativi (0 = immediato).
        visibility_scope: Scope di visibilità dell'evento conseguente.
    """

    trigger_verb: str
    consequence_verb: str
    consequence_type: str
    delay_min_days: int
    delay_max_days: int
    visibility_scope: str = "regional"


# ── Conflitto ─────────────────────────────────────────────────────────────────
CONFLICT_RULES: list[ConsequenceRule] = [
    ConsequenceRule("declared_war",  "sieged",        "conflict", 5,  15),
    ConsequenceRule("attacked",      "retaliated",    "conflict", 1,  3),
    ConsequenceRule("raided",        "retaliated",    "conflict", 2,  5),
    ConsequenceRule("assassinated",  "rivaled",       "social",   0,  0),
    ConsequenceRule("massacred",     "declared_war",  "conflict", 1,  3),
    ConsequenceRule("sieged",        "surrendered",   "conflict", 10, 30),
]

# ── Sociale ───────────────────────────────────────────────────────────────────
SOCIAL_RULES: list[ConsequenceRule] = [
    ConsequenceRule("betrayed",      "rivaled",       "social",   0, 0),
    ConsequenceRule("joined",        "allied",        "social",   3, 7),
    ConsequenceRule("pledged",       "bonded",        "social",   1, 2),
    ConsequenceRule("abandoned",     "estranged",     "social",   0, 1),
    ConsequenceRule("subjugated",    "demoralized",   "personal", 0, 2),
]

# ── Religione ─────────────────────────────────────────────────────────────────
RELIGION_RULES: list[ConsequenceRule] = [
    ConsequenceRule("desecrated",    "declared_heresy", "religion", 1, 3),
    ConsequenceRule("converted",     "proselytized",    "religion", 2, 5),
    ConsequenceRule("schismed",      "rivaled",         "social",   0, 1),
    ConsequenceRule("canonized",     "motivated",       "personal", 0, 1),
]

ALL_RULES: list[ConsequenceRule] = CONFLICT_RULES + SOCIAL_RULES + RELIGION_RULES

# Indice per lookup rapido: trigger_verb → lista di regole
_RULES_BY_TRIGGER: dict[str, list[ConsequenceRule]] = {}
for _rule in ALL_RULES:
    _RULES_BY_TRIGGER.setdefault(_rule.trigger_verb, []).append(_rule)


# ── ConsequenceEngine ─────────────────────────────────────────────────────────

class ConsequenceEngine:
    """Applica le regole causa-effetto agli eventi del world state.

    Non conosce il player direttamente — riceve PlayerEntity e PlayerKnowledgeBase
    come parametri per aggiornare la conoscenza dopo ogni evento generato.

    Args:
        cooldown_tracker: Traccia i cooldown per evitare rumore.
        visibility_engine: Valuta cosa il player può conoscere.
        rng: Random number generator iniettabile (per test deterministici).
    """

    def __init__(
        self,
        cooldown_tracker: CooldownTracker,
        visibility_engine: VisibilityEngine,
        rng: Optional[random_module.Random] = None,
    ) -> None:
        self._cooldown = cooldown_tracker
        self._visibility = visibility_engine
        self._rng = rng or random_module.Random()

    def process_event(
        self,
        event: GameEvent,
        world_state: WorldState,
        world_clock: WorldClock,
        player: Optional[PlayerEntity] = None,
        player_kb: Optional[PlayerKnowledgeBase] = None,
    ) -> list[GameEvent]:
        """Elabora un evento e genera le sue conseguenze.

        Controlla il cooldown, applica le regole matching, genera conseguenze
        immediate (con cascata) o ritardate (schedule). Aggiorna la
        PlayerKnowledgeBase via VisibilityEngine per ogni evento immediato.

        Args:
            event: L'evento trigger da elaborare.
            world_state: Il world state globale.
            world_clock: Il WorldClock corrente (per il giorno narrativo).
            player: Il PlayerEntity corrente (opzionale — necessario per KB update).
            player_kb: La PlayerKnowledgeBase (opzionale — necessario per KB update).

        Returns:
            Lista degli eventi immediati generati (non include quelli schedulati).
        """
        # Guard: cascade troppo profonda
        if event.cascade_depth >= MAX_CASCADE_DEPTH:
            logger.debug(
                "cascade_depth=%d raggiunto per evento %s — stop cascata.",
                event.cascade_depth,
                event.id,
            )
            return []

        current_day = world_clock.world_time.to_absolute_days()
        emitter_id = event.emitter.id
        verb = event.verb

        # Cooldown check — anti-rumore
        if self._cooldown.is_on_cooldown(emitter_id, verb, current_day):
            logger.debug(
                "Cooldown attivo per (%s, %s) — conseguenze ignorate.",
                emitter_id,
                verb,
            )
            return []

        rules = _RULES_BY_TRIGGER.get(verb, [])
        if not rules:
            return []

        # Registra cooldown PRIMA di generare conseguenze (anti-doppio trigger)
        self._cooldown.set_cooldown(emitter_id, verb, current_day)

        immediate: list[GameEvent] = []

        for rule in rules:
            consequence = self._build_consequence(event, rule, world_clock)

            if rule.delay_min_days == 0 and rule.delay_max_days == 0:
                # Conseguenza immediata
                world_state.append_event(consequence)
                world_clock.advance_tick()
                immediate.append(consequence)

                # Aggiorna PlayerKnowledgeBase se disponibile
                if player is not None and player_kb is not None:
                    update = self._visibility.evaluate(consequence, player, world_state)
                    if update is not None:
                        player_kb.apply_update(update, consequence, world_clock.world_time)

                # Ricorsione (cascata)
                sub = self.process_event(consequence, world_state, world_clock, player, player_kb)
                immediate.extend(sub)

            else:
                # Conseguenza ritardata → schedule
                delay = self._rng.randint(rule.delay_min_days, rule.delay_max_days)
                trigger_day = current_day + delay
                scheduled = ScheduledEvent(
                    trigger_world_day=trigger_day,
                    created_at=world_clock.world_time,
                    created_by_event_id=event.id,
                    event_template={
                        "verb": rule.consequence_verb,
                        "type": rule.consequence_type,
                        "emitter_id": emitter_id,
                        "emitter_kind": event.emitter.kind,
                        "emitter_name": event.emitter.name,
                        "target_id": event.target.id if event.target else None,
                        "target_kind": event.target.kind if event.target else None,
                        "target_name": event.target.name if event.target else None,
                        "visibility_scope": rule.visibility_scope,
                        "cascade_depth": event.cascade_depth + 1,
                        "parent_event_id": event.id,
                    },
                )
                world_state.schedule_event(scheduled)
                logger.debug(
                    "Conseguenza ritardata: %s → %s tra %d giorni (trigger day %d).",
                    verb,
                    rule.consequence_verb,
                    delay,
                    trigger_day,
                )

        return immediate

    def _build_consequence(
        self,
        trigger_event: GameEvent,
        rule: ConsequenceRule,
        world_clock: WorldClock,
    ) -> GameEvent:
        """Costruisce un GameEvent conseguente da una regola.

        L'emittente della conseguenza è lo stesso dell'evento trigger.
        Il tick viene avanzato dal WorldClock.

        Args:
            trigger_event: L'evento che ha scatenato la regola.
            rule: La regola applicata.
            world_clock: Il WorldClock corrente.

        Returns:
            Il GameEvent conseguente (non ancora appendato al world state).
        """
        return GameEvent(
            tick=world_clock.tick + 1,
            world_time=world_clock.world_time,
            cascade_depth=trigger_event.cascade_depth + 1,
            parent_event_id=trigger_event.id,
            type=rule.consequence_type,
            verb=rule.consequence_verb,
            emitter=trigger_event.emitter,
            target=trigger_event.target,
            payload=dict(trigger_event.payload),  # copia shallow del payload
            visibility=EventVisibility(scope=rule.visibility_scope),
        )


# ── ScheduledEventProcessor ───────────────────────────────────────────────────

class ScheduledEventProcessor:
    """Elabora gli eventi schedulati scaduti ogni DAILY tick.

    Chiamato dal TickScheduler (Fase 4) nella fase "consequence" del DAILY tick.
    Per ogni ScheduledEvent scaduto, genera il GameEvent corrispondente e lo
    processa attraverso il ConsequenceEngine.

    Args:
        consequence_engine: Il ConsequenceEngine da usare per elaborare gli eventi.
    """

    def __init__(self, consequence_engine: ConsequenceEngine) -> None:
        self._engine = consequence_engine

    def run(
        self,
        world_state: WorldState,
        world_clock: WorldClock,
        player: Optional[PlayerEntity] = None,
        player_kb: Optional[PlayerKnowledgeBase] = None,
    ) -> list[GameEvent]:
        """Elabora tutti gli eventi schedulati con trigger_world_day <= giorno corrente.

        Args:
            world_state: Il world state globale.
            world_clock: Il WorldClock corrente.
            player: Il PlayerEntity corrente (opzionale).
            player_kb: La PlayerKnowledgeBase (opzionale).

        Returns:
            Lista di tutti gli eventi generati dagli scheduled events scaduti.
        """
        current_day = world_clock.world_time.to_absolute_days()
        due = world_state.pop_due_events(current_day)

        if not due:
            return []

        all_generated: list[GameEvent] = []
        for scheduled in due:
            event = self._build_from_template(scheduled, world_clock)
            world_state.append_event(event)
            world_clock.advance_tick()

            # Aggiorna KB per l'evento schedulato stesso
            if player is not None and player_kb is not None:
                update = self._engine._visibility.evaluate(event, player, world_state)
                if update is not None:
                    player_kb.apply_update(update, event, world_clock.world_time)

            # Propaga conseguenze (cascata dal scheduled)
            sub = self._engine.process_event(event, world_state, world_clock, player, player_kb)
            all_generated.append(event)
            all_generated.extend(sub)

        logger.debug(
            "ScheduledEventProcessor: %d scheduled elaborati, %d eventi generati.",
            len(due),
            len(all_generated),
        )
        return all_generated

    def _build_from_template(
        self,
        scheduled: ScheduledEvent,
        world_clock: WorldClock,
    ) -> GameEvent:
        """Costruisce un GameEvent da un ScheduledEvent template.

        Args:
            scheduled: Lo scheduled event scaduto.
            world_clock: Il WorldClock corrente.

        Returns:
            Il GameEvent da appendare al world state.
        """
        tmpl = scheduled.event_template
        emitter = EventActor(
            id=tmpl["emitter_id"],
            kind=tmpl["emitter_kind"],
            name=tmpl["emitter_name"],
        )
        target: Optional[EventActor] = None
        if tmpl.get("target_id"):
            target = EventActor(
                id=tmpl["target_id"],
                kind=tmpl["target_kind"],
                name=tmpl["target_name"],
            )
        return GameEvent(
            tick=world_clock.tick + 1,
            world_time=world_clock.world_time,
            cascade_depth=tmpl.get("cascade_depth", 0),
            parent_event_id=tmpl.get("parent_event_id"),
            type=tmpl["type"],
            verb=tmpl["verb"],
            emitter=emitter,
            target=target,
            visibility=EventVisibility(scope=tmpl.get("visibility_scope", "regional")),
        )
