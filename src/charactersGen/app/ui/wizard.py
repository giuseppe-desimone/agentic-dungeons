"""Wizard interattivo per la creazione del personaggio GDR v0.8.

Guida il giocatore step-by-step:
  1. Nome e sesso
  2. Razza
  3. Età
  4. Caratteristiche (tiro automatico + visualizzazione)
  5. PF e locazioni (calcolati)
  6. Background
  7. Distribuzione gradi abilità
  8. Spesa PX → apprendimenti
  9. Equipaggiamento iniziale
  10. Unicità [PLACEHOLDER]
  11. Riepilogo + export JSON
"""

from __future__ import annotations

from app.core.character_builder import (
    ALL_STATS,
    STAT_LABELS,
    apply_background,
    apply_background_skills,
    assign_ability_grades,
    assign_stats_manual,
    build_ability_list,
    build_body,
    compute_resistenza,
    compute_starting_px,
    initial_ability_budget,
    roll_stat_pool,
)
from app.core.px_system import PXSystem
from app.data.abilities import ABILITIES
from app.data.backgrounds import get_available_backgrounds
from app.data.equipment import ARMORS, MELEE_WEAPONS, RANGED_WEAPONS, SHIELDS
from app.data.learnings import LEARNINGS, get_affordable_learnings
from app.core.aging import SimulationResult
from app.data.lifestyles import BACKGROUND_DEFAULT_LIFESTYLE, LIFESTYLES, get_lifestyle
from app.data.races import get_race_definition
from app.export.json_export import export_character
from app.schemas import (
    IMPLEMENTED_RACES,
    AbilityGrade,
    ArmorItem,
    Background,
    Character,
    CharacterStats,
    Race,
    Sex,
    ShieldItem,
    WeaponItem,
)
from app.ui.display import (
    ask_choice,
    ask_int,
    ask_text,
    press_enter,
    print_abilities,
    print_body,
    print_character_sheet,
    print_header,
    print_stats,
)


