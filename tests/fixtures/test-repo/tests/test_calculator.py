"""Tests for calculator module."""

from src.calculator import add, subtract


def test_add() -> None:
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract() -> None:
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5
    assert subtract(10, 10) == 0
