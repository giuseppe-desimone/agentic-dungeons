"""Bridge verso il Game Engine esterno — implementazione completa (Fase 9).

Questo modulo è il confine tra il World Engine (AI Layer) e il Game Engine
che gestisce meccaniche di combattimento, movimento, inventario e XP.

Regole critiche:
- Combat NON avanza WorldTime — il Game Engine gestisce la durata interna.
- Movement AVANZA WorldTime via advance_world_time(movement_type).
- Ogni operazione genera un GameEvent nel WorldState (append-only).
- Le firme includono world_clock dove necessario per timestamp e avanzamento.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..engine.world_clock import WorldClock
from ..engine.world_state import WorldState
from ..models.base import EntityKind
from ..models.entity import NPCEntity
from ..models.event import EventActor, EventVerb, EventVisibility, GameEvent

logger = logging.getLogger(__name__)

# Soglia XP per level-up: ogni livello richiede level * XP_PER_LEVEL XP totali.
# Es: level 1 → 100 XP; level 2 → 200 XP; level 3 → 300 XP.
XP_PER_LEVEL: int = 100


def spawn_entity(
    npc: NPCEntity,
    location_id: str,
    world_state: WorldState,
    world_clock: WorldClock,
) -> str:
    """Registra un NPC generato dall'AI nel WorldState e genera SPAWNED event.

    Chiamato dopo la pipeline: AI → validazione Pydantic → spawn_entity → WorldState.
    Non avanza il WorldTime.

    Args:
        npc: L'entità NPC validata da iniettare nel mondo.
        location_id: Location in cui spawnare l'NPC.
        world_state: Il world state globale da aggiornare.
        world_clock: Il WorldClock corrente (per timestamp e tick).

    Returns:
        event_id dell'evento SPAWNED generato.
    """
    # Aggiorna la location del NPC
    npc_placed = npc.model_copy(
        update={"mechanical": {**npc.mechanical, "location_id": location_id}}
    )
    world_state.add_entity(npc_placed)

    # Genera evento SPAWNED
    tick = world_clock.advance_tick()
    event = GameEvent(
        tick=tick,
        world_time=world_clock.world_time,
        type="existence",
        verb=EventVerb.SPAWNED,
        emitter=EventActor(
            id=npc_placed.id,
            kind=EntityKind.NPC,
            name=npc_placed.identity.name,
        ),
        visibility=EventVisibility(scope="local"),
        payload={"location_id": location_id},
    )
    world_state.append_event(event)

    logger.debug("spawn_entity: %s spawned at %s (event=%s)", npc_placed.identity.name, location_id, event.id)
    return event.id


def resolve_combat(
    attacker_id: str,
    defender_id: str,
    world_state: WorldState,
    world_clock: WorldClock,
) -> dict[str, Any]:
    """Esegue un combattimento tra due entità e genera ATTACKED event.

    IMPORTANTE: NON chiama advance_world_time. Il tempo di combattimento
    è gestito internamente dal Game Engine, non dal WorldClock.

    Args:
        attacker_id: entity_id dell'attaccante.
        defender_id: entity_id del difensore.
        world_state: Il world state globale.
        world_clock: Il WorldClock corrente (per timestamp e tick, NON per advance_world_time).

    Returns:
        Dict con: event_id, attacker_id, defender_id, outcome.

    Raises:
        ValueError: Se attacker o defender non trovati nel WorldState.
    """
    attacker = world_state.get_entity(attacker_id)
    if attacker is None:
        raise ValueError(f"Attaccante non trovato: {attacker_id}")

    defender = world_state.get_entity(defender_id)
    if defender is None:
        raise ValueError(f"Difensore non trovato: {defender_id}")

    # NON advance_world_time — il combat non avanza il tempo narrativo
    tick = world_clock.advance_tick()

    location_id = attacker.mechanical.get("location_id") if hasattr(attacker, "mechanical") else None

    event = GameEvent(
        tick=tick,
        world_time=world_clock.world_time,
        type="conflict",
        verb=EventVerb.ATTACKED,
        emitter=EventActor(
            id=attacker.id,
            kind=attacker.kind,
            name=attacker.identity.name,
        ),
        target=EventActor(
            id=defender.id,
            kind=defender.kind,
            name=defender.identity.name,
        ),
        visibility=EventVisibility(scope="local"),
        payload={"location_id": location_id} if location_id else {},
    )
    world_state.append_event(event)

    logger.debug(
        "resolve_combat: %s → %s (event=%s)",
        attacker.identity.name, defender.identity.name, event.id,
    )
    return {
        "event_id": event.id,
        "attacker_id": attacker_id,
        "defender_id": defender_id,
        "outcome": "attacked",
    }


def apply_movement(
    entity_id: str,
    from_location_id: str,
    to_location_id: str,
    movement_type: str,
    world_state: WorldState,
    world_clock: WorldClock,
) -> str:
    """Sposta un'entità tra due location, avanza il WorldTime e genera MIGRATED event.

    A differenza del combat, il movimento avanza il tempo narrativo
    chiamando world_clock.advance_world_time(movement_type).

    Args:
        entity_id: entity_id da spostare.
        from_location_id: Location di partenza.
        to_location_id: Location di destinazione.
        movement_type: "travel_short" | "travel_medium" | "travel_long".
        world_state: Il world state globale.
        world_clock: Il WorldClock da aggiornare.

    Returns:
        event_id dell'evento MIGRATED generato.

    Raises:
        ValueError: Se l'entità non viene trovata nel WorldState.
    """
    entity = world_state.get_entity(entity_id)
    if entity is None:
        raise ValueError(f"Entità non trovata: {entity_id}")

    # Aggiorna la location dell'entità
    if hasattr(entity, "mechanical"):
        updated = entity.model_copy(
            update={"mechanical": {**entity.mechanical, "location_id": to_location_id}}
        )
        world_state.update_entity(updated)
    else:
        logger.warning("apply_movement: entity %s non ha campo 'mechanical'", entity_id)

    # Il movimento avanza il WorldTime — questa è la differenza fondamentale rispetto al combat
    world_clock.advance_world_time(movement_type)
    tick = world_clock.advance_tick()

    event = GameEvent(
        tick=tick,
        world_time=world_clock.world_time,
        type="world",
        verb=EventVerb.MIGRATED,
        emitter=EventActor(
            id=entity.id,
            kind=entity.kind,
            name=entity.identity.name,
        ),
        visibility=EventVisibility(scope="local"),
        payload={
            "location_id": to_location_id,
            "from_location_id": from_location_id,
            "movement_type": movement_type,
        },
    )
    world_state.append_event(event)

    logger.debug(
        "apply_movement: %s %s → %s (event=%s)",
        entity.identity.name, from_location_id, to_location_id, event.id,
    )
    return event.id


def apply_inventory(
    entity_id: str,
    item_id: str,
    action: str,
    world_state: WorldState,
    world_clock: WorldClock,
) -> str:
    """Applica un'azione di inventario e genera l'evento corrispondente.

    Genera TRADED per scambi/acquisti/drop, STOLEN per furti.

    Args:
        entity_id: entity_id che esegue l'azione.
        item_id: entity_id o identificatore dell'oggetto.
        action: "give" | "take" | "drop" → TRADED; "steal" → STOLEN.
        world_state: Il world state globale.
        world_clock: Il WorldClock corrente (per timestamp e tick).

    Returns:
        event_id dell'evento generato.

    Raises:
        ValueError: Se l'entità non viene trovata.
    """
    entity = world_state.get_entity(entity_id)
    if entity is None:
        raise ValueError(f"Entità non trovata: {entity_id}")

    verb = EventVerb.STOLEN if action == "steal" else EventVerb.TRADED
    tick = world_clock.advance_tick()

    event = GameEvent(
        tick=tick,
        world_time=world_clock.world_time,
        type="economy",
        verb=verb,
        emitter=EventActor(
            id=entity.id,
            kind=entity.kind,
            name=entity.identity.name,
        ),
        visibility=EventVisibility(scope="local"),
        payload={
            "item_id": item_id,
            "action": action,
        },
    )
    world_state.append_event(event)

    logger.debug(
        "apply_inventory: %s %s item=%s (event=%s)",
        entity.identity.name, action, item_id, event.id,
    )
    return event.id


def apply_xp(
    entity_id: str,
    amount: int,
    world_state: WorldState,
    world_clock: WorldClock,
) -> Optional[str]:
    """Assegna XP a un'entità e genera LEVELED se raggiunge la soglia.

    La soglia di level-up è: xp_totali >= livello_corrente * XP_PER_LEVEL.
    Esempio: livello 1 → 100 XP; livello 2 → 200 XP aggiuntivi; ecc.

    Args:
        entity_id: entity_id del destinatario.
        amount: Quantità di XP da assegnare.
        world_state: Il world state globale.
        world_clock: Il WorldClock corrente (per timestamp e tick).

    Returns:
        event_id dell'evento LEVELED generato, None se non c'è level-up.

    Raises:
        ValueError: Se l'entità non viene trovata o non ha campo 'mechanical'.
    """
    entity = world_state.get_entity(entity_id)
    if entity is None:
        raise ValueError(f"Entità non trovata: {entity_id}")
    if not hasattr(entity, "mechanical"):
        raise ValueError(f"Entità {entity_id} non ha campo 'mechanical'")

    old_xp: int = entity.mechanical.get("xp", 0)
    old_level: int = entity.mechanical.get("level", 1)
    new_xp = old_xp + amount

    leveled_up = new_xp >= old_level * XP_PER_LEVEL
    new_level = old_level + 1 if leveled_up else old_level

    # Aggiorna entità
    updated_mechanical = {**entity.mechanical, "xp": new_xp, "level": new_level}
    updated = entity.model_copy(update={"mechanical": updated_mechanical})
    world_state.update_entity(updated)

    if not leveled_up:
        logger.debug("apply_xp: %s +%d XP (total=%d, no level-up)", entity_id, amount, new_xp)
        return None

    # Genera LEVELED event
    tick = world_clock.advance_tick()
    event = GameEvent(
        tick=tick,
        world_time=world_clock.world_time,
        type="personal",
        verb=EventVerb.LEVELED,
        emitter=EventActor(
            id=entity.id,
            kind=entity.kind,
            name=entity.identity.name,
        ),
        visibility=EventVisibility(scope="private"),
        payload={
            "old_level": old_level,
            "new_level": new_level,
            "xp_total": new_xp,
        },
    )
    world_state.append_event(event)

    logger.debug(
        "apply_xp: %s +%d XP → LEVELED %d→%d (event=%s)",
        entity_id, amount, old_level, new_level, event.id,
    )
    return event.id
