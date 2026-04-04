"""Subset degli apprendimenti del sistema GDR v0.8 (216 totali).

Implementati: Combattimento Generici, Abilità Generiche, Magia base.
Gli altri sono predisposti come struttura ma non ancora dettagliati.
"""

from __future__ import annotations

from app.schemas import Learning

LEARNINGS: list[Learning] = [
    # -----------------------------------------------------------------------
    # COMBATTIMENTO — Generici
    # -----------------------------------------------------------------------
    Learning(
        name="Addestramento (L)",
        category="Combattimento",
        subcategory="Generico",
        description="Permette di diventare competente con le armi Leggere: somma DES al tiro per colpire.",
        cost=800,
    ),
    Learning(
        name="Addestramento (M)",
        category="Combattimento",
        subcategory="Generico",
        description="Permette di diventare competente con le armi Medie: somma DES al tiro per colpire.",
        cost=800,
    ),
    Learning(
        name="Addestramento (P)",
        category="Combattimento",
        subcategory="Generico",
        description="Permette di diventare competente con le armi Pesanti: somma DES al tiro per colpire.",
        cost=800,
    ),
    Learning(
        name="Addestramento (T)",
        category="Combattimento",
        subcategory="Generico",
        description="Permette di diventare competente con le armi da Lancio: somma DES al tiro per colpire.",
        cost=800,
    ),
    Learning(
        name="Ad Hoc",
        category="Combattimento",
        subcategory="Generico",
        description=(
            "Competenza con una specifica categoria di arma (Spada, Arma inastata, Mazza, "
            "Ascia, Arco, Balestra, Pugnale, Speciali), indipendentemente dalla classe di peso."
        ),
        cost=800,
    ),
    Learning(
        name="Esercizio (L)",
        category="Combattimento",
        subcategory="Generico",
        description="Aumenta il bonus a colpire di +2 con armi Leggere.",
        cost=1000,
        prerequisites=["Addestramento (L)"],
    ),
    Learning(
        name="Esercizio (M)",
        category="Combattimento",
        subcategory="Generico",
        description="Aumenta il bonus a colpire di +2 con armi Medie.",
        cost=1000,
        prerequisites=["Addestramento (M)"],
    ),
    Learning(
        name="Esercizio (P)",
        category="Combattimento",
        subcategory="Generico",
        description="Aumenta il bonus a colpire di +2 con armi Pesanti.",
        cost=1000,
        prerequisites=["Addestramento (P)"],
    ),
    Learning(
        name="Esercizio (T)",
        category="Combattimento",
        subcategory="Generico",
        description="Aumenta il bonus a colpire di +2 con armi da Lancio.",
        cost=1000,
        prerequisites=["Addestramento (T)"],
    ),
    Learning(
        name="Milite",
        category="Combattimento",
        subcategory="Generico",
        description="Sei in grado di utilizzare armature L e M.",
        cost=800,
    ),
    Learning(
        name="Uomo D'arme",
        category="Combattimento",
        subcategory="Generico",
        description="Sei in grado di utilizzare armature M e P.",
        cost=800,
    ),
    Learning(
        name="Mano Pesante",
        category="Combattimento",
        subcategory="Generico",
        description="+2 ai danni e alle prove di forza in combattimento, -2 alle prove di manualità e furtività.",
        cost=600,
        special_notes="Requisito FOR: 8. Esclude Manosperta.",
    ),
    Learning(
        name="Arte Marziale",
        category="Combattimento",
        subcategory="Mischia",
        description=(
            "+3 nelle prove in lotta e fai d6 di danno a mani nude. "
            "In combattimento non sei considerato scoperto alle spalle (se l'avversario non è nascosto). "
            "La minaccia si estende in tutta l'area, in portata, attorno a te."
        ),
        cost=1000,
        special_notes="Richiede: nessuna o armatura leggera.",
    ),
    Learning(
        name="Ambi­destro",
        category="Combattimento",
        subcategory="Generico",
        description=(
            "Il personaggio somma il bonus DES quando colpisce con armi di cui è competente "
            "sia con la destra che con la sinistra. "
            "Può impugnare armi diverse in entrambe le mani senza richiedere entrambe le mani contemporaneamente."
        ),
        cost=1000,
    ),
    Learning(
        name="Come un Bue",
        category="Combattimento",
        subcategory="Generico",
        description="Una volta al giorno acquistate metà dei Punti Fatica senza riposare neanche un round.",
        cost=1200,
    ),
    Learning(
        name="Impeto (L)",
        category="Combattimento",
        subcategory="Mischia",
        description="Utilizzando 2 punti fatica puoi compiere due attacchi con armi da Mischia L.",
        cost=800,
        prerequisites=["Addestramento (L)"],
    ),
    Learning(
        name="Impeto (M)",
        category="Combattimento",
        subcategory="Mischia",
        description="Utilizzando 3 punti fatica, puoi compiere 2 attacchi nello stesso turno con armi da Mischia M.",
        cost=800,
        prerequisites=["Addestramento (M)"],
    ),
    Learning(
        name="Impeto (P)",
        category="Combattimento",
        subcategory="Mischia",
        description="Utilizzando 5 punti fatica, puoi compiere 2 attacchi nello stesso turno con armi da Mischia P.",
        cost=800,
        prerequisites=["Addestramento (P)"],
    ),
    Learning(
        name="Scudo I",
        category="Combattimento",
        subcategory="Scudo",
        description="Permette di parare i colpi una volta a round utilizzando lo scudo.",
        cost=400,
    ),
    Learning(
        name="Scudo II",
        category="Combattimento",
        subcategory="Scudo",
        description="Permette di contrattaccare se la parata è andata a buon fine.",
        cost=800,
        prerequisites=["Scudo I"],
    ),
    Learning(
        name="Scudo III",
        category="Combattimento",
        subcategory="Scudo",
        description="Aumenta il valore di 'Schivare' degli scudi di +2.",
        cost=800,
        prerequisites=["Scudo II"],
    ),
    Learning(
        name="Guardia",
        category="Combattimento",
        subcategory="Mischia",
        description=(
            "Ti consente, se sei in piedi, di scegliere in che Guardia fronteggiare l'avversario. "
            "Guardia Offensiva: -2 Schivare, +4 Danni. "
            "Guardia Difensiva: +2 Schivare, -4 Danni. "
            "Guardia Stanca: +1 Schivare, -2 Danni."
        ),
        cost=800,
        prerequisites=["Esercizio (L)", "Esercizio (M)", "Esercizio (P)"],
        special_notes="Richiede uno qualsiasi degli Esercizi.",
    ),
    Learning(
        name="Muro di Scudi",
        category="Combattimento",
        subcategory="Scudo",
        description=(
            "Se sei affianco a uno o più personaggi con 'Muro di Scudi', "
            "potete unirvi e formare un muro di scudi. "
            "Il valore di 'Schivare' del muro è la somma dei singoli scudi."
        ),
        cost=800,
        prerequisites=["Scudo II"],
    ),
    Learning(
        name="Difesa Cieca",
        category="Combattimento",
        subcategory="Scudo",
        description=(
            "Se hai uno scudo e ti viene negata la DES ma sei libero di muoverti, "
            "hai diritto a un tentativo di parata agli attacchi (anche furtivi)."
        ),
        cost=1400,
        prerequisites=["Scudo II"],
    ),
    Learning(
        name="Resistenza Fisica",
        category="Combattimento",
        subcategory="Generico",
        description=(
            "Puoi indossare un'armatura L e una M o P contemporaneamente nella stessa locazione. "
            "Si sommano tutti i bonus e malus."
        ),
        cost=800,
        special_notes="Requisito FOR: 6. Richiede Addestramento (M o P).",
    ),
    Learning(
        name="Istinto Primordiale",
        category="Combattimento",
        subcategory="Mischia",
        description=(
            "Permette di sostituire la caratteristica di lancio con IST per i tiri su: "
            "Colpire, Cercare, Percepire Intenzioni, Concentrazione."
        ),
        cost=800,
        special_notes="Disponibile solo alla creazione del personaggio (o per effetti magici).",
    ),

    # -----------------------------------------------------------------------
    # ABILITÀ — Generiche
    # -----------------------------------------------------------------------
    Learning(
        name="Alfabetismo",
        category="Abilità",
        subcategory="Generico",
        description="Sei in grado di leggere e scrivere.",
        cost=800,
    ),
    Learning(
        name="A Lume di Candela",
        category="Abilità",
        subcategory="Generico",
        description=(
            "Il personaggio è abituato a muoversi al buio. "
            "Nelle condizioni di scarsa luminosità ottiene +2 alla percezione. "
            "In piena luce ha malus alla percezione di -1."
        ),
        cost=600,
    ),
    Learning(
        name="Amanuense",
        category="Abilità",
        subcategory="Generico",
        description="Puoi falsificare documenti, firme e sigilli con un +2 in manualità.",
        cost=1000,
    ),
    Learning(
        name="Anima Antica",
        category="Abilità",
        subcategory="Generico",
        description=(
            "Ottieni +3 PF e +2 a Schivare ad una locazione a tua scelta "
            "e +1 ad una abilità a tua scelta."
        ),
        cost=1000,
        special_notes="Disponibile solo alla creazione del personaggio.",
    ),

    # -----------------------------------------------------------------------
    # MAGIA — Base
    # -----------------------------------------------------------------------
    Learning(
        name="Risveglio",
        category="Magia",
        subcategory="Base",
        description=(
            "Ti dona un dado potere (specificare al master se si intende utilizzare "
            "la magia spontanea o appresa). Sblocca l'accesso al piano arcano."
        ),
        cost=1500,
        special_notes="Prerequisito per quasi tutti gli apprendimenti di Magia.",
    ),
    Learning(
        name="Pensiero Eclettico",
        category="Magia",
        subcategory="Base",
        description="Una volta al giorno tiri un dado potere; il risultato può essere ripartito in più incanti a piacere.",
        cost=600,
    ),
    Learning(
        name="Vedere il Vero",
        category="Magia",
        subcategory="Base",
        description=(
            "La tua affinità alla trama arcana ti permette di vedere le tracce di energia arcana pura. "
            "Le visioni non sono mai nitide, ma ti consentono di capire cosa sia magico e cosa no, "
            "se è attivo un incantesimo in un luogo ecc."
        ),
        cost=800,
        prerequisites=["Risveglio"],
        special_notes="Requisiti: Conoscenze Arcane (3), DP: 4.",
    ),
    Learning(
        name="Connessione Intima",
        category="Magia",
        subcategory="Arcano",
        description=(
            "Permette di collegarti al piano arcano e sfruttare le connessioni arcane. "
            "A questo stadio si può solo ottenere un bersaglio (se questo è vivo)."
        ),
        cost=2000,
    ),
    Learning(
        name="Catalizzazione",
        category="Magia",
        subcategory="Arcano",
        description=(
            "Conosci bene la relazione tra l'energia arcana e la materia. "
            "Infondendo lentamente potere arcano in un oggetto puoi renderlo un 'Catalizzatore'. "
            "Il risultato del tiro dei dadi potere dev'essere minimo 25. "
            "Non si possono creare più catalizzatori del numero di dadi potere diviso due."
        ),
        cost=1500,
        prerequisites=["Risveglio"],
        special_notes="Requisiti: DP: 5, Conoscenze Arcane: 2.",
    ),
]

