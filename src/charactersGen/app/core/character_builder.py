"""Logica pura per la creazione del personaggio GDR v0.8.

Separato dall'UI: tutte le funzioni accettano valori già scelti
e restituiscono oggetti del dominio. Usato sia dal wizard interattivo
che dalla generazione automatica NPC.
"""

from __future__ import annotations

import random

from app.data.abilities import ABILITIES, AbilityDefinition
from app.data.backgrounds import get_available_backgrounds
from app.data.equipment import ARMORS, MELEE_WEAPONS, SHIELDS
from app.data.races import (
    RACE_DEFINITIONS,
    RaceDefinition,
    get_race_definition,
    get_stat_dice_count,
)
from app.core.dice import roll_nd
from app.core.aging import SimulationResult, simulate_past
from app.schemas import (
    AbilityGrade,
    ArmorItem,
    Background,
    BodyLocation,
    Character,
    CharacterStats,
    Race,
    Sex,
    ShieldItem,
    WeaponItem,
)


# ---------------------------------------------------------------------------
# Costruzione caratteristiche
# ---------------------------------------------------------------------------

# Ordine canonico delle 7 caratteristiche (alias Pydantic)
ALL_STATS: list[str] = ["cos", "for", "des", "vol", "int", "ist", "emp"]
STAT_LABELS: dict[str, str] = {
    "cos": "COS", "for": "FOR", "des": "DES",
    "vol": "VOL", "int": "INT", "ist": "IST", "emp": "EMP",
}


def roll_stat_pool(race: Race, age: int, rng: random.Random | None = None) -> list[int]:
    """Tira 7 valori grezzi da assegnare alle caratteristiche.

    I valori vengono tirati con i dadi della razza e dell'età,
    ma non sono ancora assegnati a nessuna caratteristica specifica.

    Args:
        race: la razza del personaggio.
        age: l'età (determina il numero di dadi: 2d4 <20, 3d4 >=20).
        rng: generatore casuale opzionale.

    Returns:
        Lista di 7 interi (valori grezzi non assegnati).
    """
    race_def = get_race_definition(race)
    num_dice = get_stat_dice_count(age)
    return [roll_nd(num_dice, race_def.phys_die, rng).total for _ in range(7)]


def assign_stats_weighted(
    pool: list[int],
    priorities: list[str],
    rng: random.Random | None = None,
) -> CharacterStats:
    """Assegna i valori del pool alle caratteristiche con distribuzione pesata.

    Algoritmo:
    - Ordina il pool dal più alto al più basso.
    - Le top 3 statistiche (priorities) ricevono i 3 valori più alti
      (ordine casuale tra di loro).
    - Le restanti 4 statistiche ricevono i 4 valori più bassi
      (ordine casuale tra di loro).
    - I modificatori d'età sono applicati separatamente da simulate_past.

    Args:
        pool: lista di 7 valori tirati.
        priorities: top 3 caratteristiche da favorire (es. ['FOR', 'DES', 'COS']).
        rng: generatore casuale opzionale.

    Returns:
        CharacterStats con valori assegnati (senza modificatori età).
    """
    _rng = rng or random
    sorted_values = sorted(pool, reverse=True)

    prio_keys = [p.lower() for p in priorities[:3]]
    prio_keys = [k for k in prio_keys if k in ALL_STATS]
    remaining = [s for s in ALL_STATS if s not in prio_keys]
    _rng.shuffle(remaining)
    while len(prio_keys) < 3 and remaining:
        prio_keys.append(remaining.pop(0))

    non_prio = [s for s in ALL_STATS if s not in prio_keys]
    _rng.shuffle(prio_keys)
    _rng.shuffle(non_prio)

    assignment: dict[str, int] = {}
    for i, stat in enumerate(prio_keys):
        assignment[stat] = sorted_values[i]
    for i, stat in enumerate(non_prio):
        assignment[stat] = sorted_values[3 + i]

    return CharacterStats(**assignment)


