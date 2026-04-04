"""Stili di vita del sistema GDR v0.8.

Ogni stile di vita descrive come il personaggio ha trascorso un periodo di 5 anni.
Influenza:
- PX guadagnati ogni 5 anni
- Quali stat migliorano (bonus roll) e quali peggiorano (malus roll)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Lifestyle:
    """Definizione di uno stile di vita."""

    id: str
    name: str
    description: str

    # Formula PX: main_stat × stat_mult + 1d8 × die_mult (solo se bonus roll riesce)
    px_stat: str
    """Alias Pydantic della stat di riferimento per il calcolo PX (es. 'for')."""
    stat_mult: int
    """Moltiplicatore della stat per la quota PX garantita."""
    die_mult: int
    """Moltiplicatore del dado 1d8 per la quota bonus PX (solo su successo bonus roll)."""

    # Effetti sui tiri
    bonus_stats: list[str]
    """Stat che migliorano di +1 su successo bonus roll."""
    malus_stats: list[str]
    """Stat che peggiorano di -1 su fallimento malus roll."""

    # Preferenze spesa PX (per NPC auto-spending)
    px_category_weights: dict[str, int] = field(default_factory=dict)
    """Pesi relativi per categoria apprendimento. Es. {'Combattimento': 70, 'Generico': 20}."""


# ---------------------------------------------------------------------------
# Definizioni degli 8 stili di vita
# ---------------------------------------------------------------------------

LIFESTYLES: list[Lifestyle] = [
    Lifestyle(
        id="guerriero",
        name="Guerriero/Soldato",
        description=(
            "Il personaggio trascorre il periodo in servizio militare, addestramento "
            "fisico intenso o campagne di guerra."
        ),
        px_stat="for",
        stat_mult=200,
        die_mult=350,
        bonus_stats=["for", "des", "cos"],
        malus_stats=["int", "emp"],
        px_category_weights={"Combattimento": 70, "Conoscenza": 5, "Generico": 20, "Magia": 5},
    ),
    Lifestyle(
        id="studioso",
        name="Studioso/Accademico",
        description=(
            "Il personaggio si dedica allo studio, alla ricerca e all'apprendimento. "
            "La mente rimane acuta, il corpo si atrofizza."
        ),
        px_stat="int",
        stat_mult=200,
        die_mult=400,
        bonus_stats=["int", "vol"],
        malus_stats=["for", "cos", "des"],
        px_category_weights={"Combattimento": 5, "Conoscenza": 50, "Generico": 25, "Magia": 20},
    ),
    Lifestyle(
        id="artigiano",
        name="Artigiano",
        description=(
            "Il personaggio lavora con le mani e con l'ingegno: fabbro, falegname, "
            "sarto, orafo. Manualità e intelletto si affinano."
        ),
        px_stat="des",
        stat_mult=190,
        die_mult=300,
        bonus_stats=["des", "int", "vol"],
        malus_stats=["for", "ist"],
        px_category_weights={"Combattimento": 15, "Conoscenza": 25, "Generico": 55, "Magia": 5},
    ),
    Lifestyle(
        id="viandante",
        name="Viandante/Mercante",
        description=(
            "Il personaggio viaggia continuamente: mercante, messaggero, esploratore. "
            "L'esperienza con le persone e i riflessi si affinano."
        ),
        px_stat="ist",
        stat_mult=190,
        die_mult=300,
        bonus_stats=["ist", "emp", "des"],
        malus_stats=["cos", "vol"],
        px_category_weights={"Combattimento": 25, "Conoscenza": 20, "Generico": 50, "Magia": 5},
    ),
    Lifestyle(
        id="religioso",
        name="Religioso/Monaco",
        description=(
            "Il personaggio vive in una comunità religiosa o come monaco errante. "
            "La disciplina spirituale rafforza volontà, compassione e cultura."
        ),
        px_stat="vol",
        stat_mult=190,
        die_mult=300,
        bonus_stats=["vol", "emp", "int"],
        malus_stats=["for", "des"],
        px_category_weights={"Combattimento": 10, "Conoscenza": 35, "Generico": 30, "Magia": 25},
    ),
    Lifestyle(
        id="selvaggio",
        name="Selvaggio/Cacciatore",
        description=(
            "Il personaggio vive in natura, caccia e sopravvive lontano dalla civiltà. "
            "Il corpo e l'istinto primordiale si rafforzano; il lato sociale si atrofizza."
        ),
        px_stat="cos",
        stat_mult=185,
        die_mult=280,
        bonus_stats=["cos", "for", "ist"],
        malus_stats=["vol", "emp", "int"],
        px_category_weights={"Combattimento": 45, "Conoscenza": 10, "Generico": 40, "Magia": 5},
    ),
    Lifestyle(
        id="delinquente",
        name="Delinquente/Criminale",
        description=(
            "Il personaggio opera ai margini della legge. "
            "Riflessi, astuzia e determinazione crescono; empatia e cultura si erodono."
        ),
        px_stat="des",
        stat_mult=190,
        die_mult=300,
        bonus_stats=["des", "ist", "vol"],
        malus_stats=["emp", "int", "cos"],
        px_category_weights={"Combattimento": 35, "Conoscenza": 10, "Generico": 50, "Magia": 5},
    ),
    Lifestyle(
        id="comune",
        name="Comune",
        description=(
            "Il personaggio conduce una vita ordinaria: contadino, servo, cittadino. "
            "Solo l'empatia comunitaria cresce; il fisico decade senza protezione."
        ),
        px_stat="ist",
        stat_mult=150,
        die_mult=200,
        bonus_stats=["emp"],
        malus_stats=["for", "cos", "des"],
        px_category_weights={"Combattimento": 20, "Conoscenza": 10, "Generico": 70, "Magia": 0},
    ),
]

# ---------------------------------------------------------------------------
# Stili di vita intermedi
# Combinano due percorsi, PX medi (~2000-2100), bonus/malus più sfumati
# ---------------------------------------------------------------------------

LIFESTYLES_INTERMEDI: list[Lifestyle] = [
    Lifestyle(
        id="mercenario",
        name="Mercenario/Soldato di Ventura",
        description=(
            "Combatte per denaro, non per ideali. Affilato in combattimento e "
            "istinto di sopravvivenza, ma perde legami morali e disciplina interiore."
        ),
        px_stat="for",
        stat_mult=175,
        die_mult=280,
        bonus_stats=["for", "des", "ist"],
        malus_stats=["emp", "vol"],
        px_category_weights={"Combattimento": 65, "Generico": 30, "Conoscenza": 5, "Magia": 0},
    ),
    Lifestyle(
        id="esploratore",
        name="Esploratore/Ranger",
        description=(
            "Percorre terre selvagge e cartografa l'ignoto. Corpo resistente e "
            "sensi acuti, ma la solitudine erode i legami sociali."
        ),
        px_stat="ist",
        stat_mult=175,
        die_mult=280,
        bonus_stats=["ist", "cos", "des"],
        malus_stats=["vol", "emp"],
        px_category_weights={"Combattimento": 35, "Generico": 45, "Conoscenza": 20, "Magia": 0},
    ),
    Lifestyle(
        id="alchimista",
        name="Alchimista/Erborista",
        description=(
            "Studia e pratica: non solo libri ma esperimenti, distillati, rimedi. "
            "Mente e mani affilate, corpo trascurato tra i vapori del laboratorio."
        ),
        px_stat="int",
        stat_mult=180,
        die_mult=300,
        bonus_stats=["int", "des", "vol"],
        malus_stats=["for", "cos"],
        px_category_weights={"Conoscenza": 45, "Generico": 35, "Magia": 20, "Combattimento": 0},
    ),
    Lifestyle(
        id="bardo",
        name="Bardo/Predicatore Itinerante",
        description=(
            "Viaggia predicando, cantando o recitando. Carisma e intuito umano "
            "crescono; il fisico soffre la vita on the road."
        ),
        px_stat="vol",
        stat_mult=175,
        die_mult=270,
        bonus_stats=["vol", "emp", "ist"],
        malus_stats=["for", "cos"],
        px_category_weights={"Generico": 45, "Conoscenza": 30, "Magia": 15, "Combattimento": 10},
    ),
    Lifestyle(
        id="cacciatore_taglie",
        name="Cacciatore di Taglie",
        description=(
            "Insegue fuggitivi e criminali per denaro. Sensi pronti, corpo "
            "allenato, ma il lavoro sporco erode empatia e senso morale."
        ),
        px_stat="ist",
        stat_mult=180,
        die_mult=290,
        bonus_stats=["ist", "for", "des"],
        malus_stats=["emp", "vol"],
        px_category_weights={"Combattimento": 55, "Generico": 40, "Conoscenza": 5, "Magia": 0},
    ),
    Lifestyle(
        id="guardia",
        name="Guardia/Milite Cittadino",
        description=(
            "Pattuglia, sorveglianza, ordine pubblico. Più routine che battaglia: "
            "il corpo si mantiene ma la mente langue nella monotonia."
        ),
        px_stat="for",
        stat_mult=165,
        die_mult=240,
        bonus_stats=["for", "ist"],
        malus_stats=["int", "emp"],
        px_category_weights={"Combattimento": 50, "Generico": 40, "Conoscenza": 10, "Magia": 0},
    ),
]

# ---------------------------------------------------------------------------
# Stili di vita apprendisti
# Personaggi in formazione: PX bassi (~1200-1400), focus sull'apprendimento
# Malus ridotti, bonus orientati a INT/VOL oltre alla stat pratica
# ---------------------------------------------------------------------------

LIFESTYLES_APPRENDISTI: list[Lifestyle] = [
    Lifestyle(
        id="scudiero",
        name="Scudiero/Apprendista Guerriero",
        description=(
            "Serve un cavaliere o un capitano, impara le arti della guerra. "
            "Corpo in formazione, mente aperta alla tattica."
        ),
        px_stat="for",
        stat_mult=120,
        die_mult=150,
        bonus_stats=["for", "des", "int"],
        malus_stats=["emp"],
        px_category_weights={"Combattimento": 60, "Generico": 30, "Conoscenza": 10, "Magia": 0},
    ),
    Lifestyle(
        id="apprendista_artigiano",
        name="Apprendista Artigiano",
        description=(
            "Impara un mestiere manuale sotto la guida di un maestro. "
            "Destrezza e ingegno crescono, la forza bruta resta secondaria."
        ),
        px_stat="des",
        stat_mult=115,
        die_mult=140,
        bonus_stats=["des", "int"],
        malus_stats=["for"],
        px_category_weights={"Generico": 70, "Conoscenza": 20, "Combattimento": 10, "Magia": 0},
    ),
    Lifestyle(
        id="novizio",
        name="Novizio/Chierico in Formazione",
        description=(
            "Inizia il percorso religioso o spirituale. Studia testi sacri, "
            "pratica la disciplina interiore, costruisce l'empatia."
        ),
        px_stat="vol",
        stat_mult=115,
        die_mult=140,
        bonus_stats=["vol", "int", "emp"],
        malus_stats=["for"],
        px_category_weights={"Conoscenza": 40, "Generico": 40, "Magia": 20, "Combattimento": 0},
    ),
    Lifestyle(
        id="studente",
        name="Studente/Allievo Accademico",
        description=(
            "Frequenta una scuola, un'università o studia sotto un mentore. "
            "La mente si forma rapidamente; il corpo è completamente trascurato."
        ),
        px_stat="int",
        stat_mult=120,
        die_mult=160,
        bonus_stats=["int", "vol"],
        malus_stats=["cos", "for"],
        px_category_weights={"Conoscenza": 60, "Generico": 30, "Magia": 10, "Combattimento": 0},
    ),
    Lifestyle(
        id="apprendista_ladro",
        name="Apprendista Borsaiolo/Ladro",
        description=(
            "Impara i trucchi del mestiere criminale da un mentore di strada. "
            "Riflessi e istinto si affinano; la moralità inizia a cedere."
        ),
        px_stat="des",
        stat_mult=115,
        die_mult=140,
        bonus_stats=["des", "ist"],
        malus_stats=["vol"],
        px_category_weights={"Generico": 60, "Combattimento": 30, "Conoscenza": 10, "Magia": 0},
    ),
]

# ---------------------------------------------------------------------------
# Lista completa
# ---------------------------------------------------------------------------

LIFESTYLES: list[Lifestyle] = LIFESTYLES + LIFESTYLES_INTERMEDI + LIFESTYLES_APPRENDISTI

LIFESTYLE_BY_ID: dict[str, Lifestyle] = {ls.id: ls for ls in LIFESTYLES}


def get_lifestyle(lifestyle_id: str) -> Lifestyle | None:
    """Restituisce uno stile di vita per ID.

    Args:
        lifestyle_id: identificativo dello stile (es. 'guerriero').

    Returns:
        Lifestyle oppure None se non trovato.
    """
    return LIFESTYLE_BY_ID.get(lifestyle_id)


# Mappatura background → stile di vita tipico del passato.
# Usata per simulare i PX iniziali durante la creazione personaggio.
BACKGROUND_DEFAULT_LIFESTYLE: dict[str, str] = {
    "Criminale": "delinquente",
    "Ex Criminale": "delinquente",
    "Studioso": "studioso",
    "Guardiano": "guerriero",
    "Nato per Combattere": "guerriero",
    "Erede della Foresta": "selvaggio",
    "Esiliato": "selvaggio",
    "Nobile": "comune",
    "Indottrinato": "religioso",
    "Servo della Follia": "religioso",
    "Nato in Sella": "viandante",
    "Sempliciotto": "comune",
}
