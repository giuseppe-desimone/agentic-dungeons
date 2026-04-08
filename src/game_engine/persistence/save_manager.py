"""SaveManager — gestisce la struttura completa del save directory.

Struttura save:
    save_dir/
    ├── world.db          # event log SQLite (gestito da EventLogger separatamente)
    ├── state.msgpack     # WorldState snapshot (aggiornato ogni DAILY tick)
    ├── knowledge.msgpack # PlayerKnowledgeBase snapshot (aggiornato ad ogni evento)
    └── config.json       # seed mondo, parametri di gioco, FLOW_RATIO

Il world state viene ricostruito dal snapshot — load istantaneo.
L'event log SQLite serve per history, debug, fast-forward location ibernate.
Compatible con PyInstaller/Nuitka: zero dipendenze da server esterni.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..engine.knowledge import PlayerKnowledgeBase
from ..engine.world_state import WorldState
from .snapshot import SnapshotManager

logger = logging.getLogger(__name__)

DEFAULT_SAVE_DIR: Path = Path.home() / ".agentic_dungeons" / "saves" / "default"

_STATE_FILE = "state.msgpack"
_KNOWLEDGE_FILE = "knowledge.msgpack"
_CONFIG_FILE = "config.json"
_DB_FILE = "world.db"


class SaveManager:
    """Gestisce la persistenza completa di una partita.

    Salva e carica WorldState, PlayerKnowledgeBase e configurazione.
    Il file SQLite (world.db) è gestito dall'EventLogger separatamente.

    Args:
        save_dir: Directory dove salvare i file. Default: ~/.agentic_dungeons/saves/default
    """

    def __init__(self, save_dir: Path = DEFAULT_SAVE_DIR) -> None:
        self.save_dir = save_dir
        self._snapshot = SnapshotManager()

    def save(
        self,
        world_state: WorldState,
        player_kb: PlayerKnowledgeBase,
        config: dict[str, Any],
    ) -> None:
        """Salva lo stato completo della partita.

        Crea la directory se non esiste. Sovrascrive i file esistenti.

        Args:
            world_state: World state globale da salvare.
            player_kb: Knowledge base del player da salvare.
            config: Dizionario di configurazione (seed, parametri, ecc.).
        """
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self._snapshot.save_world_state(world_state, self.save_dir / _STATE_FILE)
        self._snapshot.save_knowledge_base(player_kb, self.save_dir / _KNOWLEDGE_FILE)

        config_path = self.save_dir / _CONFIG_FILE
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))

        logger.info(
            "Save completato in %s (entities=%d, events=%d, known=%d)",
            self.save_dir,
            len(world_state.entity_store),
            len(world_state.event_log),
            len(player_kb.known_events),
        )

    def load(self) -> tuple[WorldState, PlayerKnowledgeBase, dict[str, Any]]:
        """Carica lo stato completo della partita.

        Args:
            Nessuno — usa self.save_dir.

        Returns:
            Tuple (WorldState, PlayerKnowledgeBase, config_dict).

        Raises:
            FileNotFoundError: Se uno dei file di save non esiste.
        """
        world_state = self._snapshot.load_world_state(self.save_dir / _STATE_FILE)
        player_kb = self._snapshot.load_knowledge_base(self.save_dir / _KNOWLEDGE_FILE)

        config_path = self.save_dir / _CONFIG_FILE
        if not config_path.exists():
            raise FileNotFoundError(f"Config non trovato: {config_path}")
        config = json.loads(config_path.read_text(encoding="utf-8"))

        logger.info(
            "Load completato da %s (entities=%d, events=%d, known=%d)",
            self.save_dir,
            len(world_state.entity_store),
            len(world_state.event_log),
            len(player_kb.known_events),
        )
        return world_state, player_kb, config

    def save_exists(self) -> bool:
        """Verifica se esiste un save valido nella directory.

        Returns:
            True se il file state.msgpack esiste.
        """
        return (self.save_dir / _STATE_FILE).exists()

    @property
    def db_path(self) -> Path:
        """Path del file SQLite per l'EventLogger."""
        return self.save_dir / _DB_FILE
