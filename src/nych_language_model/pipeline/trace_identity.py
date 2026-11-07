"""Builder 3 candidate: word-occurrence digest and English suffix derivation.

This module computes the approved SHA-256 material and the derived suffix/display
component. Final ID serialization and domain binding remain separate decisions.
Source text is never modified or retained by these functions.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Collection
from hashlib import sha256

_ENGLISH_VOWELS = frozenset("aeiou")  # y is retained as a consonant in V1.
_ENGLISH_CONSONANTS = frozenset("bcdfghjklmnpqrstvwxyz")
_WORD_ID_TAG = b"NYCH-WORD-ID\x00v1\x00"
_UINT64_MAX = (1 << 64) - 1


def word_occurrence_sha256(
    source_sha256_hex: str,
    occurrence_index: int,
    byte_start: int,
    byte_end: int,
) -> str:
    """Hash a word occurrence from source digest and its exact byte position.

    The source digest must be B1's SHA-256 of the exact UTF-8 input. Occurrence
    indexes are zero-based; byte offsets are source-relative, start-inclusive,
    and end-exclusive. The version tag, 32-byte digest, and three fixed-width
    unsigned 64-bit big-endian integers form an unambiguous payload.
    """
    if not isinstance(source_sha256_hex, str) or len(source_sha256_hex) != 64:
        raise ValueError("source_sha256_hex must contain exactly 64 hex characters")
    try:
        source_digest = bytes.fromhex(source_sha256_hex)
    except ValueError as exc:
        raise ValueError("source_sha256_hex must contain exactly 64 hex characters") from exc
    if len(source_digest) != 32:
        raise ValueError("source_sha256_hex must contain exactly 64 hex characters")

    values = (occurrence_index, byte_start, byte_end)
    names = ("occurrence_index", "byte_start", "byte_end")
    for name, value in zip(names, values, strict=True):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value < 0 or value > _UINT64_MAX:
            raise ValueError(f"{name} must fit an unsigned 64-bit integer")
    if byte_end <= byte_start:
        raise ValueError("byte_end must be greater than byte_start")

    payload = (
        _WORD_ID_TAG
        + source_digest
        + occurrence_index.to_bytes(8, "big")
        + byte_start.to_bytes(8, "big")
        + byte_end.to_bytes(8, "big")
    )
    return sha256(payload).hexdigest()


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
