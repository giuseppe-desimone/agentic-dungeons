"""Background del sistema GDR v0.8.

Ogni background definisce:
- px_threshold: PX minimi del personaggio per applicarlo
- px_usable: PX aggiuntivi utilizzabili (alcuni background ne forniscono)
- stat_bonuses: modificatori alle caratteristiche
- skill_bonuses: modificatori alle abilità
- granted_abilities/learnings: concessioni senza prerequisiti
- race_required: se applicabile solo a una razza specifica
"""

from __future__ import annotations

from app.schemas import Background, Race, SkillBonus, StatBonus

BACKGROUNDS: list[Background] = [
    Background(
        name="Indottrinato",
        description=(
            "Il PG ha ricevuto un forte indottrinamento verso una divinità o dogmi."
        ),
        px_threshold=4000,
        px_usable=0,
        stat_bonuses=[StatBonus(stat="vol", value=2), StatBonus(stat="int", value=-2)],
        skill_bonuses=[],
        granted_abilities=["Conoscenza (Religioni)"],
        stat_priorities=["VOL", "EMP", "INT"],
        special_notes="Acquisisce Conoscenze (Religioni) anche senza soddisfarne i requisiti.",
    ),
    Background(
        name="Ex Criminale",
        description=(
            "Il PG proviene da un passato burrascoso e da malaffari. "
            "Questo può influire sulle relazioni in gioco."
        ),
        px_threshold=4000,
        px_usable=0,
        stat_bonuses=[],
        skill_bonuses=[
            SkillBonus(ability="Percepire Intenzioni", value=2),
            SkillBonus(ability="Raggirare", value=1),
        ],
        granted_abilities=["Conoscenza (Sobborghi)"],
        stat_priorities=["DES", "IST", "EMP"],
        special_notes="Conoscenze (Sobborghi) senza requisiti.",
    ),
    Background(
        name="Criminale",
        description=(
            "Il PG è nella malavita da vari anni. "
            "Parte con notorietà 'Conosciuto' in ambienti criminali."
        ),
        px_threshold=7000,
        px_usable=0,
        stat_bonuses=[],
        skill_bonuses=[
            SkillBonus(ability="Percepire Intenzioni", value=2),
            SkillBonus(ability="Conoscenza (Sobborghi)", value=2, ignore_prerequisites=True),
            SkillBonus(ability="Raggirare", value=2),
            SkillBonus(ability="Furtività", value=2),
        ],
        granted_abilities=["Conoscenza (Sobborghi)"],
        stat_priorities=["DES", "IST", "VOL"],
        special_notes=(
            "Notorietà 'Conosciuto' in ambienti criminali. "
            "Le azioni criminali passate avranno ripercussioni in gioco."
        ),
    ),
    Background(
        name="Studioso",
        description=(
            "Il PG ha passato gran parte della sua vita studiando. "
            "(Il PG deve avere almeno 35 anni da umano.)"
        ),
        px_threshold=7000,
        px_usable=2000,
        stat_bonuses=[
            StatBonus(stat="ist", value=-3),
            StatBonus(stat="for", value=-4),
            StatBonus(stat="cos", value=-2),
            StatBonus(stat="des", value=-3),
            StatBonus(stat="int", value=3),
        ],
        skill_bonuses=[SkillBonus(ability="Concentrazione", value=2)],
        granted_abilities=[
            "Conoscenza (Arcane)",
            "Conoscenza (Geografia e Storia)",
            "Conoscenza (Nobiltà)",
            "Conoscenza (Guarigione)",
            "Conoscenza (Alchimia)",
            "Conoscenza (Natura)",
            "Conoscenza (Ingegneria)",
            "Conoscenza (Religioni)",
        ],
        stat_priorities=["INT", "VOL", "EMP"],
        special_notes=(
            "Tutte le conoscenze elencate sono concesse senza requisiti. "
            "Parte con 2000 PX utili su 7000 totali."
        ),
    ),
    Background(
        name="Erede della Foresta",
        description=(
            "Il personaggio è cresciuto allo stato brado, lontano dalla civiltà "
            "e a contatto costante con gli animali."
        ),
        px_threshold=5000,
        px_usable=1000,
        stat_bonuses=[StatBonus(stat="ist", value=2), StatBonus(stat="emp", value=-2)],
        skill_bonuses=[
            SkillBonus(ability="Sopravvivenza", value=2),
            SkillBonus(ability="Percezione", value=1),
            SkillBonus(ability="Empatia Animale", value=3),
        ],
        granted_abilities=["Conoscenza (Natura)"],
        stat_priorities=["IST", "EMP", "COS"],
        special_notes=(
            "Alle prove di Empatia Animale usa IST invece di EMP. "
            "Conoscenza (Natura) senza requisiti. "
            "Parte con 1000 PX utili su 5000 totali."
        ),
    ),
    Background(
        name="Esiliato",
        description=(
            "Provieni da una tribù sperduta, hai avuto pochissimi contatti con la civiltà, "
            "sei stato esiliato e ripudiato. Hai una menomazione permanente."
        ),
        px_threshold=2000,
        px_usable=0,
        stat_bonuses=[],
        skill_bonuses=[],
        granted_abilities=["Conoscenza (Geografia e Storia)"],
        stat_priorities=["IST", "COS", "FOR"],
        special_notes=(
            "Scegli una menomazione permanente tra: Sordità, Cecità, Lingua Mozzata, Mano amputata. "
            "Conoscenza (Geografia e Storia) senza requisiti. "
            "Se possiedi l'apprendimento 'Risveglio', parti con un dado potere aggiuntivo."
        ),
    ),
    Background(
        name="Nato in Sella",
        description="Hai vantaggio ogni volta che compi un tiro abilità nei confronti della tua cavalcatura.",
        px_threshold=2000,
        px_usable=0,
        stat_bonuses=[],
        skill_bonuses=[],
        granted_abilities=[],
        stat_priorities=["DES", "IST", "FOR"],
        special_notes=(
            "Vantaggio a tutte le prove riguardanti la propria cavalcatura: "
            "gestione, combattimento, peripezie della cavalcata."
        ),
    ),
    Background(
        name="Servo della Follia",
        description=(
            "Il personaggio venera una divinità inventata da sé stesso. "
            "Ottiene Devozione come di norma ma non conosce la propria divinità."
        ),
        px_threshold=2000,
        px_usable=0,
        stat_bonuses=[],
        skill_bonuses=[],
        granted_abilities=[],
        stat_priorities=["VOL", "EMP", "IST"],
        special_notes=(
            "La divinità viene gestita interamente dal DM. "
            "Il personaggio crede fermamente in questo Dio."
        ),
    ),
    Background(
        name="Sempliciotto",
        description=(
            "Il personaggio non spicca per la sua intelligenza, "
            "anche nelle situazioni più pericolose pare essere a suo agio."
        ),
        px_threshold=2000,
        px_usable=0,
        stat_bonuses=[
            StatBonus(stat="int", value=-2),
            StatBonus(stat="ist", value=-2),
            StatBonus(stat="vol", value=3),
        ],
        skill_bonuses=[],
        granted_abilities=[],
        stat_priorities=["FOR", "COS", "VOL"],
    ),
    Background(
        name="Guardiano",
        description="Hai passato anni a proteggere e sorvegliare qualcuno o qualcosa.",
        px_threshold=2000,
        px_usable=0,
        stat_bonuses=[],
        skill_bonuses=[
            SkillBonus(ability="Percezione", value=1),
            SkillBonus(ability="Percepire Intenzioni", value=1),
        ],
        granted_abilities=[],
        stat_priorities=["IST", "FOR", "COS"],
    ),
    Background(
        name="Nobile",
        description=(
            "Il tuo personaggio è di nobili origini, ha ricevuto una buona istruzione "
            "ed è abituato a un certo standard di vita."
        ),
        px_threshold=4000,
        px_usable=2000,
        stat_bonuses=[
            StatBonus(stat="vol", value=-1),
            StatBonus(stat="for", value=-1),
            StatBonus(stat="ist", value=-2),
        ],
        skill_bonuses=[
            SkillBonus(ability="Conoscenza (Nobiltà)", value=2, ignore_prerequisites=True),
            SkillBonus(
                ability="Conoscenza (Geografia e Storia)", value=2, ignore_prerequisites=True
            ),
            SkillBonus(ability="Persuasione", value=1),
            SkillBonus(ability="Valutare", value=1),
            SkillBonus(ability="Cavalcare", value=1),
        ],
        granted_abilities=["Conoscenza (Nobiltà)", "Conoscenza (Geografia e Storia)"],
        stat_priorities=["VOL", "INT", "EMP"],
        special_notes=(
            "Notorietà iniziale: 'Sentito'. "
            "Parte con 2000 PX utili su 4000 totali."
        ),
    ),
    Background(
        name="Nato per Combattere",
        description=(
            "Il tuo Clan ti ha destinato al combattimento e alla difesa sin da bambino. "
            "Disponibile solo per i Nani."
        ),
        px_threshold=9000,
        px_usable=1000,
        stat_bonuses=[
            StatBonus(stat="vol", value=2),
            StatBonus(stat="des", value=1),
            StatBonus(stat="cos", value=1),
        ],
        skill_bonuses=[],
        granted_abilities=[],
        granted_learnings=[
            "Addestramento (M)",
            "Esercizio (M)",
            "Scudo I",
            "Scudo II",
            "Muro di Scudi",
            "Difesa Cieca",
            "Come un Bue",
        ],
        stat_priorities=["FOR", "COS", "VOL"],
        special_notes=(
            "Non puoi partire con gradi in: Camuffare, Persuasione, tutte le Conoscenze, "
            "Percepire Intenzioni, Empatia Animale, Valutare, Raggirare, Furtività. "
            "Puoi acquistare 'Anni di Esperienza'. "
            "Parte con 1000 PX utili su 9000 totali."
        ),
        race_required=Race.NANO,
    ),
]

BACKGROUND_NAMES: list[str] = [b.name for b in BACKGROUNDS]


def get_background(name: str) -> Background | None:
    """Restituisce il background per nome.

    Args:
        name: nome esatto del background.

    Returns:
        Background oppure None se non trovato.
    """
    return next((b for b in BACKGROUNDS if b.name == name), None)


def get_available_backgrounds(race: Race, px_total: int) -> list[Background]:
    """Restituisce i background applicabili per razza e PX disponibili.

    Args:
        race: la razza del personaggio.
        px_total: i PX totali disponibili alla creazione.

    Returns:
        Lista di Background applicabili.
    """
    result = []
    for bg in BACKGROUNDS:
        if bg.race_required is not None and bg.race_required != race:
            continue
        if px_total >= bg.px_threshold:
            result.append(bg)
    return result
