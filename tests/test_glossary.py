"""Tests for glossary display helpers."""
import unittest


class TestNormalizeGlossaryTerm(unittest.TestCase):
    def test_trims_leading_and_trailing_whitespace(self):
        from poc_v1.ontology.glossary import normalize_glossary_term

        self.assertEqual(
            normalize_glossary_term("  Market transition  "),
            "Market transition",
        )

    def test_collapses_repeated_spaces(self):
        from poc_v1.ontology.glossary import normalize_glossary_term

        self.assertEqual(
            normalize_glossary_term("Market    transition"),
            "Market transition",
        )

    def test_collapses_tabs_and_newlines(self):
        from poc_v1.ontology.glossary import normalize_glossary_term

        self.assertEqual(
            normalize_glossary_term("Market\ttransition\nstage"),
            "Market transition stage",
        )

    def test_already_clean_term_is_unchanged(self):
        from poc_v1.ontology.glossary import normalize_glossary_term

        self.assertEqual(
            normalize_glossary_term("Market transition"),
            "Market transition",
        )


if __name__ == "__main__":
    unittest.main()