LEARNING_NAMES: list[str] = [l.name for l in LEARNINGS]


def get_learning(name: str) -> Learning | None:
    """Restituisce un apprendimento per nome.

    Args:
        name: nome esatto dell'apprendimento.

    Returns:
        Learning oppure None se non trovato.
    """
    return next((l for l in LEARNINGS if l.name == name), None)


def get_learnings_by_category(category: str) -> list[Learning]:
    """Restituisce tutti gli apprendimenti di una categoria.

    Args:
        category: categoria (es. 'Combattimento', 'Magia', 'Abilità').

    Returns:
        Lista di Learning.
    """
    return [l for l in LEARNINGS if l.category == category]


def get_affordable_learnings(px_available: int, owned: list[str]) -> list[Learning]:
    """Restituisce gli apprendimenti acquistabili dati i PX e gli apprendimenti già posseduti.

    Args:
        px_available: PX rimanenti.
        owned: lista dei nomi degli apprendimenti già posseduti.

    Returns:
        Lista di Learning acquistabili (costo ≤ px_available, prerequisiti soddisfatti, non già posseduto).
    """
    result = []
    for learning in LEARNINGS:
        if learning.name in owned:
            continue
        if learning.cost > px_available:
            continue
        if all(p in owned for p in learning.prerequisites):
            result.append(learning)
    return result
