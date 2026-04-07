"""EventLogger: persistenza append-only dell'event log su SQLite (aiosqlite).

Il log è la fonte storica di verità — non viene mai modificato, solo esteso.
Serve per: history, debug, fast-forward di location ibernate, query narrative.

Schema:
    events              — tutti gli eventi del world state
    player_known_events — mapping player → eventi noti (dalla PlayerKnowledgeBase)

Uso:
    EventLogger usa una connessione persistente — va aperta con open() e chiusa
    con close(), oppure usata come async context manager (async with EventLogger(...)).
    Questo evita problemi con SQLite in-memory (ogni nuova connessione è un DB vuoto).

Il world state in-memory è la fonte di verità per la simulazione corrente.
SQLite è il registro storico e la base per il salvataggio (Fase 8).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import aiosqlite

from ..models.event import GameEvent

logger = logging.getLogger(__name__)

SCHEMA_VERSION: int = 1

# ── Schema SQL ────────────────────────────────────────────────────────────────

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id               TEXT PRIMARY KEY,
    tick             INTEGER NOT NULL,
    world_day        INTEGER NOT NULL,
    world_moment     TEXT NOT NULL,
    verb             TEXT NOT NULL,
    type             TEXT NOT NULL,
    emitter_id       TEXT NOT NULL,
    emitter_kind     TEXT NOT NULL,
    emitter_name     TEXT NOT NULL,
    target_id        TEXT,
    target_kind      TEXT,
    target_name      TEXT,
    cascade_depth    INTEGER DEFAULT 0,
    parent_event_id  TEXT,
    payload          TEXT,
    visibility_scope TEXT NOT NULL,
    known_to         TEXT,
    status           TEXT DEFAULT 'active'
);
"""

_CREATE_PLAYER_KNOWN = """
CREATE TABLE IF NOT EXISTS player_known_events (
    player_id      TEXT NOT NULL,
    event_id       TEXT NOT NULL,
    how_learned    TEXT NOT NULL,
    certainty      REAL NOT NULL,
    learned_at_day INTEGER NOT NULL,
    PRIMARY KEY (player_id, event_id)
);
"""

_CREATE_SCHEMA_META = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_world_day  ON events(world_day);",
    "CREATE INDEX IF NOT EXISTS idx_events_verb       ON events(verb);",
    "CREATE INDEX IF NOT EXISTS idx_events_emitter    ON events(emitter_id);",
    "CREATE INDEX IF NOT EXISTS idx_events_target     ON events(target_id);",
    "CREATE INDEX IF NOT EXISTS idx_events_status     ON events(status);",
]


