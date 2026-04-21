"""Shared test fixtures."""

from __future__ import annotations

import pytest

from app.services.character_loader import get_character


@pytest.fixture
def aria():
    return get_character("aria_knight")


@pytest.fixture
def nori():
    return get_character("nori_librarian")


@pytest.fixture
def zen():
    return get_character("zen_hacker")