def run_wizard() -> Character:
    """Esegue il wizard interattivo di creazione personaggio.

    Returns:
        Character completato.
    """
    print_header("CREAZIONE PERSONAGGIO — GDR v0.8")

    # ------------------------------------------------------------------
    # Step 1: Nome e sesso
    # ------------------------------------------------------------------
    print("\n[STEP 1] Nome e Sesso")
    name = ask_text("Nome del personaggio", default="Senza Nome")
    sex_choice = ask_choice("Sesso", [s.value for s in Sex])
    sex = list(Sex)[sex_choice]

    # ------------------------------------------------------------------
    # Step 2: Razza
    # ------------------------------------------------------------------
    print("\n[STEP 2] Razza")
    race_options = [r.value for r in IMPLEMENTED_RACES]
    race_choice = ask_choice("Scegli la razza", race_options)
    race = list(IMPLEMENTED_RACES)[race_choice]
    race_def = get_race_definition(race)
    print(f"  → {race.value}: {race_def.description}")

    # ------------------------------------------------------------------
    # Step 3: Età
    # ------------------------------------------------------------------
    print("\n[STEP 3] Età")
    print("  Il personaggio standard ha 20+ anni.")
    print("  Sotto i 20 anni: tira 2d4 per le caratteristiche invece di 3d4.")
    print("  Ogni 5 anni oltre i 20: -1 COS, -1 FOR, -1 DES, -1 IST; +1 EMP, +1 VOL")
    print("  [PLACEHOLDER: progressione PX con l'età da definire]")
    age = ask_int("Età del personaggio", min_val=1, max_val=120)

    if age < 20:
        print(f"  ⚠  Età {age}: le caratteristiche verranno tirate con 2d4.")

    # ------------------------------------------------------------------
    # Step 4: Background (prima del tiro, per avere i suggerimenti)
    # ------------------------------------------------------------------
    print("\n[STEP 4] Background")
    available_bgs = get_available_backgrounds(race, px_total=5000)

    chosen_background: Background | None = None
    if available_bgs:
        bg_options = [f"{b.name} (soglia: {b.px_threshold} PX)" for b in available_bgs]
        bg_options.append("Nessun background")
        bg_idx = ask_choice("Scegli il background", bg_options)
        if bg_idx < len(available_bgs):
            chosen_background = available_bgs[bg_idx]
            _print_background_details(chosen_background)
    else:
        print("  Nessun background disponibile con i PX attuali.")

    # ------------------------------------------------------------------
    # Step 5: Stile di vita corrente
    # ------------------------------------------------------------------
    print("\n[STEP 5] Stile di Vita")
    print("  Lo stile di vita descrive come hai trascorso gli ultimi 5 anni.")
    print("  Influenza i PX guadagnati e la protezione dall'invecchiamento.")

    # Suggerisci uno stile di vita basato sul background
    suggested_id: str | None = None
    if chosen_background:
        suggested_id = BACKGROUND_DEFAULT_LIFESTYLE.get(chosen_background.name)
        if suggested_id:
            suggested = get_lifestyle(suggested_id)
            if suggested:
                print(f"\n  Suggerimento per '{chosen_background.name}': {suggested.name}")

    ls_options = [f"{ls.name} — {ls.description[:60]}..." for ls in LIFESTYLES]
    ls_idx = ask_choice("Scegli il tuo stile di vita corrente", ls_options)
    chosen_lifestyle = LIFESTYLES[ls_idx]
    print(f"\n  → Stile di vita: {chosen_lifestyle.name}")
    press_enter()

    # ------------------------------------------------------------------
    # Step 6: Tiro pool caratteristiche + assegnazione interattiva
    # ------------------------------------------------------------------
    print("\n[STEP 6] Caratteristiche — Tiro e Assegnazione")
    print("  Tiro pool in corso...")
    pool = roll_stat_pool(race, age)
    sorted_pool = sorted(pool, reverse=True)
    print(f"\n  Valori tirati: {sorted_pool}")

    if chosen_background and chosen_background.stat_priorities:
        prio = chosen_background.stat_priorities[:3]
        print(f"\n  Suggerimento '{chosen_background.name}':")
        print(f"  Priorità consigliate: {' > '.join(prio)}")
        print("  (puoi ignorare il suggerimento e assegnare come vuoi)")

    stats = _run_stat_assignment(pool, age)
    print("\n  Caratteristiche assegnate:")
    print_stats(stats)

    # Applica bonus/malus stat del background
    if chosen_background:
        stats = apply_background(stats, chosen_background)
        if chosen_background.stat_bonuses:
            print("\n  Caratteristiche dopo bonus background:")
            print_stats(stats)

    press_enter()

    # ------------------------------------------------------------------
    # Step 7: PF, Locazioni, Resistenza
    # ------------------------------------------------------------------
    print("\n[STEP 7] Punti Ferita e Locazioni")
    body = build_body(race_def, stats)
    res = compute_resistenza(stats)
    temp_char = _build_temp_character(name, sex, race, age, stats, body, res)
    print_body(temp_char)
    press_enter()

    # ------------------------------------------------------------------
    # Step 8: Abilità
    # ------------------------------------------------------------------
    print("\n[STEP 8] Distribuzione Gradi Abilita'")
    abilities = build_ability_list(stats)

    if chosen_background:
        abilities = apply_background_skills(abilities, chosen_background, stats)

    budget = initial_ability_budget(stats)
    print(f"  Budget gradi: {budget} (max(INT={stats.int_}, VOL={stats.vol}) // 2)")
    print(f"  Limite gradi per abilità: {stats.int_} (= INT)")
    abilities = _run_ability_assignment(abilities, budget, stats)

    # ------------------------------------------------------------------
    # Step 9: PX e Apprendimenti
    # ------------------------------------------------------------------
    print("\n[STEP 9] Spesa PX — Apprendimenti")
    print("  Simulazione periodi passati in corso...")
    sim = compute_starting_px(chosen_background, age, stats)

    # Applica variazioni stat dalla simulazione del passato
    if sim.final_stat_deltas:
        stats_data = stats.model_dump(by_alias=True)
        for stat, delta in sim.final_stat_deltas.items():
            stats_data[stat] = max(1, min(20, stats_data.get(stat, 1) + delta))
        stats = CharacterStats(**stats_data)
        print("  Caratteristiche dopo la simulazione del passato:")
        print_stats(stats)

    lifestyle_history = sim.lifestyle_history + [(age, chosen_lifestyle.id)]

    # Log sintetico periodi (solo se > 20 anni)
    if sim.period_log:
        print(f"\n  Periodi simulati: {len(sim.period_log)}")
        for p in sim.period_log:
            b = f"B+ d4={p.bonus_d4}" if p.bonus_success else "B-"
            m = f"M- d4={p.malus_d4}" if not p.malus_avoided else "M+"
            chg = "  ".join(
                f"{s.upper()}{'+' if v > 0 else ''}{v}" for s, v in p.stat_changes.items()
            ) if p.stat_changes else "nessuna variazione"
            print(f"    {p.age_start}a [{b}][{m}] {chg:<25} +{p.px_total} PX")

    print(f"\n  PX totali: {sim.px_total}")
    px_sys = PXSystem(px_total=sim.px_total)

    owned_learnings: list[str] = list(
        chosen_background.granted_learnings if chosen_background else []
    )
    if owned_learnings:
        print(f"  Apprendimenti da background: {', '.join(owned_learnings)}")

    print(f"  PX disponibili: {px_sys.px_remaining}")
    abilities = _run_px_spending(px_sys, owned_learnings, abilities, stats)

    # ------------------------------------------------------------------
    # Step 10: Equipaggiamento
    # ------------------------------------------------------------------
    print("\n[STEP 10] Equipaggiamento Iniziale")
    armor_list, weapon_list, shield_list = _run_equipment_selection(owned_learnings)

    # ------------------------------------------------------------------
    # Step 11: Unicità [PLACEHOLDER]
    # ------------------------------------------------------------------
    print("\n[STEP 11] Unicità del Personaggio")
    print("  [PLACEHOLDER] Questa sezione sarà definita nelle prossime versioni.")
    print("  I tratti unici (positivi e negativi) saranno aggiunti qui.")
    press_enter("  Premi INVIO per continuare...")

    # ------------------------------------------------------------------
    # Step 12: Riepilogo e Export
    # ------------------------------------------------------------------
    character = Character(
        name=name,
        sex=sex,
        race=race,
        age=age,
        stats=stats,
        body_locations=body,
        resistenza=res,
        background=chosen_background,
        ability_grades=abilities,
        learnings=owned_learnings,
        armor=armor_list,
        weapons=weapon_list,
        shields=shield_list,
        px_total=px_sys.px_total,
        px_spent=px_sys.px_spent,
        px_remaining=px_sys.px_remaining,
        lifestyle_id=chosen_lifestyle.id,
        lifestyle_history=lifestyle_history,
        bonus_cd=sim.final_bonus_cd,
        malus_cd=sim.final_malus_cd,
    )

    print("\n[STEP 12] Riepilogo Finale")
    print_character_sheet(character)
    print(px_sys.summary())

    save = input("\nSalvare il personaggio in JSON? [S/n]: ").strip().lower()
    if save != "n":
        path = export_character(character)
        print(f"\n  ✓ Personaggio salvato in: {path}")

    return character


