"""PlayerKnowledgeBase e VisibilityEngine: la vista soggettiva del player sul mondo.

Principio fondamentale: il player vive in un mondo parzialmente opaco.
PlayerKnowledgeBase è l'UNICA fonte di dati per l'Agente Narrativo — mai il world state globale.

VisibilityEngine è il guardiano: determina se e come un evento entra nella
PlayerKnowledgeBase, in base alla posizione del player e alla visibilità dell'evento.

Separazione garantita:
    WORLD STATE (globale, omnisciente)
        └── EventLog: tutti gli eventi
        └── Entities: stato reale di tutte le entità

    PLAYER KNOWLEDGE BASE (soggettiva, limitata)
        └── known_events: eventi che il player conosce
        └── known_entities: stato delle entità come il player le conosce
        └── active_rumors: eventi incerti (certainty < 0.7)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from ..models.base import WorldTime
from ..models.entity import PlayerEntity
from ..models.event import GameEvent

if TYPE_CHECKING:
    from .world_state import WorldState


class KnowledgeUpdate(BaseModel):
    """Risultato del VisibilityEngine: descrive come il player ha appreso un evento.

    Args:
        event_id: ID dell'evento appreso.
        how_learned: Modalità di apprendimento.
        certainty: Grado di certezza del player (0.0–1.0).
        learned_at: WorldTime in cui il player ha appreso l'evento (opzionale).
    """

    event_id: str
    how_learned: str   # "direct_witness" | "informed" | "rumor" | "investigation"
    certainty: float   # 0.0–1.0
    learned_at: Optional[WorldTime] = None


class KnownEventEntry(BaseModel):
    """Un evento nella memoria del player, con metadati epistemici.

    Args:
        event_id: ID dell'evento nel world state.
        how_learned: Come il player lo ha appreso.
        certainty: Quanto è certo il player che sia vero (1.0 = testimone diretto).
        learned_at: WorldTime in cui ha appreso l'evento.
        source_entity_id: Chi ha informato il player (per "informed" e "rumor").
    """

    event_id: str
    how_learned: str
    certainty: float
    learned_at: WorldTime
    source_entity_id: Optional[str] = None


class KnownEntityState(BaseModel):
    """Lo stato di un'entità come il player la conosce.

    Può essere diverso dallo stato reale nel world state.
    Es: il player crede che Aldric sia in città, ma Aldric è partito 2 giorni fa.

    Args:
        entity_id: ID dell'entità.
        last_seen_at: Quando il player ha visto/saputo dell'entità per l'ultima volta.
        last_known_location_id: Ultima location nota (può essere obsoleta).
        last_known_status: Ultimo stato noto ("active", "dead", ecc.).
        last_known_relations: Relazioni come il player le conosce (possono essere obsolete).
    """

    entity_id: str
    last_seen_at: WorldTime
    last_known_location_id: Optional[str] = None
    last_known_status: str = "active"
    last_known_relations: list[dict] = Field(default_factory=list)


class PlayerKnowledgeBase(BaseModel):
    """Tutto ciò che il player sa del mondo.

    Questa è l'UNICA fonte di dati per l'Agente Narrativo.
    Non contiene MAI informazioni non percepite o apprese dal player.

    Args:
        player_id: ID del player proprietario di questa knowledge base.
        known_events: Tutti gli eventi che il player ha percepito o appreso.
        known_entities: Stato delle entità come il player le conosce.
        active_rumors: event_id con certainty < 0.7 — il player non è sicuro siano veri.
    """

    player_id: str
    known_events: list[KnownEventEntry] = Field(default_factory=list)
    known_entities: dict[str, KnownEntityState] = Field(default_factory=dict)
    active_rumors: list[str] = Field(default_factory=list)

    def get_events_since(self, world_day: int) -> list[KnownEventEntry]:
        """Filtra gli eventi noti dal giorno narrativo indicato in poi.

        Args:
            world_day: Giorno narrativo assoluto di inizio (incluso).

        Returns:
            Lista di KnownEventEntry ordinata per learned_at.
        """
        return [
            e for e in self.known_events
            if e.learned_at.to_absolute_days() >= world_day
        ]

    def apply_update(
        self,
        update: KnowledgeUpdate,
        event: GameEvent,
        world_time: WorldTime,
    ) -> None:
        """Aggiorna la knowledge base con un nuovo evento appreso.

        Chiamato dal VisibilityEngine dopo ogni evento processato.
        Aggiorna known_events, active_rumors e known_entities.

        Args:
            update: Il risultato del VisibilityEngine.
            event: L'evento originale dal world state.
            world_time: WorldTime corrente (quando il player ha appreso l'evento).
        """
        learned_at = update.learned_at if update.learned_at is not None else world_time

        entry = KnownEventEntry(
            event_id=update.event_id,
            how_learned=update.how_learned,
            certainty=update.certainty,
            learned_at=learned_at,
        )
        self.known_events.append(entry)

        # Rumor: certainty bassa, il player non è sicuro
        if update.certainty < 0.7:
            self.active_rumors.append(update.event_id)

        # Aggiorna lo stato dell'entità emittente come il player la conosce
        emitter_id = event.emitter.id
        if emitter_id not in self.known_entities:
            self.known_entities[emitter_id] = KnownEntityState(
                entity_id=emitter_id,
                last_seen_at=learned_at,
                last_known_status="active",
            )

        # Aggiorna last_seen solo se la certezza è sufficiente (non per rumor fumosi)
        if update.certainty >= 0.5:
            existing = self.known_entities[emitter_id]
            self.known_entities[emitter_id] = KnownEntityState(
                entity_id=existing.entity_id,
                last_seen_at=learned_at,
                last_known_location_id=existing.last_known_location_id,
                last_known_status=existing.last_known_status,
                last_known_relations=existing.last_known_relations,
            )


class VisibilityEngine:
    """Determina se e come un evento entra nella PlayerKnowledgeBase.

    Opera sul world state globale, produce KnowledgeUpdate da passare a
    PlayerKnowledgeBase.apply_update(). È il guardiano della separazione
    world state / player knowledge.

    Regole (in ordine di priorità):
        1. Player fisicamente nella stessa location dell'evento → direct_witness (1.0)
        2. Player esplicitamente in event.visibility.known_to → informed (0.9)
        3. Evento è un rumor in scope local/regional raggiungibile → rumor (0.4)
        4. Nessuna regola → None (il player non sa nulla)
    """

    def evaluate(
        self,
        event: GameEvent,
        player: PlayerEntity,
        world_state: "WorldState",
    ) -> Optional[KnowledgeUpdate]:
        """Valuta se e come il player apprende un evento.

        Args:
            event: L'evento da valutare dal world state globale.
            player: Il PlayerEntity corrente.
            world_state: Il world state globale (non esposto al player).

        Returns:
            KnowledgeUpdate se il player apprende l'evento, None altrimenti.
        """
        # Regola 1: testimonianza diretta — stessa location fisica
        if self._player_in_event_location(event, player):
            return KnowledgeUpdate(
                event_id=event.id,
                how_learned="direct_witness",
                certainty=1.0,
            )

        # Regola 2: il player è esplicitamente informato
        if player.id in event.visibility.known_to:
            return KnowledgeUpdate(
                event_id=event.id,
                how_learned="informed",
                certainty=0.9,
            )

        # Regola 3: rumor che si diffonde nella regione del player
        if event.verb == "rumored" and self._player_in_scope(event, player, world_state):
            return KnowledgeUpdate(
                event_id=event.id,
                how_learned="rumor",
                certainty=0.4,
            )

        return None

    def _player_in_event_location(
        self,
        event: GameEvent,
        player: PlayerEntity,
    ) -> bool:
        """Verifica se il player è fisicamente nella stessa location dell'evento.

        Usa player.mechanical["location_id"] e event.payload["location_id"].
        Se uno dei due manca → False.

        Args:
            event: L'evento da valutare.
            player: Il PlayerEntity corrente.

        Returns:
            True se player e evento condividono la stessa location_id.
        """
        player_loc = player.mechanical.get("location_id")
        event_loc = event.payload.get("location_id")
        if player_loc is None or event_loc is None:
            return False
        return player_loc == event_loc

    def _player_in_scope(
        self,
        event: GameEvent,
        player: PlayerEntity,
        world_state: "WorldState",
    ) -> bool:
        """Verifica se il player è nel raggio di diffusione di un rumor.

        Fase 2: semplificazione deliberata.
        - scope "local" → il player deve essere nella stessa location
        - scope "regional" → il rumor raggiunge sempre il player (modello semplificato)
        Il dettaglio geografico completo sarà aggiunto in Fase 5 con il SliceBuilder.

        Args:
            event: L'evento rumor da valutare.
            player: Il PlayerEntity corrente.
            world_state: Il world state globale.

        Returns:
            True se il rumor può raggiungere il player.
        """
        scope = event.visibility.scope
        if scope == "regional":
            return True
        if scope == "local":
            return self._player_in_event_location(event, player)
        return False