def assign_stats_manual(
    pool: list[int],
    assignment_map: dict[str, int],
) -> CharacterStats:
    """Assegna i valori del pool alle caratteristiche secondo la scelta del giocatore.

    Args:
        pool: lista originale dei valori tirati (usata per validazione).
        assignment_map: {alias_stat: valore} — mappa completa delle 7 caratteristiche.

    Returns:
        CharacterStats con i valori scelti.

    Raises:
        ValueError: se l'assegnazione non copre tutte le 7 caratteristiche.
    """
    missing = [s for s in ALL_STATS if s not in assignment_map]
    if missing:
        raise ValueError(f"Caratteristiche non assegnate: {missing}")

    assigned_values = sorted(assignment_map.values())
    pool_sorted = sorted(pool)
    if assigned_values != pool_sorted:
        raise ValueError(
            f"I valori assegnati {sorted(assignment_map.values())} "
            f"non corrispondono al pool tirati {pool_sorted}."
        )

    return CharacterStats(**{stat: assignment_map[stat] for stat in ALL_STATS})


def roll_stats(race: Race, age: int, rng: random.Random | None = None) -> CharacterStats:
    """Tira e assegna casualmente le caratteristiche (senza priorità background).

    Usato nei test e come fallback. I modificatori d'età sono gestiti da simulate_past.

    Args:
        race: la razza del personaggio.
        age: l'età del personaggio (usata solo per il numero di dadi).
        rng: generatore casuale opzionale.

    Returns:
        CharacterStats con valori assegnati in ordine casuale.
    """
    pool = roll_stat_pool(race, age, rng)
    _rng = rng or random
    shuffled_stats = ALL_STATS[:]
    _rng.shuffle(shuffled_stats)
    assignment = dict(zip(shuffled_stats, sorted(pool, reverse=True)))
    return CharacterStats(**assignment)


# ---------------------------------------------------------------------------
# Costruzione corpo (PF e schivare)
# ---------------------------------------------------------------------------


def build_body(race_def: RaceDefinition, stats: CharacterStats) -> list[BodyLocation]:
    """Calcola le locazioni corporee con PF e valore schivare.

    Formule:
        PF = pf_base[locazione] + COS
        Schivare = schivare_base[locazione] + DES

    Args:
        race_def: definizione della razza.
        stats: le caratteristiche del personaggio.

    Returns:
        Lista di BodyLocation.
    """
    locations = []
    for loc_name, base_pf in race_def.pf_base.items():
        max_pf = base_pf + stats.cos
        schivare = race_def.schivare_base[loc_name] + stats.des
        locations.append(
            BodyLocation(
                name=loc_name,
                max_pf=max_pf,
                current_pf=max_pf,
                schivare=schivare,
            )
        )
    return locations


def compute_resistenza(stats: CharacterStats) -> int:
    """Calcola la Resistenza del personaggio.

    RES = (FOR + DES) // 2

    Args:
        stats: le caratteristiche del personaggio.

    Returns:
        Valore intero della Resistenza.
    """
    return (stats.for_ + stats.des) // 2


# ---------------------------------------------------------------------------
# Abilità
# ---------------------------------------------------------------------------


def initial_ability_budget(stats: CharacterStats) -> int:
    """Calcola il numero di gradi abilità da distribuire alla creazione.

    Budget = max(INT, VOL) // 2

    Args:
        stats: le caratteristiche del personaggio.

    Returns:
        Numero di gradi disponibili.
    """
    return max(stats.int_, stats.vol) // 2


def build_ability_list(stats: CharacterStats) -> list[AbilityGrade]:
    """Crea la lista di tutte le abilità con 0 gradi.

    Args:
        stats: caratteristiche (non usate qui, ma utili per validazioni future).

    Returns:
        Lista di AbilityGrade con grades=0.
    """
    return [
        AbilityGrade(
            name=a.name,
            characteristics=a.characteristics,
            grades=0,
        )
        for a in ABILITIES
    ]


