import unittest
from hashlib import sha256

from nych_language_model.pipeline.trace_identity import (
    accent_fold_english_suffix,
    emoji_skeleton_display,
    format_trace_id,
    word_occurrence_sha256,
)


class TraceIdentitySuffixTests(unittest.TestCase):
    def test_chinchilla_suffix(self):
        self.assertEqual(accent_fold_english_suffix("Chinchilla"), "chnchl")

    def test_attacking_suffix(self):
        self.assertEqual(accent_fold_english_suffix("Attacking"), "tckng")

    def test_accent_folded_english_words(self):
        self.assertEqual(accent_fold_english_suffix("café"), "cf")
        self.assertEqual(accent_fold_english_suffix("naïve"), "nv")

    def test_y_is_retained_as_consonant(self):
        self.assertEqual(accent_fold_english_suffix("yellow"), "ylw")

    def test_source_string_is_unchanged(self):
        source = "Café"
        before = source.encode("utf-8")
        self.assertEqual(accent_fold_english_suffix(source), "cf")
        self.assertEqual(source.encode("utf-8"), before)

    def test_empty_and_unsupported_input_rejected(self):
        with self.assertRaises(ValueError):
            accent_fold_english_suffix("")
        with self.assertRaises(ValueError):
            accent_fold_english_suffix("東京")

    def test_unfoldable_latin_letters_fail_closed(self):
        for word in ("æther", "cœur", "smørrebrød", "Łódź"):
            with self.subTest(word=word), self.assertRaisesRegex(
                ValueError, "unsupported non-English suffix character"
            ):
                accent_fold_english_suffix(word)

    def test_all_vowel_word_has_empty_structured_suffix_and_visible_marker(self):
        self.assertEqual(accent_fold_english_suffix("aeiou"), "")
        self.assertEqual(emoji_skeleton_display("aeiou", "🦫", ("🦫",)), "🦫_∅")

    def test_exact_inventory_emoji_required(self):
        inventory = ("🦫", "⚔️")
        self.assertEqual(emoji_skeleton_display("Chinchilla", "🦫", inventory), "🦫_chnchl")
        with self.assertRaises(ValueError):
            emoji_skeleton_display("Chinchilla", "🦫⚔️", inventory)
        with self.assertRaises(ValueError):
            emoji_skeleton_display("Chinchilla", "🦫🏻", inventory)

    def test_occurrence_hash_matches_versioned_binary_contract(self):
        source_digest = "ab" * 32
        payload = (
            b"NYCH-WORD-ID\x00v1\x00"
            + bytes.fromhex(source_digest)
            + (3).to_bytes(8, "big")
            + (12).to_bytes(8, "big")
            + (21).to_bytes(8, "big")
        )
        expected = sha256(payload).hexdigest()
        actual = word_occurrence_sha256(source_digest, 3, 12, 21)
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 64)
        self.assertEqual(actual, word_occurrence_sha256(source_digest.upper(), 3, 12, 21))

    def test_occurrence_hash_changes_for_occurrence_and_span(self):
        digest = "ab" * 32
        baseline = word_occurrence_sha256(digest, 0, 0, 4)
        self.assertNotEqual(baseline, word_occurrence_sha256(digest, 1, 0, 4))
        self.assertNotEqual(baseline, word_occurrence_sha256(digest, 0, 1, 5))
        self.assertNotEqual(baseline, word_occurrence_sha256("cd" * 32, 0, 0, 4))

    def test_occurrence_hash_validates_digest_and_byte_span(self):
        valid = "ab" * 32
        with self.assertRaises(ValueError):
            word_occurrence_sha256("not-a-digest", 0, 0, 1)
        with self.assertRaises(ValueError):
            word_occurrence_sha256(valid, 0, 2, 2)
        with self.assertRaises(ValueError):
            word_occurrence_sha256(valid, -1, 0, 1)
        with self.assertRaises(TypeError):
            word_occurrence_sha256(valid, True, 0, 1)

    def test_canonical_trace_id_format(self):
        digest = "a1" * 32
        self.assertEqual(format_trace_id(digest, "chnchl"), f"sha256:{digest}_chnchl")
        self.assertEqual(format_trace_id(digest, ""), f"sha256:{digest}_∅")

    def test_trace_id_format_rejects_noncanonical_fields(self):
        with self.assertRaises(ValueError):
            format_trace_id("A1" * 32, "chnchl")
        with self.assertRaises(ValueError):
            format_trace_id("a1" * 32, "bad_suffix")
        with self.assertRaises(ValueError):
            format_trace_id("a1" * 32, "∅")


if __name__ == "__main__":
    unittest.main()
