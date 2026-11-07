import unittest

from nych_language_model.pipeline.trace_identity import (
    accent_fold_english_suffix,
    emoji_skeleton_display,
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


if __name__ == "__main__":
    unittest.main()
