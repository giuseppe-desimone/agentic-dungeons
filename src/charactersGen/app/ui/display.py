"""Funzioni di visualizzazione testo per il sistema GDR v0.8.

Stampa schede personaggio, tabelle, riepilogo step-by-step.
Usa solo la libreria standard (nessuna dipendenza esterna).
"""

from __future__ import annotations

from app.schemas import Character, CharacterStats


_SEP = "=" * 60
_SEP_THIN = "-" * 60


def _header(title: str) -> str:
    pad = (_SEP.__len__() - len(title) - 2) // 2
    return f"{_SEP}\n{'=' * pad} {title} {'=' * pad}\n{_SEP}"


def print_header(title: str) -> None:
    """Stampa un header decorato."""
    print(_header(title))


def print_stats(stats: CharacterStats) -> None:
    """Stampa le 7 caratteristiche in formato tabella."""
    print(_SEP_THIN)
    print("CARATTERISTICHE")
    print(_SEP_THIN)
    rows = [
        ("Costituzione (COS)", stats.cos),
        ("Forza        (FOR)", stats.for_),
        ("Destrezza    (DES)", stats.des),
        ("Volontà      (VOL)", stats.vol),
        ("Intelligenza (INT)", stats.int_),
        ("Istinto      (IST)", stats.ist),
        ("Empatia      (EMP)", stats.emp),
    ]
    for label, value in rows:
        print(f"  {label:30s} {value:>3}")
    print(_SEP_THIN)


def print_body(character: Character) -> None:
    """Stampa le locazioni corporee con PF e schivare."""
    print(_SEP_THIN)
    print(f"CORPO   (Resistenza: {character.resistenza})")
    print(_SEP_THIN)
    print(f"  {'Locazione':<18} {'PF Max':>6}  {'Schivare':>8}")
    print(f"  {'-' * 18} {'-' * 6}  {'-' * 8}")
    for loc in character.body_locations:
        print(f"  {loc.name:<18} {loc.max_pf:>6}  {loc.schivare:>8}")
    print(_SEP_THIN)


def print_abilities(character: Character) -> None:
    """Stampa le abilità con i relativi gradi."""
    print(_SEP_THIN)
    print("ABILITÀ")
    print(_SEP_THIN)
    print(f"  {'Abilità':<25} {'Gradi':>6}  {'Caratteristica'}")
    print(f"  {'-' * 25} {'-' * 6}  {'-' * 15}")
    for ab in character.ability_grades:
        if ab.grades > 0 or True:  # mostra tutte
            competence = "*" * ab.grades + "." * max(0, 3 - ab.grades)
            chars = "/".join(ab.characteristics)
            print(f"  {ab.name:<25} {competence:>6}  {chars}")
    print(_SEP_THIN)


def print_learnings(character: Character) -> None:
    """Stampa gli apprendimenti acquisiti."""
    if not character.learnings:
        print("  Nessun apprendimento.")
        return
    print(_SEP_THIN)
    print("APPRENDIMENTI")
    print(_SEP_THIN)
    for name in character.learnings:
        print(f"  • {name}")
    print(_SEP_THIN)


def print_equipment(character: Character) -> None:
    """Stampa l'equipaggiamento del personaggio."""
    print(_SEP_THIN)
    print("EQUIPAGGIAMENTO")
    print(_SEP_THIN)
    if character.armor:
        print("  Armature:")
        for a in character.armor:
            locs = ", ".join(a.locations)
            rd = ", ".join(f"{k}:{v}" for k, v in a.damage_reduction.items())
            print(f"    [{a.weight_class.value}] {a.name:<30} Loc: {locs:<25} RD: {rd}")
    if character.shields:
        print("  Scudi:")
        for s in character.shields:
            print(f"    [{s.weight_class.value}] {s.name:<30} Schivare: +{s.schivare}")
    if character.weapons:
        print("  Armi:")
        for w in character.weapons:
            types = "/".join(t.value for t in w.damage_types)
            print(f"    [{w.weight_class.value}] {w.name:<30} Danno: {w.damage_die} ({types})")
    print(_SEP_THIN)


def print_character_sheet(character: Character) -> None:
    """Stampa la scheda completa del personaggio."""
    print_header(f"SCHEDA PERSONAGGIO: {character.name.upper()}")
    print(f"  Razza:   {character.race.value}")
    print(f"  Sesso:   {character.sex.value}")
    print(f"  Età:     {character.age} anni")
    if character.background:
        print(f"  Background: {character.background.name}")
    print(f"  Stato Mentale:  {character.mental_status.value}")
    print(f"  Stato Fisico:   {character.physical_status.value}")
    print(f"  PX Totali: {character.px_total}  |  Spesi: {character.px_spent}  |  Rimanenti: {character.px_remaining}")
    print(f"  Unicità: {character.uniqueness_notes}")
    print()
    print_stats(character.stats)
    print()
    print_body(character)
    print()
    print_abilities(character)
    print()
    print_learnings(character)
    print()
    print_equipment(character)
    print(_SEP)


def ask_choice(prompt: str, options: list[str], allow_none: bool = False) -> int:
    """Chiede all'utente di scegliere tra opzioni numerate.

    Args:
        prompt: messaggio da mostrare.
        options: lista di opzioni.
        allow_none: se True, 0 è un'opzione valida (nessuna scelta).

    Returns:
        Indice nella lista `options` (0-based).
    """
    print(f"\n{prompt}")
    for i, opt in enumerate(options, start=1):
        print(f"  {i}. {opt}")
    if allow_none:
        print("  0. Nessuno / Salta")

    while True:
        raw = input("> ").strip()
        try:
            choice = int(raw)
        except ValueError:
            print("  Inserisci un numero valido.")
            continue
        if allow_none and choice == 0:
            return -1
        if 1 <= choice <= len(options):
            return choice - 1
        print(f"  Scegli tra 1 e {len(options)}.")


def ask_int(prompt: str, min_val: int, max_val: int) -> int:
    """Chiede un intero in un intervallo.

    Args:
        prompt: messaggio da mostrare.
        min_val: valore minimo accettato.
        max_val: valore massimo accettato.

    Returns:
        Intero scelto dall'utente.
    """
    while True:
        raw = input(f"{prompt} [{min_val}-{max_val}]: ").strip()
        try:
            val = int(raw)
        except ValueError:
            print("  Inserisci un numero valido.")
            continue
        if min_val <= val <= max_val:
            return val
        print(f"  Valore fuori range ({min_val}-{max_val}).")


def ask_text(prompt: str, default: str = "") -> str:
    """Chiede testo libero all'utente.

    Args:
        prompt: messaggio da mostrare.
        default: valore di default se lasciato vuoto.

    Returns:
        Stringa inserita dall'utente (o default).
    """
    raw = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return raw if raw else default


def press_enter(msg: str = "Premi INVIO per continuare...") -> None:
    """Attende che l'utente prema INVIO."""
    input(msg)
