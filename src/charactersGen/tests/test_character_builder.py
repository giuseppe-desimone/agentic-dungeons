"""Test per la logica di creazione personaggio."""

import random
import pytest
from app.core.character_builder import (
    build_body,
    compute_resistenza,
    initial_ability_budget,
    roll_stats,
)
from app.data.races import get_race_definition
from app.schemas import CharacterStats, Race


def make_rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def make_stats(**kwargs: int) -> CharacterStats:
    # Mappa i nomi Python (for_, int_) agli alias Pydantic (for, int)
    alias_map = {"for_": "for", "int_": "int"}
    mapped = {alias_map.get(k, k): v for k, v in kwargs.items()}
    defaults = {"cos": 8, "for": 7, "des": 6, "vol": 5, "int": 7, "ist": 5, "emp": 4}
    defaults.update(mapped)
    return CharacterStats(**defaults)


class TestRollStats:
    def test_umano_adult_range(self) -> None:
        rng = make_rng()
        stats = roll_stats(Race.UMANO, age=25, rng=rng)
        # 3d4 → min 3, max 12; ma i mod età per 25 anni: una volta -1 a COS/FOR/DES/IST e +1 EMP/VOL
        # min dopo mod = 2, max = 12
        for val in [stats.cos, stats.for_, stats.des, stats.vol, stats.int_, stats.ist, stats.emp]:
            assert val >= 1

    def test_young_character_lower_stats(self) -> None:
        """Personaggio sotto i 20 anni usa 2d4 (max 8) invece di 3d4 (max 12)."""
        rng = make_rng()
        # Con 2d4 il massimo è 8, con 3d4 è 12
        stats_young = roll_stats(Race.UMANO, age=15, rng=rng)
        rng2 = make_rng()
        stats_adult = roll_stats(Race.UMANO, age=25, rng=rng2)
        # Non possiamo garantire che young < adult per singolo tiro,
        # ma verifichiamo che i valori siano nel range corretto
        for val in [stats_young.cos, stats_young.for_]:
            assert 1 <= val <= 8  # 2d4 max = 8

    def test_age_modifiers_applied(self) -> None:
        """A 30 anni (2 periodi di 5 anni) si applicano -2 a COS, FOR, DES, IST."""
        rng = make_rng(99)
        stats_base = roll_stats(Race.UMANO, age=20, rng=rng)
        rng2 = make_rng(99)
        stats_old = roll_stats(Race.UMANO, age=30, rng=rng2)
        # 30 anni → (30-20)//5 = 2 periodi → -2 a COS e FOR (min 1)
        assert stats_old.cos == max(1, stats_base.cos - 2)
        assert stats_old.for_ == max(1, stats_base.for_ - 2)


class TestBuildBody:
    def test_umano_pf_formula(self) -> None:
        stats = make_stats(cos=8, des=6)
        race_def = get_race_definition(Race.UMANO)
        body = build_body(race_def, stats)

        loc_map = {loc.name: loc for loc in body}
        assert loc_map["Testa"].max_pf == 10 + 8      # 18
        assert loc_map["Torace"].max_pf == 40 + 8     # 48
        assert loc_map["Braccio Sx"].max_pf == 15 + 8 # 23
        assert loc_map["Gamba Sx"].max_pf == 20 + 8   # 28

    def test_umano_schivare_formula(self) -> None:
        stats = make_stats(cos=8, des=6)
        race_def = get_race_definition(Race.UMANO)
        body = build_body(race_def, stats)

        loc_map = {loc.name: loc for loc in body}
        assert loc_map["Testa"].schivare == 20 + 6    # 26
        assert loc_map["Torace"].schivare == 10 + 6   # 16

    def test_nano_pf_formula(self) -> None:
        stats = make_stats(cos=9, des=5)
        race_def = get_race_definition(Race.NANO)
        body = build_body(race_def, stats)

        loc_map = {loc.name: loc for loc in body}
        assert loc_map["Testa"].max_pf == 15 + 9      # 24
        assert loc_map["Braccio Sx"].max_pf == 18 + 9 # 27

    def test_current_pf_equals_max_on_creation(self) -> None:
        stats = make_stats()
        race_def = get_race_definition(Race.UMANO)
        body = build_body(race_def, stats)
        for loc in body:
            assert loc.current_pf == loc.max_pf

    def test_six_locations(self) -> None:
        stats = make_stats()
        race_def = get_race_definition(Race.UMANO)
        body = build_body(race_def, stats)
        assert len(body) == 6


class TestResistenza:
    def test_formula(self) -> None:
        stats = make_stats(for_=8, des=6)
        assert compute_resistenza(stats) == (8 + 6) // 2  # 7

    def test_rounding_down(self) -> None:
        stats = make_stats(for_=7, des=6)
        assert compute_resistenza(stats) == (7 + 6) // 2  # 6


class TestAbilityBudget:
    def test_int_higher_than_vol(self) -> None:
        stats = make_stats(int_=10, vol=6)
        assert initial_ability_budget(stats) == 10 // 2  # 5

    def test_vol_higher_than_int(self) -> None:
        stats = make_stats(int_=6, vol=10)
        assert initial_ability_budget(stats) == 10 // 2  # 5

    def test_equal_stats(self) -> None:
        stats = make_stats(int_=8, vol=8)
        assert initial_ability_budget(stats) == 8 // 2  # 4
