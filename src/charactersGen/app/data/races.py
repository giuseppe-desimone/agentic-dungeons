"""Definizioni razze per il sistema GDR v0.8.

Razze implementate: Umano, Nano.
Razze placeholder: Elfo, Mezz'orco, Goblin (NotImplementedError).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import Race, IMPLEMENTED_RACES


@dataclass
class RaceDefinition:
    """Definizione completa di una razza."""

    race: Race
    # Dadi caratteristiche fisiche (FOR, DES, COS)
    phys_num_dice: int  # numero dadi
    phys_die: int       # tipo dado

    # Dadi caratteristiche mentali (INT, VOL, IST, EMP)
    ment_num_dice: int
    ment_die: int

    # PF base per locazione: formula "base + COS"
    # formato: {nome_locazione: base_pf}
    pf_base: dict[str, int] = field(default_factory=dict)

    # Schivare base per locazione: formula "base + DES"
    # formato: {nome_locazione: base_schivare}
    schivare_base: dict[str, int] = field(default_factory=dict)

    description: str = ""


# ---------------------------------------------------------------------------
# Razze implementate
# ---------------------------------------------------------------------------

RACE_DEFINITIONS: dict[Race, RaceDefinition] = {
    Race.UMANO: RaceDefinition(
        race=Race.UMANO,
        phys_num_dice=3,
        phys_die=4,
        ment_num_dice=3,
        ment_die=4,
        pf_base={
            "Testa": 10,
            "Torace": 40,
            "Braccio Sx": 15,
            "Braccio Dx": 15,
            "Gamba Sx": 20,
            "Gamba Dx": 20,
        },
        schivare_base={
            "Testa": 20,
            "Torace": 10,
            "Braccio Sx": 15,
            "Braccio Dx": 15,
            "Gamba Sx": 12,
            "Gamba Dx": 12,
        },
        description="La razza più comune. Equilibrata in tutte le caratteristiche.",
    ),
    Race.NANO: RaceDefinition(
        race=Race.NANO,
        phys_num_dice=3,
        phys_die=4,
        ment_num_dice=3,
        ment_die=4,
        pf_base={
            "Testa": 15,
            "Torace": 40,
            "Braccio Sx": 18,
            "Braccio Dx": 18,
            "Gamba Sx": 20,
            "Gamba Dx": 20,
        },
        schivare_base={
            "Testa": 17,
            "Torace": 10,
            "Braccio Sx": 15,
            "Braccio Dx": 15,
            "Gamba Sx": 15,
            "Gamba Dx": 15,
        },
        description="Robusti e resistenti. PF più alti, schivata leggermente ridotta alla testa.",
    ),
}

# Placeholder per future razze
_UNIMPLEMENTED_RACES: set[Race] = set(Race) - IMPLEMENTED_RACES


def get_race_definition(race: Race) -> RaceDefinition:
    """Restituisce la definizione della razza richiesta.

    Args:
        race: la razza da cercare.

    Returns:
        RaceDefinition per la razza.

    Raises:
        NotImplementedError: se la razza non è ancora implementata.
    """
    if race in _UNIMPLEMENTED_RACES:
        raise NotImplementedError(
            f"La razza '{race.value}' non è ancora implementata. "
            f"Razze disponibili: {[r.value for r in IMPLEMENTED_RACES]}"
        )
    return RACE_DEFINITIONS[race]


def get_age_stat_modifiers(age: int) -> dict[str, int]:
    """Calcola i modificatori alle caratteristiche in base all'età.

    Ogni 5 anni oltre i 20: -1 COS, -1 FOR, +1 EMP, -1 DES, -1 IST, +1 VOL, 0 INT.

    Args:
        age: età del personaggio in anni.

    Returns:
        Dizionario {nome_stat: modificatore}.

    Note:
        [PLACEHOLDER] La progressione dei PX in base all'età è da definire.
        I modificatori per l'invecchiamento avanzato (oltre 60 anni)
        potrebbero essere estesi in future versioni.
    """
    if age <= 20:
        return {}

    periods = (age - 20) // 5  # ogni 5 anni oltre i 20
    if periods == 0:
        return {}

    return {
        "cos": -1 * periods,
        "for": -1 * periods,
        "emp": +1 * periods,
        "des": -1 * periods,
        "ist": -1 * periods,
        "vol": +1 * periods,
        "int": 0,
    }


def get_stat_dice_count(age: int) -> int:
    """Restituisce il numero di dadi da tirare per le caratteristiche in base all'età.

    - Età < 20: 2d4 (meno sviluppato)
    - Età >= 20: 3d4

    Args:
        age: età del personaggio.

    Returns:
        Numero di dadi da tirare.
    """
    return 2 if age < 20 else 3
