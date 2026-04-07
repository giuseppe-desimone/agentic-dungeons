"""CooldownTracker: anti-rumore per il ConsequenceEngine.

Impedisce che lo stesso tipo di evento venga generato ripetutamente dalla stessa
entità in un arco di tempo ravvicinato. Il cooldown è espresso in giorni narrativi.

Principio: il ConsequenceEngine controlla il cooldown PRIMA di generare conseguenze.
Se l'entità è in cooldown per quel verb → la conseguenza viene ignorata silenziosamente.
"""

from __future__ import annotations

# Durata default del cooldown in giorni narrativi.
# Derivata dalla spec: "Cooldown: 3 giorni narrativi."
COOLDOWN_DAYS: int = 3


class CooldownTracker:
    """Traccia i cooldown per coppie (entity_id, verb) in giorni narrativi.

    Storage: dizionario in-memory `{(entity_id, verb): last_triggered_world_day}`.
    Non persiste tra sessioni — viene ricostruito dall'event log al caricamento (Fase 8).

    Args:
        cooldown_days: Durata del cooldown in giorni narrativi (default: 3).
    """

    def __init__(self, cooldown_days: int = COOLDOWN_DAYS) -> None:
        self._cooldown_days = cooldown_days
        self._last_triggered: dict[tuple[str, str], int] = {}

    def set_cooldown(self, entity_id: str, verb: str, world_day: int) -> None:
        """Registra che l'entità ha appena triggerato questo verb.

        Args:
            entity_id: ID dell'entità emittente.
            verb: Verb dell'evento (stringa, non necessariamente EventVerb).
            world_day: Giorno narrativo assoluto corrente.
        """
        self._last_triggered[(entity_id, verb)] = world_day

    def is_on_cooldown(self, entity_id: str, verb: str, current_world_day: int) -> bool:
        """Verifica se l'entità è ancora in cooldown per questo verb.

        Args:
            entity_id: ID dell'entità da controllare.
            verb: Verb da controllare.
            current_world_day: Giorno narrativo assoluto corrente.

        Returns:
            True se il cooldown è ancora attivo (non abbastanza giorni passati).
            False se il cooldown è scaduto o non è mai stato impostato.
        """
        key = (entity_id, verb)
        if key not in self._last_triggered:
            return False
        days_elapsed = current_world_day - self._last_triggered[key]
        return days_elapsed < self._cooldown_days

    def clear(self) -> None:
        """Svuota tutti i cooldown. Utile per test e reset di stato."""
        self._last_triggered.clear()

    def remaining_days(self, entity_id: str, verb: str, current_world_day: int) -> int:
        """Giorni narrativi rimanenti di cooldown per questa coppia (entity, verb).

        Args:
            entity_id: ID dell'entità.
            verb: Verb da controllare.
            current_world_day: Giorno narrativo assoluto corrente.

        Returns:
            Giorni rimanenti (0 se scaduto o mai impostato).
        """
        key = (entity_id, verb)
        if key not in self._last_triggered:
            return 0
        elapsed = current_world_day - self._last_triggered[key]
        return max(0, self._cooldown_days - elapsed)
