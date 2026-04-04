"""Modelli Pydantic per il sistema GDR v0.8."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enum di base
# ---------------------------------------------------------------------------


class Race(str, Enum):
    """Razze giocabili. Le razze non ancora implementate solleveranno NotImplementedError."""

    UMANO = "Umano"
    NANO = "Nano"
    # Placeholder razze future
    ELFO = "Elfo"
    MEZZORCO = "Mezz'orco"
    GOBLIN = "Goblin"


IMPLEMENTED_RACES: set[Race] = {Race.UMANO, Race.NANO}


class Sex(str, Enum):
    MASCHIO = "Maschio"
    FEMMINA = "Femmina"
    ALTRO = "Altro"


class MentalStatus(str, Enum):
    SANO = "Sano"
    DISTURBATO = "Disturbato"
    PAZZO = "Pazzo"
    FOLLE = "Folle"


class PhysicalStatus(str, Enum):
    SANO = "Sano"
    AMMALATO = "Ammalato"
    FRATTURA = "Frattura"
    AVVELENATO = "Avvelenato"


class WeightClass(str, Enum):
    LEGGERA = "L"
    MEDIA = "M"
    PESANTE = "P"
    LANCIO = "T"


class DamageType(str, Enum):
    TAGLIO = "T"
    PENETRANTE = "P"
    CONTUNDENTE = "C"
    FUOCO = "Fuoco"


# ---------------------------------------------------------------------------
# Caratteristiche
# ---------------------------------------------------------------------------


class CharacterStats(BaseModel):
    """Le 7 caratteristiche fondamentali del personaggio."""

    cos: int = Field(ge=1, description="Costituzione — fisico, PF per locazione")
    for_: int = Field(ge=1, alias="for", description="Forza — muscolare, danno CaC")
    des: int = Field(ge=1, description="Destrezza — controllo corpo, schivare")
    vol: int = Field(ge=1, description="Volontà — mentale, diplomazia, charme")
    int_: int = Field(ge=1, alias="int", description="Intelligenza — ragionamento, conoscenze")
    ist: int = Field(ge=1, description="Istinto — percez. immediata, iniziativa")
    emp: int = Field(ge=1, description="Empatia — capire gli altri")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Locazioni corporee e PF
# ---------------------------------------------------------------------------


class BodyLocation(BaseModel):
    """Una locazione corporea con i suoi PF e la difficoltà di schivare."""

    name: str
    max_pf: int = Field(ge=0)
    current_pf: int = Field(ge=-999)
    schivare: int = Field(ge=0, description="Soglia schivare (1d20+DES deve superarla)")

    @model_validator(mode="after")
    def current_not_above_max(self) -> BodyLocation:
        if self.current_pf > self.max_pf:
            self.current_pf = self.max_pf
        return self


# ---------------------------------------------------------------------------
# Abilità
# ---------------------------------------------------------------------------


class AbilityGrade(BaseModel):
    """Un'abilità con i gradi acquisiti dal personaggio."""

    name: str
    characteristics: list[str] = Field(description="Caratteristiche collegate (es. ['DES'])")
    grades: int = Field(ge=0, default=0, description="Gradi nell'abilità (0 = non competente)")
    notes: str = ""


class KnowledgeBranch(BaseModel):
    """Una branca specifica di Conoscenza (Storia, Arcane, ecc.)."""

    name: str
    int_required: int = Field(ge=1, description="INT minima per apprenderla")
    grades: int = Field(ge=0, default=0)


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


class StatBonus(BaseModel):
    """Bonus/malus a una singola caratteristica."""

    stat: str = Field(description="Nome caratteristica in minuscolo (es. 'cos', 'for')")
    value: int


class SkillBonus(BaseModel):
    """Bonus/malus a un'abilità specifica."""

    ability: str
    value: int
    ignore_prerequisites: bool = False


class Background(BaseModel):
    """Background del personaggio con i suoi effetti meccanici."""

    name: str
    description: str
    px_threshold: int = Field(
        description="PX minimi necessari al personaggio per applicare questo background"
    )
    px_usable: int = Field(
        default=0,
        description="PX aggiuntivi usabili forniti dal background (es. Studioso: 2000)",
    )
    stat_bonuses: list[StatBonus] = Field(default_factory=list)
    skill_bonuses: list[SkillBonus] = Field(default_factory=list)
    granted_abilities: list[str] = Field(
        default_factory=list,
        description="Abilità concesse indipendentemente dai prerequisiti",
    )
    granted_learnings: list[str] = Field(
        default_factory=list,
        description="Apprendimenti concessi",
    )
    stat_priorities: list[str] = Field(
        default_factory=list,
        description=(
            "Top 3 caratteristiche suggerite da questo background "
            "(es. ['FOR', 'DES', 'COS']). "
            "Usate per l'assegnazione pesata NPC e come suggerimento nel wizard."
        ),
    )
    special_notes: str = ""
    race_required: Optional[Race] = None