# ---------------------------------------------------------------------------
# Funzioni helper del wizard
# ---------------------------------------------------------------------------


def _build_temp_character(
    name: str,
    sex: Sex,
    race: Race,
    age: int,
    stats: CharacterStats,
    body: list,
    res: int,
) -> Character:
    """Costruisce un Character temporaneo per la visualizzazione intermedia."""
    return Character(
        name=name,
        sex=sex,
        race=race,
        age=age,
        stats=stats,
        body_locations=body,
        resistenza=res,
    )


def _print_background_details(bg: Background) -> None:
    """Stampa i dettagli del background scelto."""
    print(f"\n  Background: {bg.name}")
    print(f"  {bg.description}")
    if bg.stat_bonuses:
        print("  Modificatori caratteristiche:")
        for sb in bg.stat_bonuses:
            sign = "+" if sb.value >= 0 else ""
            print(f"    {sb.stat.upper()}: {sign}{sb.value}")
    if bg.skill_bonuses:
        print("  Modificatori abilità:")
        for skb in bg.skill_bonuses:
            sign = "+" if skb.value >= 0 else ""
            print(f"    {skb.ability}: {sign}{skb.value}")
    if bg.granted_abilities:
        print(f"  Abilità concesse: {', '.join(bg.granted_abilities)}")
    if bg.granted_learnings:
        print(f"  Apprendimenti concessi: {', '.join(bg.granted_learnings)}")
    if bg.special_notes:
        print(f"  Note: {bg.special_notes}")
    if bg.px_usable > 0:
        print(f"  PX usabili aggiuntivi: {bg.px_usable}")


