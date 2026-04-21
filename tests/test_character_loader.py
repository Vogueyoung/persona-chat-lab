from __future__ import annotations

from app.services.character_loader import get_character, list_characters


def test_list_contains_three_personas():
    ids = {c.id for c in list_characters()}
    assert ids == {"aria_knight", "nori_librarian", "zen_hacker"}


def test_characters_have_distinct_tones(aria, nori, zen):
    # The whole point of having three is to exercise different tone knobs.
    formalities = {aria.tone.formality, nori.tone.formality, zen.tone.formality}
    assert formalities == {"high", "mid", "low"}


def test_required_fields_populated(aria):
    assert aria.name
    assert aria.backstory
    assert aria.personality
    assert aria.speaking_style
    assert aria.example_dialogues  # few-shot matters for persona stickiness


def test_lookup_missing_raises():
    import pytest

    from app.services.character_loader import CharacterNotFoundError

    with pytest.raises(CharacterNotFoundError):
        get_character("does_not_exist")
