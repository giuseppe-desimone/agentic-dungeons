"""Entry point CLI per il sistema GDR v0.8.

Uso:
    python run.py          (dalla root del progetto)
    python -m app.main     (dalla root del progetto)

Menu principale:
    1) Crea nuovo Personaggio (wizard interattivo)
    2) Genera NPC automatico
    3) Esci
"""

from __future__ import annotations

import sys

from app.core.character_builder import generate_npc
from app.export.json_export import export_character
from app.schemas import Race
from app.ui.display import ask_choice, ask_int, print_character_sheet, print_header
from app.ui.wizard import run_wizard


def main() -> None:
    """Punto di ingresso principale."""
    print_header("GDR v0.8 — Sistema di Creazione Personaggio")
    print("  Benvenuto nel sistema di creazione personaggio.")
    print("  Razze disponibili: Umano, Nano\n")

    options = [
        "Crea nuovo Personaggio (wizard interattivo)",
        "Genera NPC automatico",
        "Esci",
    ]

    choice = ask_choice("Cosa vuoi fare?", options)

    if choice == 0:
        character = run_wizard()
        print("\nPersonaggio creato con successo!")

    elif choice == 1:
        print("\n[NPC AUTOMATICO]")
        race_options = ["Casuale", "Umano", "Nano"]
        r_choice = ask_choice("Razza NPC", race_options)
        race_map = {1: Race.UMANO, 2: Race.NANO}
        npc_race = race_map.get(r_choice)

        age_choice = ask_choice(
            "Età NPC",
            ["Casuale (16-55)", "Specifica manualmente"],
        )
        npc_age = None
        if age_choice == 1:
            npc_age = ask_int("Età", min_val=1, max_val=120)

        print("\n  Generazione NPC in corso...")
        character = generate_npc(race=npc_race, age=npc_age)
        print_character_sheet(character)

        save = input("\nSalvare l'NPC in JSON? [S/n]: ").strip().lower()
        if save != "n":
            path = export_character(character)
            print(f"  ✓ NPC salvato in: {path}")

    elif choice == 2:
        print("\nArrivederci!")
        sys.exit(0)


if __name__ == "__main__":
    main()
