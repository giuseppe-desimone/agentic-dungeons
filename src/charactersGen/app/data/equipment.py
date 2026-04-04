"""Tabelle equipaggiamento del sistema GDR v0.8.

Include: armature, scudi, armi corpo a corpo, armi a distanza, munizioni.
"""

from __future__ import annotations

from app.schemas import ArmorItem, DamageType, ShieldItem, WeaponItem, WeightClass

# ---------------------------------------------------------------------------
# Armature
# ---------------------------------------------------------------------------

ARMORS: list[ArmorItem] = [
    ArmorItem(
        name="Camicia Imbottita",
        weight_class=WeightClass.LEGGERA,
        schivare=0,
        fatica=0,
        locations=["Corpo", "Braccia"],
        damage_reduction={"C": 2},
    ),
    ArmorItem(
        name="Gambeson",
        weight_class=WeightClass.LEGGERA,
        schivare=0,
        fatica=0,
        locations=["Corpo", "Braccia"],
        damage_reduction={"C": 3},
    ),
    ArmorItem(
        name="Armatura in Pelle",
        weight_class=WeightClass.LEGGERA,
        schivare=0,
        fatica=0,
        locations=["Corpo", "Braccia"],
        damage_reduction={"T": 1, "C": 1},
    ),
    ArmorItem(
        name="Cotta di Maglia",
        weight_class=WeightClass.MEDIA,
        schivare=0,
        fatica=0,
        locations=["Testa", "Corpo", "Braccia"],
        damage_reduction={"T": 4, "P": 2},
    ),
    ArmorItem(
        name="Cotta di Maglia Rivettata",
        weight_class=WeightClass.MEDIA,
        schivare=0,
        fatica=0,
        locations=["Testa", "Corpo", "Braccia"],
        damage_reduction={"T": 4, "P": 3},
    ),
    ArmorItem(
        name="Armatura in Cuoio",
        weight_class=WeightClass.MEDIA,
        schivare=0,
        fatica=0,
        locations=["Corpo"],
        damage_reduction={"T": 2, "C": 2},
    ),
    ArmorItem(
        name="Bracciali di Cuoio",
        weight_class=WeightClass.MEDIA,
        schivare=0,
        fatica=0,
        locations=["Braccia"],
        damage_reduction={"T": 2, "C": 2},
    ),
    ArmorItem(
        name="Gambali di Cuoio",
        weight_class=WeightClass.MEDIA,
        schivare=0,
        fatica=0,
        locations=["Gambe"],
        damage_reduction={"T": 2, "C": 2},
    ),
    ArmorItem(
        name="Brigantina",
        weight_class=WeightClass.MEDIA,
        schivare=-1,
        fatica=0,
        locations=["Corpo", "Braccia"],
        damage_reduction={"T": 3, "C": 1},
    ),
    ArmorItem(
        name="Armatura a Bande",
        weight_class=WeightClass.PESANTE,
        schivare=-2,
        fatica=-1,
        locations=["Corpo"],
        damage_reduction={"T": 5, "P": 3},
    ),
    ArmorItem(
        name="Armatura a Piastre",
        weight_class=WeightClass.PESANTE,
        schivare=-4,
        fatica=-2,
        locations=["Corpo"],
        damage_reduction={"T": 8, "P": 4},
    ),
    ArmorItem(
        name="Armatura Completa a Piastre",
        weight_class=WeightClass.PESANTE,
        schivare=-4,
        fatica=-2,
        locations=["Testa", "Corpo", "Braccia", "Gambe"],
        damage_reduction={"T": 8, "P": 4},
        notes="Riduzione applicata a ogni locazione coperta.",
    ),
    ArmorItem(
        name="Gambali a Bande",
        weight_class=WeightClass.PESANTE,
        schivare=-1,
        fatica=0,
        locations=["Gambe"],
        damage_reduction={"T": 5, "P": 3},
    ),
    ArmorItem(
        name="Gambali a Piastre",
        weight_class=WeightClass.PESANTE,
        schivare=-2,
        fatica=0,
        locations=["Gambe"],
        damage_reduction={"T": 8, "P": 4},
    ),
    ArmorItem(
        name="Bracciali a Piastre",
        weight_class=WeightClass.PESANTE,
        schivare=-1,
        fatica=0,
        locations=["Braccia"],
        damage_reduction={"T": 8, "P": 4},
    ),
    ArmorItem(
        name="Celata",
        weight_class=WeightClass.PESANTE,
        schivare=-2,
        fatica=0,
        locations=["Testa"],
        damage_reduction={"T": 8, "P": 4},
    ),
    # Armature speciali
    ArmorItem(
        name="Armatura Completa Nanica",
        weight_class=WeightClass.PESANTE,
        schivare=-5,
        fatica=-3,
        locations=["Testa", "Corpo", "Braccia", "Gambe"],
        damage_reduction={"T": 6, "P": 5, "C": 4},
        special=True,
        notes="Solo background Nano o trovata in gioco. Resistenza al fuoco: 2.",
    ),
]

ARMOR_NAMES: list[str] = [a.name for a in ARMORS]

