#!/usr/bin/env python3
"""Regression checks for fail-closed integration evidence gate."""
import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).with_name("verify_mt5_integration.py")
spec = importlib.util.spec_from_file_location("mt5_gate", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class IntegrationEvidenceTests(unittest.TestCase):
    def test_empty_evidence_fails_closed(self):
        result = gate.verify({})
        self.assertFalse(result["ready"])
        self.assertEqual(set(result["missing"]), set(gate.REQUIRED))

    def test_partial_evidence_cannot_claim_signed_apk(self):
        result = gate.verify({
            "chart_host_class": "ChartSurface",
            "chart_host_method": "setChartId",
            "verified_parent_type": "FrameLayout",
        })
        self.assertFalse(result["ready"])
        self.assertIn("injection_callsite", result["missing"])
        self.assertIn("signed_apk", result["missing"])

    def test_all_evidence_fields_pass_structural_gate_only(self):
        report = {key: "verified-by-external-audit" for key in gate.REQUIRED}
        result = gate.verify(report)
        self.assertTrue(result["ready"])
        self.assertEqual(result["missing"], [])

if __name__ == "__main__":
    unittest.main()
