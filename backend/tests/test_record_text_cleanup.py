import unittest

from app.record.text_cleanup import clean_record_transcript, preserve_draft_prefix


class RecordTextCleanupTests(unittest.TestCase):
    def test_removes_known_trailing_whisper_hallucination(self) -> None:
        text, removed = clean_record_transcript("Demat deoc'h. Pelec’h ar bloaz-mañ.")
        self.assertEqual(text, "Demat deoc'h")
        self.assertEqual(removed, ["Pelec’h ar bloaz-mañ."])

    def test_keeps_same_words_inside_real_transcript(self) -> None:
        source = "Pelec'h ar bloaz-mañ e vo graet. Demat deoc'h."
        text, removed = clean_record_transcript(source)
        self.assertEqual(text, source)
        self.assertEqual(removed, [])

    def test_removes_repeated_trailing_variants(self) -> None:
        text, removed = clean_record_transcript("Test. pelec'h ar bloaz man! Pelec’h ar bloaz-mañ")
        self.assertEqual(text, "Test")
        self.assertEqual(len(removed), 2)

    def test_removes_new_city_question_hallucination(self) -> None:
        text, removed = clean_record_transcript("eo an amzer hiziv. Pelec'h em eus ar c'hêr ?")
        self.assertEqual(text, "eo an amzer hiziv")
        self.assertEqual(len(removed), 1)

    def test_removes_unknown_pelec_h_variant_without_separator(self) -> None:
        text, removed = clean_record_transcript("brav eo an amzer hiziv Pelec'h emañ an ti nevez eta?")
        self.assertEqual(text, "brav eo an amzer hiziv")
        self.assertEqual(removed, ["Pelec'h emañ an ti nevez eta?"])

    def test_keeps_a_real_sentence_that_starts_with_pelec_h(self) -> None:
        source = "Pelec'h emañ an ti nevez? Demat deoc'h."
        text, removed = clean_record_transcript(source)
        self.assertEqual(text, source)
        self.assertEqual(removed, [])

    def test_preserves_word_missing_at_start_of_whisper(self) -> None:
        text, preserved = preserve_draft_prefix("brav eo an amzer hiziv", "eo an amzer hiziv")
        self.assertEqual(text, "brav eo an amzer hiziv")
        self.assertTrue(preserved)

    def test_does_not_merge_unrelated_versions(self) -> None:
        text, preserved = preserve_draft_prefix("demat dit", "penaos emañ kont")
        self.assertEqual(text, "penaos emañ kont")
        self.assertFalse(preserved)


if __name__ == "__main__":
    unittest.main()