# ---------------------------------------------------------------------------
# Scudi
# ---------------------------------------------------------------------------

SHIELDS: list[ShieldItem] = [
    ShieldItem(
        name="Scudo a Torre",
        weight_class=WeightClass.PESANTE,
        schivare=8,
        fatica=-2,
        damage_reduction={"T": 6, "P": 4, "C": 5},
    ),
    ShieldItem(
        name="Scudo",
        weight_class=WeightClass.MEDIA,
        schivare=5,
        fatica=-1,
        damage_reduction={"T": 5, "P": 3, "C": 5},
    ),
    ShieldItem(
        name="Scudo Piccolo",
        weight_class=WeightClass.LEGGERA,
        schivare=3,
        fatica=0,
        damage_reduction={"T": 4, "P": 2, "C": 2},
    ),
    ShieldItem(
        name="Brocchiere",
        weight_class=WeightClass.LEGGERA,
        schivare=2,
        fatica=0,
        damage_reduction={"T": 4, "C": 2},
    ),
]

SHIELD_NAMES: list[str] = [s.name for s in SHIELDS]

# ---------------------------------------------------------------------------
# Armi corpo a corpo
# ---------------------------------------------------------------------------

MELEE_WEAPONS: list[WeaponItem] = [
    WeaponItem(
        name="Coltello",
        damage_types=[DamageType.TAGLIO, DamageType.PENETRANTE],
        damage_die="1d4",
        threat_range="Base",
        weight_class=WeightClass.LEGGERA,
    ),
    WeaponItem(
        name="Pugnale",
        damage_types=[DamageType.TAGLIO, DamageType.PENETRANTE],
        damage_die="1d6",
        threat_range="Base",
        weight_class=WeightClass.LEGGERA,
    ),
    WeaponItem(
        name="Daga",
        damage_types=[DamageType.TAGLIO, DamageType.PENETRANTE],
        damage_die="1d8",
        threat_range="Base",
        weight_class=WeightClass.LEGGERA,
    ),
    WeaponItem(
        name="Spada Corta",
        damage_types=[DamageType.TAGLIO, DamageType.PENETRANTE],
        damage_die="1d8",
        threat_range="Base",
        weight_class=WeightClass.LEGGERA,
    ),
    WeaponItem(
        name="Spada a Una Mano",
        damage_types=[DamageType.TAGLIO, DamageType.PENETRANTE],
        damage_die="1d10/8",
        threat_range="+1 metro",
        weight_class=WeightClass.MEDIA,
        notes="Danno T: 1d10, danno P: 1d8",
    ),
    WeaponItem(
        name="Spada Bastarda",
        damage_types=[DamageType.TAGLIO, DamageType.PENETRANTE],
        damage_die="1d10/8",
        threat_range="+1 metro",
        weight_class=WeightClass.MEDIA,
    ),
    WeaponItem(
        name="Spada a Due Mani",
        damage_types=[DamageType.TAGLIO, DamageType.PENETRANTE, DamageType.CONTUNDENTE],
        damage_die="1d10/8/6",
        threat_range="+2 metri",
        weight_class=WeightClass.MEDIA,
        notes="T: 1d10, P: 1d8, C: 1d6",
    ),
    WeaponItem(
        name="Ascia",
        damage_types=[DamageType.TAGLIO, DamageType.CONTUNDENTE],
        damage_die="1d6/1d6",
        threat_range="+1 metro",
        weight_class=WeightClass.MEDIA,
    ),
    WeaponItem(
        name="Martello da Guerra",
        damage_types=[DamageType.CONTUNDENTE, DamageType.PENETRANTE],
        damage_die="1d6/1d6",
        threat_range="+1 metro",
        weight_class=WeightClass.MEDIA,
    ),
    WeaponItem(
        name="Mazza",
        damage_types=[DamageType.CONTUNDENTE, DamageType.PENETRANTE],
        damage_die="1d8/1d4",
        threat_range="+1 metro",
        weight_class=WeightClass.MEDIA,
    ),
    WeaponItem(
        name="Mazza Pesante (1 mano)",
        damage_types=[DamageType.CONTUNDENTE, DamageType.PENETRANTE],
        damage_die="2d6/1d4",
        threat_range="+1 metro",
        weight_class=WeightClass.PESANTE,
    ),
    WeaponItem(
        name="Mazza a Due Mani",
        damage_types=[DamageType.CONTUNDENTE, DamageType.PENETRANTE],
        damage_die="2d8/1d4",
        threat_range="+2 metri",
        weight_class=WeightClass.PESANTE,
    ),
    WeaponItem(
        name="Martello a Due Mani",
        damage_types=[DamageType.CONTUNDENTE],
        damage_die="2d8",
        threat_range="+2 metri",
        weight_class=WeightClass.PESANTE,
    ),
    WeaponItem(
        name="Bastone",
        damage_types=[DamageType.CONTUNDENTE],
        damage_die="1d6",
        threat_range="+1 metro",
        weight_class=WeightClass.LEGGERA,
    ),
    WeaponItem(
        name="Bastone Due Mani",
        damage_types=[DamageType.CONTUNDENTE],
        damage_die="1d8",
        threat_range="+3 metri",
        weight_class=WeightClass.LEGGERA,
    ),
    WeaponItem(
        name="Bastone Ferrato",
        damage_types=[DamageType.CONTUNDENTE],
        damage_die="1d10",
        threat_range="+3 metri",
        weight_class=WeightClass.MEDIA,
    ),
    WeaponItem(
        name="Lancia",
        damage_types=[DamageType.PENETRANTE, DamageType.CONTUNDENTE],
        damage_die="2d6/1d6",
        threat_range="+3 metri",
        weight_class=WeightClass.MEDIA,
    ),
    WeaponItem(
        name="Lancia Corta",
        damage_types=[DamageType.PENETRANTE, DamageType.CONTUNDENTE],
        damage_die="2d4/1d4",
        threat_range="+2 metri",
        weight_class=WeightClass.LEGGERA,
    ),
    WeaponItem(
        name="Alabarda",
        damage_types=[DamageType.CONTUNDENTE, DamageType.TAGLIO],
        damage_die="2d4T/1d6C",
        threat_range="+3 metri",
        weight_class=WeightClass.PESANTE,
    ),
    WeaponItem(
        name="Frusta",
        damage_types=[DamageType.CONTUNDENTE],
        damage_die="2d4",
        threat_range="+2 metri",
        weight_class=WeightClass.MEDIA,
    ),
]

