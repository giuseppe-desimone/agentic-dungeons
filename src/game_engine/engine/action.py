"""Action System — PlayerAction, ActionFilterEngine, IntentScheduler, InteractionManager.

Il player esprime intenzioni, non comandi immediati.
Le azioni con world_time_cost == 0 sono immediate.
Le azioni con world_time_cost > 0 diventano PlayerIntent schedulati nel tempo narrativo.

InteractionManager gestisce le intrusioni spaziali:
  - L'unico criterio è la prossimità fisica (stessa location_id).
  - Non esistono livelli di urgenza per le intrusioni.
  - open_to_intrusion=False blocca tutte le intrusioni (isolamento fisico).
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from ..models.entity import NPCEntity, PlayerEntity
from ..models.intent import ActiveInteraction, PlayerIntent
from .world_clock import WORLD_TIME_COST, WORLD_UNITS_PER_DAY, WorldClock

if TYPE_CHECKING:
    from ..models.event import GameEvent
    from .world_state import WorldState

logger = logging.getLogger(__name__)


# ── PlayerAction ──────────────────────────────────────────────────────────────


class PlayerAction(BaseModel):
    """Un'azione disponibile per il player nel contesto corrente.

    Le azioni con world_time_cost == 0 sono immediate.
    Le azioni con world_time_cost > 0 diventano PlayerIntent
    che si completano nel tempo narrativo.

    Args:
        id: Identificatore univoco dell'azione nel menu corrente.
        label: Etichetta leggibile dal player (es. "Parla con Aldric").
        action_type: Chiave in WORLD_TIME_COST (es. "player_action_quick").
        world_time_cost: Costo in world_units (letto da WORLD_TIME_COST).
        target_id: Entità target dell'azione (opzionale).
        payload: Dati contestuali aggiuntivi.
        requires_location_id: Location richiesta per eseguire l'azione.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    action_type: str
    world_time_cost: int
    target_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    requires_location_id: Optional[str] = None


# ── Action Filter Engine ──────────────────────────────────────────────────────

# Azioni base sempre disponibili
_BASE_ACTIONS: list[dict[str, Any]] = [
    {
        "label": "Guarda intorno",
        "action_type": "player_action_quick",
        "world_time_cost": WORLD_TIME_COST["player_action_quick"],
    },
    {
        "label": "Aspetta",
        "action_type": "player_action_quick",
        "world_time_cost": WORLD_TIME_COST["player_action_quick"],
    },
    {
        "label": "Riposa brevemente",
        "action_type": "rest_short",
        "world_time_cost": WORLD_TIME_COST["rest_short"],
    },
    {
        "label": "Riposa (notte intera)",
        "action_type": "rest_full",
        "world_time_cost": WORLD_TIME_COST["rest_full"],
    },
]


class ActionFilterEngine:
    """Costruisce il menu di azioni disponibili per il player nel contesto corrente.

    Le azioni disponibili dipendono da:
    - Location corrente del player
    - NPC presenti nella location (dalla PlayerKnowledgeBase o fisicamente)
    - TimeScale corrente (PAUSE → solo azioni immediate)
    """

    def build_menu(
        self,
        world_state: "WorldState",
        player: PlayerEntity,
        world_clock: WorldClock,
    ) -> list[PlayerAction]:
        """Costruisce il menu di azioni disponibili.

        Args:
            world_state: World state globale.
            player: Entità player.
            world_clock: Orologio narrativo corrente.

        Returns:
            Lista di PlayerAction disponibili nel contesto corrente.
        """
        from .world_clock import TimeScale

        player_location = player.mechanical.get("location_id")
        actions: list[PlayerAction] = []

        # Azioni base
        for base in _BASE_ACTIONS:
            cost = base["world_time_cost"]
            # In PAUSE: solo azioni immediate (cost == 0)
            if world_clock.scale == TimeScale.PAUSE and cost > 0:
                continue
            actions.append(
                PlayerAction(
                    label=base["label"],
                    action_type=base["action_type"],
                    world_time_cost=cost,
                )
            )

        # Azioni contestuali — NPC nella stessa location
        if player_location:
            for entity in world_state.entity_store.values():
                if not isinstance(entity, NPCEntity):
                    continue
                if entity.mechanical.get("location_id") != player_location:
                    continue

                # Parla con NPC (cost=0 — breve scambio)
                actions.append(
                    PlayerAction(
                        label=f"Parla con {entity.identity.name}",
                        action_type="player_action_quick",
                        world_time_cost=WORLD_TIME_COST["player_action_quick"],
                        target_id=entity.id,
                        requires_location_id=player_location,
                    )
                )

                # Contratta con NPC (cost=2 — negoziazione)
                trade_cost = WORLD_TIME_COST["player_action_slow"]
                if world_clock.scale != TimeScale.PAUSE or trade_cost == 0:
                    actions.append(
                        PlayerAction(
                            label=f"Commercia con {entity.identity.name}",
                            action_type="player_action_slow",
                            world_time_cost=trade_cost,
                            target_id=entity.id,
                            requires_location_id=player_location,
                        )
                    )

        return actions


# ── Intent Scheduler ──────────────────────────────────────────────────────────


