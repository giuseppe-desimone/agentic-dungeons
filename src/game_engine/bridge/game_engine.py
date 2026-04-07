"""Bridge verso il Game Engine esterno.

Questo modulo è il confine tra il World Engine (AI Layer) e il Game Engine
che gestisce meccaniche di combattimento, movimento, inventario e XP.

Regola critica: il combat NON fa avanzare il WorldTime — è il Game Engine
che gestisce la durata del combattimento. Solo movement e azioni lente
avanzano il tempo narrativo.

Stato: STUB — le implementazioni saranno aggiunte in Fase 9.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..models.entity import NPCEntity
from ..engine.world_state import WorldState
from ..engine.world_clock import WorldClock

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED_MSG = "Bridge non implementato (Fase 9). Nessuna azione eseguita."


def spawn_entity(
    npc: NPCEntity,
    location_id: str,
    world_state: WorldState,
) -> None:
    """Registra un NPC generato dall'AI nel WorldState.

    Chiamato dopo la pipeline: AI → validazione Pydantic → Game Engine → WorldState.
    Non avanza il WorldTime.

    Args:
        npc: L'entità NPC validata da iniettare nel mondo.
        location_id: Location in cui spawnare l'NPC.
        world_state: Il world state globale da aggiornare.
    """
    logger.warning(_NOT_IMPLEMENTED_MSG)


def resolve_combat(
    attacker_id: str,
    defender_id: str,
    world_state: WorldState,
) -> dict[str, Any]:
    """Esegue un combattimento tra due entità.

    IMPORTANTE: NON chiama advance_world_time. Il tempo di combattimento
    è gestito internamente dal Game Engine, non dal WorldClock.

    Args:
        attacker_id: entity_id dell'attaccante.
        defender_id: entity_id del difensore.
        world_state: Il world state globale.

    Returns:
        Risultato del combattimento (dict con outcome, danni, ecc.).
    """
    logger.warning(_NOT_IMPLEMENTED_MSG)
    return {}


def apply_movement(
    entity_id: str,
    from_location_id: str,
    to_location_id: str,
    movement_type: str,
    world_state: WorldState,
    world_clock: WorldClock,
) -> None:
    """Sposta un'entità tra due location e avanza il WorldTime.

    A differenza del combat, il movimento avanza il tempo narrativo
    chiamando world_clock.advance_world_time con il tipo di viaggio corretto.

    Args:
        entity_id: entity_id da spostare.
        from_location_id: Location di partenza.
        to_location_id: Location di destinazione.
        movement_type: "travel_short" | "travel_medium" | "travel_long".
        world_state: Il world state globale.
        world_clock: Il WorldClock da aggiornare.
    """
    logger.warning(_NOT_IMPLEMENTED_MSG)


def apply_inventory(
    entity_id: str,
    item_id: str,
    action: str,
    world_state: WorldState,
) -> Optional[str]:
    """Applica un'azione di inventario e genera l'evento corrispondente.

    Genera TRADED per scambi/acquisti, STOLEN per furti.

    Args:
        entity_id: entity_id che esegue l'azione.
        item_id: entity_id dell'oggetto.
        action: "give" | "take" | "steal" | "drop".
        world_state: Il world state globale.

    Returns:
        event_id dell'evento generato, None se non implementato.
    """
    logger.warning(_NOT_IMPLEMENTED_MSG)
    return None


def apply_xp(
    entity_id: str,
    amount: int,
    world_state: WorldState,
) -> Optional[str]:
    """Assegna XP a un'entità e genera LEVELED se raggiunge la soglia.

    Args:
        entity_id: entity_id del destinatario.
        amount: Quantità di XP da assegnare.
        world_state: Il world state globale.

    Returns:
        event_id dell'evento LEVELED generato, None se non c'è level up.
    """
    logger.warning(_NOT_IMPLEMENTED_MSG)
    return None