# ---------------------------------------------------------------------------
# Armi a distanza
# ---------------------------------------------------------------------------

RANGED_WEAPONS: list[WeaponItem] = [
    WeaponItem(
        name="Arco Corto",
        damage_types=[DamageType.PENETRANTE],
        damage_die="Munizione +2",
        threat_range="Tiro dritto +10m",
        weight_class=WeightClass.LEGGERA,
        notes="Usa munizioni per il danno.",
    ),
    WeaponItem(
        name="Arco Lungo",
        damage_types=[DamageType.PENETRANTE],
        damage_die="Munizione×2 +4",
        threat_range="Tiro dritto +20m",
        weight_class=WeightClass.MEDIA,
        notes="Usa munizioni per il danno. Moltiplica il dado munizione per 2.",
    ),
    WeaponItem(
        name="Arco Composito",
        damage_types=[DamageType.PENETRANTE],
        damage_die="Munizione×3 +7",
        threat_range="Tiro dritto +30m",
        weight_class=WeightClass.PESANTE,
        notes="Usa munizioni per il danno. Moltiplica il dado munizione per 3.",
    ),
    WeaponItem(
        name="Balestra Leggera",
        damage_types=[DamageType.PENETRANTE],
        damage_die="Munizione +4",
        threat_range="Tiro dritto +10m",
        weight_class=WeightClass.LEGGERA,
        notes="Sparare è azione gratuita (0.5s). Ricarica: 1 round.",
    ),
    WeaponItem(
        name="Balestra a Crocco",
        damage_types=[DamageType.PENETRANTE],
        damage_die="Munizione×2 +7",
        threat_range="Tiro dritto +20m",
        weight_class=WeightClass.MEDIA,
        notes="Sparare è azione gratuita (0.5s). Ricarica: 1 round.",
    ),
    WeaponItem(
        name="Balestra Pesante",
        damage_types=[DamageType.PENETRANTE],
        damage_die="Munizione×3 +10",
        threat_range="Tiro dritto +30m",
        weight_class=WeightClass.PESANTE,
        notes="Sparare è azione gratuita (0.5s). Ricarica: 2 round.",
    ),
]

# ---------------------------------------------------------------------------
# Armi da lancio
# ---------------------------------------------------------------------------

THROWING_WEAPONS: list[WeaponItem] = [
    WeaponItem(
        name="Pugnale da Lancio",
        damage_types=[DamageType.PENETRANTE],
        damage_die="1d6",
        threat_range="+6 metri",
        weight_class=WeightClass.LANCIO,
    ),
    WeaponItem(
        name="Ascia da Lancio",
        damage_types=[DamageType.CONTUNDENTE, DamageType.TAGLIO],
        damage_die="1d4/1d4",
        threat_range="+4 metri",
        weight_class=WeightClass.LANCIO,
    ),
    WeaponItem(
        name="Martello da Lancio",
        damage_types=[DamageType.CONTUNDENTE],
        damage_die="1d8",
        threat_range="+4 metri",
        weight_class=WeightClass.LANCIO,
    ),
]

ALL_WEAPONS: list[WeaponItem] = MELEE_WEAPONS + RANGED_WEAPONS + THROWING_WEAPONS
WEAPON_NAMES: list[str] = [w.name for w in ALL_WEAPONS]


def get_weapon(name: str) -> WeaponItem | None:
    """Restituisce un'arma per nome."""
    return next((w for w in ALL_WEAPONS if w.name == name), None)


def get_armor(name: str) -> ArmorItem | None:
    """Restituisce un'armatura per nome."""
    return next((a for a in ARMORS if a.name == name), None)


def get_shield(name: str) -> ShieldItem | None:
    """Restituisce uno scudo per nome."""
    return next((s for s in SHIELDS if s.name == name), None)