def assign_ability_grades(
    abilities: list[AbilityGrade],
    assignments: dict[str, int],
    stats: CharacterStats,
) -> list[AbilityGrade]:
    """Assegna gradi alle abilità rispettando i limiti.

    Limiti:
    - I gradi per una singola abilità non possono superare INT del personaggio.
    - Il totale dei gradi assegnati non può superare il budget.

    Args:
        abilities: lista corrente delle abilità.
        assignments: {nome_abilità: gradi_da_assegnare}.
        stats: caratteristiche (per il limite INT).

    Returns:
        Lista aggiornata di AbilityGrade.

    Raises:
        ValueError: se si superano i limiti.
    """
    updated = {a.name: a for a in abilities}
    for ability_name, grades in assignments.items():
        if ability_name not in updated:
            raise ValueError(f"Abilità '{ability_name}' non trovata.")
        if grades > stats.int_:
            raise ValueError(
                f"I gradi in '{ability_name}' ({grades}) non possono superare INT ({stats.int_})."
            )
        updated[ability_name] = updated[ability_name].model_copy(update={"grades": grades})
    return list(updated.values())


# ---------------------------------------------------------------------------
# Applicazione background
# ---------------------------------------------------------------------------


def apply_background(stats: CharacterStats, background: Background) -> CharacterStats:
    """Applica i bonus/malus del background alle caratteristiche.

    Args:
        stats: caratteristiche base.
        background: background scelto.

    Returns:
        Nuove CharacterStats con i modificatori applicati.
    """
    data = stats.model_dump(by_alias=True)
    for bonus in background.stat_bonuses:
        key = bonus.stat
        data[key] = max(1, data[key] + bonus.value)
    return CharacterStats(**data)


def apply_background_skills(
    abilities: list[AbilityGrade],
    background: Background,
    stats: CharacterStats,
) -> list[AbilityGrade]:
    """Applica i bonus abilità del background.

    Args:
        abilities: lista corrente delle abilità.
        background: background scelto.
        stats: caratteristiche (per il limite INT).

    Returns:
        Lista aggiornata di AbilityGrade.
    """
    updated = {a.name: a for a in abilities}
    for skill_bonus in background.skill_bonuses:
        name = skill_bonus.ability
        if name in updated:
            new_grades = min(
                updated[name].grades + skill_bonus.value,
                stats.int_,
            )
            updated[name] = updated[name].model_copy(update={"grades": new_grades})
        else:
            # Abilità di background non nella lista standard (es. conoscenze specifiche)
            updated[name] = AbilityGrade(
                name=name,
                characteristics=["INT"],
                grades=max(0, skill_bonus.value),
                notes=f"Da background: {background.name}",
            )
    return list(updated.values())


# ---------------------------------------------------------------------------
# Calcolo PX iniziali
# ---------------------------------------------------------------------------


def compute_starting_px(
    background: Background | None,
    age: int,
    stats: CharacterStats,
    rng: random.Random | None = None,
) -> SimulationResult:
    """Calcola i PX totali disponibili alla creazione simulando il passato.

    Simula tutti i periodi di 5 anni dalla nascita all'età attuale con i tiri
    bonus/malus. Aggiunge i PX usabili extra forniti dal background al totale.

    Args:
        background: il background scelto (o None).
        age: età del personaggio.
        stats: caratteristiche (usate per i bonus PX da stat).
        rng: generatore casuale opzionale.

    Returns:
        SimulationResult con px_total, lifestyle_history, stat_deltas e CD finali.
    """
    stats_snapshot = stats.model_dump(by_alias=True)
    bg_name = background.name if background else None

    sim = simulate_past(
        age=age,
        background_name=bg_name,
        stats=stats_snapshot,
        rng=rng,
    )

    # Aggiungi PX bonus del background al totale simulato
    px_usable_bonus = background.px_usable if background else 0
    # Modifica il totale senza ricreare il dataclass — semplice addizione
    sim.px_total += px_usable_bonus
    # Aggiungi 5000 PX base (creazione personaggio a 20 anni)
    sim.px_total += 5000

    return sim


# ---------------------------------------------------------------------------
# Generatore automatico NPC
# ---------------------------------------------------------------------------