# ---------------------------------------------------------------------------
# Apprendimenti
# ---------------------------------------------------------------------------


class Learning(BaseModel):
    """Un apprendimento acquistabile con PX."""

    name: str
    category: str = Field(description="Es. 'Combattimento', 'Magia', 'Generico'")
    subcategory: str = ""
    description: str
    cost: int = Field(ge=0)
    prerequisites: list[str] = Field(default_factory=list)
    race_required: Optional[Race] = None
    special_notes: str = ""


# ---------------------------------------------------------------------------
# Equipaggiamento
# ---------------------------------------------------------------------------


class ArmorItem(BaseModel):
    """Un pezzo di armatura."""

    name: str
    weight_class: WeightClass
    schivare: int = Field(default=0, description="Malus allo schivare (negativo)")
    fatica: int = Field(default=0, description="Malus alla fatica (negativo)")
    locations: list[str] = Field(description="Locazioni coperte")
    damage_reduction: dict[str, int] = Field(
        default_factory=dict,
        description="Riduzione danno per tipo: {'T': 4, 'P': 2}",
    )
    durability: int = Field(default=0)
    special: bool = False
    notes: str = ""


class WeaponItem(BaseModel):
    """Un'arma."""

    name: str
    damage_types: list[DamageType]
    damage_die: str = Field(description="Es. '1d6', '1d10/8' (slash per tipi multipli)")
    threat_range: str = Field(default="Base", description="Portata/minaccia")
    weight_class: WeightClass
    durability: int = Field(default=0)
    notes: str = ""


class ShieldItem(BaseModel):
    """Uno scudo."""

    name: str
    weight_class: WeightClass
    schivare: int = Field(description="Bonus schivare fornito dallo scudo")
    fatica: int = Field(default=0)
    damage_reduction: dict[str, int] = Field(default_factory=dict)
    notes: str = ""


# ---------------------------------------------------------------------------
# Personaggio completo
# ---------------------------------------------------------------------------


class Character(BaseModel):
    """Il personaggio completo, pronto per l'export JSON."""

    # Anagrafica
    name: str
    sex: Sex
    race: Race
    age: int = Field(ge=1)

    # Caratteristiche
    stats: CharacterStats

    # Corpo
    body_locations: list[BodyLocation] = Field(default_factory=list)
    resistenza: int = Field(ge=0, description="(FOR + DES) // 2")

    # Background
    background: Optional[Background] = None

    # Abilità
    ability_grades: list[AbilityGrade] = Field(default_factory=list)

    # Apprendimenti acquisiti
    learnings: list[str] = Field(default_factory=list, description="Nomi degli apprendimenti")

    # Equipaggiamento
    armor: list[ArmorItem] = Field(default_factory=list)
    weapons: list[WeaponItem] = Field(default_factory=list)
    shields: list[ShieldItem] = Field(default_factory=list)

    # PX
    px_total: int = Field(default=5000, description="PX totali disponibili alla creazione")
    px_spent: int = Field(default=0)
    px_remaining: int = Field(default=5000)
    px_accumulated: int = Field(default=0, description="PX non ancora spesi (accumulati tra periodi)")

    # Stile di vita e storia
    lifestyle_id: Optional[str] = Field(
        default=None,
        description="ID dello stile di vita corrente (es. 'guerriero')",
    )
    lifestyle_history: list[tuple[int, str]] = Field(
        default_factory=list,
        description="Periodi vissuti: [(eta_inizio, lifestyle_id), ...]",
    )

    # Streak CD aging
    bonus_cd: int = Field(default=10, description="CD attuale tiro bonus (streak)")
    malus_cd: int = Field(default=10, description="CD attuale tiro malus (streak)")

    # Stato
    mental_status: MentalStatus = MentalStatus.SANO
    physical_status: PhysicalStatus = PhysicalStatus.SANO

    # Unicità — PLACEHOLDER: da definire nelle prossime versioni
    uniqueness_traits: list[str] = Field(
        default_factory=list,
        description="[PLACEHOLDER] Tratti unici positivi/negativi. Da definire.",
    )
    uniqueness_notes: str = "DA DEFINIRE"

    @model_validator(mode="after")
    def sync_px_remaining(self) -> Character:
        self.px_remaining = self.px_total - self.px_spent
        return self
