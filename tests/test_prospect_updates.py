import copy
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test")

from gtm_agent import data_service
from gtm_agent import gtm_agent
from gtm_agent.gtm_records import OFFERINGS, PROSPECTS


class ProspectUpdateTests(unittest.TestCase):
    prospect_id = "LEAD-39002"

    def setUp(self):
        os.environ["LANGSMITH_TRACING"] = "false"
        self.original_record = copy.deepcopy(PROSPECTS[self.prospect_id])
        self.original_profile = data_service._PROFILES.get(self.prospect_id)
        self.had_profile = self.prospect_id in data_service._PROFILES

    def tearDown(self):
        PROSPECTS[self.prospect_id] = self.original_record
        if self.had_profile:
            data_service._PROFILES[self.prospect_id] = self.original_profile
        else:
            data_service._PROFILES.pop(self.prospect_id, None)

    def test_update_persists_technology_to_source_record(self):
        result = data_service.update_prospect_info(self.prospect_id, "Terraform")

        self.assertTrue(result["updated"])
        self.assertIn("Terraform", data_service.fetch_tech_stack(self.prospect_id))

    def test_profile_rebuild_uses_updated_technology(self):
        gtm_agent.build_prospect_profile.func(self.prospect_id)

        data_service.update_prospect_info(self.prospect_id, "Terraform")
        rebuilt = gtm_agent.build_prospect_profile.func(self.prospect_id)

        self.assertIn("Terraform", rebuilt["prospect_profile"]["tech_stack"])

    def test_missing_prospect_does_not_report_success(self):
        result = data_service.update_prospect_info("LEAD-MISSING", "Terraform")

        self.assertFalse(result["updated"])
        self.assertFalse(result["found"])
        self.assertNotIn("tech_stack", result)

    def test_score_uses_saved_technology_after_update(self):
        stale_profile = {
            "prospect_id": self.prospect_id,
            "tech_stack": list(data_service.fetch_tech_stack(self.prospect_id)),
        }
        data_service.update_prospect_info(self.prospect_id, "Terraform")
        score = SimpleNamespace(model_dump=lambda: {"score": 90})

        with patch.object(gtm_agent, "_scoring_llm") as scoring_llm:
            scoring_llm.invoke.return_value = score
            gtm_agent.score_prospect.func(
                stale_profile, OFFERINGS["OFFER-10004"]
            )

        scoring_request = scoring_llm.invoke.call_args.args[0][1]["content"]
        self.assertIn('"Terraform"', scoring_request)


if __name__ == "__main__":
    unittest.main()
