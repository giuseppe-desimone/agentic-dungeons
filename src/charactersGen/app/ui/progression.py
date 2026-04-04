"""Loop di progressione a 5 anni — GDR v0.8.

Ogni ciclo:
  1. Scelta stile di vita per il prossimo periodo
  2. Tiro bonus (1d20 vs CD_bonus): successo → +1 a bonus_stats + PX bonus
  3. Tiro malus (1d20 vs CD_malus): successo → eviti i malus; fallimento → -1 a malus_stats
  4. [Opzionale] Spesa PX in apprendimenti
"""

from __future__ import annotations

from app.core.aging import advance_five_years
from app.data.learnings import get_affordable_learnings
from app.data.lifestyles import LIFESTYLES, get_lifestyle
from app.core.px_system import PXSystem
from app.schemas import Character, CharacterStats
from app.ui.display import ask_choice, press_enter, print_header, print_stats

_STAT_LABELS: dict[str, str] = {
    "cos": "COS", "for": "FOR", "des": "DES",
    "vol": "VOL", "int": "INT", "ist": "IST", "emp": "EMP",
}


def run_progression(character: Character) -> Character:
    """Esegue un ciclo di progressione di 5 anni per il personaggio.

    Args:
        character: personaggio da far progredire.

    Returns:
        Nuovo Character aggiornato.
    """
    print_header(f"PROGRESSIONE — {character.name} (eta': {character.age})")
    print(f"  CD Bonus attuale: {character.bonus_cd}  |  CD Malus attuale: {character.malus_cd}")

    # ------------------------------------------------------------------
    # Step 1: Scelta stile di vita
    # ------------------------------------------------------------------
    print("\n[1] Scelta Stile di Vita")
    current_ls = get_lifestyle(character.lifestyle_id or "comune")
    if current_ls:
        print(f"  Stile corrente: {current_ls.name}")

    ls_options = [
        f"{ls.name}  [bonus: {', '.join(s.upper() for s in ls.bonus_stats)} | "
        f"malus: {', '.join(s.upper() for s in ls.malus_stats)}]"
        for ls in LIFESTYLES
    ]
    ls_idx = ask_choice("Scegli lo stile di vita per i prossimi 5 anni", ls_options)
    chosen_lifestyle = LIFESTYLES[ls_idx]
    press_enter()

    # ------------------------------------------------------------------
    # Step 2: Tiri
    # ------------------------------------------------------------------
    stats_snapshot = character.stats.model_dump(by_alias=True)

    result = advance_five_years(
        age=character.age,
        lifestyle_id=chosen_lifestyle.id,
        stats=stats_snapshot,
        bonus_cd=character.bonus_cd,
        malus_cd=character.malus_cd,
    )

    print(f"\n[2] Risultati — {chosen_lifestyle.name}  [{character.age} → {character.age + 5} anni]")
    print(f"\n  Tiro BONUS: {result.bonus_roll} vs CD {result.bonus_cd}", end="  ->  ")
    if result.bonus_success:
        bonus_changes = {s: v for s, v in result.stat_changes.items() if v > 0}
        bonus_str = "  ".join(f"{s.upper()}+{v}" for s, v in bonus_changes.items()) or "nessuna stat"
        print(f"SUCCESSO! (d4={result.bonus_d4})  {bonus_str}  |  +{result.px_bonus} PX bonus")
    else:
        print("fallito — nessun bonus")

    print(f"  Tiro MALUS:  {result.malus_roll} vs CD {result.malus_cd}", end="  ->  ")
    if result.malus_avoided:
        print("evitato!")
    else:
        malus_changes = {s: -v for s, v in result.stat_changes.items() if v < 0}
        malus_str = "  ".join(f"{s.upper()}-{v}" for s, v in malus_changes.items()) or "nessuna stat"
        print(f"MALUS! (d4={result.malus_d4})  {malus_str}")

    print(f"\n  PX guadagnati: {result.px_base} (base) + {result.px_bonus} (bonus) = {result.px_total}")
    print(f"  Prossima CD Bonus: {result.new_bonus_cd}  |  Prossima CD Malus: {result.new_malus_cd}")

    # ------------------------------------------------------------------
    # Step 3: Applica variazioni stat
    # ------------------------------------------------------------------
    new_stats_data = stats_snapshot.copy()
    if result.stat_changes:
        print("\n  Variazioni caratteristiche:")
        for stat, delta in result.stat_changes.items():
            old_val = new_stats_data.get(stat, 1)
            new_val = max(1, old_val + delta)
            new_stats_data[stat] = new_val
            sign = "+" if delta > 0 else ""
            print(f"    {_STAT_LABELS.get(stat, stat)}: {old_val} → {new_val} ({sign}{delta})")
    else:
        print("\n  Nessuna variazione alle caratteristiche.")

    new_stats = CharacterStats(**new_stats_data)
    print_stats(new_stats)

    new_accumulated = character.px_accumulated + result.px_total
    print(f"\n  PX accumulati totali: {new_accumulated}")
    press_enter()

    # ------------------------------------------------------------------
    # Step 4: [Opzionale] Spesa PX
    # ------------------------------------------------------------------
    new_learnings = list(character.learnings)
    px_spent_now = 0

    spend = input("  Vuoi spendere PX in apprendimenti? [S/n]: ").strip().lower()
    if spend != "n":
        px_sys = PXSystem(px_total=new_accumulated)

        while True:
            print(f"\n  PX disponibili: {px_sys.px_remaining}")
            affordable = get_affordable_learnings(px_sys.px_remaining, new_learnings)
            if not affordable:
                print("  Nessun apprendimento acquistabile.")
                break

            # Suggerimenti dal lifestyle
            suggestions = [l for l in affordable if l.category in chosen_lifestyle.px_category_weights
                           and chosen_lifestyle.px_category_weights.get(l.category, 0) >= 20]
            if suggestions:
                print(f"  Tipici per {chosen_lifestyle.name}: "
                      f"{', '.join(s.name for s in suggestions[:4])}")

            options = [f"{l.name} ({l.cost} PX) [{l.category}]" for l in affordable]
            options.append("Fine spesa")
            choice = ask_choice("Acquista", options)
            if choice == len(affordable):
                break

            success, msg = px_sys.buy_learning(affordable[choice].name, new_learnings)
            print(f"  {'OK' if success else 'ERRORE'}: {msg}")

        px_spent_now = px_sys.px_spent
        new_accumulated = px_sys.px_remaining

    # ------------------------------------------------------------------
    # Costruzione nuovo Character
    # ------------------------------------------------------------------
    new_history = list(character.lifestyle_history) + [(character.age, chosen_lifestyle.id)]

    return character.model_copy(update={
        "age": character.age + 5,
        "stats": new_stats,
        "lifestyle_id": chosen_lifestyle.id,
        "lifestyle_history": new_history,
        "bonus_cd": result.new_bonus_cd,
        "malus_cd": result.new_malus_cd,
        "px_accumulated": new_accumulated,
        "px_spent": character.px_spent + px_spent_now,
    })
