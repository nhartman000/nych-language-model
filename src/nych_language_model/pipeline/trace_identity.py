"""Builder 3 candidate: English word-skeleton derivation.

This module implements only the derived suffix/display component. It does not
create the final trace ID: SHA-256 material, occurrence identity, separators,
and domain binding remain owner decisions. Source text is never modified.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Collection

_ENGLISH_VOWELS = frozenset("aeiou")  # y is retained as a consonant in V1.
_ENGLISH_CONSONANTS = frozenset("bcdfghjklmnpqrstvwxyz")


def accent_fold_english_suffix(word: str) -> str:
    """Return the English consonant skeleton for one word span.

    Accent folding is applied to this derived value only. The caller's source
    string and offsets remain untouched. Vowels a/e/i/o/u are removed, y is
    retained, and adjacent repeated consonants collapse to one.
    """
    if not isinstance(word, str):
        raise TypeError("word must be str")
    if not word:
        raise ValueError("word must not be empty")

    decomposed = unicodedata.normalize("NFKD", word).lower()
    ascii_word: list[str] = []
    for ch in decomposed:
        if unicodedata.combining(ch):
            continue
        if ch.isascii() and ch.isalnum():
            ascii_word.append(ch)
            continue
        # Never silently drop a letter that cannot be accent-folded to ASCII.
        if ch.isalpha():
            raise ValueError(f"unsupported non-English suffix character: {ch!r}")
        # Punctuation and symbols delimit word content; they are not suffix units.
    if not ascii_word:
        raise ValueError("word must contain English letters or digits")

    skeleton: list[str] = []
    for ch in ascii_word:
        if ch in _ENGLISH_VOWELS:
            continue
        if ch in _ENGLISH_CONSONANTS and skeleton and skeleton[-1] == ch:
            continue
        skeleton.append(ch)
    return "".join(skeleton)


def emoji_skeleton_display(
    word: str,
    selected_emoji: str,
    emoji_inventory: Collection[str],
) -> str:
    """Return an inventory-validated emoji plus the word's skeleton.

    The inventory is the authority for allowed emoji graphemes. Runtime code
    never asks an LLM to select a domain emoji. The inventory itself must be
    curated and versioned by the caller.
    """
    if not isinstance(selected_emoji, str) or not selected_emoji:
        raise ValueError("selected_emoji must be a non-empty string")
    if not emoji_inventory:
        raise ValueError("emoji_inventory must not be empty")
    if any(not isinstance(item, str) or not item for item in emoji_inventory):
        raise ValueError("emoji_inventory entries must be non-empty strings")

    emoji = unicodedata.normalize("NFC", selected_emoji)
    allowed = {unicodedata.normalize("NFC", item) for item in emoji_inventory}
    if emoji not in allowed:
        raise ValueError("selected_emoji is not an exact approved inventory entry")

    suffix = accent_fold_english_suffix(word)
    # Keep the machine value empty for all-vowel words; use an explicit display
    # marker so the suffix's absence is visible and cannot be confused with a
    # missing delimiter or truncated result.
    return f"{emoji}_{suffix if suffix else '∅'}"
