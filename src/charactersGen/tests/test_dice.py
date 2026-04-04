"""Test per il motore dadi."""

import random
import pytest
from app.core.dice import (
    roll_nd,
    roll_advantage,
    roll_disadvantage,
    roll_1d20,
    skill_check,
)


def make_rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


class TestRollNd:
    def test_output_range(self) -> None:
        rng = make_rng()
        for _ in range(100):
            result = roll_nd(3, 4, rng)
            assert 3 <= result.total <= 12
            assert len(result.rolls) == 3

    def test_single_die(self) -> None:
        rng = make_rng()
        for _ in range(50):
            result = roll_nd(1, 6, rng)
            assert 1 <= result.total <= 6

    def test_total_equals_sum(self) -> None:
        rng = make_rng()
        result = roll_nd(4, 6, rng)
        assert result.total == sum(result.rolls)

    def test_kept_equals_total_for_normal_roll(self) -> None:
        rng = make_rng()
        result = roll_nd(3, 4, rng)
        assert result.kept == result.total


class TestAdvantage:
    def test_kept_is_max(self) -> None:
        rng = make_rng()
        for _ in range(50):
            result = roll_advantage(20, rng)
            assert result.kept == max(result.rolls)
            assert len(result.rolls) == 2

    def test_range(self) -> None:
        rng = make_rng()
        for _ in range(50):
            result = roll_advantage(20, rng)
            assert 1 <= result.kept <= 20


class TestDisadvantage:
    def test_kept_is_min(self) -> None:
        rng = make_rng()
        for _ in range(50):
            result = roll_disadvantage(20, rng)
            assert result.kept == min(result.rolls)
            assert len(result.rolls) == 2

    def test_range(self) -> None:
        rng = make_rng()
        for _ in range(50):
            result = roll_disadvantage(20, rng)
            assert 1 <= result.kept <= 20


class TestSkillCheck:
    def test_competent_roll(self) -> None:
        rng = make_rng()
        dice, final = skill_check(characteristic=8, grades=2, bonus=0, rng=rng)
        # Final = dado (1-20) + 8 + 2 = 11-30
        assert 11 <= final <= 30

    def test_non_competent_uses_half_stat(self) -> None:
        rng = make_rng(1)
        # Non competente: usa caratteristica//2
        dice, final = skill_check(characteristic=8, grades=0, rng=rng)
        # Final = dado minore (1-20) + 4
        assert 5 <= final <= 24

    def test_advantage(self) -> None:
        rng = make_rng()
        dice, _ = skill_check(characteristic=5, grades=1, advantage=True, rng=rng)
        assert dice.kept == max(dice.rolls)

    def test_disadvantage(self) -> None:
        rng = make_rng()
        dice, _ = skill_check(characteristic=5, grades=1, disadvantage=True, rng=rng)
        assert dice.kept == min(dice.rolls)
