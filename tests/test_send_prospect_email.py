import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test")

from gtm_agent import gtm_agent


class SendProspectEmailTests(TestCase):
    def send_email(self, prospect):
        return gtm_agent.send_prospect_email.func(
            prospect,
            "Subject",
            "Body",
            SimpleNamespace(config={}),
            from_rep={"email": "rep@example.com", "name": "Rep"},
        )

    @patch("gtm_agent.gtm_agent.uuid.uuid4")
    @patch("gtm_agent.gtm_agent.data_service.get_prospect_record")
    def test_disqualified_prospect_is_blocked_without_generating_message_id(
        self, get_prospect_record, uuid4
    ):
        get_prospect_record.return_value = {"disqualified": True}

        result = self.send_email({"prospect_id": "LEAD-1", "email": "lead@example.com"})

        self.assertEqual(result["status"], "blocked")
        self.assertIn("disqualified", result["error"])
        self.assertIn("not sent", result["error"])
        self.assertNotIn("message_id", result)
        get_prospect_record.assert_called_once_with("LEAD-1")
        uuid4.assert_not_called()

    @patch("gtm_agent.gtm_agent.uuid.uuid4")
    @patch("gtm_agent.gtm_agent.data_service.get_prospect_record")
    def test_missing_record_is_blocked_without_generating_message_id(
        self, get_prospect_record, uuid4
    ):
        get_prospect_record.return_value = None

        result = self.send_email({"prospect_id": "LEAD-MISSING", "email": "lead@example.com"})

        self.assertEqual(result["status"], "blocked")
        self.assertIn("not found", result["error"])
        self.assertNotIn("disqualified", result["error"])
        self.assertIn("not sent", result["error"])
        self.assertNotIn("message_id", result)
        get_prospect_record.assert_called_once_with("LEAD-MISSING")
        uuid4.assert_not_called()

    @patch("gtm_agent.gtm_agent.uuid.uuid4", return_value=SimpleNamespace(hex="123456789abc"))
    @patch("gtm_agent.gtm_agent.data_service.get_prospect_record")
    def test_qualified_prospect_is_sent(self, get_prospect_record, uuid4):
        get_prospect_record.return_value = {"disqualified": False}

        result = self.send_email({"prospect_id": "LEAD-1", "email": "lead@example.com"})

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["message_id"], "msg-123456789abc")
        self.assertEqual(result["to"], "lead@example.com")
        uuid4.assert_called_once()

    def test_prompt_requires_disqualification_check_and_accurate_send_reporting(self):
        self.assertIn(
            "Check the disqualified flag returned by get_prospect",
            gtm_agent.SYSTEM_PROMPT,
        )
        self.assertIn("never email a disqualified prospect", gtm_agent.SYSTEM_PROMPT)
        self.assertIn(
            "Report blocked or failed send_prospect_email results accurately",
            gtm_agent.SYSTEM_PROMPT,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