class IntentScheduler:
    """Gestisce il ciclo di vita dei PlayerIntent nel tempo narrativo."""

    def schedule(
        self,
        player_action: PlayerAction,
        world_clock: WorldClock,
    ) -> PlayerIntent:
        """Crea un PlayerIntent da un'azione con costo > 0.

        Il completamento è calcolato in giorni narrativi:
        completes_at_world_day = current_day + (cost // WORLD_UNITS_PER_DAY)
        Con un minimo di 1 giorno se il costo è > 0 ma < WORLD_UNITS_PER_DAY.

        Args:
            player_action: Azione da schedulare.
            world_clock: Orologio narrativo corrente.

        Returns:
            PlayerIntent in stato "pending".
        """
        current_day = world_clock.world_time.to_absolute_days()
        duration_days = max(1, player_action.world_time_cost // WORLD_UNITS_PER_DAY)

        return PlayerIntent(
            action_id=player_action.action_type,
            target_id=player_action.target_id,
            payload=player_action.payload,
            scheduled_at=world_clock.world_time,
            estimated_duration_units=player_action.world_time_cost,
            completes_at_world_day=current_day + duration_days,
            status="pending",
        )

    def is_completed(
        self,
        intent: PlayerIntent,
        world_clock: WorldClock,
    ) -> bool:
        """Verifica se un PlayerIntent è completato in base al tempo narrativo.

        Args:
            intent: Intenzione da verificare.
            world_clock: Orologio narrativo corrente.

        Returns:
            True se il giorno narrativo corrente ha raggiunto completes_at_world_day.
        """
        if intent.is_terminal():
            return intent.status == "completed"
        current_day = world_clock.world_time.to_absolute_days()
        return current_day >= intent.completes_at_world_day

    def interrupt(
        self,
        intent: PlayerIntent,
        event_id: str,
    ) -> PlayerIntent:
        """Interrompe un PlayerIntent a causa di un evento del mondo.

        Args:
            intent: Intenzione da interrompere.
            event_id: ID dell'evento che ha causato l'interruzione.

        Returns:
            PlayerIntent in stato "interrupted" (nuovo oggetto immutabile).
        """
        return intent.model_copy(
            update={
                "status": "interrupted",
                "interrupt_event_id": event_id,
            }
        )

    def complete(self, intent: PlayerIntent) -> PlayerIntent:
        """Segna un PlayerIntent come completato.

        Args:
            intent: Intenzione da completare.

        Returns:
            PlayerIntent in stato "completed".
        """
        return intent.model_copy(update={"status": "completed"})


# ── Interaction Manager ───────────────────────────────────────────────────────


class InteractionManager:
    """Gestisce le interazioni attive e le intrusioni spaziali.

    Non esistono livelli di urgenza — l'unico criterio per le intrusioni è:
    l'evento accade nella stessa location dell'interazione?

    Se open_to_intrusion=False → nessuna intrusione possibile
    (isolamento fisico: stanza chiusa, rito segreto).
    """

    def try_intrude(
        self,
        event: "GameEvent",
        interaction: ActiveInteraction,
        world_state: "WorldState",
    ) -> bool:
        """Tenta di introdurre un evento in un'interazione attiva.

        Criteri:
        1. interaction.open_to_intrusion deve essere True
        2. L'evento deve essere avvenuto nella stessa location dell'interazione

        La decisione su COME l'evento entra nell'interazione è narrativa —
        viene delegata all'Agente Narrativo tramite il contesto aggiornato.

        Args:
            event: Evento da valutare.
            interaction: Interazione attiva.
            world_state: World state globale (non usato nella logica corrente).

        Returns:
            True se l'evento può entrare nell'interazione.
        """
        if not interaction.open_to_intrusion:
            return False

        event_location = event.payload.get("location_id")
        if event_location != interaction.location_id:
            return False

        return True

    def suspend(
        self,
        interaction: ActiveInteraction,
        world_time: Any,
    ) -> None:
        """Sospende un'interazione attiva.

        Imposta suspended_at al WorldTime corrente.
        L'interazione può essere ripresa in seguito se resumable=True.

        Args:
            interaction: Interazione da sospendere.
            world_time: WorldTime corrente al momento della sospensione.
        """
        interaction.suspended_at = world_time

    def resume(
        self,
        interaction: ActiveInteraction,
        world_state: "WorldState",
        world_clock: WorldClock,
    ) -> dict[str, Any]:
        """Riprende un'interazione sospesa.

        Restituisce il contesto per l'Agente Narrativo:
        - Lo stato originale dell'interazione
        - I giorni narrativi trascorsi durante la sospensione
        - Gli eventi accaduti durante la sospensione NOTI AL PLAYER

        IMPORTANTE: usa player_knowledge.get_events_since() — mai world_state.event_log.

        Args:
            interaction: Interazione da riprendere.
            world_state: World state globale (per accedere a player_knowledge).
            world_clock: Orologio narrativo corrente.

        Returns:
            Dict con original_state, elapsed_days, known_events_during_suspension.
        """
        if interaction.suspended_at is None:
            return {
                "original_state": interaction.state,
                "elapsed_days": 0,
                "known_events_during_suspension": [],
            }

        suspended_day = interaction.suspended_at.to_absolute_days()
        current_day = world_clock.world_time.to_absolute_days()
        elapsed_days = current_day - suspended_day

        known_events_during: list[str] = []
        if world_state.player_knowledge is not None:
            known_entries = world_state.player_knowledge.get_events_since(suspended_day)
            known_events_during = [e.event_id for e in known_entries]

        return {
            "original_state": interaction.state,
            "elapsed_days": elapsed_days,
            "known_events_during_suspension": known_events_during,
        }
