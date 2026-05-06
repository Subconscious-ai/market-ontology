import unittest


class SeededSymphonyRepairTest(unittest.TestCase):
    def test_seeded_validation_failure_is_repaired(self):
        self.assertEqual("seeded-failure", "repaired")
