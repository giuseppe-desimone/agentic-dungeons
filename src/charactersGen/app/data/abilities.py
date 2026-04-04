"""Lista delle abilità del sistema GDR v0.8.

Ogni abilità è collegata a una o più caratteristiche.
I gradi nell'abilità non possono superare il valore di INT del personaggio.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AbilityDefinition:
    """Definizione di un'abilità."""

    name: str
    characteristics: list[str]  # caratteristiche collegate (es. ['DES', 'FOR'])
    description: str = ""
    notes: str = ""


# Conoscenze: ogni branca ha un INT minimo richiesto
KNOWLEDGE_BRANCHES: dict[str, int] = {
    "Conoscenze Arcane": 8,
    "Conoscenze Geografia e Storia": 5,
    "Conoscenze Popolari": 3,
    "Conoscenze Nobiltà": 5,
    "Conoscenza Economia e Legge": 6,
    "Conoscenze Guarigione": 7,
    "Conoscenze Natura": 6,
    "Conoscenze Ingegneria": 8,
    "Conoscenze Artigianato": 4,
    "Conoscenze Religioni": 5,
}


ABILITIES: list[AbilityDefinition] = [
    AbilityDefinition(
        name="Atletica",
        characteristics=["DES", "FOR"],
        description=(
            "Prove fisiche: forza (scalare, sollevare) usa FOR; "
            "acrobazia ed equilibrio usa DES."
        ),
    ),
    AbilityDefinition(
        name="Camuffare",
        characteristics=["INT", "EMP"],
        description=(
            "Occultare oggetti o travestirsi. INT per prove studiate, "
            "EMP quando c'è fretta e pressione."
        ),
    ),
    AbilityDefinition(
        name="Cavalcare",
        characteristics=["DES"],
        description="Usare efficacemente una cavalcatura. Evitare di essere disarcionati.",
    ),
    AbilityDefinition(
        name="Cercare",
        characteristics=["INT"],
        description="Trovare oggetti nascosti, passaggi segreti, persone o animali.",
    ),
    AbilityDefinition(
        name="Concentrazione",
        characteristics=["VOL"],
        description=(
            "Mantenersi concentrati in situazioni difficili: combat, invocazioni, lavoro mentale."
        ),
    ),
    AbilityDefinition(
        name="Conoscenza",
        characteristics=["INT"],
        description=(
            "Studio, memoria, cultura. Divisa in branche specifiche (vedi KNOWLEDGE_BRANCHES). "
            "Max branche = INT // 2."
        ),
        notes="Ogni branca ha un requisito INT minimo. Con manuale/trattato: +2 alla prova.",
    ),
    AbilityDefinition(
        name="Empatia Animale",
        characteristics=["EMP"],
        description=(
            "Comunicare con gli animali, capire il loro stato e intenzioni. "
            "Necessaria ogni volta che si approccia un animale non senziente in modo non ostile."
        ),
    ),
    AbilityDefinition(
        name="Furtività",
        characteristics=["DES"],
        description="Muoversi senza essere visti o sentiti.",
    ),
    AbilityDefinition(
        name="Manualità",
        characteristics=["DES"],
        description=(
            "Uso preciso delle mani: strumenti delicati, serrature, suture, oggetti artigianali."
        ),
    ),
    AbilityDefinition(
        name="Percezione",
        characteristics=["IST"],
        description="Usare i sensi per avere un quadro completo della situazione.",
    ),
    AbilityDefinition(
        name="Persuasione",
        characteristics=["VOL"],
        description="Convincere gli altri con parole, retorica, presenza.",
    ),
    AbilityDefinition(
        name="Percepire Intenzioni",
        characteristics=["EMP"],
        description="Leggere il comportamento altrui, captare menzogne e intenzioni nascoste.",
    ),
    AbilityDefinition(
        name="Raggirare",
        characteristics=["VOL"],
        description="Mentire, fingersi qualcun altro, sostenere una falsità sotto pressione.",
    ),
    AbilityDefinition(
        name="Sopravvivenza",
        characteristics=["INT", "IST"],
        description=(
            "Sopravvivere in ambienti ostili: trovare acqua, evitare pericoli, orientarsi. "
            "INT per approccio logico, IST per istinto animale."
        ),
    ),
    AbilityDefinition(
        name="Valutare",
        characteristics=["INT"],
        description="Dare il giusto valore a oggetti, riconoscere metalli, pietre, affari truffaldini.",
    ),
]

ABILITY_NAMES: list[str] = [a.name for a in ABILITIES]


def get_ability(name: str) -> AbilityDefinition | None:
    """Restituisce la definizione di un'abilità per nome.

    Args:
        name: nome esatto dell'abilità.

    Returns:
        AbilityDefinition oppure None se non trovata.
    """
    return next((a for a in ABILITIES if a.name == name), None)