def generate_npc(
    race: Race | None = None,
    background_name: str | None = None,
    age: int | None = None,
    rng: random.Random | None = None,
) -> Character:
    """Genera un NPC in modo completamente automatico.

    Tutte le scelte non specificate vengono fatte casualmente.

    Args:
        race: razza dell'NPC (casuale se None).
        background_name: nome del background (casuale tra quelli applicabili se None).
        age: età dell'NPC (casuale tra 16 e 60 se None).
        rng: generatore casuale opzionale.

    Returns:
        Character completo pronto per l'export.
    """
    _rng = rng or random.Random()

    from app.schemas import IMPLEMENTED_RACES  # evita import circolare

    # 1. Razza
    chosen_race = race or _rng.choice(list(IMPLEMENTED_RACES))

    # 2. Sesso e nome (semplificato per NPC)
    chosen_sex = _rng.choice(list(Sex))
    npc_name = f"NPC_{_rng.randint(1000, 9999)}"

    # 3. Età
    chosen_age = age or _rng.randint(16, 55)

    # 4. Background (scelto prima delle caratteristiche per usare le priorità)
    available_bgs = get_available_backgrounds(chosen_race, px_total=5000)
    chosen_background: Background | None = None
    if available_bgs:
        chosen_background = _rng.choice(available_bgs)

    # 5. Caratteristiche: pool → assegnazione pesata per background
    pool = roll_stat_pool(chosen_race, chosen_age, _rng)
    priorities = chosen_background.stat_priorities if chosen_background else []
    stats = assign_stats_weighted(pool, priorities, _rng)

    # Applica i bonus/malus stat del background dopo l'assegnazione
    if chosen_background:
        stats = apply_background(stats, chosen_background)

    # 6. PF e locazioni
    race_def = get_race_definition(chosen_race)
    body = build_body(race_def, stats)
    res = compute_resistenza(stats)

    # Debug: stat iniziali prima dell'aging
    _sd = stats.model_dump(by_alias=True)
    print(f"\n  [START STATS] {chosen_race.value} | {chosen_age} anni | bg: {chosen_background.name if chosen_background else '-'}")
    print(f"  COS:{_sd['cos']}  FOR:{_sd['for']}  DES:{_sd['des']}  VOL:{_sd['vol']}  INT:{_sd['int']}  IST:{_sd['ist']}  EMP:{_sd['emp']}")

    # 7. PX — simulazione del passato del personaggio
    sim = compute_starting_px(chosen_background, chosen_age, stats, _rng)
    px_total = sim.px_total
    lifestyle_history = sim.lifestyle_history
    current_lifestyle_id = lifestyle_history[-1][1] if lifestyle_history else "comune"

    # Debug log aging simulation
    if sim.period_log:
        print(f"\n  [AGING LOG] {len(sim.period_log)} periodi — lifestyle: {sim.period_log[0].lifestyle_id}")
        print(f"  {'Età':<6} {'B.Roll':>6} {'B.CD':>5} {'B.Ok':>5} {'M.Roll':>6} {'M.CD':>5} {'M.Ok':>5}  {'Variazioni':<28}  {'PX':>6}")
        print(f"  {'-'*85}")
        for p in sim.period_log:
            b_ok = "SI" if p.bonus_success else "NO"
            m_ok = "SI" if p.malus_avoided else "NO"
            chg = "  ".join(
                f"{s.upper()}{'+' if v > 0 else ''}{v}" for s, v in p.stat_changes.items()
            ) if p.stat_changes else "-"
            print(f"  {p.age_start:<6} {p.bonus_roll:>6} {p.bonus_cd:>5} {b_ok:>5} {p.malus_roll:>6} {p.malus_cd:>5} {m_ok:>5}  {chg:<28}  {p.px_total:>6}")
        print(f"  {'-'*85}")
        print(f"  {'TOTALE':>55}  {sim.px_total:>6}")
        print(f"  Stat finali delta: { {s: v for s, v in sim.final_stat_deltas.items()} }")

    # Applica le variazioni stat accumulate durante la simulazione
    if sim.final_stat_deltas:
        stats_data = stats.model_dump(by_alias=True)
        for stat, delta in sim.final_stat_deltas.items():
            stats_data[stat] = max(1, min(20, stats_data.get(stat, 1) + delta))
        stats = CharacterStats(**stats_data)

    # 8. Abilità: distribuisce i gradi in modo casuale
    abilities = build_ability_list(stats)
    budget = initial_ability_budget(stats)
    abilities = _auto_assign_abilities(abilities, budget, stats, _rng)

    # Applica bonus abilità dal background
    if chosen_background:
        abilities = apply_background_skills(abilities, chosen_background, stats)

    # 9. Apprendimenti: spende PX in apprendimenti casuali
    from app.core.px_system import PXSystem
    px_sys = PXSystem(px_total=px_total)
    learnings_owned = list(chosen_background.granted_learnings) if chosen_background else []
    px_sys.px_spent = 0

    from app.data.learnings import get_affordable_learnings
    for _ in range(20):  # max 20 tentativi
        affordable = get_affordable_learnings(
            px_sys.px_total - px_sys.px_spent, learnings_owned
        )
        if not affordable:
            break
        pick = _rng.choice(affordable)
        if px_sys.spend(pick.cost):
            learnings_owned.append(pick.name)

    # 10. Equipaggiamento di base (casuale)
    armor_list, weapon_list, shield_list = _auto_equip(_rng, learnings_owned)

    return Character(
        name=npc_name,
        sex=chosen_sex,
        race=chosen_race,
        age=chosen_age,
        stats=stats,
        body_locations=body,
        resistenza=res,
        background=chosen_background,
        ability_grades=abilities,
        learnings=learnings_owned,
        armor=armor_list,
        weapons=weapon_list,
        shields=shield_list,
        px_total=px_sys.px_total,
        px_spent=px_sys.px_spent,
        px_remaining=px_sys.px_total - px_sys.px_spent,
        lifestyle_id=current_lifestyle_id,
        lifestyle_history=lifestyle_history,
        bonus_cd=sim.final_bonus_cd,
        malus_cd=sim.final_malus_cd,
    )


