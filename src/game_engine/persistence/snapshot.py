"""SnapshotManager — serializzazione/deserializzazione via msgpack.

Strategia:
    Serializzazione manuale → plain Python dict/list/primitives
    msgpack.packb(data)     → bytes su disco
    msgpack.unpackb(bytes)  → dict
    Model.model_validate()  → ricostruisce i modelli Pydantic

WorldState è una plain Python class (non Pydantic) — serializzazione manuale.
PlayerKnowledgeBase IS Pydantic — usa model_dump/model_validate direttamente.

Le entità sono serializzate con model_dump(mode='json') e ricostruite
usando il campo 'kind' per dispatch tra NPCEntity e PlayerEntity.

Aggiornato ogni DAILY tick per il WorldState, ad ogni evento per la PlayerKnowledgeBase.
"""

from __future__ import annotations

import logging
from pathlib import Path

import msgpack

from ..engine.knowledge import PlayerKnowledgeBase
from ..engine.world_state import ScheduledEvent, WorldState
from ..models.entity import NPCEntity, PlayerEntity
from ..models.event import GameEvent

logger = logging.getLogger(__name__)

_ENTITY_KIND_MAP = {
    "npc": NPCEntity,
    "player": PlayerEntity,
}


def _serialize_world_state(world_state: WorldState) -> dict:
    """Serializza WorldState in un plain dict JSON-safe."""
    return {
        "entity_store": {
            k: v.model_dump(mode="json")
            for k, v in world_state.entity_store.items()
        },
        "event_log": [e.model_dump(mode="json") for e in world_state.event_log],
        "consequence_queue": [e.model_dump(mode="json") for e in world_state.consequence_queue],
        "scheduled_events": [s.model_dump(mode="json") for s in world_state.scheduled_events],
    }


def _deserialize_world_state(data: dict) -> WorldState:
    """Ricostruisce WorldState da un plain dict."""
    ws = WorldState()

    for entity_id, entity_data in data.get("entity_store", {}).items():
        kind = entity_data.get("kind", "npc")
        entity_cls = _ENTITY_KIND_MAP.get(kind, NPCEntity)
        entity = entity_cls.model_validate(entity_data)
        ws.entity_store[entity_id] = entity

    for event_data in data.get("event_log", []):
        ws.event_log.append(GameEvent.model_validate(event_data))

    for event_data in data.get("consequence_queue", []):
        ws.consequence_queue.append(GameEvent.model_validate(event_data))

    for sched_data in data.get("scheduled_events", []):
        ws.scheduled_events.append(ScheduledEvent.model_validate(sched_data))

    return ws


class SnapshotManager:
    """Serializza e deserializza WorldState e PlayerKnowledgeBase via msgpack.

    Stateless — tutti i metodi sono statici. Nessuna connessione persistente.
    """

    @staticmethod
    def save_world_state(world_state: WorldState, path: Path) -> None:
        """Serializza WorldState in msgpack. Sovrascrive il file se esiste.

        Args:
            world_state: World state globale da serializzare.
            path: Path del file di destinazione.
        """
        data = _serialize_world_state(world_state)
        path.write_bytes(msgpack.packb(data, use_bin_type=True))
        logger.debug("WorldState snapshot saved → %s (%d bytes)", path, path.stat().st_size)

    @staticmethod
    def load_world_state(path: Path) -> WorldState:
        """Carica WorldState da file msgpack.

        Args:
            path: Path del file snapshot.

        Returns:
            WorldState ricostruito.

        Raises:
            FileNotFoundError: Se il file non esiste.
        """
        if not path.exists():
            raise FileNotFoundError(f"WorldState snapshot non trovato: {path}")
        data = msgpack.unpackb(path.read_bytes(), raw=False)
        state = _deserialize_world_state(data)
        logger.debug("WorldState snapshot loaded ← %s (%d entities, %d events)",
                     path, len(state.entity_store), len(state.event_log))
        return state

    @staticmethod
    def save_knowledge_base(kb: PlayerKnowledgeBase, path: Path) -> None:
        """Serializza PlayerKnowledgeBase in msgpack.

        Args:
            kb: Knowledge base del player da serializzare.
            path: Path del file di destinazione.
        """
        data = kb.model_dump(mode="json")
        path.write_bytes(msgpack.packb(data, use_bin_type=True))
        logger.debug("PlayerKnowledgeBase snapshot saved → %s", path)

    @staticmethod
    def load_knowledge_base(path: Path) -> PlayerKnowledgeBase:
        """Carica PlayerKnowledgeBase da file msgpack.

        Args:
            path: Path del file snapshot.

        Returns:
            PlayerKnowledgeBase ricostruita.

        Raises:
            FileNotFoundError: Se il file non esiste.
        """
        if not path.exists():
            raise FileNotFoundError(f"PlayerKnowledgeBase snapshot non trovato: {path}")
        data = msgpack.unpackb(path.read_bytes(), raw=False)
        kb = PlayerKnowledgeBase.model_validate(data)
        logger.debug("PlayerKnowledgeBase snapshot loaded ← %s (%d known events)",
                     path, len(kb.known_events))
        return kb
