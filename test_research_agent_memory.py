import tempfile
import unittest
from pathlib import Path
from research_agent_memory import ResearchEvidence, ResearchMemory, SKILLS

class AgentMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=ResearchMemory(Path(self.tmp.name)/"memory.sqlite")
    def tearDown(self):
        self.tmp.cleanup()
    def item(self, **updates):
        data=dict(event_id="event-20261103",skill="news",summary="An official publication requiring independent review.",source_url="https://example.gov/report",published_at="2026-11-03T10:00:00Z",observed_at="2026-11-03T10:01:00Z",evidence_status="confirmed")
        data.update(updates)
        return ResearchEvidence(**data)
    def test_all_skills(self):
        self.assertEqual(len(SKILLS),7)
    def test_quarantine_forged_confirmation(self):
        self.assertTrue(self.memory.ingest(self.item()))
        self.assertEqual(self.memory.retrieve(),[])
        self.assertEqual(self.memory.review_summary()["counts"]["unverified"],1)
    def test_duplicate_is_idempotent(self):
        self.assertTrue(self.memory.ingest(self.item()))
        self.assertFalse(self.memory.ingest(self.item()))
    def test_reject_untrusted_url(self):
        with self.assertRaises(ValueError):
            self.memory.ingest(self.item(source_url="http://example.gov/report"))
    def test_no_automatic_trade_or_publish(self):
        result=self.memory.review_summary()
        self.assertFalse(result["trade"])
        self.assertFalse(result["publish"])
if __name__=="__main__":
    unittest.main()
