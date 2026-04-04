"""Serializzazione del personaggio in formato JSON.

Il file viene salvato come: personaggio_<nome>.json
nella directory corrente o in un percorso specificato.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import Character


def export_character(character: Character, output_dir: str | Path = ".") -> Path:
    """Esporta il personaggio in un file JSON.

    Args:
        character: il personaggio da esportare.
        output_dir: directory di output (default: directory corrente).

    Returns:
        Path del file creato.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in character.name)
    file_path = output_path / f"personaggio_{safe_name}.json"

    data = character.model_dump(mode="json", by_alias=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return file_path


def character_to_json_string(character: Character) -> str:
    """Serializza il personaggio come stringa JSON formattata.

    Args:
        character: il personaggio da serializzare.

    Returns:
        Stringa JSON indentata.
    """
    data = character.model_dump(mode="json", by_alias=True)
    return json.dumps(data, ensure_ascii=False, indent=2)
