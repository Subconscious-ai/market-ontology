import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "poc_v1" / "contracts"


def load_contract(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def load_example(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / "examples" / name).read_text(encoding="utf-8"))


def validate(instance: dict, schema_name: str) -> list[str]:
    return [error.message for error in validation_errors(instance, schema_name)]


def validation_errors(instance: dict, schema_name: str):
    schema = load_contract(schema_name)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error
        for error in sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    ]


class WandbOntologyLoopContractTest(unittest.TestCase):
    def test_wandb_loop_examples_validate(self):
        examples = {
            "experiment_run_mapping.wandb.valid.json": "experiment_run_mapping.schema.json",
            "normalized_experiment_results.wandb.valid.json": "normalized_experiment_results.schema.json",
        }

        for example_name, schema_name in examples.items():
            with self.subTest(example=example_name):
                example = load_example(example_name)
                self.assertEqual([], validate(example, schema_name))

    def test_experiment_context_projects_dependent_variable_and_trait_levels_from_ontology(self):
        context = {
            "experiment_context_version": "1.1.0",
            "ontology_snapshot_hash": "sha256:telemedicine-demo",
            "generated_at": "2026-05-05T14:35:58Z",
            "market": {
                "id": "market_us_telemedicine_2026",
                "name": "US telemedicine market",
                "period": "2026",
            },
            "transition": {
                "id": "transition_patient_prefers_telemedicine",
                "name": "Patient prefers telemedicine",
                "from_stage": "activation",
                "to_stage": "retention",
            },
            "dependent_variable": {
                "target_behavior": "patient preference for telemedicine services over in-person visits",
                "respondent_prompt": (
                    "Please indicate which healthcare provider you would choose "
                    "for your routine check-ups."
                ),
            },
            "stakeholder_archetypes": [
                {
                    "id": "persona_us_routine_checkup_patient",
                    "name": "US routine check-up patient",
                    "archetype_type": "customer",
                    "trait_levels": [
                        {
                            "trait_id": "trait_health_anxiety_sensitivity",
                            "trait_name": "Health Anxiety Sensitivity",
                            "trait_level_id": "trait_level_health_anxiety_medium",
                            "trait_level_label": "Medium",
                            "role": "effect_modifier",
                        }
                    ],
                }
            ],
            "offering": {
                "id": "offering_telemedicine_service",
                "name": "Telemedicine service",
                "company_name": "Example Health",
                "attributes": [
                    {
                        "id": "attr_app_access_speed",
                        "name": "App Access Speed",
                        "data_type": "categorical",
                        "levels": [
                            {
                                "id": "attr_level_app_access_0_2s",
                                "value": "0-2s Response Time",
                                "label": "0-2s Response Time",
                                "is_status_quo": False,
                            },
                            {
                                "id": "attr_level_app_access_2_5s",
                                "value": "2-5s Response Time",
                                "label": "2-5s Response Time",
                                "is_status_quo": True,
                            },
                        ],
                    }
                ],
            },
        }

        self.assertEqual([], validate(context, "experiment_context.schema.json"))

        duplicated_transition_id = json.loads(json.dumps(context))
        duplicated_transition_id["dependent_variable"][
            "transition_id"
        ] = "transition_patient_prefers_telemedicine"
        self.assertTrue(
            any(
                "Additional properties" in error
                for error in validate(
                    duplicated_transition_id,
                    "experiment_context.schema.json",
                )
            )
        )

        missing_dependent_variable = dict(context)
        missing_dependent_variable.pop("dependent_variable")
        self.assertTrue(
            any(
                "'dependent_variable' is a required property" in error
                for error in validate(
                    missing_dependent_variable,
                    "experiment_context.schema.json",
                )
            )
        )

        loose_persona = json.loads(json.dumps(context))
        loose_persona["stakeholder_archetypes"][0].pop("trait_levels")
        self.assertTrue(
            any(
                "'trait_levels' is a required property" in error
                for error in validate(loose_persona, "experiment_context.schema.json")
            )
        )

    def test_mapping_requires_ontology_inputs_before_wandb_run_local_ids(self):
        mapping = {
            "experiment_run_mapping_version": "1.0.0",
            "ontology_snapshot_hash": "sha256:telemedicine-demo",
            "experiment_run": {
                "experiment_run_id": "experiment_run_reaction_20260505",
                "super_ego_run_id": None,
                "wandb_entity": "why-earth",
                "wandb_project": "dev-subconscious-ai",
                "wandb_run_id": "e467562c-8b76-451a-9228-d28fbed927e5",
                "wandb_run_name": "reaction-26-05-05-14-35-57-804",
            },
            "experiment_inputs": {
                "dependent_variable": {
                    "ontology_ref": {
                        "ontology_node_type": "Transition",
                        "ontology_node_id": "transition_patient_prefers_telemedicine",
                    },
                    "source_fields": [
                        "experiment_definition.respondent_dependent_variable",
                        "experiment_definition.target_behavior",
                    ],
                    "target_behavior_text": "patient preference for telemedicine services over in-person visits",
                    "respondent_dependent_variable_text": (
                        "Please read the descriptions of healthcare options carefully. "
                        "Then, please indicate which healthcare provider you would choose "
                        "for your routine check-ups."
                    ),
                },
                "persona": {
                    "ontology_ref": {
                        "ontology_node_type": "StakeholderArchetype",
                        "ontology_node_id": "persona_us_routine_checkup_patient",
                    },
                    "source_fields": [
                        "experiment_definition.target_population",
                        "calculations.Ind_Est_2.HB_Data.Demographics",
                    ],
                    "trait_levels": [
                        {
                            "trait": {
                                "ontology_node_type": "Trait",
                                "ontology_node_id": "trait_health_anxiety_sensitivity",
                            },
                            "trait_level": {
                                "ontology_node_type": "TraitLevel",
                                "ontology_node_id": "trait_level_health_anxiety_medium",
                            },
                            "role": "effect_modifier",
                            "observed_column": "Health Anxiety Sensitivity",
                            "run_local_value": "Medium",
                            "label": "Health Anxiety Sensitivity: Medium",
                        }
                    ],
                },
                "treatments": [
                    {
                        "attribute": {
                            "ontology_node_type": "Attribute",
                            "ontology_node_id": "attr_app_access_speed",
                        },
                        "run_local_attribute_id": 0,
                        "attribute_text": "App Access Speed",
                        "levels": [
                            {
                                "attribute_level": {
                                    "ontology_node_type": "AttributeLevel",
                                    "ontology_node_id": "attr_level_app_access_0_2s",
                                },
                                "run_local_level_id": 2,
                                "level_text": "0-2s Response Time",
                                "is_base_level": False,
                            }
                        ],
                    }
                ],
                "context": [
                    {
                        "ontology_node_type": "Market",
                        "ontology_node_id": "market_us_telemedicine_2026",
                    }
                ],
            },
            "wandb_artifacts": [
                {
                    "entity": "why-earth",
                    "project": "dev-subconscious-ai",
                    "run_id": "e467562c-8b76-451a-9228-d28fbed927e5",
                    "name": "experiment_beta_amce_reaction-26-05-05-14-35-57-804",
                    "type": "analytics_output",
                    "version": "v0",
                    "digest": "98450ba043482ceb54ddc4d0c9401a00",
                    "aliases": ["latest"],
                    "files": [
                        {
                            "path": "amce_reaction-26-05-05-14-35-57-804.json",
                            "md5": "x4CO/bPQE94gsDrD5rWh0Q==",
                            "size_bytes": 8525,
                        }
                    ],
                }
            ],
            "ontology_mappings": [],
            "attribute_mappings": [
                {
                    "ontology_attribute_id": "attr_app_access_speed",
                    "super_ego_attribute_id": 0,
                    "attribute_text": "App Access Speed",
                }
            ],
            "level_mappings": [
                {
                    "ontology_attribute_id": "attr_app_access_speed",
                    "ontology_attribute_level_id": "attr_level_app_access_0_2s",
                    "super_ego_attribute_id": 0,
                    "super_ego_level_id": 2,
                    "level_text": "0-2s Response Time",
                    "match_confidence": 1.0,
                }
            ],
        }

        self.assertEqual([], validate(mapping, "experiment_run_mapping.schema.json"))

    def test_mapping_rejects_wrong_ontology_node_types_for_structural_inputs(self):
        mapping = load_example("experiment_run_mapping.wandb.valid.json")

        wrong_outcome = json.loads(json.dumps(mapping))
        wrong_outcome["experiment_inputs"]["dependent_variable"]["ontology_ref"][
            "ontology_node_type"
        ] = "Market"
        self.assert_const_error(
            wrong_outcome,
            ["experiment_inputs", "dependent_variable", "ontology_ref", "ontology_node_type"],
            "Transition",
        )

        wrong_persona = json.loads(json.dumps(mapping))
        wrong_persona["experiment_inputs"]["persona"]["ontology_ref"][
            "ontology_node_type"
        ] = "Trait"
        self.assert_const_error(
            wrong_persona,
            ["experiment_inputs", "persona", "ontology_ref", "ontology_node_type"],
            "StakeholderArchetype",
        )

        wrong_treatment = json.loads(json.dumps(mapping))
        wrong_treatment["experiment_inputs"]["treatments"][0]["attribute"][
            "ontology_node_type"
        ] = "Trait"
        self.assert_const_error(
            wrong_treatment,
            ["experiment_inputs", "treatments", 0, "attribute", "ontology_node_type"],
            "Attribute",
        )

        wrong_level = json.loads(json.dumps(mapping))
        wrong_level["experiment_inputs"]["treatments"][0]["levels"][0][
            "attribute_level"
        ]["ontology_node_type"] = "Attribute"
        self.assert_const_error(
            wrong_level,
            [
                "experiment_inputs",
                "treatments",
                0,
                "levels",
                0,
                "attribute_level",
                "ontology_node_type",
            ],
            "AttributeLevel",
        )

    def assert_const_error(self, payload: dict, path: list, expected_value: str):
        errors = validation_errors(payload, "experiment_run_mapping.schema.json")
        self.assertTrue(
            any(
                list(error.absolute_path) == path
                and error.validator == "const"
                and error.validator_value == expected_value
                for error in errors
            ),
            [error.message for error in errors],
        )

    def test_mapping_rejects_run_local_treatments_without_ontology_refs(self):
        mapping = {
            "experiment_run_mapping_version": "1.0.0",
            "ontology_snapshot_hash": "sha256:telemedicine-demo",
            "experiment_run": {"experiment_run_id": "experiment_run_reaction_20260505"},
            "experiment_inputs": {
                "dependent_variable": {
                    "ontology_ref": {
                        "ontology_node_type": "Transition",
                        "ontology_node_id": "transition_patient_prefers_telemedicine",
                    }
                },
                "persona": {
                    "ontology_ref": {
                        "ontology_node_type": "StakeholderArchetype",
                        "ontology_node_id": "persona_us_routine_checkup_patient",
                    },
                    "trait_levels": [],
                },
                "treatments": [
                    {
                        "run_local_attribute_id": 0,
                        "attribute_text": "App Access Speed",
                        "levels": [],
                    }
                ],
            },
            "wandb_artifacts": [],
            "ontology_mappings": [],
        }

        errors = validate(mapping, "experiment_run_mapping.schema.json")

        self.assertTrue(any("'attribute' is a required property" in error for error in errors))

    def test_normalized_results_keep_outcome_and_wandb_source_lineage(self):
        normalized = {
            "normalized_experiment_results_version": "1.0.0",
            "ontology_snapshot_hash": "sha256:telemedicine-demo",
            "experiment_run_id": "experiment_run_reaction_20260505",
            "subconscious_experiment_id": "e467562c-8b76-451a-9228-d28fbed927e5",
            "model_version": "hb-amce-importance",
            "estimated_at": "2026-05-05T14:35:58Z",
            "outcome": {
                "ontology_node_type": "Transition",
                "ontology_node_id": "transition_patient_prefers_telemedicine",
            },
            "wandb_run": {
                "entity": "why-earth",
                "project": "dev-subconscious-ai",
                "run_id": "e467562c-8b76-451a-9228-d28fbed927e5",
                "run_name": "reaction-26-05-05-14-35-57-804",
            },
            "estimates": [
                {
                    "estimate_id": "estimate_amce_app_access_0_2s",
                    "estimate_type": "amce",
                    "value": -0.55,
                    "ci_low": -0.64,
                    "ci_high": -0.4,
                    "about": {
                        "ontology_node_type": "AttributeLevel",
                        "ontology_node_id": "attr_level_app_access_0_2s",
                    },
                    "conditioned_on": [
                        {
                            "ontology_node_type": "StakeholderArchetype",
                            "ontology_node_id": "persona_us_routine_checkup_patient",
                        }
                    ],
                    "source_wandb": {
                        "artifact_name": "experiment_beta_amce_reaction-26-05-05-14-35-57-804",
                        "artifact_type": "analytics_output",
                        "artifact_version": "v0",
                        "artifact_digest": "98450ba043482ceb54ddc4d0c9401a00",
                        "file_path": "amce_reaction-26-05-05-14-35-57-804.json",
                        "row_key": "attribute_id=0;level_ids=2",
                        "run_local_attribute_id": 0,
                        "run_local_level_id": 2,
                    },
                }
            ],
        }

        self.assertEqual([], validate(normalized, "normalized_experiment_results.schema.json"))

        missing_wandb_source = json.loads(json.dumps(normalized))
        missing_wandb_source["estimates"][0].pop("source_wandb")
        self.assertTrue(
            any(
                "'source_wandb' is a required property" in error
                for error in validate(
                    missing_wandb_source,
                    "normalized_experiment_results.schema.json",
                )
            )
        )

        duplicate_lineage = json.loads(json.dumps(normalized))
        duplicate_lineage["estimates"][0]["ontology_snapshot_hash"] = "sha256:different"
        self.assertTrue(
            any(
                "Additional properties" in error
                for error in validate(
                    duplicate_lineage,
                    "normalized_experiment_results.schema.json",
                )
            )
        )

        wrong_outcome = json.loads(json.dumps(normalized))
        wrong_outcome["outcome"]["ontology_node_type"] = "Market"
        self.assertTrue(
            any(
                "'Transition' was expected" in error
                for error in validate(
                    wrong_outcome,
                    "normalized_experiment_results.schema.json",
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
