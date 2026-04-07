"""Tipi fondamentali del game engine: enums, GameTick, WorldTime, DayMoment.

Doppio registro temporale:
    GameTick  — contatore atomico di simulazione. Avanza di 1 per ogni evento
                processato. Non ha unità di tempo reale. Usato dal
                ConsequenceEngine per ordinamento e diagnostica.
    WorldTime — tempo narrativo. Avanza in world_units in base al tipo di azione.
                1 min reale = 30 min narrativi in FLOW.
                Decadimenti, cooldown, soglie: SEMPRE in giorni narrativi.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EntityKind(StrEnum):
    """Tipi di entità nel world state."""

    NPC = "npc"
    PLAYER = "player"
    CREATURE = "creature"
    FACTION = "faction"
    RELIGION = "religion"
    GUILD = "guild"
    LOCATION = "location"
    ITEM = "item"
    SYSTEM = "system"


class EntityStatus(StrEnum):
    """Stato di vita di un'entità."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEAD = "dead"
    DISSOLVED = "dissolved"
    LEGENDARY = "legendary"  # non esiste più ma influenza lore e quest


class RelationType(StrEnum):
    """Tipo di relazione tra entità."""

    MEMBER_OF = "member_of"
    ALLIED = "allied"
    RIVAL = "rival"
    SUBJUGATED = "subjugated"
    BONDED = "bonded"
    ESTRANGED = "estranged"
    PLEDGED = "pledged"


class LocationMood(StrEnum):
    """Atmosfera narrativa di una location, derivata dagli eventi noti."""

    TENSE = "tense"
    WAR_TORN = "war-torn"
    GRIEVING = "grieving"
    FEARFUL = "fearful"
    HOPEFUL = "hopeful"
    BUSTLING = "bustling"
    SUSPICIOUS = "suspicious"
    CURIOUS = "curious"
    STAGNANT = "stagnant"
    PEACEFUL = "peaceful"
    CHAOTIC = "chaotic"
    HAUNTED = "haunted"


@dataclass(frozen=True)
class GameTick:
    """Contatore atomico di simulazione.

    Immutabile: ogni operazione crea un nuovo GameTick.
    Usato per ordinare eventi nel log e per diagnostica del ConsequenceEngine.
    """

    value: int = 0

    def __lt__(self, other: "GameTick") -> bool:
        """Ordine naturale per uso nel log eventi."""
        return self.value < other.value

    def __add__(self, n: int) -> "GameTick":
        """Crea un nuovo GameTick avanzato di n passi."""
        return GameTick(self.value + n)


class DayMoment(StrEnum):
    """Fascia narrativa sub-giorno.

    Non corrisponde a ore fisse — è una suddivisione narrativa del giorno.
    Influenza il tono dell'Agente Narrativo e la disponibilità degli NPC.
    """

    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"
    NIGHT = "night"


# Offset in giorni per ogni stagione (anno = 360 giorni, 4 stagioni da 90 giorni)
_SEASON_DAY_OFFSET: dict[str, int] = {
    "spring": 0,
    "summer": 90,
    "autumn": 180,
    "winter": 270,
}


@dataclass(frozen=True)
class WorldTime:
    """Tempo narrativo del mondo.

    Avanza in world_units (1 world_unit = 15 min narrativi).
    1 giorno narrativo = 20 world_units = 5 momenti × 4 unità.

    Immutabile: non si modifica mai in-place.
    """

    year: int = 0
    season: str = "spring"   # "spring" | "summer" | "autumn" | "winter"
    day: int = 1              # 1-90 per stagione
    moment: DayMoment = DayMoment.MORNING

    def to_absolute_days(self) -> int:
        """Converte in giorni assoluti dall'inizio del mondo (anno 0, spring, giorno 1 → 0).

        Returns:
            Numero di giorni narrativi dall'origine del tempo.
        """
        offset = _SEASON_DAY_OFFSET[self.season]
        return self.year * 360 + offset + (self.day - 1)

    def __lt__(self, other: "WorldTime") -> bool:
        """Confronto temporale: prima per giorno assoluto, poi per momento."""
        self_days = self.to_absolute_days()
        other_days = other.to_absolute_days()
        if self_days != other_days:
            return self_days < other_days
        moment_order = list(DayMoment)
        return moment_order.index(self.moment) < moment_order.index(other.moment)

    def __le__(self, other: "WorldTime") -> bool:
        """Minore o uguale."""
        return self == other or self < other