class EventLogger:
    """Logger asincrono per l'event log su SQLite.

    Mantiene una connessione persistente al DB — necessario per SQLite in-memory
    (ogni nuova connessione crea un DB vuoto separato).

    Uso come context manager (raccomandato):
        async with EventLogger(":memory:") as log:
            await log.init_schema()
            await log.append(event)

    Uso manuale:
        log = EventLogger(":memory:")
        await log.open()
        await log.init_schema()
        await log.append(event)
        await log.close()

    Args:
        db_path: Percorso al file SQLite, o ":memory:" per in-memory.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def open(self) -> None:
        """Apre la connessione al database."""
        self._conn = await aiosqlite.connect(self._db_path)

    async def close(self) -> None:
        """Chiude la connessione al database."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> "EventLogger":
        await self.open()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _db(self) -> aiosqlite.Connection:
        """Restituisce la connessione attiva.

        Raises:
            RuntimeError: Se la connessione non è stata aperta.
        """
        if self._conn is None:
            raise RuntimeError(
                "EventLogger non connesso. Chiamare open() o usare 'async with'."
            )
        return self._conn

    async def init_schema(self) -> None:
        """Crea le tabelle e gli indici se non esistono. Idempotente.

        Imposta anche schema_version nella tabella schema_meta.
        """
        db = self._db()
        await db.execute(_CREATE_EVENTS)
        await db.execute(_CREATE_PLAYER_KNOWN)
        await db.execute(_CREATE_SCHEMA_META)
        for idx in _CREATE_INDEXES:
            await db.execute(idx)
        await db.execute(
            "INSERT OR IGNORE INTO schema_meta (key, value) VALUES (?, ?);",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        await db.commit()
        logger.debug("EventLogger schema inizializzato su %s", self._db_path)

    async def append(self, event: GameEvent) -> None:
        """Inserisce un evento nel log. Il log è append-only.

        Usa INSERT OR IGNORE per idempotenza (doppio append dello stesso id = no-op).

        Args:
            event: L'evento da persistere.
        """
        payload_json = json.dumps(event.payload)
        known_to_json = json.dumps(event.visibility.known_to)
        target_id = event.target.id if event.target else None
        target_kind = event.target.kind if event.target else None
        target_name = event.target.name if event.target else None

        db = self._db()
        await db.execute(
            """
            INSERT OR IGNORE INTO events (
                id, tick, world_day, world_moment,
                verb, type,
                emitter_id, emitter_kind, emitter_name,
                target_id, target_kind, target_name,
                cascade_depth, parent_event_id,
                payload, visibility_scope, known_to, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                event.id,
                event.tick.value,
                event.world_time.to_absolute_days(),
                event.world_time.moment,
                event.verb,
                event.type,
                event.emitter.id,
                event.emitter.kind,
                event.emitter.name,
                target_id,
                target_kind,
                target_name,
                event.cascade_depth,
                event.parent_event_id,
                payload_json,
                event.visibility.scope,
                known_to_json,
                event.status,
            ),
        )
        await db.commit()

    async def mark_known(
        self,
        player_id: str,
        event_id: str,
        how_learned: str,
        certainty: float,
        learned_at_day: int,
    ) -> None:
        """Registra che il player ha appreso un evento.

        Usa INSERT OR REPLACE per aggiornare se cambia how_learned/certainty.

        Args:
            player_id: ID del player.
            event_id: ID dell'evento appreso.
            how_learned: "direct_witness" | "informed" | "rumor" | "investigation".
            certainty: Grado di certezza (0.0–1.0).
            learned_at_day: Giorno narrativo assoluto in cui il player ha appreso l'evento.
        """
        db = self._db()
        await db.execute(
            """
            INSERT OR REPLACE INTO player_known_events
                (player_id, event_id, how_learned, certainty, learned_at_day)
            VALUES (?, ?, ?, ?, ?);
            """,
            (player_id, event_id, how_learned, certainty, learned_at_day),
        )
        await db.commit()

    async def query_since(
        self,
        world_day: int,
        player_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Restituisce eventi dal giorno narrativo indicato in poi.

        Se player_id è fornito, filtra solo gli eventi noti al player
        (join con player_known_events). Altrimenti restituisce tutti gli eventi.

        Args:
            world_day: Giorno narrativo assoluto di inizio (incluso).
            player_id: Se presente, filtra per gli eventi noti a questo player.

        Returns:
            Lista di dizionari con i campi degli eventi.
        """
        db = self._db()
        db.row_factory = aiosqlite.Row
        if player_id is not None:
            cursor = await db.execute(
                """
                SELECT e.*, pke.how_learned, pke.certainty, pke.learned_at_day
                FROM events e
                JOIN player_known_events pke
                    ON e.id = pke.event_id AND pke.player_id = ?
                WHERE e.world_day >= ?
                ORDER BY e.world_day ASC, e.tick ASC;
                """,
                (player_id, world_day),
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM events
                WHERE world_day >= ?
                ORDER BY world_day ASC, tick ASC;
                """,
                (world_day,),
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_schema_version(self) -> int:
        """Legge la versione dello schema dal DB.

        Returns:
            Versione dello schema (int), 0 se tabella non esiste.
        """
        try:
            db = self._db()
            cursor = await db.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version';"
            )
            row = await cursor.fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    async def migrate_if_needed(self, current_version: int = SCHEMA_VERSION) -> None:
        """Controlla la versione e applica migration se necessario. Idempotente.

        Fase 8 implementerà le migration effettive. Qui è uno stub che
        verifica la versione e logga se c'è disallineamento.

        Args:
            current_version: Versione dello schema attesa.
        """
        try:
            db_version = await self.get_schema_version()
        except RuntimeError:
            # Connessione non aperta → apriamo, inizializziamo, chiudiamo
            await self.open()
            await self.init_schema()
            return

        if db_version == 0:
            await self.init_schema()
            return
        if db_version < current_version:
            logger.warning(
                "Schema DB versione %d < versione attesa %d. "
                "Migration non ancora implementata (Fase 8).",
                db_version,
                current_version,
            )
        else:
            logger.debug("Schema DB aggiornato (versione %d).", db_version)