def _auto_assign_abilities(
    abilities: list[AbilityGrade],
    budget: int,
    stats: CharacterStats,
    rng: random.Random,
) -> list[AbilityGrade]:
    """Distribuisce gradi abilità in modo casuale rispettando i limiti.

    Args:
        abilities: lista abilità con grades=0.
        budget: gradi totali da distribuire.
        stats: caratteristiche (per il limite INT).
        rng: generatore casuale.

    Returns:
        Lista aggiornata.
    """
    updated = {a.name: a for a in abilities}
    remaining = budget
    ability_names = [a.name for a in abilities]

    while remaining > 0 and ability_names:
        pick = rng.choice(ability_names)
        current = updated[pick].grades
        if current >= stats.int_:
            ability_names.remove(pick)
            continue
        updated[pick] = updated[pick].model_copy(update={"grades": current + 1})
        remaining -= 1

    return list(updated.values())


def _auto_equip(
    rng: random.Random,
    learnings: list[str],
) -> tuple[list[ArmorItem], list[WeaponItem], list[ShieldItem]]:
    """Assegna equipaggiamento base casuale a un NPC.

    Sceglie armatura e arma compatibili con gli apprendimenti posseduti.

    Args:
        rng: generatore casuale.
        learnings: apprendimenti già posseduti.

    Returns:
        Tupla (armature, armi, scudi).
    """
    armor_list: list[ArmorItem] = []
    weapon_list: list[WeaponItem] = []
    shield_list: list[ShieldItem] = []

    # Armatura leggera disponibile a tutti; media/pesante richiede Milite/Uomo D'arme
    light_armors = [a for a in ARMORS if a.weight_class.value == "L" and not a.special]
    medium_armors = [a for a in ARMORS if a.weight_class.value == "M" and not a.special]

    if "Uomo D'arme" in learnings or "Milite" in learnings:
        pool = medium_armors or light_armors
    else:
        pool = light_armors

    if pool:
        armor_list.append(rng.choice(pool))

    # Arma: leggera disponibile a tutti
    light_weapons = [w for w in MELEE_WEAPONS if w.weight_class.value == "L"]
    medium_weapons = [w for w in MELEE_WEAPONS if w.weight_class.value == "M"]

    if "Addestramento (M)" in learnings and medium_weapons:
        weapon_list.append(rng.choice(medium_weapons))
    elif light_weapons:
        weapon_list.append(rng.choice(light_weapons))

    # Scudo: solo se ha Scudo I
    if "Scudo I" in learnings:
        from app.data.equipment import SHIELDS
        if SHIELDS:
            shield_list.append(rng.choice(SHIELDS))

    return armor_list, weapon_list, shield_list