def _run_ability_assignment(
    abilities: list[AbilityGrade],
    budget: int,
    stats: CharacterStats,
) -> list[AbilityGrade]:
    """Gestisce il loop interattivo di assegnazione gradi abilità.

    Args:
        abilities: lista abilità con gradi attuali.
        budget: gradi totali da distribuire.
        stats: caratteristiche (per il limite INT).

    Returns:
        Lista abilità aggiornata.
    """
    remaining = budget
    print(f"\n  Gradi da distribuire: {remaining}")
    print(f"  Massimo per abilità: {stats.int_}")
    print_abilities(_build_temp_char_abilities(abilities))

    while remaining > 0:
        print(f"\n  Gradi rimanenti: {remaining}")
        ability_names = [
            f"{a.name} (attuale: {a.grades}, max: {stats.int_})"
            for a in abilities
        ]
        ability_names.append("Fine distribuzione")

        choice = ask_choice("Assegna un grado a:", ability_names)
        if choice == len(abilities):
            break

        selected = abilities[choice]
        if selected.grades >= stats.int_:
            print(f"  '{selected.name}' ha già raggiunto il massimo ({stats.int_}).")
            continue

        abilities[choice] = selected.model_copy(update={"grades": selected.grades + 1})
        remaining -= 1
        print(f"  ✓ '{selected.name}' ora a grado {abilities[choice].grades}")

    return abilities


def _run_px_spending(
    px_sys: PXSystem,
    owned_learnings: list[str],
    abilities: list[AbilityGrade],
    stats: CharacterStats,
) -> list[AbilityGrade]:
    """Gestisce il loop interattivo di spesa PX.

    Args:
        px_sys: sistema PX.
        owned_learnings: lista apprendimenti già posseduti (modificata in-place).
        abilities: lista abilità (modificata in-place).
        stats: caratteristiche.

    Returns:
        Lista abilità aggiornata.
    """
    while True:
        print(f"\n  PX rimanenti: {px_sys.px_remaining}")
        options = [
            "Acquista un Apprendimento",
            "Aumenta un grado Abilità",
            "Fine spesa PX",
        ]
        choice = ask_choice("Cosa vuoi fare?", options)

        if choice == 2:  # Fine
            break

        elif choice == 0:  # Apprendimenti
            affordable = get_affordable_learnings(px_sys.px_remaining, owned_learnings)
            if not affordable:
                print("  Nessun apprendimento acquistabile con i PX rimanenti.")
                continue
            learn_options = [
                f"{l.name} ({l.cost} PX) [{l.category}]" for l in affordable
            ]
            learn_options.append("Annulla")
            l_choice = ask_choice("Scegli apprendimento", learn_options)
            if l_choice < len(affordable):
                success, msg = px_sys.buy_learning(affordable[l_choice].name, owned_learnings)
                print(f"  {'✓' if success else '✗'} {msg}")

        elif choice == 1:  # Abilità
            upgradeable = [
                a for a in abilities if a.grades < stats.int_
                and px_sys.can_afford((a.grades + 1) * 500)
            ]
            if not upgradeable:
                print("  Nessuna abilità migliorabile con i PX rimanenti.")
                continue
            ab_options = [
                f"{a.name} (grado {a.grades} → {a.grades + 1}, costo: {(a.grades + 1) * 500} PX)"
                for a in upgradeable
            ]
            ab_options.append("Annulla")
            ab_choice = ask_choice("Scegli abilità", ab_options)
            if ab_choice < len(upgradeable):
                success, msg = px_sys.buy_ability_grade(
                    upgradeable[ab_choice].name, abilities, stats.int_
                )
                print(f"  {'✓' if success else '✗'} {msg}")

    return abilities


