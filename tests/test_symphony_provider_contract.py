import json
import unittest
from pathlib import Path


class SymphonyProviderContractTest(unittest.TestCase):
    def test_provider_contract_marker_is_stable(self):
        marker_path = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "symphony_provider_contract.json"
        )

        self.assertTrue(marker_path.exists(), f"{marker_path} must exist")
        marker = json.loads(marker_path.read_text(encoding="utf-8"))

        self.assertEqual(
            {
                "contract_name": "symphony-dependency-chain-provider",
                "provider_repository": "market-ontology",
                "provider_issue": "BEC-1812",
                "provider_contract_version": "market-ontology-provider-proof-1",
                "product_behavior_change": False,
            },
            marker,
        )


if __name__ == "__main__":
    unittest.main()
