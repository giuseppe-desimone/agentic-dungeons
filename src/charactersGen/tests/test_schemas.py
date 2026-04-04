"""Test per i modelli Pydantic."""

import pytest
from pydantic import ValidationError
from app.schemas import (
    BodyLocation,
    Character,
    CharacterStats,
    Race,
    Sex,
)


def make_stats(**kwargs: int) -> CharacterStats:
    alias_map = {"for_": "for", "int_": "int"}
    mapped = {alias_map.get(k, k): v for k, v in kwargs.items()}
    defaults = {"cos": 8, "for": 7, "des": 6, "vol": 5, "int": 7, "ist": 5, "emp": 4}
    defaults.update(mapped)
    return CharacterStats(**defaults)


class TestCharacterStats:
    def test_valid_stats(self) -> None:
        stats = make_stats()
        assert stats.cos == 8
        assert stats.for_ == 7

    def test_alias_for(self) -> None:
        stats = CharacterStats(**{"cos": 5, "for": 6, "des": 5, "vol": 5, "int": 5, "ist": 5, "emp": 5})
        assert stats.for_ == 6

    def test_stat_minimum_one(self) -> None:
        with pytest.raises(ValidationError):
            make_stats(cos=0)

    def test_negative_stat_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_stats(**{"for": -1})  # usa alias diretto per forzare la validazione


class TestBodyLocation:
    def test_valid_location(self) -> None:
        loc = BodyLocation(name="Testa", max_pf=18, current_pf=18, schivare=26)
        assert loc.max_pf == 18

    def test_current_pf_capped_at_max(self) -> None:
        loc = BodyLocation(name="Testa", max_pf=10, current_pf=999, schivare=20)
        assert loc.current_pf == 10

    def test_negative_current_pf_allowed(self) -> None:
        loc = BodyLocation(name="Testa", max_pf=10, current_pf=-5, schivare=20)
        assert loc.current_pf == -5


class TestCharacter:
    def make_character(self, **kwargs: object) -> Character:
        defaults: dict[str, object] = {
            "name": "Testino",
            "sex": Sex.MASCHIO,
            "race": Race.UMANO,
            "age": 25,
            "stats": make_stats(),
            "resistenza": 7,
        }
        defaults.update(kwargs)
        return Character(**defaults)  # type: ignore[arg-type]

    def test_basic_creation(self) -> None:
        char = self.make_character()
        assert char.name == "Testino"
        assert char.race == Race.UMANO

    def test_px_remaining_computed(self) -> None:
        char = self.make_character(px_total=5000, px_spent=1500)
        assert char.px_remaining == 3500

    def test_default_mental_status(self) -> None:
        from app.schemas import MentalStatus
        char = self.make_character()
        assert char.mental_status == MentalStatus.SANO

    def test_uniqueness_placeholder(self) -> None:
        char = self.make_character()
        assert char.uniqueness_notes == "DA DEFINIRE"
        assert char.uniqueness_traits == []