def _run_equipment_selection(
    owned_learnings: list[str],
) -> tuple[list[ArmorItem], list[WeaponItem], list[ShieldItem]]:
    """Gestisce la selezione interattiva dell'equipaggiamento.

    Args:
        owned_learnings: apprendimenti posseduti (per filtrare le opzioni).

    Returns:
        Tupla (armature, armi, scudi).
    """
    armor_list: list[ArmorItem] = []
    weapon_list: list[WeaponItem] = []
    shield_list: list[ShieldItem] = []

    # Armature
    can_heavy = "Uomo D'arme" in owned_learnings
    can_medium = can_heavy or "Milite" in owned_learnings

    available_armor = [
        a for a in ARMORS
        if not a.special and (
            a.weight_class.value == "L"
            or (a.weight_class.value == "M" and can_medium)
            or (a.weight_class.value == "P" and can_heavy)
        )
    ]
    if available_armor:
        armor_opts = [
            f"{a.name} [{a.weight_class.value}] — RD: {a.damage_reduction}" for a in available_armor
        ]
        armor_opts.append("Nessuna armatura")
        print("\n  Scegli armatura per il Corpo:")
        a_choice = ask_choice("Armatura", armor_opts)
        if a_choice < len(available_armor):
            armor_list.append(available_armor[a_choice])

    # Scudi
    if "Scudo I" in owned_learnings:
        shield_opts = [f"{s.name} [+{s.schivare} Schivare]" for s in SHIELDS]
        shield_opts.append("Nessuno scudo")
        print("\n  Scegli uno scudo:")
        s_choice = ask_choice("Scudo", shield_opts)
        if s_choice < len(SHIELDS):
            shield_list.append(SHIELDS[s_choice])

    # Armi
    can_medium_w = "Addestramento (M)" in owned_learnings
    can_heavy_w = "Addestramento (P)" in owned_learnings
    available_weapons = [
        w for w in (MELEE_WEAPONS + RANGED_WEAPONS)
        if (
            w.weight_class.value == "L"
            or (w.weight_class.value == "M" and can_medium_w)
            or (w.weight_class.value == "P" and can_heavy_w)
        )
    ]
    if available_weapons:
        weapon_opts = [
            f"{w.name} [{w.weight_class.value}] — {w.damage_die}" for w in available_weapons
        ]
        weapon_opts.append("Nessuna arma")
        print("\n  Scegli un'arma:")
        w_choice = ask_choice("Arma", weapon_opts)
        if w_choice < len(available_weapons):
            weapon_list.append(available_weapons[w_choice])

    return armor_list, weapon_list, shield_list


def _run_stat_assignment(pool: list[int], age: int) -> CharacterStats:
    """Loop interattivo per assegnare i valori del pool alle 7 caratteristiche.

    Mostra i valori rimanenti e chiede al giocatore dove assegnare ciascuno.

    Args:
        pool: i 7 valori tirati (non ordinati).
        age: eta' (per applicare i modificatori di invecchiamento).

    Returns:
        CharacterStats con i valori scelti dal giocatore.
    """
    stat_names = {
        "cos": "Costituzione (COS)",
        "for": "Forza       (FOR)",
        "des": "Destrezza   (DES)",
        "vol": "Volonta'    (VOL)",
        "int": "Intelligenza(INT)",
        "ist": "Istinto     (IST)",
        "emp": "Empatia     (EMP)",
    }

    remaining_values = sorted(pool, reverse=True)
    remaining_stats = list(ALL_STATS)  # ["cos","for","des","vol","int","ist","emp"]
    assignment: dict[str, int] = {}

    print("\n  Assegna ogni valore a una caratteristica.")
    print("  I valori vengono proposti dal piu' alto al piu' basso.\n")

    for value in remaining_values:
        opts = [stat_names[s] for s in remaining_stats]
        print(f"  Valori rimanenti: {remaining_values[remaining_values.index(value):]}")
        idx = ask_choice(f"Dove assegni il valore  {value}?", opts)
        chosen_stat = remaining_stats[idx]
        assignment[chosen_stat] = value
        remaining_stats.remove(chosen_stat)

    return assign_stats_manual(pool, assignment)


def _build_temp_char_abilities(abilities: list[AbilityGrade]) -> Character:
    """Costruisce un Character temporaneo minimo per visualizzare le abilità."""
    from app.schemas import CharacterStats, Sex, Race

    dummy_stats = CharacterStats(**{"cos": 5, "for": 5, "des": 5, "vol": 5, "int": 5, "ist": 5, "emp": 5})
    return Character(
        name="temp",
        sex=Sex.ALTRO,
        race=Race.UMANO,
        age=20,
        stats=dummy_stats,
        resistenza=5,
        ability_grades=abilities,
    )
